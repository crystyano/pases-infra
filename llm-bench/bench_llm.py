#!/srv/pases/llm-bench/.venv/bin/python
"""PASES-Bench v1 (LLM) com fixtures SINTETICAS - runner (Cap. 8.2 / 8.9 do manual).
Mede o modelo de codigo no Ollama contra as metas do manual: velocidade, tempo ate o 1o token (a quente), memoria e precisao.
Itens: 1 geracao de codigo | 2 refatoracao | 5 generalista PT-BR | 6 tarefa agentica com ferramentas. (Itens 3 e 4, visao: nao se aplicam a modelo so de texto.)
Uso:  bench_llm.py --validar            confere as fixtures contra as solucoes de referencia (nao chama o modelo)
      bench_llm.py [--modelo qwen-cline] [--reps 3]"""
import argparse, ast, json, os, re, shutil, statistics, subprocess, sys, tempfile, threading, time, urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixtures"
PY = str(HERE / ".venv/bin/python")
OLLAMA = "http://127.0.0.1:11434"
N_ESPERADO = {"i1": 23, "i2": 193, "i6": 12}     # testes ocultos de cada item (confirmados por --validar)
MAX_PASSOS = 20
THINK = {"off": False, "on": True}.get(os.environ.get("BENCH_THINK", ""))   # None = padrao do modelo; BENCH_THINK=off/on forca o modo de raciocinio (modelos com "thinking")


# ------------------------------------------------------------------ Ollama
def _req(path, dados):
    return urllib.request.Request(OLLAMA + path, json.dumps(dados).encode(), {"Content-Type": "application/json"})


def _think():
    return {} if THINK is None else {"think": THINK}


def gerar_stream(modelo, mensagens, opcoes):
    """/api/chat em streaming; mede o tempo ate o 1o token e a velocidade de geracao."""
    t0 = time.time(); ttft = None; partes = []; fim = {}
    with urllib.request.urlopen(_req("/api/chat", {"model": modelo, "messages": mensagens, "stream": True, "options": opcoes, **_think()}), timeout=900) as r:
        for linha in r:
            if not linha.strip():
                continue
            d = json.loads(linha)
            c = d.get("message", {}).get("content", "")
            if c and ttft is None:
                ttft = time.time() - t0
            partes.append(c)
            if d.get("done"):
                fim = d
    ev, evd = fim.get("eval_count", 0), fim.get("eval_duration", 1)
    return {"texto": "".join(partes), "ttft_s": ttft, "tokens": ev, "tok_s": ev / (evd / 1e9) if ev else 0,
            "prompt_tokens": fim.get("prompt_eval_count", 0), "total_s": time.time() - t0, "carga_s": fim.get("load_duration", 0) / 1e9}


def chat_ferramentas(modelo, mensagens, ferramentas, opcoes):
    t0 = time.time()
    with urllib.request.urlopen(_req("/api/chat", {"model": modelo, "messages": mensagens, "tools": ferramentas, "stream": False, "options": opcoes, **_think()}), timeout=900) as r:
        d = json.load(r)
    ev, evd = d.get("eval_count", 0), d.get("eval_duration", 1)
    return d["message"], {"tokens": ev, "tok_s": ev / (evd / 1e9) if ev else 0, "total_s": time.time() - t0}


def ollama_ps():
    out = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout.strip().splitlines()
    return out[1] if len(out) > 1 else ""


class Monitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True); self.parar = False; self.vram = {}; self.ram = 0.0; self.temp = 0.0; self.pot = 0.0
    def run(self):
        while not self.parar:
            tot = 0.0
            for l in subprocess.run("nvidia-smi --query-gpu=index,memory.used,temperature.gpu,power.draw --format=csv,noheader,nounits", shell=True, capture_output=True, text=True).stdout.splitlines():
                try:
                    i, m, t, p = [float(x) for x in l.split(",")]
                except ValueError:
                    continue
                self.vram[int(i)] = max(self.vram.get(int(i), 0), m); self.temp = max(self.temp, t); tot += p
            self.pot = max(self.pot, tot)
            mem = {k: int(v.split()[0]) for k, v in (l.split(":") for l in open("/proc/meminfo"))}
            self.ram = max(self.ram, (mem["MemTotal"] - mem["MemAvailable"]) / 1e6)
            time.sleep(1)


# --------------------------------------------------------------- utilitarios
def extrair_codigo(texto, marca):
    blocos = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", texto, re.S)
    if not blocos:
        return None
    com = [b for b in blocos if marca in b]
    return (com[0] if com else max(blocos, key=len)).rstrip() + "\n"


def rodar_pytest(pasta, arquivos, n_esperado):
    env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(pasta)}
    try:
        r = subprocess.run([PY, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider", *arquivos], cwd=pasta, capture_output=True, text=True, timeout=120, env=env)
        saida = (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return {"passou": 0, "total": n_esperado, "fracao": 0.0, "nota": "timeout (120 s)"}
    p = re.search(r"(\d+) passed", saida); f = re.search(r"(\d+) failed", saida); e = re.search(r"(\d+) error", saida)
    passou = int(p.group(1)) if p else 0
    return {"passou": passou, "total": n_esperado, "fracao": passou / n_esperado, "nota": saida.splitlines()[-1] if saida else "sem saida",
            "falhas": int(f.group(1)) if f else 0, "erros": int(e.group(1)) if e else 0}


def metricas_ast(codigo):
    try:
        arvore = ast.parse(codigo)
    except SyntaxError:
        return {"funcoes": 0, "maior_funcao_linhas": 0, "erro_sintaxe": True}
    fs = [n for n in ast.walk(arvore) if isinstance(n, ast.FunctionDef)]
    return {"funcoes": len(fs), "maior_funcao_linhas": max((n.end_lineno - n.lineno + 1 for n in fs), default=0)}


# --------------------------------------------------------------------- itens
def item1(modelo, opcoes, rep, saida):
    spec = (FIX / "i1_orcamento/spec.md").read_text(encoding="utf-8")
    g = gerar_stream(modelo, [{"role": "user", "content": spec}], {**opcoes, "seed": rep})
    codigo = extrair_codigo(g["texto"], "class Orcamento")
    (saida / f"i1_rep{rep}.txt").write_text(g["texto"], encoding="utf-8")
    if not codigo:
        return {"geracao": _g(g), "teste": {"passou": 0, "total": N_ESPERADO["i1"], "fracao": 0.0, "nota": "sem bloco de codigo"}}
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); (t / "orcamento.py").write_text(codigo); shutil.copy(FIX / "i1_orcamento/test_hidden.py", t)
        return {"geracao": _g(g), "teste": rodar_pytest(t, ["test_hidden.py"], N_ESPERADO["i1"])}


CFG_REFAT = {
    "i2":  {"dir": "i2_refatoracao", "arquivo": "pedido.py",   "funcao": "calcular_pedido",   "assinatura": "calcular_pedido(pedido)",   "n": 193},
    "i2b": {"dir": "i2b_parcelas",   "arquivo": "parcelas.py", "funcao": "calcular_parcelas", "assinatura": "calcular_parcelas(venda)",  "n": 241},
    "i2c": {"dir": "i2c_producao",   "arquivo": "producao.py", "funcao": "resumo_producao",   "assinatura": "resumo_producao(ordens)",   "n": 141},
}


def primeiro_erro(pasta, arquivos):
    """Causa do primeiro teste que falha (para saber SE o codigo quebra ou so se comporta diferente)."""
    env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(pasta)}
    r = subprocess.run([PY, "-m", "pytest", "-q", "-x", "--tb=line", "-p", "no:cacheprovider", *arquivos], cwd=pasta, capture_output=True, text=True, timeout=120, env=env)
    linhas = [l.strip() for l in (r.stdout + r.stderr).splitlines() if re.search(r"Error|assert|Exception", l)]
    return linhas[0][:200] if linhas else ""


def refatoracao(modelo, opcoes, rep, saida, chave="i2"):
    c = CFG_REFAT[chave]; pasta_fix = FIX / c["dir"]
    orig = (pasta_fix / c["arquivo"]).read_text(encoding="utf-8")
    prompt = ("Refatore o módulo abaixo para melhorar a legibilidade e a manutenção, SEM mudar o comportamento (mesmos resultados para as mesmas entradas, "
              f"inclusive os casos especiais e os erros). Mantenha o nome e a assinatura de `{c['assinatura']}`. Divida em funções menores com nomes claros, elimine a "
              "duplicação e use constantes ou tabelas onde fizer sentido. Responda com um único bloco ```python com o módulo completo "
              f"(arquivo `{c['arquivo']}`), sem explicações longas.\n\n```python\n" + orig + "```\n")
    g = gerar_stream(modelo, [{"role": "user", "content": prompt}], {**opcoes, "seed": rep})
    codigo = extrair_codigo(g["texto"], "def " + c["funcao"])
    (saida / f"{chave}_rep{rep}.txt").write_text(g["texto"], encoding="utf-8")
    base = metricas_ast(orig)
    if not codigo:
        return {"geracao": _g(g), "teste": {"passou": 0, "total": c["n"], "fracao": 0.0, "nota": "sem bloco de codigo"}, "ast": None, "ast_original": base, "primeiro_erro": "sem bloco de codigo"}
    with tempfile.TemporaryDirectory() as t:
        t = Path(t); (t / c["arquivo"]).write_text(codigo)
        for a in ("test_hidden.py", "casos.json"):
            shutil.copy(pasta_fix / a, t)
        res = rodar_pytest(t, ["test_hidden.py"], c["n"])
        erro = primeiro_erro(t, ["test_hidden.py"]) if res["passou"] < c["n"] else ""
    m = metricas_ast(codigo)
    m["melhorou_estrutura"] = bool(m["funcoes"] >= 3 and m["maior_funcao_linhas"] < base["maior_funcao_linhas"])
    return {"geracao": _g(g), "teste": res, "ast": m, "ast_original": base, "primeiro_erro": erro}


def item2(modelo, opcoes, rep, saida):
    return refatoracao(modelo, opcoes, rep, saida, "i2")


def _norm_num(s):
    return re.sub(r"[^0-9,.]", "", s)


def item5(modelo, opcoes, rep, saida):
    pergunta = (FIX / "i5_negocio/pergunta.md").read_text(encoding="utf-8")
    g = gerar_stream(modelo, [{"role": "user", "content": pergunta}], {**opcoes, "seed": rep})
    txt = g["texto"]; (saida / f"i5_rep{rep}.txt").write_text(txt, encoding="utf-8")
    # lucro certo = R$ 1.116,50 ; margem certa = 23,02%
    nums = [_norm_num(x) for x in re.findall(r"R?\$?\s?\d[\d.,]*\d|\d", txt)]
    lucro_ok = any(n.replace(".", "").replace(",", ".") in ("1116.5", "1116.50") or n in ("1116.5", "1116.50", "1.116,50", "1.116,5") for n in nums)
    marg = [float(n.replace(".", "").replace(",", ".")) for n in nums if re.fullmatch(r"\d{1,2}[.,]\d{1,3}", n)] + [float(n) for n in nums if re.fullmatch(r"\d{2}", n)]
    margem_ok = any(22.9 <= m <= 23.1 for m in marg)
    palavras = re.findall(r"[a-zçãõáéíóúâêô]+", txt.lower())
    pt = sum(p in {"de", "que", "o", "a", "para", "é", "em", "um", "uma", "os", "as", "do", "da", "com", "por", "lucro", "preço", "venda"} for p in palavras)
    en = sum(p in {"the", "and", "is", "of", "to", "profit", "price", "margin"} for p in palavras)
    linhas = [l for l in txt.splitlines() if l.strip()]
    return {"geracao": _g(g), "lucro_correto": lucro_ok, "margem_correta": margem_ok, "em_portugues": bool(palavras and pt / len(palavras) > 0.15 and en <= 2),
            "linhas": len(linhas), "respeitou_6_linhas": len(linhas) <= 6}


def _ferramentas():
    f = lambda nome, desc, props, req: {"type": "function", "function": {"name": nome, "description": desc, "parameters": {"type": "object", "properties": props, "required": req}}}
    return [f("list_files", "Lista os arquivos do repositório", {}, []),
            f("read_file", "Lê um arquivo do repositório", {"path": {"type": "string", "description": "caminho relativo"}}, ["path"]),
            f("write_file", "Grava (substitui) um arquivo do repositório com o conteúdo completo", {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
            f("run_tests", "Roda os testes do repositório (pytest) e devolve a saída", {}, [])]


def item6(modelo, opcoes, rep, saida):
    tarefa = (FIX / "i6_agente/tarefa.md").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as t:
        raiz = Path(t) / "repo"; shutil.copytree(FIX / "i6_agente/repo_inicial", raiz)
        def caminho(p):
            c = (raiz / str(p)).resolve()
            if raiz.resolve() not in c.parents and c != raiz.resolve():
                raise ValueError("caminho fora do repositorio")
            return c
        def executar(nome, a):
            try:
                if nome == "list_files":
                    return "\n".join(sorted(str(x.relative_to(raiz)) for x in raiz.rglob("*") if x.is_file() and "__pycache__" not in x.parts))
                if nome == "read_file":
                    return caminho(a["path"]).read_text(encoding="utf-8")
                if nome == "write_file":
                    c = caminho(a["path"]); c.parent.mkdir(parents=True, exist_ok=True); c.write_text(a["content"], encoding="utf-8"); return f"ok: {a['path']} gravado ({len(a['content'])} caracteres)"
                if nome == "run_tests":
                    env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(raiz)}
                    r = subprocess.run([PY, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=raiz, capture_output=True, text=True, timeout=60, env=env)
                    return (r.stdout + r.stderr)[-3000:]
                return f"ferramenta desconhecida: {nome}"
            except Exception as e:
                return f"ERRO: {e!r}"
        msgs = [{"role": "system", "content": "Você é um agente de programação que trabalha em um repositório Python usando as ferramentas fornecidas. Responda em português."},
                {"role": "user", "content": tarefa}]
        passos = 0; chamadas = []; tokens = 0; tempo = 0.0; terminou = False; velocidades = []
        for passos in range(1, MAX_PASSOS + 1):
            m, est = chat_ferramentas(modelo, msgs, _ferramentas(), {**opcoes, "seed": rep * 100 + passos})
            tokens += est["tokens"]; tempo += est["total_s"]
            if est["tokens"] >= 50: velocidades.append(est["tok_s"])
            msgs.append(m)
            tc = m.get("tool_calls") or []
            if not tc:
                terminou = True; break
            for c in tc:
                nome = c["function"]["name"]; args = c["function"].get("arguments") or {}
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except Exception: args = {}
                chamadas.append(nome)
                msgs.append({"role": "tool", "tool_name": nome, "content": executar(nome, args)})
        # testou depois da ultima gravacao?
        ult = max((i for i, n in enumerate(chamadas) if n == "write_file"), default=-1)
        testou_depois = any(n == "run_tests" for n in chamadas[ult + 1:]) if ult >= 0 else False
        for a in ("test_reserva.py", "test_relatorio_reserva.py"):
            shutil.copy(FIX / "i6_agente/hidden" / a, raiz)
        res = rodar_pytest(raiz, ["test_reserva.py", "test_relatorio_reserva.py"], N_ESPERADO["i6"])
        v = rodar_pytest(raiz, ["test_basico.py"], 1)   # o modelo pode ACRESCENTAR testes; so interessa se a suite visivel passa
        visiveis = {"testes": v["passou"] + v.get("falhas", 0) + v.get("erros", 0), "passou_tudo": bool(v["passou"] > 0 and v.get("falhas", 0) == 0 and v.get("erros", 0) == 0), "nota": v["nota"]}
        d = saida / f"i6_rep{rep}"; d.mkdir(exist_ok=True)
        for x in raiz.glob("*.py"):
            if not x.name.startswith("test_reserva") and x.name != "test_relatorio_reserva.py":
                shutil.copy(x, d / x.name)
        (d / "transcricao.json").write_text(json.dumps([{**m, "content": (m.get("content") or "")[:1500]} for m in msgs], ensure_ascii=False, indent=1), encoding="utf-8")
    return {"teste": res, "visiveis": visiveis, "passos": passos, "terminou": terminou, "chamadas": {n: chamadas.count(n) for n in set(chamadas)},
            "testou_antes_de_terminar": testou_depois, "tokens": tokens, "tempo_s": round(tempo, 1), "tok_s_mediana": round(statistics.median(velocidades), 1) if velocidades else 0}


def _g(g):
    return {"ttft_s": round(g["ttft_s"], 2) if g["ttft_s"] else None, "tokens": g["tokens"], "tok_s": round(g["tok_s"], 1), "prompt_tokens": g["prompt_tokens"], "total_s": round(g["total_s"], 1)}


# ---------------------------------------------------------------- validacao
def validar():
    ok = True
    def conta(pasta, arqs):
        env = {"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(pasta)}
        r = subprocess.run([PY, "-m", "pytest", "-q", "--tb=no", "-p", "no:cacheprovider", *arqs], cwd=pasta, capture_output=True, text=True, env=env)
        return r.stdout.strip().splitlines()[-1]
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        for nome, arqs, ref, n in [("i1", ["test_hidden.py"], ["i1_orcamento/reference/orcamento.py", "i1_orcamento/test_hidden.py"], N_ESPERADO["i1"])]:
            d = t / nome; d.mkdir(); [shutil.copy(FIX / r, d) for r in ref]; s = conta(d, arqs); ok &= f"{n} passed" in s; print(nome, "referencia:", s)
        d = t / "i2"; d.mkdir(); shutil.copy(FIX / "i2_refatoracao/reference/pedido_refatorado.py", d / "pedido.py"); [shutil.copy(FIX / "i2_refatoracao" / a, d) for a in ("test_hidden.py", "casos.json")]
        s = conta(d, ["test_hidden.py"]); ok &= f"{N_ESPERADO['i2']} passed" in s; print("i2 referencia:", s)
        for chave, ref in (("i2b", "parcelas_refatorado.py"), ("i2c", "producao_refatorado.py")):
            c = CFG_REFAT[chave]; d = t / chave; d.mkdir(); shutil.copy(FIX / c["dir"] / "reference" / ref, d / c["arquivo"]); [shutil.copy(FIX / c["dir"] / a, d) for a in ("test_hidden.py", "casos.json")]
            s = conta(d, ["test_hidden.py"]); ok &= f"{c['n']} passed" in s; print(chave, "referencia:", s)
        d = t / "i6"; d.mkdir(); [shutil.copy(x, d) for x in (FIX / "i6_agente/reference").glob("*.py")]; [shutil.copy(x, d) for x in (FIX / "i6_agente/hidden").glob("*.py")]
        s = conta(d, ["test_reserva.py", "test_relatorio_reserva.py"]); ok &= f"{N_ESPERADO['i6']} passed" in s; print("i6 referencia:", s)
        d = t / "i6b"; d.mkdir(); [shutil.copy(x, d) for x in (FIX / "i6_agente/repo_inicial").glob("*.py")]; [shutil.copy(x, d) for x in (FIX / "i6_agente/hidden").glob("*.py")]
        print("i6 repo inicial x ocultos (deve falhar):", conta(d, ["test_reserva.py", "test_relatorio_reserva.py"]))
    print("FIXTURES OK" if ok else "FIXTURES COM PROBLEMA"); return ok


def main_refatoracao(a, saida):
    opcoes = {"num_predict": 4096}
    subprocess.run(["ollama", "stop", a.modelo], capture_output=True); time.sleep(3)
    gerar_stream(a.modelo, [{"role": "user", "content": "Responda apenas: pronto"}], {**opcoes, "seed": 0})      # carga + aquecimento
    res = {"modelo": a.modelo, "parametros_modelfile": [l.strip() for l in subprocess.run(["ollama", "show", a.modelo, "--modelfile"], capture_output=True, text=True).stdout.splitlines() if l.startswith("PARAMETER")], "fixtures": {k: [] for k in CFG_REFAT}}
    for rep in range(1, a.reps + 1):
        for chave in CFG_REFAT:
            try:
                r = refatoracao(a.modelo, opcoes, rep, saida, chave)
            except Exception as e:
                r = {"erro": repr(e)}
            res["fixtures"][chave].append(r); t = r.get("teste", {})
            print(f"[{chave} rep{rep}] testes {t.get('passou')}/{t.get('total')} | {r.get('primeiro_erro', r.get('erro', ''))[:120]}", flush=True)
            (saida / "resultado.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    print("PRONTO:", saida / "resultado.json")


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--modelo", default="qwen-cline"); ap.add_argument("--reps", type=int, default=3); ap.add_argument("--validar", action="store_true"); ap.add_argument("--refatoracao", action="store_true", help="roda SO o item 2 (refatoracao) em todas as fixtures de refatoracao")
    a = ap.parse_args()
    if a.validar:
        sys.exit(0 if validar() else 1)
    if not validar():
        sys.exit("ABORTADO: as fixtures nao validaram")
    run = datetime.now().strftime("%Y-%m-%d_%H%M") + "_" + a.modelo.replace(":", "-") + ("_refatoracao" if a.refatoracao else ""); saida = HERE / "results" / run; saida.mkdir(parents=True, exist_ok=True)
    if a.refatoracao:
        return main_refatoracao(a, saida)
    opcoes = {"num_predict": 4096}          # demais parametros (temperature, top_k, top_p, num_ctx) vem do Modelfile do modelo
    info = subprocess.run(["ollama", "show", a.modelo, "--modelfile"], capture_output=True, text=True).stdout
    params = [l.strip() for l in info.splitlines() if l.startswith("PARAMETER")]
    subprocess.run(["ollama", "stop", a.modelo], capture_output=True); time.sleep(3)
    mon = Monitor(); mon.start()
    # carga fria + aquecimento
    w = gerar_stream(a.modelo, [{"role": "user", "content": "Responda apenas: pronto"}], {**opcoes, "seed": 0})
    carga = {"carga_s": round(w["carga_s"], 1), "primeira_resposta_s": round(w["total_s"], 1)}
    ps = ollama_ps(); print("carga fria:", carga, "| ollama ps:", ps, flush=True)
    # TTFT a quente com prompt curto
    curtos = [gerar_stream(a.modelo, [{"role": "user", "content": "Responda apenas: pronto"}], {**opcoes, "seed": s}) for s in range(1, 6)]
    ttft_curto = statistics.median(c["ttft_s"] for c in curtos if c["ttft_s"])
    print("TTFT a quente (prompt curto), mediana:", round(ttft_curto, 2), "s", flush=True)
    resultado = {"modelo": a.modelo, "run": run, "parametros_modelfile": params, "opcoes_runner": opcoes, "think": THINK, "carga_fria": carga, "ollama_ps": ps, "ttft_curto_mediana_s": round(ttft_curto, 2), "itens": {"i1": [], "i2": [], "i5": [], "i6": []}}
    for rep in range(1, a.reps + 1):
        for nome, fn in [("i1", item1), ("i2", item2), ("i5", item5), ("i6", item6)]:
            t0 = time.time()
            try:
                r = fn(a.modelo, opcoes, rep, saida)
            except Exception as e:
                r = {"erro": repr(e)}
            resultado["itens"][nome].append(r)
            t = r.get("teste", {})
            print(f"[{nome} rep{rep}] {round(time.time()-t0,1)} s |", (f"testes {t.get('passou')}/{t.get('total')}" if t else json.dumps(r, ensure_ascii=False)[:160]), flush=True)
            (saida / "resultado.json").write_text(json.dumps(resultado, indent=1, ensure_ascii=False), encoding="utf-8")
    mon.parar = True; mon.join()
    resultado["recursos"] = {"vram_pico_mib_por_gpu": mon.vram, "ram_pico_gb": round(mon.ram, 1), "temp_pico_c": mon.temp, "potencia_pico_w": round(mon.pot)}
    (saida / "resultado.json").write_text(json.dumps(resultado, indent=1, ensure_ascii=False), encoding="utf-8")
    print("PRONTO:", saida / "resultado.json")


if __name__ == "__main__":
    main()
