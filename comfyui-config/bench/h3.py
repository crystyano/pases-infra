#!/usr/bin/env python3
"""MiniMax H3 (fl2va, pruned int8_convrot) no ComfyUI: texto / primeiro quadro / primeiro+ultimo quadro -> video com audio estereo.
Fluxo em formato de API equivalente ao template video_minimax_h3_i2v (subgrafo "Image to Video (MiniMax H3)") com o LoRA turbo de 4 passos (768p).
Comprimento valido: 17k+5 quadros (ex.: 3 s -> 73). Largura/altura multiplos de 32, ate 768x1344 pixels (Cap. 8A.14 do manual).
Licenca: MiniMax H3 Community License (so dentro do territorio: exclui UE, Reino Unido, Coreia do Sul e EUA; nao exibir resultados fora dele).
Uso: h3.py --first quadro.png [--last quadro2.png] --prompt "..." --seconds 3 --tag teste1 [--largura 480 --altura 832 --seed 1 --passos 4]"""
import argparse, json, subprocess, threading, time, urllib.request
URL = "http://127.0.0.1:8188"

def req(path, dados=None):
    r = urllib.request.Request(URL + path, json.dumps(dados).encode() if dados is not None else None, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))

def comprimento(seg):
    n = max(5, round(seg * 24)); return n + (5 - n % 17) % 17

def grafo(a):
    g = {
     "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "minimax_h3_fl2va_pruned_int8_convrot.safetensors", "weight_dtype": "default"}},
     "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors", "type": "minimax", "device": "default"}},
     "3": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"}},
     "4": {"class_type": "VAELoader", "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"}},
     "5": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors", "strength_model": 1.0}},
     "9": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "prompt": a.prompt, "width": a.largura, "height": a.altura, "length": comprimento(a.seconds)}},
     "10": {"class_type": "BasicGuider", "inputs": {"model": ["5", 0], "conditioning": ["9", 0]}},
     "11": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
     "12": {"class_type": "BasicScheduler", "inputs": {"model": ["5", 0], "scheduler": "simple", "steps": a.passos, "denoise": 1.0}},
     "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": a.seed}},
     "14": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["13", 0], "guider": ["10", 0], "sampler": ["11", 0], "sigmas": ["12", 0], "latent_image": ["9", 1]}},
     "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["3", 0]}},
     "16": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["14", 0], "vae": ["4", 0]}},
     "17": {"class_type": "CreateVideo", "inputs": {"images": ["15", 0], "audio": ["16", 0], "fps": 24.0}},
     "18": {"class_type": "SaveVideo", "inputs": {"video": ["17", 0], "filename_prefix": "video/h3_" + a.tag, "format": "auto", "codec": "auto"}},
    }
    if a.first:
        g["6"] = {"class_type": "LoadImage", "inputs": {"image": a.first}}; g["9"]["inputs"]["first_frame"] = ["6", 0]
    if a.last:
        g["7"] = {"class_type": "LoadImage", "inputs": {"image": a.last}}; g["9"]["inputs"]["last_frame"] = ["7", 0]
    return g

class VRAM(threading.Thread):
    def __init__(s): super().__init__(daemon=True); s.parar = False; s.pico = 0; s.ram = 0
    def run(s):
        while not s.parar:
            try:
                o = subprocess.run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits", shell=True, capture_output=True, text=True).stdout.splitlines()
                s.pico = max(s.pico, max(int(l.split(",")[1]) for l in o if l.split(",")[0].strip() == "1"))
                m = subprocess.run("free -m | awk 'NR==2{print $3}'", shell=True, capture_output=True, text=True).stdout.strip(); s.ram = max(s.ram, int(m))
            except Exception: pass
            time.sleep(2)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--first"); p.add_argument("--last"); p.add_argument("--prompt", required=True); p.add_argument("--seconds", type=float, default=3)
    p.add_argument("--tag", default="teste"); p.add_argument("--seed", type=int, default=1); p.add_argument("--passos", type=int, default=4)
    p.add_argument("--largura", type=int, default=480); p.add_argument("--altura", type=int, default=832)
    a = p.parse_args(); assert a.largura % 32 == 0 and a.altura % 32 == 0 and a.largura * a.altura <= 768 * 1344
    m = VRAM(); m.start(); t0 = time.time()
    r = req("/prompt", {"prompt": grafo(a)}); pid = r["prompt_id"]; print("fila:", pid, "| quadros:", comprimento(a.seconds), flush=True)
    while True:
        h = req("/history/" + pid)
        if pid in h and h[pid].get("status", {}).get("completed") is not None: h = h[pid]; break
        time.sleep(5)
    m.parar = True
    print("status:", h["status"]["status_str"], "| tempo %.0fs" % (time.time() - t0), "| pico VRAM GPU1 %.1f GiB | pico RAM %.1f GiB" % (m.pico / 1024, m.ram / 1024))
    for msg in h["status"].get("messages", []):
        if msg[0] == "execution_error": print("ERRO:", json.dumps(msg[1], ensure_ascii=False)[:1500])
    print("saidas:", json.dumps(h.get("outputs", {}), ensure_ascii=False)[:500])
