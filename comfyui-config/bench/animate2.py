#!/usr/bin/env python3
"""Wan-Animate-2 destilado (int8 convrot) no ComfyUI: imagem de referencia + video de movimento -> personagem executando o movimento.
Fluxo equivalente ao template video_wan_animate2_distilled (subgrafo "Motion Transfer"), em formato de API. Cap. 8A do manual.
Uso: animate2.py --ref texugo_frente.jpg --video street_dance_drive.mp4 --tag teste1 [--length 81] [--seed 1] [--cache gpu|cpu]"""
import argparse, json, subprocess, threading, time, urllib.request
URL = "http://127.0.0.1:8188"
NEG = "色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走"

def req(path, dados=None):
    r = urllib.request.Request(URL + path, json.dumps(dados).encode() if dados is not None else None, {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=60))

def grafo(a):
    g = {
     "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan_animate_2_distill_int8_convrot.safetensors", "weight_dtype": "default"}},
     "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
     "3": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
     "4": {"class_type": "VAELoader", "inputs": {"vae_name": "Wan2_1_VAE_bf16.safetensors"}},
     "5": {"class_type": "LoadImage", "inputs": {"image": a.ref}},
     "6": {"class_type": "LoadVideo", "inputs": {"file": a.video}},
     "7": {"class_type": "GetVideoComponents", "inputs": {"video": ["6", 0]}},
     "8": {"class_type": "ResizeImageMaskNode", "inputs": {"input": ["7", 0], "resize_type": "scale dimensions", "resize_type.width": a.largura, "resize_type.height": a.altura, "resize_type.crop": "center", "scale_method": "area"}},
     "9": {"class_type": "GetImageSize", "inputs": {"image": ["8", 0]}},
     "10": {"class_type": "ResizeImageMaskNode", "inputs": {"input": ["5", 0], "resize_type": "scale dimensions", "resize_type.width": ["9", 0], "resize_type.height": ["9", 1], "resize_type.crop": "center", "scale_method": "area"}},
     "11": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["3", 0], "image": ["10", 0], "crop": "none"}},
     "12": {"class_type": "ImageFromBatch", "inputs": {"image": ["8", 0], "batch_index": 0, "length": 1}},
     "13": {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["3", 0], "image": ["12", 0], "crop": "none"}},
     "14": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": a.personagem}},
     "15": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": NEG}},
     "16": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": a.movimento}},
     "17": {"class_type": "WanAnimate2ToVideo", "inputs": {"positive": ["14", 0], "negative": ["15", 0], "vae": ["4", 0], "width": ["9", 0], "height": ["9", 1], "length": a.length, "batch_size": 1, "video_frame_offset": 0, "pose_strength": 1.0, "pose_start_percent": 0.0, "pose_end_percent": 1.0, "reference_image_strength": 1.0, "reference_image": ["10", 0], "pose_video": ["8", 0], "clip_vision_output": ["11", 0], "positive_pose": ["16", 0], "clip_vision_output_pose": ["13", 0]}},
     "18": {"class_type": "WanAnimate2Cache", "inputs": {"model": ["1", 0], "device": a.cache, "dtype": "int8"}},
     "19": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["18", 0], "shift": 5.0}},
     "20": {"class_type": "BasicScheduler", "inputs": {"model": ["18", 0], "scheduler": "simple", "steps": a.passos, "denoise": 1.0}},
     "21": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "lcm"}},
     "22": {"class_type": "SamplerCustom", "inputs": {"model": ["19", 0], "add_noise": True, "noise_seed": a.seed, "cfg": 1.0, "positive": ["17", 0], "negative": ["17", 1], "sampler": ["21", 0], "sigmas": ["20", 0], "latent_image": ["17", 2]}},
     "23": {"class_type": "TrimVideoLatent", "inputs": {"samples": ["22", 0], "trim_amount": ["17", 3]}},
     "24": {"class_type": "VAEDecode", "inputs": {"samples": ["23", 0], "vae": ["4", 0]}},
     "25": {"class_type": "CreateVideo", "inputs": {"images": ["24", 0], "fps": ["7", 2]}},
     "26": {"class_type": "SaveVideo", "inputs": {"video": ["25", 0], "filename_prefix": "video/animate2_" + a.tag, "format": "auto", "codec": "auto"}},
    }
    return g

class VRAM(threading.Thread):
    def __init__(s): super().__init__(daemon=True); s.parar = False; s.pico = 0
    def run(s):
        while not s.parar:
            try:
                o = subprocess.run("nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits", shell=True, capture_output=True, text=True).stdout.splitlines()
                s.pico = max(s.pico, max(int(l.split(",")[1]) for l in o if l.split(",")[0].strip() == "1"))
            except Exception: pass
            time.sleep(2)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ref", required=True); p.add_argument("--video", required=True); p.add_argument("--tag", default="teste")
    p.add_argument("--length", type=int, default=81); p.add_argument("--seed", type=int, default=1); p.add_argument("--passos", type=int, default=10)
    p.add_argument("--largura", type=int, default=482); p.add_argument("--altura", type=int, default=854); p.add_argument("--cache", default="gpu")
    p.add_argument("--personagem", default="Character appearance description: A chubby honey badger mascot, black fur with a creamy-white mane along the back, small round ears, a scar over the right eye, a wide mischievous toothy grin, thick claws, collectible 3D toy render.\nBackground description: a rainy neon-lit city street corner at night, wet asphalt reflecting purple-blue and red neon signs, light mist, cinematic night photography.")
    p.add_argument("--movimento", default="A honey badger doing energetic street dance with popping body waves and fast spinning moves, rain falling around him.")
    a = p.parse_args()
    m = VRAM(); m.start(); t0 = time.time()
    r = req("/prompt", {"prompt": grafo(a)}); pid = r["prompt_id"]; print("fila:", pid, flush=True)
    while True:
        h = req("/history/" + pid)
        if pid in h and h[pid].get("status", {}).get("completed") is not None:
            h = h[pid]; break
        time.sleep(5)
    m.parar = True
    print("status:", h["status"]["status_str"], "| tempo %.0fs" % (time.time() - t0), "| pico VRAM GPU1 %.1f GiB" % (m.pico / 1024))
    for msg in h["status"].get("messages", []):
        if msg[0] == "execution_error": print("ERRO:", json.dumps(msg[1], ensure_ascii=False)[:1500])
    print("saidas:", json.dumps(h.get("outputs", {}), ensure_ascii=False)[:600])
