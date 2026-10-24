#!/srv/pases/tts/.venv/bin/python
"""Monta o video de treinamento do Ardus a partir do roteiro.json (material em /home/pases/Treinamento).
Ferramentas locais: Kokoro-82M (voz pt-BR, Apache 2.0) + ffmpeg (cartoes, Ken Burns, congelar quadro, texto na tela, fusoes).
O TEMPO de cada cena vem da fala real gerada (nao da estimativa do roteiro): cena = max(midia, fala + folga).
Uso: montar_treinamento.py [--caps 1 2 ...] [--voz pm_alex] [--velocidade 0.85] [--sem-voz-cache]
Saida: /home/pases/Treinamento-video/{capitulos/NN-*.mp4, legendas/NN-*.srt, Ardus_Treinamento_completo.mp4}"""
import argparse, json, os, re, subprocess, sys, textwrap
from pathlib import Path
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1"); os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

SRC = Path("/home/pases/Treinamento"); OUT = Path("/home/pases/Treinamento-video")
W, H, FPS = 1920, 1080, 30
COR_TITULO = "0x07515B"; FUNDO_DOC = "0xE9ECEF"
FONTE = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"; FONTE_REG = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
XF = 0.3            # fusao entre cenas
FOLGA = 0.7         # silencio depois da fala antes da proxima cena
ATRASO = 0.35       # a fala comeca um pouco depois do inicio da cena
TITULO_S = 3.5
PRONUNCIA = [(r"\bRender IA\b", "Render com inteligência artificial"), (r"\btour\b", "túr"), (r"\bcooktop\b", "cúqui tóp")]

def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode: sys.exit("ERRO ffmpeg:\n" + " ".join(map(str, cmd))[:600] + "\n" + r.stderr[-1500:])
    return r

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)

def esc(t):  # texto para drawtext
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")

_pipe = None
def falar(texto, wav, voz, vel):
    global _pipe
    if wav.exists(): return dur(wav)
    import numpy as np, soundfile as sf
    if _pipe is None:
        from kokoro import KPipeline
        _pipe = KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M")
    # so na VOZ (a legenda mantem o texto original); testado com o Whisper em 19/10/2026
    for a_, b_ in PRONUNCIA: texto = re.sub(a_, b_, texto, flags=re.I)
    a = np.concatenate([np.asarray(x.numpy() if hasattr(x, "numpy") else x) for _, _, x in _pipe(texto, voice=voz, speed=vel)])
    wav.parent.mkdir(parents=True, exist_ok=True); sf.write(str(wav), a, 24000)
    return dur(wav)

def texto_na_tela(t):
    t = esc(t)
    return (f"drawtext=fontfile={FONTE}:text='{t}':fontsize=40:fontcolor=white:x=70:y=h-140:"
            f"box=1:boxcolor=0x07515B@0.88:boxborderw=18:alpha='if(lt(t,0.3),t/0.3,if(lt(t,2.7),1,if(lt(t,3.2),(3.2-t)/0.5,0)))'")

def cena(s, d, tmp, idx):
    """Renderiza uma cena em video (sem audio) com duracao d."""
    out = tmp / f"cena_{idx:02d}.mp4"; n = int(round(d * FPS))
    base = ["ffmpeg", "-v", "error", "-y"]
    enc = ["-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", str(out)]
    if s["tipo"] == "titulo":
        txt = esc(s["naTela"])
        vf = (f"drawtext=fontfile={FONTE}:text='{txt}':fontsize=76:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2,"
              f"drawtext=fontfile={FONTE_REG}:text='Ardus — treinamento para projetistas':fontsize=34:fontcolor=white@0.75:x=(w-text_w)/2:y=h/2+90")
        sh(base + ["-f", "lavfi", "-i", f"color=c={COR_TITULO}:s={W}x{H}:r={FPS}:d={d}", "-vf", vf, "-frames:v", str(n)] + enc); return out
    src = SRC / s["arquivo"]
    if s["tipo"] == "video":
        clip = dur(src); pad = max(0.0, d - clip)
        vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={FUNDO_DOC},fps={FPS},tpad=stop_mode=clone:stop_duration={pad:.3f}"
        if s.get("naTela"): vf += "," + texto_na_tela(s["naTela"])
        sh(base + ["-i", str(src), "-vf", vf, "-frames:v", str(n)] + enc); return out
    # foto: encaixa em 1920x1080 e faz zoom lento (Ken Burns) ate a regiao indicada
    z = s.get("zoom") or {}; esc_max = z.get("escala", 1.08); zx, zy = z.get("x", 0.5), z.get("y", 0.5)
    S = 2  # superamostragem para o zoom nao tremer
    pre = f"scale={W*S}:{H*S}:force_original_aspect_ratio=decrease,pad={W*S}:{H*S}:(ow-iw)/2:(oh-ih)/2:color={FUNDO_DOC}"
    zexp = f"1+({esc_max}-1)*on/{max(1,n-1)}"
    xexp = f"(iw-iw/zoom)*{zx}"; yexp = f"(ih-ih/zoom)*{zy}"
    vf = f"{pre},zoompan=z='{zexp}':x='{xexp}':y='{yexp}':d={n}:s={W}x{H}:fps={FPS}"
    if s.get("naTela"): vf += "," + texto_na_tela(s["naTela"])
    sh(base + ["-loop", "1", "-i", str(src), "-vf", vf, "-frames:v", str(n)] + enc); return out

def blocos_legenda(txt, d_fala, t0):
    """Divide a fala em blocos de ate ~2 linhas e distribui o tempo pelo numero de caracteres."""
    partes = [p.strip() for p in re.split(r"(?<=[.;:!?,])\s+", txt) if p.strip()]
    blocos, atual = [], ""
    for p in partes:
        if len(atual) + len(p) + 1 <= 84: atual = (atual + " " + p).strip()
        else:
            if atual: blocos.append(atual)
            atual = p
    if atual: blocos.append(atual)
    tot = sum(len(b) for b in blocos); t = t0; res = []
    for b in blocos:
        dt = d_fala * len(b) / tot; res.append((t, t + dt - 0.05, "\n".join(textwrap.wrap(b, 44)))); t += dt
    return res

def srt_tempo(t):
    h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s-int(s))*1000)):03d}"

def capitulo(cap, a, extra=None):
    nome = cap["pasta"]; tmp = OUT / "tmp" / nome; tmp.mkdir(parents=True, exist_ok=True)
    cenas = list(cap["cenas"]); falas, durs = [], []
    if extra: cenas = [extra] + cenas
    for i, s in enumerate(cenas):
        txt = (s.get("narracao") or "").strip()
        f = falar(txt, OUT / "voz" / nome / f"{s['id']}.wav", a.voz, a.velocidade) if txt else 0.0
        if s["tipo"] == "titulo": d = TITULO_S
        elif s["tipo"] == "video": d = max(dur(SRC / s["arquivo"]), ATRASO + f + FOLGA)
        else: d = max(3.0, ATRASO + f + FOLGA)
        falas.append(f); durs.append(d + (XF if i < len(cenas) - 1 else 0))  # cada cena "empresta" XF para a fusao
    vids = [cena(s, durs[i], tmp, i) for i, s in enumerate(cenas)]
    # encadeia com xfade; calcula o inicio de cada cena no capitulo
    inicios, acc = [], 0.0
    for i, d in enumerate(durs): inicios.append(acc); acc += d - (XF if i < len(durs) - 1 else 0)
    total = acc
    entradas, fc, ult = [], [], "0:v"
    for v in vids: entradas += ["-i", str(v)]
    for i in range(1, len(vids)):
        lab = f"v{i}"; fc.append(f"[{ult}][{i}:v]xfade=transition=fade:duration={XF}:offset={inicios[i]:.3f}[{lab}]"); ult = lab
    # audio: cada fala posicionada no inicio da cena + ATRASO
    aud_in, mix = [], []
    k = len(vids)
    for i, s in enumerate(cenas):
        if falas[i] > 0:
            aud_in += ["-i", str(OUT / "voz" / nome / f"{s['id']}.wav")]
            ms = int((inicios[i] + ATRASO) * 1000); mix.append(f"[{k}:a]adelay={ms}|{ms},aresample=48000[a{k}]"); k += 1
    labs = "".join(f"[a{j}]" for j in range(len(vids), k))
    mix.append(f"{labs}amix=inputs={k-len(vids)}:normalize=0,apad=whole_dur={total:.3f},atrim=0:{total:.3f},loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    destino = OUT / "capitulos" / f"{nome}.mp4"; destino.parent.mkdir(parents=True, exist_ok=True)
    vmap = f"[{ult}]" if len(vids) > 1 else "0:v"
    sh(["ffmpeg", "-v", "error", "-y"] + entradas + aud_in + ["-filter_complex", ";".join(fc + mix), "-map", vmap, "-map", "[aout]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", str(destino)])
    # legenda .srt no tempo real da fala
    linhas, n = [], 1
    for i, s in enumerate(cenas):
        if falas[i] > 0:
            for t1, t2, t in blocos_legenda(s["narracao"], falas[i], inicios[i] + ATRASO):
                linhas.append(f"{n}\n{srt_tempo(t1)} --> {srt_tempo(t2)}\n{t}\n"); n += 1
    (OUT / "legendas").mkdir(exist_ok=True); (OUT / "legendas" / f"{nome}.srt").write_text("\n".join(linhas), encoding="utf-8")
    return destino, total

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--caps", nargs="*", type=int); ap.add_argument("--voz", default="pm_alex")
    ap.add_argument("--velocidade", type=float, default=0.85); ap.add_argument("--completo", action="store_true"); a = ap.parse_args()
    rot = json.loads((SRC / "roteiro.json").read_text(encoding="utf-8"))
    caps = [c for c in rot["capitulos"] if not a.caps or c["numero"] in a.caps]
    res = []
    for c in caps:
        extra = None
        if c["numero"] == 1:  # abertura sobre o video que o proprio Ardus gerou
            extra = {"id": "00-abertura", "tipo": "video", "arquivo": "14-imagens-e-video/video-do-projeto-horizontal.mp4",
                     "naTela": "", "narracao": rot["abertura"]["narracao"]}
        d, t = capitulo(c, a, extra); res.append((d, t)); print(f"{d.name}: {t:.1f} s", flush=True)
    if a.completo:
        lst = OUT / "tmp" / "lista.txt"
        lst.write_text("".join(f"file '{OUT / 'capitulos' / (c['pasta'] + '.mp4')}'\n" for c in rot["capitulos"]))
        fim = OUT / "Ardus_Treinamento_completo.mp4"
        sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(fim)])
        print(f"{fim.name}: {dur(fim):.1f} s")
