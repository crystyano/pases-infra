"""Workflow do LTX 2.5 em formato de API (ComfyUI), espelhando o template oficial
`video_ltx2_5_t2v` (dois estagios: amostragem em meia resolucao com 8 passos, upscale
latente x2 e refino em 4 passos; video e audio num latente conjunto).
Dimensoes finais devem ser multiplos de 64 (o estagio 1 roda na metade e precisa de multiplos de 32).
Frames = segundos * fps + 1 e precisa ser 8n+1 (ex.: 2 s a 24 fps = 49; 5 s = 121).
"""
NEG = "pc game, console game, video game, cartoon, childish, ugly"
SIGMAS_1 = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"   # estagio 1: 8 passos
SIGMAS_2 = "0.85, 0.7250, 0.4219, 0.0"                                               # estagio 2: 3 passos de refino


def wf_ltx(prompt, seed, prefix, w, h, segundos, fps=24, imagem_inicial=None):
    assert w % 64 == 0 and h % 64 == 0, "largura e altura finais devem ser multiplos de 64"
    frames = segundos * fps + 1
    assert (frames - 1) % 8 == 0, "frames precisa ser 8n+1 (ajuste segundos*fps)"
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "ltx-2.5-22b-distilled-transformer-comfy-int8-convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "VAELoader", "inputs": {"vae_name": "ltx-2.5-video-vae-bf16.safetensors"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ltx-2.5-audio-vae-bf16.safetensors"}},
        "4": {"class_type": "CLIPLoader", "inputs": {"clip_name": "gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors", "type": "ltxv", "device": "default"}},
        "5": {"class_type": "LatentUpscaleModelLoader", "inputs": {"model_name": "ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": prompt}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["4", 0], "text": NEG}},
        "8": {"class_type": "LTXVConditioning", "inputs": {"positive": ["6", 0], "negative": ["7", 0], "frame_rate": float(fps)}},
        "9": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": w // 2, "height": h // 2, "length": frames, "batch_size": 1}},
        "10": {"class_type": "LTXVEmptyLatentAudio", "inputs": {"audio_vae": ["3", 0], "frames_number": frames, "frame_rate": fps, "batch_size": 1}},
        # estagio 1
        "11": {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["9", 0], "audio_latent": ["10", 0]}},
        "12": {"class_type": "LTXVDualCFGGuider", "inputs": {"model": ["1", 0], "positive": ["8", 0], "negative": ["8", 1], "video_cfg": 1, "audio_cfg": 1}},
        "13": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "14": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler_ancestral"}},
        "15": {"class_type": "ManualSigmas", "inputs": {"sigmas": SIGMAS_1}},
        "16": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["13", 0], "guider": ["12", 0], "sampler": ["14", 0], "sigmas": ["15", 0], "latent_image": ["11", 0]}},
        "17": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["16", 0]}},
        # upscale latente x2
        "18": {"class_type": "LTXVLatentUpsampler", "inputs": {"samples": ["17", 0], "upscale_model": ["5", 0], "vae": ["2", 0]}},
        "19": {"class_type": "LTXVConcatAVLatent", "inputs": {"video_latent": ["18", 0], "audio_latent": ["17", 1]}},
        # estagio 2 (refino)
        "20": {"class_type": "LTXVDualCFGGuider", "inputs": {"model": ["1", 0], "positive": ["8", 0], "negative": ["8", 1], "video_cfg": 1, "audio_cfg": 1}},
        "21": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}},
        "22": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler_ancestral"}},
        "23": {"class_type": "ManualSigmas", "inputs": {"sigmas": SIGMAS_2}},
        "24": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["21", 0], "guider": ["20", 0], "sampler": ["22", 0], "sigmas": ["23", 0], "latent_image": ["19", 0]}},
        "25": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["24", 0]}},
        # decodificacao
        "26": {"class_type": "VAEDecodeTiled", "inputs": {"samples": ["25", 0], "vae": ["2", 0], "tile_size": 512, "overlap": 64, "temporal_size": 16, "temporal_overlap": 8}},
        "27": {"class_type": "LTXVAudioVAEDecode", "inputs": {"samples": ["25", 1], "audio_vae": ["3", 0]}},
        "28": {"class_type": "CreateVideo", "inputs": {"images": ["26", 0], "audio": ["27", 0], "fps": float(fps)}},
        "29": {"class_type": "SaveVideo", "inputs": {"video": ["28", 0], "filename_prefix": prefix, "format": "auto", "codec": "auto"}},
    }
    if imagem_inicial:
        # imagem-para-video (template video_ltx2_5_i2v): a imagem entra no latente no estagio 1 (forca 0.7)
        # e de novo apos o upscale (forca 1.0). `imagem_inicial` e o nome do arquivo na pasta input/ do ComfyUI.
        wf["30"] = {"class_type": "LoadImage", "inputs": {"image": imagem_inicial}}
        wf["31"] = {"class_type": "ImageScale", "inputs": {"image": ["30", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}}
        wf["32"] = {"class_type": "LTXVPreprocess", "inputs": {"image": ["31", 0], "img_compression": 18}}
        wf["33"] = {"class_type": "LTXVImgToVideoInplace", "inputs": {"vae": ["2", 0], "image": ["32", 0], "latent": ["9", 0], "strength": 0.7, "bypass": False}}
        wf["34"] = {"class_type": "LTXVImgToVideoInplace", "inputs": {"vae": ["2", 0], "image": ["32", 0], "latent": ["18", 0], "strength": 1.0, "bypass": False}}
        wf["11"]["inputs"]["video_latent"] = ["33", 0]
        wf["19"]["inputs"]["video_latent"] = ["34", 0]
    return wf
