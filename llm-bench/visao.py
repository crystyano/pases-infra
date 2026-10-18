#!/usr/bin/env python3
"""PASES-Bench v1 — itens de VISAO com fixtures sinteticas (item 3 visao tecnica, item 4 OCR) + tarefas gerais.
Compara modelos do Ollama com as mesmas imagens, perguntas e opcoes; corrige automaticamente contra fixtures/visao/gabarito.json.
Uso: visao.py --modelos qwen3.8:27b qwen3-vl:8b [--reps 3] [--num-predict 1500]
Atencao: o qwen3-vl:8b IGNORA think=false e raciocina ~800-1500 tokens antes de responder; use --num-predict 6000 para ele.   (gere antes as fixtures com gerar_visao.py)"""
import argparse, base64, difflib, json, re, statistics, subprocess, threading, time, urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; FIX = HERE / "fixtures" / "visao"; OLLAMA = "http://127.0.0.1:11434"
GAB = json.loads((FIX / "gabarito.json").read_text(encoding="utf-8"))

TAREFAS = {
 "i4_nota_fiscal": (FIX / "i4_nota_fiscal.jpg", True,
   'Extraia os dados desta nota fiscal digitalizada. Responda SOMENTE em JSON com as chaves: "emitente", "cnpj", "data", "numero", '
   '"itens" (lista de objetos com "descricao", "quantidade", "valor_total") e "total". Copie números e textos exatamente como aparecem.'),
 "i3_armario_erro": (FIX / "i3_armario_erro.png", True,
   'Você é revisor de projetos de marcenaria. Analise este desenho técnico. Há algum erro ou inconsistência nas cotas? '
   'Responda SOMENTE em JSON: {"tem_erro": true ou false, "erro": "descrição curta do erro, com os números envolvidos, ou vazio"}.'),
 "i3_armario_controle": (FIX / "i3_armario_controle.png", True,
   'Você é revisor de projetos de marcenaria. Analise este desenho técnico. Há algum erro ou inconsistência nas cotas? '
   'Responda SOMENTE em JSON: {"tem_erro": true ou false, "erro": "descrição curta do erro, com os números envolvidos, ou vazio"}.'),
 "i3_gaveteiro_lateral": (FIX / "i3_gaveteiro_lateral.png", True,
   'Você é revisor de projetos de marcenaria. Analise este desenho técnico. Há algum erro ou inconsistência nas cotas? '
   'Responda SOMENTE em JSON: {"tem_erro": true ou false, "erro": "descrição curta do erro, com os números envolvidos, ou vazio"}.'),
 "geral_grafico": (FIX / "geral_grafico.png", True,
   'Leia o gráfico. Responda SOMENTE em JSON: {"mes_maior": "mês com mais vendas", "valor_marco": número, "valor_fevereiro": número}.'),
 "geral_contagem": (FIX / "geral_contagem.png", True,
   'Conte as formas na imagem. Responda SOMENTE em JSON: {"circulos_vermelhos": número, "quadrados_azuis": número, "triangulos_verdes": número}.'),
 "geral_texto_pt": (FIX / "geral_texto_pt.png", False,
   'Transcreva exatamente o texto da imagem, com a mesma pontuação e acentuação. Responda só com o texto, sem comentários.'),
 "geral_cena": (Path(GAB["geral_cena"]["imagem"]), True,
   'Descreva a imagem. Responda SOMENTE em JSON: {"animal": "qual animal é", "quantos_animais": número, "cenario": "tipo de paisagem", '
   '"quatro_patas": true se o animal está apoiado nas quatro patas, senão false}.'),
}

def norm(s): return re.sub(r"\s+", " ", str(s)).strip().lower()
def num(s):
    try: return float(str(s).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except Exception: return None
def jsonp(t):
    m = re.search(r"\{.*\}", t, re.S)
    try: return json.loads(m.group(0)) if m else None
    except Exception: return None

def corrigir(nome, txt):
    g = GAB[nome]
    if nome == "geral_texto_pt":
        r = difflib.SequenceMatcher(None, norm(txt), norm(g)).ratio(); return r, f"similaridade {r:.3f}"
    j = jsonp(txt)
    if j is None: return 0.0, "sem JSON"
    if nome == "i4_nota_fiscal":
        ok = [norm(j.get("emitente")) == norm(g["emitente"]), re.sub(r"\D", "", str(j.get("cnpj"))) == re.sub(r"\D", "", g["cnpj"]),
              str(j.get("data", "")).strip() == g["data"], re.sub(r"\D", "", str(j.get("numero"))) == re.sub(r"\D", "", g["numero"]),
              num(j.get("total")) == num(g["total"])]
        itens = j.get("itens") or []
        tot = [num(i.get("valor_total")) for i in itens if isinstance(i, dict)]
        ok += [num(v) in tot for v in g["itens_total"]]
        return sum(ok) / len(ok), f"{sum(ok)}/{len(ok)} campos"
    if nome.startswith("i3_"):
        te = j.get("tem_erro") in (True, "true", "sim")
        if not g["tem_erro"]: return (1.0, "sem falso alarme") if not te else (0.0, "FALSO ALARME: " + str(j.get("erro"))[:80])
        if not te: return 0.0, "não viu o erro"
        e = str(j.get("erro", ""))
        if nome == "i3_armario_erro": acerto = ("1900" in e or "1.900" in e) or ("700" in e and "1800" in e.replace(".", ""))
        else: acerto = "600" in e and ("550" in e or "profund" in e.lower())
        return (1.0, "erro certo") if acerto else (0.5, "viu erro, motivo errado: " + e[:80])
    if nome == "geral_grafico":
        ok = [norm(j.get("mes_maior"))[:3] == "mar", abs((num(j.get("valor_marco")) or -99) - 160) <= 5, abs((num(j.get("valor_fevereiro")) or -99) - 95) <= 5]
        return sum(ok) / 3, f"{sum(ok)}/3"
    if nome == "geral_contagem":
        ok = [int(num(j.get(k)) or -1) == v for k, v in g.items()]; return sum(ok) / 3, f"{sum(ok)}/3 " + json.dumps(j, ensure_ascii=False)[:80]
    if nome == "geral_cena":
        ok = [any(a in norm(j.get("animal")) for a in g["animal"]), int(num(j.get("quantos_animais")) or -1) == 1,
              any(c in norm(j.get("cenario")) for c in g["cenario"]), j.get("quatro_patas") in (True, "true")]
        return sum(ok) / 4, f"{sum(ok)}/4 animal={j.get('animal')}"

NUM_PREDICT = 1500


def chamar(modelo, prompt, img, usar_json, seed):
    b = base64.b64encode(img.read_bytes()).decode()
    corpo = {"model": modelo, "stream": False, "think": False, "messages": [{"role": "user", "content": prompt, "images": [b]}],
             "options": {"temperature": 0.2, "top_p": 0.8, "num_ctx": 16384, "num_predict": NUM_PREDICT, "seed": seed}}
    if usar_json: corpo["format"] = "json"
    t0 = time.time()
    r = json.load(urllib.request.urlopen(urllib.request.Request(OLLAMA + "/api/chat", json.dumps(corpo).encode(), {"Content-Type": "application/json"}), timeout=900))
    ev, evd = r.get("eval_count", 0), r.get("eval_duration", 1)
    return r["message"]["content"], time.time() - t0, ev / (evd / 1e9) if ev else 0, r.get("load_duration", 0) / 1e9

class VRAM(threading.Thread):
    def __init__(s): super().__init__(daemon=True); s.parar = False; s.pico = {}
    def run(s):
        while not s.parar:
            for l in subprocess.run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits", shell=True, capture_output=True, text=True).stdout.splitlines():
                i, m = [x.strip() for x in l.split(",")]; s.pico[i] = max(s.pico.get(i, 0), int(m))
            time.sleep(1)

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--modelos", nargs="+", required=True); p.add_argument("--reps", type=int, default=3); p.add_argument("--num-predict", dest="num_predict", type=int, default=1500); a = p.parse_args(); NUM_PREDICT = a.num_predict
    run = datetime.now().strftime("%Y-%m-%d_%H%M") + "_visao"; saida = HERE / "results" / run; saida.mkdir(parents=True)
    res = {"run": run, "opcoes": {"temperature": 0.2, "top_p": 0.8, "num_ctx": 16384, "think": False, "num_predict": NUM_PREDICT}, "modelos": {}}
    for m in a.modelos:
        subprocess.run(["ollama", "stop", m], capture_output=True)
        for o in a.modelos: subprocess.run(["ollama", "stop", o], capture_output=True)
        mon = VRAM(); mon.start()
        _, _, _, carga = chamar(m, "Responda apenas: ok", TAREFAS["geral_contagem"][0], False, 0)
        R = {"carga_s": round(carga, 1), "tarefas": {}}
        for nome, (img, usar_json, prompt) in TAREFAS.items():
            R["tarefas"][nome] = []
            for rep in range(1, a.reps + 1):
                txt, dt, toks, _ = chamar(m, prompt, img, usar_json, rep)
                nota, det = corrigir(nome, txt)
                (saida / f"{m.replace(':', '_')}_{nome}_rep{rep}.txt").write_text(txt, encoding="utf-8")
                R["tarefas"][nome].append({"nota": round(nota, 3), "detalhe": det, "tempo_s": round(dt, 1), "tok_s": round(toks, 1)})
                print(m, nome, rep, round(nota, 2), det, f"{dt:.1f}s", flush=True)
        mon.parar = True; R["vram_pico_mib"] = mon.pico
        R["media_por_tarefa"] = {k: round(statistics.mean(x["nota"] for x in v), 3) for k, v in R["tarefas"].items()}
        R["media_geral"] = round(statistics.mean(R["media_por_tarefa"].values()), 3)
        R["tempo_mediano_s"] = round(statistics.median(x["tempo_s"] for v in R["tarefas"].values() for x in v), 1)
        res["modelos"][m] = R
        subprocess.run(["ollama", "stop", m], capture_output=True)
    (saida / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("PRONTO", saida)
    for m, R in res["modelos"].items(): print(m, "media", R["media_geral"], R["media_por_tarefa"], "tempo mediano", R["tempo_mediano_s"], "VRAM", R["vram_pico_mib"])
