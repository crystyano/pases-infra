"""Workflow do Qwen-Image 2.1 em formato de API (ComfyUI), espelhando o template oficial
`image_qwen_image_2_1_t2i` (prompt enhancer DESLIGADO, como no template).
Licenca: Qwen Research (so uso nao comercial: pesquisa/avaliacao) - ver Cap. 8A.3 e ADR-009."""

QWEN_PASSOS = 25      # template: 25 (pipeline oficial usa ~40-50)
QWEN_CFG = 1          # oficial: manter 1 (negativo e ignorado com cfg 1)


def wf_qwen(prompt, seed, prefix, w=1024, h=1024, passos=QWEN_PASSOS):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "QwenImage21Cache", "inputs": {"model": ["1", 0], "device": "auto", "dtype": "default"}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors", "type": "qwen_image", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "5": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["3", 0], "prompt": prompt, "negative_prompt": "", "resolution": 1024}},
        "6": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["2", 0], "positive": ["5", 0], "negative": ["5", 1], "latent_image": ["6", 0],
              "seed": seed, "steps": passos, "cfg": QWEN_CFG, "sampler_name": "euler", "scheduler": "simple", "denoise": 1}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["4", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
    }
