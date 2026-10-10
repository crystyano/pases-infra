"""Workflow de EDICAO do FLUX.2 klein 4B (distilled, fp8) em formato de API (ComfyUI), espelhando o
template oficial `image_flux2_klein_image_edit_4b_distilled`: a(s) imagem(ns) de referencia viram
`ReferenceLatent` no condicionamento positivo e no negativo (zerado), 4 passos, CFG 1.
Varias imagens: encadeia-se um ReferenceLatent por imagem; o tamanho de saida segue a PRIMEIRA imagem
(reduzida a ~1 megapixel). Licenca do modelo: Apache 2.0. VAE: o do repositorio Apache do klein."""

FLUX2_UNET = "flux-2-klein-4b-fp8.safetensors"
FLUX2_CLIP = "qwen_3_4b_fp8_mixed.safetensors"          # mesmo Qwen3-4B do Z-Image; template usa a versao bf16 (qwen_3_4b)
FLUX2_VAE = "flux2-klein-vae-apache.safetensors"
FLUX2_PASSOS = 4
FLUX2_CFG = 1


def wf_flux2_edit(prompt, seed, prefix, imagens, megapixels=1.0):
    """`imagens`: lista de nomes de arquivo na pasta input/ do ComfyUI (a primeira define o tamanho)."""
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": FLUX2_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": FLUX2_CLIP, "type": "flux2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": FLUX2_VAE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
    }
    pos, neg_src = ["4", 0], ["4", 0]
    zero = {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": neg_src}}
    wf["5"] = zero
    neg = ["5", 0]
    for k, nome in enumerate(imagens):
        b = 10 + k * 10
        wf[str(b)] = {"class_type": "LoadImage", "inputs": {"image": nome}}
        wf[str(b + 1)] = {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": [str(b), 0], "upscale_method": "nearest-exact", "megapixels": megapixels, "resolution_steps": 1}}
        wf[str(b + 2)] = {"class_type": "VAEEncode", "inputs": {"pixels": [str(b + 1), 0], "vae": ["3", 0]}}
        wf[str(b + 3)] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": pos, "latent": [str(b + 2), 0]}}
        wf[str(b + 4)] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": neg, "latent": [str(b + 2), 0]}}
        pos, neg = [str(b + 3), 0], [str(b + 4), 0]
    wf["90"] = {"class_type": "GetImageSize", "inputs": {"image": ["11", 0]}}
    wf["91"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": ["90", 0], "height": ["90", 1], "batch_size": 1}}
    wf["92"] = {"class_type": "Flux2Scheduler", "inputs": {"steps": FLUX2_PASSOS, "width": ["90", 0], "height": ["90", 1]}}
    wf["93"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
    wf["94"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}}
    wf["95"] = {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": pos, "negative": neg, "cfg": FLUX2_CFG}}
    wf["96"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["94", 0], "guider": ["95", 0], "sampler": ["93", 0], "sigmas": ["92", 0], "latent_image": ["91", 0]}}
    wf["97"] = {"class_type": "VAEDecode", "inputs": {"samples": ["96", 0], "vae": ["3", 0]}}
    wf["98"] = {"class_type": "SaveImage", "inputs": {"images": ["97", 0], "filename_prefix": prefix}}
    return wf


def wf_flux2_t2i(prompt, seed, prefix, w=1024, h=1024, passos=FLUX2_PASSOS, cfg=FLUX2_CFG):
    """Texto -> imagem do FLUX.2 klein 4B distilled, espelhando o template oficial
    `image_flux2_klein_text_to_image` (subgrafo "Distilled"): CFG 1, 4 passos, `euler`, negativo = condicionamento zerado.
    O template usa `flux-2-klein-4b` em bf16 (7,2 GB); aqui roda a versao fp8 (4,07 GB) do mesmo modelo distilled."""
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": FLUX2_UNET, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": FLUX2_CLIP, "type": "flux2", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": FLUX2_VAE}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "Flux2Scheduler", "inputs": {"steps": passos, "width": w, "height": h}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "9": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "10": {"class_type": "CFGGuider", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0], "cfg": cfg}},
        "11": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["9", 0], "guider": ["10", 0], "sampler": ["8", 0], "sigmas": ["7", 0], "latent_image": ["6", 0]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}},
        "13": {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": prefix}},
    }
