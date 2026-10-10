#!/srv/pases/comfyui/.venv/bin/python
"""PASES-Bench Visual v1 - runner.

Roda a suite definida em items.json, UMA geracao por vez, e grava:
  results/<run>.json      medicoes e ambiente (versionado, pequeno)
  results/<run>.md        relatorio com a ficha de avaliacao humana em branco
  /scratch/bench/<run>/   folhas de contato (nao versionado, descartavel)

Uso:
  bench.py                       suite completa (reinicia o servico = medida "a frio")
  bench.py --only I1 V1          so alguns itens
  bench.py --no-restart          nao reinicia o servico
  bench.py --dry-run             valida tudo e mostra o plano, sem gerar nada
Detalhes e criterios: Cap. 8A do manual.
"""
import argparse, hashlib, json, os, shutil, statistics, subprocess, sys, threading, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # `python -I` nao inclui a pasta do script
import ltx as _ltx
import qwen as _qwen
import flux2 as _flux2
import extend as _extend
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ITEMS = json.load(open(HERE / "items.json", encoding="utf-8"))
H = "http://127.0.0.1:8188"
OUT = Path("/scratch/comfyui/output")
INPUT = Path("/srv/pases/comfyui/input")
MODELOS = Path("/dados/modelos/comfyui")
ARQ_LTX = [
    "diffusion_models/ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", "text_encoders/gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors",
    "vae/ltx-2.5-video-vae-bf16.safetensors", "vae/ltx-2.5-audio-vae-bf16.safetensors", "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors",
]
ARQ_QWEN = [
    "diffusion_models/qwen_image_2.1_int8_convrot.safetensors", "text_encoders/qwen3vl_8b_int8_convrot.safetensors", "vae/qwen_image_2.1_vae_bf16.safetensors",
]
ARQ_QWEN2512 = [
    "diffusion_models/qwen_image_2512_fp8_e4m3fn.safetensors", "text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors", "vae/qwen_image_vae.safetensors",
]
ARQ_FLUX2 = [
    "diffusion_models/flux-2-klein-4b-fp8.safetensors", "text_encoders/qwen_3_4b_fp8_mixed.safetensors", "vae/flux2-klein-vae-apache.safetensors",
]
ARQ_MODELOS = [
    "diffusion_models/z_image_turbo_bf16.safetensors", "text_encoders/qwen_3_4b_fp8_mixed.safetensors", "vae/ae.safetensors",
    "diffusion_models/wan2.2_ti2v_5B_fp16.safetensors", "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "vae/wan2.2_vae.safetensors",
]
TEMP_ABORT = 82
GPU_ALVO = 1  # RTX 5060 Ti (ordem PCI, igual ao nvidia-smi)


def http(path, data=None):
    req = urllib.request.Request(H + path, json.dumps(data).encode() if data is not None else None,
                                 {"Content-Type": "application/json"} if data is not None else {})
    return json.load(urllib.request.urlopen(req, timeout=60))


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------- workflows
def wf_imagem(prompt, seed, prefix):
    c = ITEMS["imagem"]
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "z_image_turbo_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b_fp8_mixed.safetensors", "type": "lumina2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptySD3LatentImage", "inputs": {"width": c["largura"], "height": c["altura"], "batch_size": 1}},
        "7": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": c["shift"]}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["7", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
              "seed": seed, "steps": c["passos"], "cfg": c["cfg"], "sampler_name": c["sampler"], "scheduler": c["scheduler"], "denoise": 1}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def wf_ltx(*args, **kw):
    return _ltx.wf_ltx(*args, **kw)


def wf_video(prompt, seed, prefix, w, h, quadros, imagem_inicial=None):
    c = ITEMS["video"]
    latent = {"vae": ["3", 0], "width": w, "height": h, "length": quadros, "batch_size": 1}
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": c["negativo"]}},
        "7": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": c["shift"]}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["7", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
              "seed": seed, "steps": c["passos"], "cfg": c["cfg"], "sampler_name": c["sampler"], "scheduler": c["scheduler"], "denoise": 1}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "CreateVideo", "inputs": {"images": ["9", 0], "fps": c["fps"]}},
        "11": {"class_type": "SaveVideo", "inputs": {"video": ["10", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}},
    }
    if imagem_inicial:
        wf["12"] = {"class_type": "LoadImage", "inputs": {"image": imagem_inicial}}
        wf["13"] = {"class_type": "ImageScale", "inputs": {"image": ["12", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}}
        latent["start_image"] = ["13", 0]
    wf["6"] = {"class_type": "Wan22ImageToVideoLatent", "inputs": latent}
    return wf


# ------------------------------------------------------------------ medicao
class Monitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.parar = False
        self.vram = self.temp = self.pot = self.ram = 0.0
        self.abortou = False

    def run(self):
        while not self.parar:
            tot = 0.0
            for l in sh("nvidia-smi --query-gpu=index,memory.used,power.draw,temperature.gpu --format=csv,noheader,nounits").splitlines():
                try:
                    i, m, p, t = [float(x) for x in l.split(",")]
                except ValueError:
                    continue
                tot += p
                if int(i) == GPU_ALVO:
                    self.vram, self.temp = max(self.vram, m), max(self.temp, t)
                    if t > TEMP_ABORT and not self.abortou:
                        self.abortou = True
                        try:
                            http("/interrupt", {})
                        except Exception:
                            pass
            self.pot = max(self.pot, tot)
            mem = {k: int(v.split()[0]) for k, v in (l.split(":") for l in open("/proc/meminfo"))}
            self.ram = max(self.ram, (mem["MemTotal"] - mem["MemAvailable"]) / 1e6)
            time.sleep(0.5)


def gerar(wf, timeout_s=2400):
    mon = Monitor(); mon.start()
    t0 = time.time()
    try:
        pid = http("/prompt", {"prompt": wf})["prompt_id"]
        ok, motivo, saidas = False, "", []
        while time.time() - t0 < timeout_s:
            h = http("/history/" + pid)
            if pid in h:
                st = h[pid]["status"]
                ok = st["status_str"] == "success"
                if not ok:
                    motivo = json.dumps(st)[:400]
                for o in h[pid]["outputs"].values():
                    for k in ("images", "gifs"):
                        for f in o.get(k, []):
                            if f.get("type", "output") == "output":   # ignora previas de arquivos de ENTRADA (ex.: LoadVideo)
                                saidas.append(str(OUT / f.get("subfolder", "") / f["filename"]))
                break
            time.sleep(1)
        else:
            motivo = "timeout"
            http("/interrupt", {})
    except Exception as e:
        ok, motivo, saidas = False, repr(e), []
    dt = time.time() - t0
    mon.parar = True; mon.join()
    if mon.abortou:
        ok, motivo = False, f"abortado: temperatura > {TEMP_ABORT} C"
    return {"ok": ok, "motivo": motivo, "tempo_s": round(dt, 1), "vram_pico_mib": mon.vram, "temp_pico_c": mon.temp,
            "potencia_pico_w": round(mon.pot), "ram_pico_gb": round(mon.ram, 1), "saidas": saidas}


# ----------------------------------------------------------------- ambiente
def hashes_modelos(lista=None):
    cache_f = HERE / "results" / "model_hashes.json"
    cache = json.load(open(cache_f)) if cache_f.exists() else {}
    res = {}
    for rel in (lista or ARQ_MODELOS):
        p = MODELOS / rel; st = p.stat(); chave = f"{st.st_size}:{int(st.st_mtime)}"
        if cache.get(rel, {}).get("chave") != chave:
            h = hashlib.sha256()
            with open(p, "rb") as f:
                while c := f.read(1 << 24):
                    h.update(c)
            cache[rel] = {"chave": chave, "sha256": h.hexdigest()}
        res[rel] = cache[rel]["sha256"]
    json.dump(cache, open(cache_f, "w"), indent=1)
    return res


def ambiente(modelo="wan", imagem="zimage", edicao=False):
    s = http("/system_stats")["system"]
    return {
        "comfyui": s.get("comfyui_version"), "pytorch": s.get("pytorch_version"),
        "driver": sh("nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1"),
        "power_limit_w": sh("nvidia-smi --query-gpu=index,power.limit --format=csv,noheader").replace("\n", " | "),
        "pases_infra_commit": sh("git -C /srv/pases rev-parse --short HEAD"),
        "suite": ITEMS["versao_suite"], "modelos_sha256": hashes_modelos(ARQ_FLUX2 if edicao else ARQ_QWEN2512 if imagem == "qwen2512" else ARQ_QWEN if imagem == "qwen" else ARQ_LTX if modelo == "ltx" else None), "modelo_video": modelo, "modelo_imagem": imagem,
    }


# ------------------------------------------------------------- folhas / md
def folha_imagens(arqs, destino):
    from PIL import Image, ImageDraw
    ims = [(Path(a).stem, Image.open(a).convert("RGB")) for a in arqs if Path(a).exists()]
    if not ims:
        return
    w = 512; h = int(ims[0][1].height * w / ims[0][1].width)
    s = Image.new("RGB", (w * len(ims), h + 22), "white"); d = ImageDraw.Draw(s)
    for k, (nome, im) in enumerate(ims):
        s.paste(im.resize((w, h)), (k * w, 22)); d.text((k * w + 6, 4), nome, fill="black")
    s.save(destino)


def folha_videos(arqs, destino):
    import av
    from PIL import Image, ImageDraw
    linhas = []
    for a in arqs:
        if not Path(a).exists():
            continue
        fr = [f.to_image() for f in av.open(a).decode(video=0)]
        linhas.append((Path(a).stem, [fr[0], fr[len(fr) // 2], fr[-1]]))
    if not linhas:
        return
    w = 480; h = int(linhas[0][1][0].height * w / linhas[0][1][0].width)
    s = Image.new("RGB", (w * 3, (h + 20) * len(linhas)), "white"); d = ImageDraw.Draw(s)
    for r, (nome, q) in enumerate(linhas):
        d.text((6, r * (h + 20) + 4), nome + "  (inicio | meio | fim)", fill="black")
        for k, im in enumerate(q):
            s.paste(im.resize((w, h)), (k * w, r * (h + 20) + 20))
    s.save(destino)


def mediana(v):
    return round(statistics.median(v), 1) if v else None


def relatorio(run, amb, regs):
    L = [f"# PASES-Bench Visual {amb['suite']} - {run}", "",
         f"ComfyUI {amb['comfyui']} | PyTorch {amb['pytorch']} | driver {amb['driver']} | power limit: {amb['power_limit_w']} | pases-infra {amb['pases_infra_commit']}", "",
         "## Medicoes (automaticas)", "",
         "| Item | Sementes | Falhas | Tempo mediana (s) | 1a geracao (s) | VRAM pico (MiB) | Temp pico (C) | Potencia pico (W) | RAM pico (GB) |", "|---|---|---|---|---|---|---|---|---|"]
    por = {}
    for r in regs:
        por.setdefault(r["item"], []).append(r)
    m = ITEMS["metas_provisorias"]; veredito = []
    for it in ITEMS["itens"]:
        rs = por.get(it["id"], [])
        if not rs:
            continue
        falhas = sum(not r["ok"] for r in rs); tempos = [r["tempo_s"] for r in rs if r["ok"]]
        L.append(f"| {it['id']} {it['nome']} | {len(rs)} | {falhas} | {mediana(tempos)} | {rs[0]['tempo_s']} | {max(r['vram_pico_mib'] for r in rs):.0f} | "
                 f"{max(r['temp_pico_c'] for r in rs):.0f} | {max(r['potencia_pico_w'] for r in rs)} | {max(r['ram_pico_gb'] for r in rs)} |")
        veredito.append((it["id"], falhas, mediana(tempos), max(r["temp_pico_c"] for r in rs), max(r["potencia_pico_w"] for r in rs)))
    L += ["", "## Metas provisorias (operacionais)", "", "| Item | Falhas (meta 0) | Mediana (s) | Meta (s) | Temp (meta <= 80 C) | Potencia (meta <= 300 W) | Resultado |", "|---|---|---|---|---|---|---|"]
    for iid, f, med, t, p in veredito:
        meta = m["imagem_mediana_s_max"] if iid.startswith("I") else m.get(iid + "_mediana_s_max")
        ok = f <= m["falhas_max"] and t <= m["temp_pico_c_max"] and p <= m["potencia_pico_w_max"] and (meta is None or (med is not None and med <= meta))
        L.append(f"| {iid} | {f} | {med} | {meta if meta else '-'} | {t:.0f} | {p} | {'OK' if ok else 'REVISAR'} |")
    L += ["", "## Ficha de avaliacao de qualidade (preencher a mao, 0 a 2 por criterio)", "",
          "Folhas de contato em `/scratch/bench/" + run + "/`. Criterios: " + "; ".join(f"**{k}**: {v}" for k, v in ITEMS["avaliacao"]["criterios"].items()), ""]
    for it in ITEMS["itens"]:
        if it["id"] not in por:
            continue
        L += [f"### {it['id']} - {it['nome']}", "", "| Semente | " + " | ".join(it["criterios"]) + " | Observacoes |", "|---|" + "---|" * (len(it["criterios"]) + 1)]
        for r in por[it["id"]]:
            L.append(f"| {r['semente']} | " + " | ".join("" for _ in it["criterios"]) + " | |")
        L.append("")
    L += ["Qualidade = soma dos pontos / maximo possivel. Meta provisoria: >= 80%, e I2 com texto ao menos parcial.", ""]
    return "\n".join(L)


# --------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*"); ap.add_argument("--no-restart", action="store_true"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--edicao", action="store_true", help="roda so os itens de EDICAO de imagem (E1-E4) com o FLUX.2 klein 4B")
    ap.add_argument("--imagem", choices=["zimage", "qwen", "qwen2512"], default="zimage", help="modelo de IMAGEM; qwen (2.1, so avaliacao) e qwen2512 (Apache 2.0) rodam so os itens de imagem")
    ap.add_argument("--modelo", choices=["wan", "ltx"], default="wan", help="modelo de VIDEO (imagem sempre Z-Image); ltx roda so os itens de video")
    a = ap.parse_args()
    run = datetime.now().strftime("%Y-%m-%d_%H%M") + ("_flux2edit" if a.edicao else "_" + a.imagem if a.imagem != "zimage" else "_ltx" if a.modelo == "ltx" else "")

    ocupado = [l for l in sh("ollama ps").splitlines()[1:] if l.strip()]
    if ocupado:
        sys.exit("ABORTADO: ha modelo carregado no Ollama (ocupa VRAM da 5060 Ti). Rode `ollama stop <modelo>`:\n" + "\n".join(ocupado))
    if sh("systemctl --user is-active comfyui") != "active":
        sys.exit("ABORTADO: comfyui.service nao esta ativo")
    itens = [i for i in ITEMS["itens"] if ((i["tipo"] == "edicao") == a.edicao) and (a.imagem == "zimage" or i["tipo"] == "imagem") and (not a.only or i["id"] in a.only) and (a.modelo == "ltx" or i["tipo"] not in ("video_flf", "video_ext")) and (a.modelo == "wan" or i["tipo"] != "imagem")]
    if any(i["tipo"] == "video_i2v" for i in itens) and not any(i["id"] == "I1" for i in itens) and not (OUT / "bench").exists():
        sys.exit("ABORTADO: V3 precisa da saida do I1 (rode I1 junto)")
    total = sum(len(ITEMS["sementes_imagem"]) if i["tipo"] == "imagem" else len(i["sementes"]) for i in itens)
    print(f"Run {run}: {len(itens)} itens, {total} geracoes. Itens: {[i['id'] for i in itens]}")
    if a.dry_run:
        print("dry-run: ambiente:", json.dumps({k: v for k, v in ambiente(a.modelo, a.imagem, a.edicao).items() if k != 'modelos_sha256'}, ensure_ascii=False)); return

    if not a.no_restart:
        print("Reiniciando comfyui.service (1a geracao = medida a frio)...")
        sh("systemctl --user restart comfyui"); time.sleep(5)
        for _ in range(60):
            try:
                http("/system_stats"); break
            except Exception:
                time.sleep(2)
    amb = ambiente(a.modelo, a.imagem, a.edicao); regs = []
    pasta_run = Path("/scratch/bench") / run; pasta_run.mkdir(parents=True, exist_ok=True)
    costuras = []
    saida_json = HERE / "results" / f"{run}.json"; saidas_i1 = {}

    def salvar():
        json.dump({"run": run, "ambiente": amb, "registros": regs, "costuras": costuras}, open(saida_json, "w"), indent=1, ensure_ascii=False)

    for it in itens:
        if it["tipo"] == "video_ext":
            r_, c_ = _extend.executar(it, run, pasta_run, gerar, INPUT, OUT, ITEMS)
            regs += r_; costuras += c_; salvar(); continue
        if it["tipo"] == "imagem":
            sementes = ITEMS["sementes_imagem"]
        else:
            sementes = it["sementes"]
        arqs = []
        for sd in sementes:
            prefixo = f"bench/{run}/{it['id']}_{sd}"
            if it["tipo"] == "imagem":
                wf = {"qwen": _qwen.wf_qwen, "qwen2512": _qwen.wf_qwen2512}[a.imagem](it["prompt"], sd, prefixo) if a.imagem != "zimage" else wf_imagem(it["prompt"], sd, prefixo)
            elif it["tipo"] == "edicao":
                nomes = []
                for nome in it["imagens"]:
                    shutil.copy(HERE / "fixtures" / nome, INPUT / f"pases_bench_{nome}"); nomes.append(f"pases_bench_{nome}")
                wf = _flux2.wf_flux2_edit(it["prompt"], sd, prefixo, nomes)
            elif it["tipo"] == "video_flf":
                for nome in it["extremos"]:
                    shutil.copy(HERE / "fixtures" / nome, INPUT / f"pases_bench_{nome}")
                wf = _ltx.wf_ltx_flf(it["prompt"], sd, prefixo, it["largura_ltx"], it["altura_ltx"], (it["quadros"] - 1) // ITEMS["video"]["fps"], ITEMS["video"]["fps"],
                                     f"pases_bench_{it['extremos'][0]}", f"pases_bench_{it['extremos'][1]}")
            elif it["tipo"] == "video" and a.modelo == "ltx":
                wf = wf_ltx(it["prompt"], sd, prefixo, it["largura_ltx"], it["altura_ltx"], (it["quadros"] - 1) // ITEMS["video"]["fps"])
            elif it["tipo"] == "video":
                wf = wf_video(it["prompt"], sd, prefixo, it["largura"], it["altura"], it["quadros"])
            else:
                src = saidas_i1.get(int(it["imagem_inicial"].split(":")[1])) or next(iter(sorted((OUT / "bench").glob("*/I1_101_*.png"))[-1:]), None)
                if not src:
                    regs.append({"item": it["id"], "semente": sd, "ok": False, "motivo": "sem imagem inicial (I1:101)"}); continue
                nome_in = f"bench_{run}_I1_101.png"; shutil.copy(src, INPUT / nome_in)
                if a.modelo == "ltx":
                    wf = wf_ltx(it["prompt"], sd, prefixo, it["largura_ltx"], it["altura_ltx"], (it["quadros"] - 1) // ITEMS["video"]["fps"], imagem_inicial=nome_in)
                else:
                    wf = wf_video(it["prompt"], sd, prefixo, it["largura"], it["altura"], it["quadros"], imagem_inicial=nome_in)
            print(f"[{it['id']} sem={sd}] gerando...", flush=True)
            r = gerar(wf); r.update({"item": it["id"], "semente": sd}); regs.append(r); salvar()
            print(f"   {'ok' if r['ok'] else 'FALHA ' + r['motivo']} {r['tempo_s']}s vram={r['vram_pico_mib']:.0f} temp={r['temp_pico_c']:.0f} pot={r['potencia_pico_w']}W", flush=True)
            if r["ok"]:
                arqs += r["saidas"]
                if it["id"] == "I1" and r["saidas"]:
                    saidas_i1[sd] = r["saidas"][0]
            if r["motivo"].startswith("abortado"):
                print("Parando a suite por seguranca termica."); break
        try:
            if it["tipo"] == "edicao":
                arqs = [str(HERE / "fixtures" / n) for n in it["imagens"]] + arqs   # originais primeiro, depois os resultados
            (folha_imagens if it["tipo"] in ("imagem", "edicao") else folha_videos)(arqs, pasta_run / f"{it['id']}.png")
        except Exception as e:
            print("   (folha de contato falhou:", repr(e), ")")
        if regs and regs[-1].get("motivo", "").startswith("abortado"):
            break
    salvar()
    md = relatorio(run, amb, [r for r in regs if "tempo_s" in r])
    if costuras:
        md += "\n## Emendas da extensao de video (X1)\n\nSalto = diferenca na emenda / mediana da diferenca entre quadros normais (~1 = emenda invisivel; >>1 = pulo visivel).\n\n| Metodo | Semente | Quadros guia | Quadros | Salto na emenda 1 | Salto na emenda 2 |\n|---|---|---|---|---|---|\n"
        for c in costuras:
            sj = [e["salto_x"] for e in c["emendas"]] + [None, None]
            md += f"| {c['metodo']} | {c['semente']} | {c['quadros_guia']} | {c['quadros']} | {sj[0]} | {sj[1]} |\n"
    (HERE / "results" / f"{run}.md").write_text(md, encoding="utf-8")
    print(f"Pronto. Relatorio: {HERE}/results/{run}.md | folhas: {pasta_run}")


if __name__ == "__main__":
    main()
