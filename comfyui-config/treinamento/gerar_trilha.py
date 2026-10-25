#!/usr/bin/env python3
"""Trilha de fundo dos videos de treinamento (v5, 24/10/2026): ACE-Step 1.5 turbo (MIT) pelo ComfyUI, instrumental.
So o codificador Qwen 0.6B, sem o LM de 4B (8,4 GB, nao baixado): o DualCLIPLoader "ace" exige dois arquivos, entao o 0.6B
vai nos dois, e generate_audio_codes=False (sem o planejador; o CLIPLoader simples carrega o 0.6B como outro modelo, o Anima).
Uso: gerar_trilha.py DESTINO [--seeds 1 2 3] [--segundos 180]   -> DESTINO/trilha_s<seed>.flac"""
import argparse, json, shutil, time, urllib.request
from pathlib import Path
API = "http://127.0.0.1:8188"; SAIDA_COMFY = Path("/scratch/comfyui/output")
TAGS = ("instrumental, calm background music for a software tutorial, soft electric piano, warm synth pads, light plucked guitar, "
        "gentle, minimal soft percussion, positive, modern, clean mix, steady, no vocals, no lead melody")

def grafo(seed, seg, bpm, tom):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "acestep_v1.5_turbo.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "qwen_0.6b_ace15.safetensors", "clip_name2": "qwen_0.6b_ace15.safetensors", "type": "ace"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ace_1.5_vae.safetensors"}},
        "4": {"class_type": "TextEncodeAceStepAudio1.5", "inputs": {"clip": ["2", 0], "tags": TAGS, "lyrics": "[Instrumental]", "seed": seed,
              "bpm": bpm, "duration": float(seg), "timesignature": "4", "language": "en", "keyscale": tom, "generate_audio_codes": False,
              "cfg_scale": 2.0, "temperature": 0.85, "top_p": 0.9, "top_k": 0, "min_p": 0.0}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptyAceStep1.5LatentAudio", "inputs": {"seconds": float(seg), "batch_size": 1}},
        "7": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.0}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["7", 0], "positive": ["4", 0], "negative": ["5", 0], "latent_image": ["6", 0],
              "seed": seed, "steps": 8, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "9": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveAudio", "inputs": {"audio": ["9", 0], "filename_prefix": f"trilha/ardus_s{seed}"}},
    }

def post(caminho, dados=None):
    req = urllib.request.Request(API + caminho, data=json.dumps(dados).encode() if dados else None, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("destino"); ap.add_argument("--seeds", nargs="*", type=int, default=[1, 2, 3, 4])
    ap.add_argument("--segundos", type=float, default=180); ap.add_argument("--bpm", type=int, default=92); ap.add_argument("--tom", default="D major")
    a = ap.parse_args(); dst = Path(a.destino); dst.mkdir(parents=True, exist_ok=True)
    for s in a.seeds:
        pid = post("/prompt", {"prompt": grafo(s, a.segundos, a.bpm, a.tom)})["prompt_id"]; t0 = time.time()
        while True:
            h = post(f"/history/{pid}")
            if pid in h and h[pid].get("status", {}).get("completed") is not None: break
            time.sleep(3)
        st = h[pid]["status"]
        if st.get("status_str") != "success": print(f"seed {s}: ERRO", json.dumps(st.get("messages", []))[-800:]); continue
        for f in h[pid]["outputs"]["10"]["audio"]:
            p = SAIDA_COMFY / f["subfolder"] / f["filename"]; shutil.copy(p, dst / f"trilha_s{s}{p.suffix}")
        print(f"seed {s}: ok em {time.time() - t0:.0f} s", flush=True)
