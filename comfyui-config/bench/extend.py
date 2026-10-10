"""Extensao de video com o LTX 2.5 (item X1 da suite). Nao existe template oficial de extensao para o LTX 2.5;
o metodo aqui e: os ultimos K quadros do trecho anterior viram guia (LTXVAddGuide, frame_idx 0) do inicio do
proximo trecho, em um estagio unico (como o flf2v). O trecho novo repete esses K quadros; ao costurar, descartam-se
os K primeiros do trecho novo. O audio de cada trecho e gerado do zero (sem condicionamento de audio).
Costura com ffmpeg; a emenda e medida pelo 'salto' visual contra a variacao normal entre quadros."""
import glob, json, shutil, subprocess
from pathlib import Path

NEG = "pc game, console game, video game, cartoon, childish, ugly"
SIGMAS_1 = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"


def wf_ltx_extend(prompt, seed, prefix, w, h, segundos, fps, video_ant, n_ant, k, forca=1.0):
    assert w % 32 == 0 and h % 32 == 0
    frames = segundos * fps + 1
    assert (frames - 1) % 8 == 0 and (k - 1) % 8 == 0 and k <= n_ant
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": "ltx-2.5-video-vae-bf16.safetensors"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ltx-2.5-audio-vae-bf16.safetensors"}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": "gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors", "type": "ltxv", "device": "default"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": prompt}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": NEG}},
        "8": {"class_type": "LTXVConditioning", "inputs": {"positive": ["6", 0], "negative": ["7", 0], "frame_rate": float(fps)}},
        # ultimos k quadros do video anterior
        "40": {"class_type": "LoadVideo", "inputs": {"file": video_ant}},
        "41": {"class_type": "GetVideoComponents", "inputs": {"video": ["40", 0]}},
        "42": {"class_type": "ImageFromBatch", "inputs": {"image": ["41", 0], "batch_index": n_ant - k, "length": k}},
        "43": {"class_type": "ImageScale", "inputs": {"image": ["42", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}},
        "44": {"class_type": "LTXVPreprocess", "inputs": {"image": ["43", 0], "img_compression": 18}},
        "9": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": w, "height": h, "length": frames, "batch_size": 1}},
        "10": {"class_type": "LTXVEmptyLatentAudio", "inputs": {"audio_vae": ["3", 0], "frames_number": frames, "frame_rate": fps, "batch_size": 1}},
        "46": {"class_type": "LTXVAddGuide", "inputs": {"positive": ["8", 0], "negative": ["8", 1], "vae": ["2", 0], "latent": ["9", 0], "image": ["44", 0], "frame_idx": 0, "strength": forca}},
        "11": {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["46", 2], "audio_latent": ["10", 0]}},
        "12": {"class_type": "LTXVDualCFGGuider", "inputs": {"model": ["1", 0], "positive": ["46", 0], "negative": ["46", 1], "video_cfg": 1, "audio_cfg": 1}},
        "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "14": {"class_type": "SamplerEulerAncestral", "inputs": {"eta": 0, "s_noise": 1}},
        "15": {"class_type": "ManualSigmas", "inputs": {"sigmas": SIGMAS_1}},
        "16": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["13", 0], "guider": ["12", 0], "sampler": ["14", 0], "sigmas": ["15", 0], "latent_image": ["11", 0]}},
        "17": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["16", 1]}},
        "18": {"class_type": "LTXVCropGuides", "inputs": {"positive": ["46", 0], "negative": ["46", 1], "latent": ["17", 0]}},
        "26": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["18", 2], "vae": ["2", 0], "tile_size": 512, "overlap": 64, "temporal_size": 16, "temporal_overlap": 8}},
        "27": {"class_type": "LTXVAudioVAEDecode", "inputs": {"samples": ["17", 1], "audio_vae": ["3", 0]}},
        "28": {"class_type": "CreateVideo", "inputs": {"images": ["26", 0], "audio": ["27", 0], "fps": float(fps)}},
        "29": {"class_type": "SaveVideo", "inputs": {"video": ["28", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}},
    }


def costurar(segmentos, k, destino, fps=24):
    """segmentos[0] inteiro + segmentos[1:] sem os k primeiros quadros/audio. Retorna o numero de quadros de cada parte."""
    n = len(segmentos)
    ent = []
    for s in segmentos:
        ent += ["-i", str(s)]
    f, cat = [], []
    for i in range(n):
        if i == 0:
            cat += ["[0:v]", "[0:a]"]
        else:
            f.append(f"[{i}:v]trim=start_frame={k},setpts=PTS-STARTPTS[v{i}];[{i}:a]atrim=start={k / fps},asetpts=PTS-STARTPTS[a{i}]")
            cat += [f"[v{i}]", f"[a{i}]"]
    fc = ";".join(f + ["".join(cat) + f"concat=n={n}:v=1:a=1[v][a]"])
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *ent, "-filter_complex", fc, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-c:a", "aac", str(destino)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-400:])


def metricas_costura(video, pontos):
    """Salto visual em cada emenda: diferenca media absoluta (cinza, 1/4 de resolucao) entre os dois quadros da emenda,
    dividida pela mediana da diferenca entre quadros consecutivos FORA das emendas. ~1 = emenda invisivel; >>1 = pulo."""
    import av, numpy as np
    qs = []
    for fr in av.open(str(video)).decode(video=0):
        a = np.asarray(fr.to_image().convert("L").resize((224, 128)), dtype=np.float32)
        qs.append(a)
    d = [float(np.abs(qs[i + 1] - qs[i]).mean()) for i in range(len(qs) - 1)]
    emendas = {p - 1 for p in pontos}   # indice i = diferenca entre quadro i e i+1
    normal = [x for i, x in enumerate(d) if i not in emendas]
    med = float(np.median(normal))
    return {"quadros": len(qs), "mediana_normal": round(med, 2),
            "emendas": [{"quadro": p, "diff": round(d[p - 1], 2), "salto_x": round(d[p - 1] / med, 2)} for p in pontos]}


def folha_emendas(video, pontos, destino):
    import av
    from PIL import Image, ImageDraw
    fr = [f.to_image().convert("RGB") for f in av.open(str(video)).decode(video=0)]
    idx = [0]
    for p in pontos:
        idx += [p - 1, p]
    idx.append(len(fr) - 1)
    w = 360; h = int(fr[0].height * w / fr[0].width)
    s = Image.new("RGB", (w * len(idx), h + 18), "white"); d = ImageDraw.Draw(s)
    for k_, i in enumerate(idx):
        s.paste(fr[i].resize((w, h)), (k_ * w, 18)); d.text((k_ * w + 4, 3), f"quadro {i}" + ("  <- emenda" if (i + 1) in pontos else ""), fill="black")
    s.save(destino)


def executar(it, run, pasta_run, gerar, INPUT, OUT, ITEMS):
    """Roda o item X1: para cada metodo e semente, encadeia `etapas` extensoes a partir do V1 do LTX e costura."""
    fps = ITEMS["video"]["fps"]; seg = it["segundos_por_trecho"]; w, h = it["largura_ltx"], it["altura_ltx"]
    regs, costuras = [], []
    saida = OUT / "bench" / run; saida.mkdir(parents=True, exist_ok=True)
    for sd in it["sementes"]:
        base = sorted(glob.glob(str(OUT / "bench" / "*_ltx" / f"{it['base']}_{sd}_*.mp4")))
        if not base:
            regs.append({"item": it["id"], "semente": str(sd), "ok": False, "motivo": f"sem video base {it['base']}_{sd} de uma rodada LTX anterior"}); continue
        for m in it["metodos"]:
            k = m["quadros_guia"]; trechos = [Path(base[-1])]; nq = 49; ok_cadeia = True
            for e in range(1, it["etapas"] + 1):
                nome_in = f"pases_ext_{run}_{m['id']}_{sd}_e{e - 1}.mp4"
                shutil.copy(trechos[-1], INPUT / nome_in)
                wf = wf_ltx_extend(it["prompt"], sd, f"bench/{run}/{it['id']}_{m['id']}_{sd}_e{e}", w, h, seg, fps, nome_in, nq, k)
                print(f"[{it['id']} {m['id']} sem={sd} etapa {e}] gerando...", flush=True)
                r = gerar(wf); r.update({"item": it["id"], "semente": f"{sd}-{m['id']}-e{e}", "metodo": m["id"], "etapa": e, "quadros_guia": k}); regs.append(r)
                print(f"   {'ok' if r['ok'] else 'FALHA ' + r['motivo']} {r['tempo_s']}s vram={r['vram_pico_mib']:.0f} temp={r['temp_pico_c']:.0f}", flush=True)
                if not r["ok"] or not r["saidas"]:
                    ok_cadeia = False; break
                trechos.append(Path(r["saidas"][0])); nq = 49
            if ok_cadeia:
                dst = saida / f"{it['id']}_{m['id']}_{sd}_costurado.mp4"
                costurar(trechos, k, dst, fps)
                pontos = []; acum = 49
                for _ in range(it["etapas"]):
                    pontos.append(acum); acum += 49 - k
                met = metricas_costura(dst, pontos); met.update({"metodo": m["id"], "quadros_guia": k, "semente": sd, "arquivo": str(dst)})
                costuras.append(met)
                folha_emendas(dst, pontos, pasta_run / f"{it['id']}_{m['id']}_{sd}_emendas.png")
                print(f"   costurado: {met['quadros']} quadros, saltos na emenda: {[e['salto_x'] for e in met['emendas']]}", flush=True)
    return regs, costuras
