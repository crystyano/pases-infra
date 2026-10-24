#!/usr/bin/env python3
"""Acelera os videos do treinamento (imagem e voz, mantendo o tom com atempo) e ajusta as legendas .srt.
Pedido do responsavel em 20/10/2026: 1,25x "nao perde nada e fica bem mais fluido" (testado num player).
Uso: acelerar.py ORIGEM DESTINO [fator]   (ORIGEM com capitulos/, legendas/ e *_completo.mp4)"""
import re, subprocess, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2]); k = float(sys.argv[3]) if len(sys.argv) > 3 else 1.25
def acelerar(a, b):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(a), "-filter_complex", f"[0:v]setpts=PTS/{k},fps=30[v];[0:a]atempo={k}[a]",
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", str(b)], check=True)
def t2s(t): h, m, s = t.split(":"); s, ms = s.split(","); return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
def s2t(x): h, r = divmod(x, 3600); m, s = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"
for f in sorted((src / "capitulos").glob("*.mp4")): acelerar(f, dst / "capitulos" / f.name); print(f.name, flush=True)
for f in sorted((src / "legendas").glob("*.srt")):
    txt = re.sub(r"(\d\d:\d\d:\d\d,\d\d\d)", lambda m: s2t(t2s(m.group(1)) / k), f.read_text(encoding="utf-8"))
    (dst / "legendas" / f.name).write_text(txt, encoding="utf-8")
for f in src.glob("*_completo.mp4"): acelerar(f, dst / f.name); print(f.name)
