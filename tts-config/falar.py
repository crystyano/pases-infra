#!/srv/pases/tts/.venv/bin/python
"""Texto -> fala (Kokoro-82M, Apache 2.0), pt-BR, local, em CPU.
Uso: falar.py "Lanchinho errado." saida.wav [--voz pm_santa] [--velocidade 0.9] [--grave 0.85]
Vozes pt-BR: pm_santa, pm_alex (masculinas), pf_dora (feminina).
--grave F (0.5-1): aprofunda a voz mudando o tom por reamostragem e compensando a duracao com ffmpeg (F=0.85 => ~15% mais grave)."""
import argparse, os, subprocess, sys
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")   # um token revogado em cache faria o Hub recusar ate repositorios publicos
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
import numpy as np, soundfile as sf
from kokoro import KPipeline

ap = argparse.ArgumentParser()
ap.add_argument("texto"); ap.add_argument("saida")
ap.add_argument("--voz", default="pm_santa"); ap.add_argument("--velocidade", type=float, default=0.9)
ap.add_argument("--grave", type=float, default=1.0)
a = ap.parse_args()
pipe = KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M")
audio = np.concatenate([np.asarray(x.numpy() if hasattr(x, "numpy") else x) for _, _, x in pipe(a.texto, voice=a.voz, speed=a.velocidade)])
sf.write(a.saida, audio, 24000)
if a.grave != 1.0:
    tmp = a.saida + ".tmp.wav"; os.replace(a.saida, tmp)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-af", f"asetrate=24000*{a.grave},aresample=24000,atempo={1/a.grave}", a.saida], check=True)
    os.remove(tmp)
print(f"{a.saida}: {sf.info(a.saida).duration:.2f} s")
