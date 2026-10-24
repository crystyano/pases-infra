#!/srv/pases/tts/.venv/bin/python
"""Treinamento Ardus — versao 3 (voz da v1 com fonemas corrigidos; abertura de treinamento, nao de venda).
Base: versao 2 (material em /home/pases/Treinamento-v2/Treinamento-v2, ver CORRECOES-v2.md).
Voz: Piper (pt-BR nativo, MIT/CC0) ou Kokoro, SEMPRE a partir de `narracaoVoz`, frase por frase com pausa de 0,25 s, velocidade 1,0.
Legenda: `narracao`, no tempo real de cada frase.
Cenas "fiel": midia indicada, fusao 0,3 s, naTela deslizando no canto, barra fina de progresso do capitulo.
Cenas "criativa" (abertura e cartoes): motion graphics com ffmpeg + letreiros desenhados com Pillow.
Uso: montar_treinamento_v2.py [--caps 0 1 ...] [--motor piper|kokoro] [--voz cadu] [--completo]   (capitulo 0 = abertura)
Saida: /home/pases/Treinamento-video/v2/"""
import argparse, json, os, re, subprocess, sys, textwrap, wave
from pathlib import Path
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1"); os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
from PIL import Image, ImageDraw, ImageFont

SRC = Path("/home/pases/Treinamento-v3/Treinamento-v3"); OUT = Path("/home/pases/Treinamento-video/v4")
PIPER = "/srv/pases/tts/.venv/bin/piper"; VOZES = Path("/srv/pases/tts/piper-voices")
W, H, FPS = 1920, 1080, 30
TEAL = "0x07515B"; TEAL_RGB = (7, 81, 91); ACENTO = "0xF2A541"; ACENTO_RGB = (242, 165, 65); FUNDO_DOC = "0xE9ECEF"
F_BLACK = "/usr/share/fonts/truetype/lato/Lato-Black.ttf"; F_BOLD = "/usr/share/fonts/truetype/lato/Lato-Bold.ttf"; F_REG = "/usr/share/fonts/truetype/lato/Lato-Regular.ttf"
XF = 0.3; FOLGA = 0.7; ATRASO = 0.35; PAUSA = 0.25; CARTAO = 4.0; VELOCIDADE = 0.85
GIRO = SRC / "00-abertura/02-giro.mp4"
LOGO = Path(__file__).resolve().parent / "ardus-logo-branco.png"   # logo oficial (branco, fundo transparente), enviado pelo responsavel em 19/10/2026

def sh(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode: sys.exit("ERRO:\n" + " ".join(map(str, cmd))[:800] + "\n" + r.stderr[-2000:])
    return r

def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)

def esc(t): return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")

# ---------------------------------------------------------------- voz
# Correcao FONETICA (a v1 soava melhor; so algumas palavras saiam erradas). Chave = saida do g2p do Kokoro para a palavra;
# valor = fonemas corretos (pronuncia.json do material v2). Conferido em 19/10/2026 contra o g2p real.
FONEMAS = [
    ("aɾədˈuz", "ˈaːɾdʊz"),    # Ardus antes de consoante sonora ("o Ardus mostra"): o g2p gera "uz"; faltava esta forma (5 cenas, cap. 2 em diante)
    ("aɾədˈus", "ˈaːɾdʊs"),    # Ardus -> ÁR-dus. Variante "D", ESCOLHIDA OUVINDO pelo responsavel (19/10; B, C, D e E corretas).
                               # NAO usar ʔ (ataque glotal): o modelo leu como "Chárdus".
    ("klozˈɛʧ", "klˈɔzeʧ"), ("klozˈets", "klˈɔzeʧs"),       # closet(s) -> CLÓ-set
    ("klˈikys", "klˈikɨs"), ("klˈikj", "klˈikɨ"), ("klˈiky", "klˈikɨ"),  # clique(s) -> CLÍ-que; "claique" ouvido na v3. Escolhida pela confianca do
                                                                        # Whisper em 5 frases reais: minima 0,56 (a da v3, klˈiki, dava 0,28)
    ("kˌooktˈɔp", "kˌukitˈɔpi"), ("kˌooktˈops", "kˌukitˈɔpis"),          # cooktop(s) -> cúqui-tóp
    ("ˈeŋter", "ˈeŋteɾ"), ("ˈɛsk", "ˈɛski"), ("ˈWʧ", "ˈawʧi"),           # Enter, Esc, Alt
    ("kˈoŋtrow", "koŋtrˈɔw"),                               # Control -> Contról
    ("tˈowr", "tˈuɾ"), ("lˈAˌWt", "lejˈawʧi"), ("imˈAl", "imˈeju"),     # tour, layout, e-mail
    ("xAŋdˈer", "xˈeŋdeɾ"), ("xAŋdˈeɾəs", "xˈeŋdeɾs"), ("ˈiæ", "ˈi ˈa"), # render(s), IA
    ("wˈatz ˈap", "wˈɔʦap"), ("xeˈɛʊs", "xˈius"), ("jˈow tˈuby", "jutˈubi"),  # WhatsApp, Reels, YouTube
    ("oŋlˈIŋ", "oŋlˈajni"), ("ɔflˈIŋ", "ɔflˈajni"), ("ɔkˈA", "okˈej"),  # online, offline, OK
]

def frases(t): return [f.strip() for f in re.split(r"(?<=[.!?;])\s+", t.strip()) if f.strip()]

_kok = None
def sintetizar(frase, wav, a):
    if a.motor == "piper":
        r = subprocess.run([PIPER, "-m", str(VOZES / f"pt_BR-{a.voz}-medium.onnx"), "-f", str(wav)], input=frase, capture_output=True, text=True)
        if r.returncode: sys.exit("piper: " + r.stderr[-500:])
    else:
        global _kok
        import numpy as np, soundfile as sf
        if _kok is None:
            from kokoro import KPipeline
            _kok = KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M")
        x = np.concatenate([np.asarray(y.numpy() if hasattr(y, "numpy") else y) for _, _, y in _kok(frase, voice=a.voz, speed=1.0)])
        sf.write(str(wav), x, 24000)

def falar_v3(cena, pasta, a):
    """Voz da v1: a cena inteira de uma vez, a partir de `narracao`, velocidade 0,85, com os fonemas das palavras-problema trocados.
    Com --motor chatterbox: usa os audios ja gerados por gerar_voz_chatterbox.py (voz aprovada em 19/10/2026), com o tempo de cada frase."""
    global _kok
    txt = (cena.get("narracao") or "").strip()
    if not txt: return None, 0.0, []
    if a.motor in ("chatterbox", "voxcpm"):
        w = OUT / "voz" / ("voxcpm" if a.motor == "voxcpm" else "chatterbox-qwen2") / pasta / f"{cena['id']}.wav"; mj = w.with_suffix(".json")
        if not w.exists(): sys.exit(f"falta a voz {w} (rode gerar_voz_{a.motor}.py)")
        return w, dur(w), json.loads(mj.read_text())
    d = OUT / "voz" / f"kokoro-{a.voz}-fonemas" / pasta; d.mkdir(parents=True, exist_ok=True); w = d / f"{cena['id']}.wav"
    if not w.exists():
        import numpy as np, soundfile as sf, torch
        from kokoro import KPipeline
        if _kok is None: _kok = KPipeline(lang_code="p", repo_id="hexgrad/Kokoro-82M")
        pack = _kok.load_voice(a.voz); partes = []
        for bloco in frases_longas(txt):
            ps = _kok.g2p(bloco); ps = ps[0] if isinstance(ps, tuple) else ps
            for errado, certo in FONEMAS: ps = ps.replace(errado, certo)
            out = KPipeline.infer(_kok.model, ps, pack, VELOCIDADE)
            partes.append(out.audio.cpu().numpy() if hasattr(out, "audio") else np.asarray(out))
            partes.append(np.zeros(int(0.18 * 24000), dtype=np.float32))
        sf.write(str(w), np.concatenate(partes[:-1]), 24000)
        (d / f"{cena['id']}.fonemas.txt").write_text(ps, encoding="utf-8")
    return w, dur(w), []

def frases_longas(t, limite=380):
    """Blocos de ate ~380 caracteres (o modelo aceita ate 510 fonemas), cortando em fim de frase."""
    out, cur = [], ""
    for f in frases(t):
        if len(cur) + len(f) + 1 > limite and cur: out.append(cur); cur = f
        else: cur = (cur + " " + f).strip()
    if cur: out.append(cur)
    return out

def falar(cena, pasta, a):
    """Gera a fala da cena frase por frase. Retorna (wav, duracao, [(ini, fim) de cada frase])."""
    voz = (cena.get("narracaoVoz") or cena.get("narracao") or "").strip()
    if not voz: return None, 0.0, []
    d = OUT / "voz" / f"{a.motor}-{a.voz}" / pasta; d.mkdir(parents=True, exist_ok=True)
    final = d / f"{cena['id']}.wav"; marcas = d / f"{cena['id']}.json"
    if final.exists() and marcas.exists():
        return final, dur(final), json.loads(marcas.read_text())
    partes, tempos, t = [], [], 0.0
    for i, f in enumerate(frases(voz)):
        w = d / f"{cena['id']}_f{i}.wav"; sintetizar(f, w, a); df = dur(w)
        partes.append(w); tempos.append((t, t + df)); t += df + PAUSA
    lista = d / f"{cena['id']}_lista.txt"
    sil = d / "silencio.wav"
    if not sil.exists(): sh(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono", "-t", str(PAUSA), sil])
    with open(lista, "w") as fh:
        for i, p in enumerate(partes):
            fh.write(f"file '{p}'\n")
            if i < len(partes) - 1: fh.write(f"file '{sil}'\n")
    sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista, "-af", "aresample=48000", "-ac", "1", final])
    for p in partes: p.unlink()
    lista.unlink(); marcas.write_text(json.dumps(tempos))
    return final, dur(final), tempos

# ---------------------------------------------------------------- letreiros (Pillow)
def png_texto(texto, fonte, tam, cor=(255, 255, 255), sombra=True, caminho=None, largura_max=None):
    f = ImageFont.truetype(fonte, tam)
    linhas = textwrap.wrap(texto, largura_max) if largura_max else [texto]
    d0 = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    bbs = [d0.textbbox((0, 0), l, font=f) for l in linhas]
    lw = max(b[2] - b[0] for b in bbs); lh = int(tam * 1.18)
    im = Image.new("RGBA", (lw + 40, lh * len(linhas) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, l in enumerate(linhas):
        if sombra: d.text((22, 22 + i * lh), l, font=f, fill=(0, 0, 0, 110))
        d.text((20, 20 + i * lh), l, font=f, fill=cor + (255,))
    im.save(caminho); return im.size

# ---------------------------------------------------------------- cenas
def lower_third(texto, ini_global, total):
    """naTela deslizando da esquerda (0,45 s), some aos 3,2 s; barra de progresso fina no rodape."""
    t = esc(texto); f = []
    if texto:
        f.append(f"drawtext=fontfile={F_BOLD}:text='{t}':fontsize=40:fontcolor=white:"
                 f"x='if(lt(t,0.45),70-520*pow(1-t/0.45,2),70)':y=h-150:box=1:boxcolor={TEAL}@0.9:boxborderw=18:"
                 f"alpha='if(lt(t,0.3),t/0.3,if(lt(t,2.7),1,if(lt(t,3.2),(3.2-t)/0.5,0)))'")
        f.append(f"drawbox=x='if(lt(t,0.45),52-520*pow(1-t/0.45,2),52)':y=ih-168:w=8:h=76:color={ACENTO}:t=fill:"
                 f"enable='lt(t,3.2)'")
    if total:
        f.append(f"drawbox=x=0:y=ih-5:w='max(1,{W}*({ini_global:.3f}+t)/{total:.3f})':h=5:color={ACENTO}@0.85:t=fill")
    return ",".join(f)

def cena_fiel(s, d, out, ini_global, total):
    n = int(round(d * FPS)); src = SRC / s["arquivo"]
    enc = ["-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", out]
    lt = lower_third(s.get("naTela", ""), ini_global, total)
    if s["tipo"] == "video":
        pad = max(0.0, d - dur(src))
        vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={FUNDO_DOC},fps={FPS},tpad=stop_mode=clone:stop_duration={pad:.3f}"
        sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", vf + ("," + lt if lt else ""), "-frames:v", n] + enc); return
    # Foto PARADA (o zoom lento parecia baixo FPS, avaliacao de 19/10). Se o roteiro pede foco (`zoom`), CORTE DIRETO para o detalhe
    # ampliado, depois de mostrar a tela inteira por ~40 % da cena (min. 2 s, deixando ao menos 1,5 s de detalhe).
    base = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={FUNDO_DOC},fps={FPS},setsar=1"
    z = s.get("zoom")
    if z and d >= 3.5:
        e = z.get("escala", 1.15); zx, zy = z.get("x", 0.5), z.get("y", 0.5); t1 = min(max(2.0, 0.4 * d), d - 1.5)
        vf = (f"[0:v]{base},split[a][b];[b]crop=iw/{e}:ih/{e}:(iw-iw/{e})*{zx}:(ih-ih/{e})*{zy},scale={W}:{H}:flags=lanczos[z];"
              f"[a][z]overlay=0:0:enable='gte(t,{t1:.2f})'" + ("," + lt if lt else "") + "[v]")
        sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", src, "-filter_complex", vf, "-map", "[v]", "-frames:v", n] + enc)
    else:
        sh(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", src, "-vf", base + ("," + lt if lt else ""), "-frames:v", n] + enc)

def logo_png(altura, caminho):
    im = Image.open(LOGO).convert("RGBA"); w = int(im.width * altura / im.height); im.resize((w, altura), Image.LANCZOS).save(caminho); return w, altura

def assinatura_png(texto, caminho, altura=46):
    """Logo pequeno + texto ao lado (substitui o nome escrito 'Ardus' nos cartoes)."""
    lg = Image.open(LOGO).convert("RGBA"); lw = int(lg.width * altura / lg.height); lg = lg.resize((lw, altura), Image.LANCZOS)
    f = ImageFont.truetype(F_REG, int(altura * 0.72)); tw = int(ImageDraw.Draw(Image.new("RGBA", (1, 1))).textlength(texto, font=f))
    m = 20  # mesma margem dos letreiros de texto, para alinhar com o numero e o titulo
    im = Image.new("RGBA", (m + lw + 28 + tw + 40, altura + 20), (0, 0, 0, 0)); im.alpha_composite(lg, (m, 10))
    d = ImageDraw.Draw(im); d.line([(m + lw + 14, 14), (m + lw + 14, altura + 6)], fill=(230, 240, 240, 160), width=2)
    d.text((m + lw + 28, 10 + int(altura * 0.12)), texto, font=f, fill=(230, 240, 240, 255)); im.save(caminho); return im.size

def cartao(numero, titulo, d, out, tmp, subtitulo="Treinamento para projetistas", giro_ini=0.0):
    """Cartao de capitulo: trecho desfocado do giro + tinta verde-petroleo; numero grande crescendo; titulo deslizando; linha se desenhando."""
    n = int(round(d * FPS))
    num_png = tmp / "c_num.png"; tit_png = tmp / "c_tit.png"; sub_png = tmp / "c_sub.png"
    if numero == "LOGO": nw, nh = logo_png(230, num_png)          # abertura: o logo no lugar do numero
    else: nw, nh = png_texto(f"{numero:02d}", F_BLACK, 260, ACENTO_RGB, caminho=num_png)
    tw, th = png_texto(titulo, F_BOLD, 66, caminho=tit_png, largura_max=34)
    if numero == "LOGO": sw, sh_ = png_texto(subtitulo, F_REG, 34, (230, 240, 240), sombra=False, caminho=sub_png)
    else: sw, sh_ = assinatura_png(subtitulo, sub_png)            # capitulos: logo pequeno + "Treinamento para projetistas"
    x0 = 180; yn = int(H * 0.5 - nh - 10); yt = int(H * 0.5 + 10)
    fc = (f"[0:v]trim=start={giro_ini:.2f}:duration={d:.2f},setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H},gblur=sigma=22,eq=brightness=-0.08:saturation=0.7[bg0];"
          f"color=c={TEAL}@0.78:s={W}x{H}:r={FPS}:d={d}[tinta];[bg0][tinta]overlay=format=auto[bg];"
          f"[1:v]format=rgba,scale=w='{nw}*(0.82+0.18*min(1,t/0.55))':h=-1:eval=frame,fade=t=in:st=0:d=0.45:alpha=1[num];"
          f"[2:v]format=rgba,fade=t=in:st=0.35:d=0.5:alpha=1[tit];"
          f"[3:v]format=rgba,fade=t=in:st=0.9:d=0.5:alpha=1[sub];"
          f"[bg][num]overlay=x={x0}:y='{yn}+({nh}-h)':shortest=0[a];"
          f"[a][tit]overlay=x='{x0}-60*max(0,1-(t-0.35)/0.5)':y={yt}[b];"
          f"[b][sub]overlay=x={x0}:y={yt + th + 30}[c];"
          f"[c]drawbox=x={x0 + 20}:y={yt - 8}:w='max(1,{min(tw, 900)}*min(1,max(0,(t-0.5)/0.7)))':h=6:color={ACENTO}:t=fill:enable='gte(t,0.5)'[v]")
    sh(["ffmpeg", "-v", "error", "-y", "-i", GIRO, "-loop", "1", "-i", num_png, "-loop", "1", "-i", tit_png, "-loop", "1", "-i", sub_png,
        "-filter_complex", fc, "-map", "[v]", "-frames:v", n, "-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", out])

def letreiro_sobre(src, d, out, texto, tmp, velocidade=1.0, ini=0.0, grande=True, ken=None, cortes=None):
    """Video (ou foto) da abertura com letreiro animado (escala + fusao) e leve vinheta."""
    n = int(round(d * FPS)); png = tmp / f"let_{abs(hash(texto)) % 10**6}.png"
    if texto: lw, lh = png_texto(texto, F_BLACK if grande else F_BOLD, 190 if grande else 76, caminho=png)
    if ken is not None:  # foto (ken=0: parada)
        S = 2; base = (f"[0:v]scale={W*S}:{H*S}:force_original_aspect_ratio=decrease,pad={W*S}:{H*S}:(ow-iw)/2:(oh-ih)/2:color={FUNDO_DOC},"
                       f"zoompan=z='1+{ken}*on/{max(1,n-1)}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={n}:s={W}x{H}:fps={FPS}[bg]")
        entrada = ["-loop", "1", "-i", src]
    else:
        if cortes:  # junta trechos (ex.: tirar o meio parado do passeio), na velocidade normal
            seg = ";".join(f"[0:v]trim={c0}:{c1},setpts=PTS-STARTPTS[s{j}]" for j, (c0, c1) in enumerate(cortes))
            base = seg + ";" + "".join(f"[s{j}]" for j in range(len(cortes))) + f"concat=n={len(cortes)}:v=1:a=0,fps={FPS},scale={W}:{H},vignette=PI/5,tpad=stop_mode=clone:stop_duration=5[bg]"
        else:
            base = f"[0:v]trim=start={ini:.2f},setpts=(PTS-STARTPTS)/{velocidade},fps={FPS},scale={W}:{H},vignette=PI/5,tpad=stop_mode=clone:stop_duration=5[bg]"
        entrada = ["-i", src]
    if texto:
        y = "h*0.14" if grande else f"{H - 230}"
        fc = (base + f";[1:v]format=rgba,scale=w='{lw}*(0.85+0.15*min(1,max(0,t-0.25)/0.6))':h=-1:eval=frame,fade=t=in:st=0.25:d=0.6:alpha=1[t];"
              f"[bg][t]overlay=x='(W-w)/2' if 0 else (W-w)/2:y={y}[v]").replace("x='(W-w)/2' if 0 else (W-w)/2", "x=(W-w)/2")
        sh(["ffmpeg", "-v", "error", "-y"] + entrada + ["-loop", "1", "-i", png, "-filter_complex", fc, "-map", "[v]", "-frames:v", n,
            "-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", out])
    else:
        sh(["ffmpeg", "-v", "error", "-y"] + entrada + ["-filter_complex", base.replace("[bg]", "[v]"), "-map", "[v]", "-frames:v", n,
            "-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", out])

def montagem_rapida(imgs, d, out, tmp, texto, rotulos=None):
    """Cortes pelas imagens (zoom leve em cada uma, deslize entre elas). Com `rotulos`, cada imagem leva o nome da etapa
    (faixa verde-petroleo embaixo, entrando deslizando); sem rotulos, um letreiro fixo."""
    k = len(imgs); seg = (d + 0.25 * (k - 1)) / k; parts = []
    for i, im in enumerate(imgs):
        p = tmp / f"m{i}.mp4"; letreiro_sobre(SRC / im, seg, p, "", tmp, ken=0.0)  # parada: sem zoom lento
        if rotulos:
            q = tmp / f"m{i}r.mp4"; t = esc(rotulos[i])
            vf = (f"drawbox=x=0:y=ih-200:w=iw:h=120:color={TEAL}@0.85:t=fill,"
                  f"drawtext=fontfile={F_BOLD}:text='{t}':fontsize=54:fontcolor=white:x='if(lt(t,0.4),120-200*pow(1-t/0.4,2),120)':y=h-176:"
                  f"alpha='min(1,t/0.35)',drawbox=x=96:y=ih-176:w=8:h=72:color={ACENTO}:t=fill")
            sh(["ffmpeg", "-v", "error", "-y", "-i", p, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", q]); p = q
        parts.append(p)
    ent, fc, ult, off = [], [], "0:v", 0.0
    for p in parts: ent += ["-i", p]
    for i in range(1, k):
        off += seg - 0.25; tr = "slideleft" if i % 2 else "slideup"
        fc.append(f"[{ult}][{i}:v]xfade=transition={tr}:duration=0.25:offset={off:.3f}[x{i}]"); ult = f"x{i}"
    if rotulos:
        fc.append(f"[{ult}]null[v]"); extra = []
    else:
        png = tmp / "let_monta.png"; lw, lh = png_texto(texto, F_BLACK, 84, caminho=png); extra = ["-loop", "1", "-i", png]
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st=0.2:d=0.5:alpha=1[t];"
                  f"[{ult}]drawbox=x=0:y={H-260}:w={W}:h=170:color={TEAL}@0.82:t=fill:enable='gte(t,0.15)'[b];"
                  f"[b][t]overlay=x=(W-w)/2:y='{H-250}+40*max(0,1-(t-0.2)/0.5)'[v]")
    sh(["ffmpeg", "-v", "error", "-y"] + ent + extra + ["-filter_complex", ";".join(fc), "-map", "[v]",
        "-frames:v", int(round(d * FPS)), "-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", out])

# ---------------------------------------------------------------- capitulo
def srt_t(t):
    h, r = divmod(max(0, t), 3600); m, s = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}"

def capitulo(numero, titulo, pasta, cenas, a, abertura=False):
    tmp = OUT / "tmp" / pasta; tmp.mkdir(parents=True, exist_ok=True)
    falas = [falar_v3(s, pasta, a) for s in cenas]
    durs = []
    for s, (w, f, _) in zip(cenas, falas):
        if s["tipo"] == "titulo": d = CARTAO
        elif abertura and s["id"] in ("00-01", "00-02"): d = ATRASO + f + 1.0
        elif s.get("montagem"): d = max(len(s["montagem"]) * 1.2, ATRASO + f + 0.8)
        elif s["tipo"] == "video": d = max(dur(SRC / s["arquivo"]), ATRASO + f + FOLGA)
        else: d = max(3.0, ATRASO + f + FOLGA)
        durs.append(d)
    xf = [0.45 if abertura else XF] * len(cenas)
    tot = [d + (xf[i] if i < len(cenas) - 1 else 0) for i, d in enumerate(durs)]
    inicios, acc = [], 0.0
    for i, d in enumerate(tot): inicios.append(acc); acc += d - (xf[i] if i < len(tot) - 1 else 0)
    total = acc; vids = []
    for i, s in enumerate(cenas):
        out = tmp / f"cena_{i:02d}.mp4"; d = tot[i]
        if s["tipo"] == "titulo":
            if abertura: cartao("LOGO", "Treinamento para projetistas", d, out, tmp, subtitulo="17 capítulos curtos, passo a passo", giro_ini=2.0)
            else:
                t = re.sub(r"^\d+\.\s*", "", s["naTela"]); cartao(numero, t, d, out, tmp, giro_ini=(numero * 0.7) % 7)
        elif abertura and s["id"] == "00-01": letreiro_sobre(SRC / s["arquivo"], d, out, "", tmp, cortes=[(0, 3.0), (10.6, 14.0)])  # medido: parado de 3 a 11 s
        elif abertura and s["id"] == "00-02": letreiro_sobre(SRC / s["arquivo"], d, out, "Ardus", tmp, velocidade=1.1)
        elif s.get("montagem"): montagem_rapida(s["montagem"], d, out, tmp, s.get("naTela") or "", rotulos=s.get("rotulos"))
        elif abertura: letreiro_sobre(SRC / s["arquivo"], d, out, s.get("naTela", ""), tmp, grande=False)
        else: cena_fiel(s, d, out, inicios[i], total)
        vids.append(out)
    ent, fc, ult = [], [], "0:v"
    for v in vids: ent += ["-i", v]
    for i in range(1, len(vids)):
        tr = ("fadeblack" if cenas[i]["tipo"] == "titulo" else "smoothleft") if abertura else "fade"
        fc.append(f"[{ult}][{i}:v]xfade=transition={tr}:duration={xf[i-1]}:offset={inicios[i]:.3f}[v{i}]"); ult = f"v{i}"
    aud, k = [], len(vids)
    for i, (w, f, _) in enumerate(falas):
        if w:
            ent += ["-i", w]; ms = int((inicios[i] + ATRASO) * 1000)
            fc.append(f"[{k}:a]adelay={ms}|{ms},aresample=48000[a{k}]"); aud.append(f"[a{k}]"); k += 1
    fc.append(f"{''.join(aud)}amix=inputs={len(aud)}:normalize=0,apad=whole_dur={total:.3f},atrim=0:{total:.3f},loudnorm=I=-16:TP=-1.5:LRA=11[ao]")
    dest = OUT / "capitulos" / f"{pasta}.mp4"; dest.parent.mkdir(parents=True, exist_ok=True)
    sh(["ffmpeg", "-v", "error", "-y"] + ent + ["-filter_complex", ";".join(fc), "-map", f"[{ult}]" if len(vids) > 1 else "0:v", "-map", "[ao]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", FPS, "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-movflags", "+faststart", dest])
    # legenda: texto de `narracao` (grafia certa), uma entrada por frase, no tempo real de cada frase gerada
    ln, nn = [], 1
    for i, (s, (w, f, marcas)) in enumerate(zip(cenas, falas)):
        if not w: continue
        fl = frases(s.get("narracao") or "")
        if not (marcas and len(marcas) == len(fl)):  # sem tempo por frase (Kokoro): distribui pelo numero de caracteres
            tc = sum(len(x) for x in fl); t0 = 0.0; marcas = []
            for x in fl: dt = f * len(x) / tc; marcas.append((t0, t0 + dt - 0.05)); t0 += dt
        for txt, (t1, t2) in zip(fl, marcas):
            b = inicios[i] + ATRASO
            # blocos de no maximo 2 linhas (~84 caracteres), cortados em pontuacao; tempo repartido dentro da frase
            partes = [x.strip() for x in re.split(r"(?<=[,:;])\s+", txt) if x.strip()]; blocos, cur = [], ""
            for x in partes:
                if cur and len(textwrap.wrap(cur + " " + x, 44)) > 2: blocos.append(cur); cur = x
                else: cur = (cur + " " + x).strip()
            if cur: blocos.append(cur)
            blocos = [y for x in blocos for y in ([" ".join(textwrap.wrap(x, 44)[k:k+2]) for k in range(0, len(textwrap.wrap(x, 44)), 2)])]  # trecho longo: 2 linhas por bloco
            tot = sum(len(x) for x in blocos); tt = t1
            for bl in blocos:
                dt = (t2 - t1) * len(bl) / tot
                ln.append(f"{nn}\n{srt_t(b + tt)} --> {srt_t(b + tt + dt - 0.04)}\n" + "\n".join(textwrap.wrap(bl, 44)) + "\n"); nn += 1; tt += dt
    (OUT / "legendas").mkdir(exist_ok=True); (OUT / "legendas" / f"{pasta}.srt").write_text("\n".join(ln), encoding="utf-8")
    return dest, total

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--caps", nargs="*", type=int); ap.add_argument("--motor", default="voxcpm")
    ap.add_argument("--voz", default="pm_alex"); ap.add_argument("--completo", action="store_true"); a = ap.parse_args()
    rot = json.loads((SRC / "roteiro.json").read_text(encoding="utf-8"))
    # Abertura de TREINAMENTO (pedido do responsavel em 19/10/2026: a da v2 soava como venda). Texto da v1, aprovado.
    m = [c for c in rot["abertura"]["cenas"] if c.get("montagem")][0]["montagem"]
    abertura = [
        {"id": "A-01", "tipo": "titulo", "naTela": "Ardus — treinamento para projetistas", "narracao": ""},
        {"id": "A-02", "tipo": "foto", "montagem": m, "naTela": "",
         "rotulos": ["Paredes do zero", "Módulos e aéreos", "Materiais e tampo", "Orçamento", "Proposta para o cliente", "Caderno executivo da obra"],
         "narracao": "Bem-vindo ao treinamento do Ardus. Nos próximos capítulos você vai ver, passo a passo, como criar um projeto de móveis planejados: "
                     "do ambiente às medidas, dos materiais ao orçamento, da proposta para o cliente ao caderno executivo da obra. "
                     "Você vai montar uma cozinha do zero, capítulo por capítulo."},
    ]
    todos = [(0, "Abertura", "00-abertura", abertura, True)] + \
            [(c["numero"], c["titulo"], c["pasta"], c["cenas"], False) for c in rot["capitulos"]]
    for num, tit, pasta, cenas, ab in todos:
        if a.caps is None or num in a.caps:
            d, t = capitulo(num, tit, pasta, cenas, a, abertura=ab); print(f"{d.name}: {t:.1f} s", flush=True)
    if a.completo:
        lst = OUT / "tmp" / "lista.txt"; lst.write_text("".join(f"file '{OUT / 'capitulos' / (p + '.mp4')}'\n" for _, _, p, _, _ in todos))
        fim = OUT / "Ardus_Treinamento_v4_completo.mp4"
        sh(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", "-movflags", "+faststart", fim])
        print(f"{fim.name}: {dur(fim):.1f} s")
