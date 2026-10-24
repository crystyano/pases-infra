#!/srv/pases/tts-qwen/.venv/bin/python
"""Qwen3-TTS 1.7B (Apache 2.0): voz pronta (CustomVoice) ou voz criada por descricao (VoiceDesign), em portugues.
Uso: qwen_tts_falar.py texto.txt saida.wav --modo pronta --falante NOME [--instrucao "..."]
     qwen_tts_falar.py texto.txt saida.wav --modo design --instrucao "voz masculina brasileira, calma..."
     qwen_tts_falar.py --listar      (falantes e idiomas suportados)"""
import argparse, os
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
import torch, soundfile as sf
from qwen_tts import Qwen3TTSModel
REPO = {"pronta": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "design": "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"}
ap = argparse.ArgumentParser(); ap.add_argument("texto", nargs="?"); ap.add_argument("saida", nargs="?")
ap.add_argument("--modo", default="pronta"); ap.add_argument("--falante"); ap.add_argument("--instrucao"); ap.add_argument("--listar", action="store_true")
ap.add_argument("--semente", type=int, default=1)
a = ap.parse_args()
m = Qwen3TTSModel.from_pretrained(REPO[a.modo], device_map="cuda:0", dtype=torch.bfloat16)
if a.listar:
    print("falantes:", m.get_supported_speakers()); print("idiomas:", m.get_supported_languages()); raise SystemExit
torch.manual_seed(a.semente)
t = open(a.texto, encoding="utf-8").read().strip() if os.path.exists(a.texto) else a.texto
if a.modo == "pronta": wavs, sr = m.generate_custom_voice(text=t, speaker=a.falante, language="Portuguese", instruct=a.instrucao)
else: wavs, sr = m.generate_voice_design(text=t, instruct=a.instrucao, language="Portuguese")
sf.write(a.saida, wavs[0], sr); print(a.saida, round(len(wavs[0]) / sr, 2), "s")
