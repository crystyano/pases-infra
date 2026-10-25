"""Treinamento Ardus — extras da versao 5 (pedido do responsavel em 24/10/2026: "va alem do roteiro", mais motion graphics
"condizentes com a proposta e sem exageros" e musica de fundo sutil). Usado por montar_treinamento_props.py e _menus.py.

Motion graphics novos (tres, todos fora da explicacao, que continua fiel):
  1. cartao de capitulo com "Neste capitulo" (os temas, da `naTela` das cenas, entrando um a um) e a barra de progresso
     "Capitulo N de M" (os anteriores cheios, o atual se enchendo em laranja);
  2. mapa do treinamento na abertura: os capitulos aparecendo em duas colunas, com uma fala curta;
  3. cartao de encerramento com o logo.
Musica: trilha instrumental gerada no ACE-Step 1.5 (MIT), continua ao longo do video inteiro, baixa (-24 dB sob a voz) e
abaixando mais quando a voz fala (sidechain); entra em fusao no inicio e sai no fim.
Volume: ganho FIXO por capitulo (mede e aplica) com limitador de picos. O loudnorm dinamico dos videos anteriores subia o ganho aos poucos
depois do silencio dos cartoes, e a primeira silaba depois de cada cartao saia baixa ("pequeno corte" ouvido em 24/10/2026)."""
import json, re, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

C = {}   # constantes do script que chama (W, H, FPS, TEAL, ACENTO, ACENTO_RGB, F_*, GIRO, sh, png_texto, logo_png, assinatura_png)
def configurar(g): C.update({k: g[k] for k in ("W", "H", "FPS", "TEAL", "ACENTO", "ACENTO_RGB", "F_BLACK", "F_BOLD", "F_REG", "GIRO",
                                               "sh", "png_texto", "logo_png", "assinatura_png")})

def _fonte(nome, tam): return ImageFont.truetype(C[nome], tam)

def pilula(texto, caminho, tam=34, numero=None, largura=None):
    """Etiqueta arredondada translucida; com `numero`, o numero em laranja na frente (mapa); sem, um ponto laranja."""
    f = _fonte("F_BOLD", tam); fn = _fonte("F_BLACK", tam)
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1))); tw = int(d0.textlength(texto, font=f))
    pre = int(d0.textlength(f"{numero:02d}", font=fn)) + 22 if numero is not None else 34
    w = largura or (pre + tw + 56); h = int(tam * 1.9)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=(255, 255, 255, 34), outline=(255, 255, 255, 90), width=2)
    if numero is not None: d.text((28, h // 2), f"{numero:02d}", font=fn, fill=C["ACENTO_RGB"] + (255,), anchor="lm")
    else: d.ellipse([26, h // 2 - 7, 40, h // 2 + 7], fill=C["ACENTO_RGB"] + (255,))
    d.text((28 + pre, h // 2), texto, font=f, fill=(255, 255, 255, 255), anchor="lm"); im.save(caminho); return w, h

def topicos_do_capitulo(cenas, titulo, maximo=6):
    """Temas do capitulo = `naTela` das cenas, sem repetir o nome da aba ("Arquivo", "Aba Arquivo")."""
    vistos, out = {titulo.lower()}, []
    for s in cenas[1:]:
        t = (s.get("naTela") or "").strip()
        if t and t.lower() not in vistos and not t.startswith("Aba "): vistos.add(t.lower()); out.append(t)
    return out[:maximo]

def camada_cartao(topicos, numero, total_caps, tmp, k0, entrada="[c0]"):
    """Filtro que acrescenta ao cartao os temas (direita) e a barra de progresso (rodape). k0 = indice do proximo -i.
    Retorna (argumentos -i extras, trecho de filter_complex de `entrada` ate [v])."""
    W, H = C["W"], C["H"]; ent, fc, ult, k = [], [], entrada, k0
    xr = 1080; y = 300
    if topicos:
        cab = tmp / "c_cab.png"; C["png_texto"]("NESTE CAPÍTULO", C["F_BLACK"], 30, (242, 165, 65), sombra=False, caminho=cab)
        ent += ["-loop", "1", "-i", cab]
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st=0.9:d=0.4:alpha=1[h{k}];{ult}[h{k}]overlay=x={xr - 20}:y={y - 70}[o{k}]"); ult = f"[o{k}]"; k += 1
        for i, t in enumerate(topicos):
            p = tmp / f"c_top{i}.png"; _, h = pilula(t, p); st = 1.1 + 0.22 * i
            ent += ["-loop", "1", "-i", p]
            fc.append(f"[{k}:v]format=rgba,fade=t=in:st={st:.2f}:d=0.35:alpha=1[t{k}];"
                      f"{ult}[t{k}]overlay=x='{xr}+70*max(0,1-(t-{st:.2f})/0.35)':y={y}[o{k}]"); ult = f"[o{k}]"; k += 1; y += h + 18
    if numero and total_caps:
        seg, gap = 56, 10; x0 = 200; yb = H - 120; larg = total_caps * seg + (total_caps - 1) * gap
        im = Image.new("RGBA", (larg + 4, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((0, 0), f"Capítulo {numero} de {total_caps}", font=_fonte("F_REG", 28), fill=(230, 240, 240, 230))
        for j in range(total_caps):
            xa = j * (seg + gap); cor = (255, 255, 255, 200) if j + 1 < numero else (255, 255, 255, 60)
            d.rounded_rectangle([xa, 52, xa + seg, 60], radius=4, fill=cor)
        pb = tmp / "c_prog.png"; im.save(pb); ent += ["-loop", "1", "-i", pb]
        xa = x0 + (numero - 1) * (seg + gap)
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st=0.6:d=0.4:alpha=1[p{k}];{ult}[p{k}]overlay=x={x0}:y={yb}[o{k}];"
                  f"[o{k}]drawbox=x={xa}:y={yb + 52}:w='max(1,{seg}*min(1,max(0,(t-0.9)/0.8)))':h=8:color={C['ACENTO']}:t=fill:enable='gte(t,0.9)'[v]")
        ult = "[v]"; k += 1
    if ult != "[v]": fc.append(f"{ult}null[v]")
    return ent, ";".join(fc)

def _fundo(d, giro_ini):
    return (f"[0:v]trim=start={giro_ini:.2f}:duration={d:.2f},setpts=PTS-STARTPTS,fps={C['FPS']},scale={C['W']}:{C['H']},gblur=sigma=22,"
            f"eq=brightness=-0.08:saturation=0.7[bg0];color=c={C['TEAL']}@0.82:s={C['W']}x{C['H']}:r={C['FPS']}:d={d}[tinta];[bg0][tinta]overlay=format=auto[bg]")

def _enc(n, out): return ["-map", "[v]", "-frames:v", n, "-r", C["FPS"], "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-an", out]

def mapa(capitulos, d, out, tmp, titulo="O que você vai ver"):
    """Mapa do treinamento: titulo + os capitulos em duas colunas, entrando um a um (0,12 s entre eles), depois parados."""
    W, H = C["W"], C["H"]; n = int(round(d * C["FPS"])); tp = tmp / "mapa_tit.png"
    tw, th = C["png_texto"](titulo, C["F_BLACK"], 64, caminho=tp)
    metade = (len(capitulos) + 1) // 2; larg = 760; tam = 30 if len(capitulos) > 12 else 32
    alt = int(tam * 1.9); passo = alt + (12 if len(capitulos) > 12 else 18); y0 = int((H - metade * passo) / 2) + 60
    ent = ["-i", C["GIRO"], "-loop", "1", "-i", tp]
    fc = [_fundo(d, 3.0), f"[1:v]format=rgba,fade=t=in:st=0.1:d=0.5:alpha=1[ti];[bg][ti]overlay=x=(W-w)/2:y='{y0 - 150}-30*max(0,1-t/0.5)'[o1]"]
    ult = "[o1]"
    for i, (num, tit) in enumerate(capitulos):
        p = tmp / f"mapa_{i}.png"; pilula(tit, p, tam=tam, numero=num, largura=larg); col, lin = divmod(i, metade)
        x = (W // 2 - larg - 20) if col == 0 else (W // 2 + 20); y = y0 + lin * passo; st = 0.6 + 0.12 * i; k = i + 2
        ent += ["-loop", "1", "-i", p]
        fc.append(f"[{k}:v]format=rgba,fade=t=in:st={st:.2f}:d=0.3:alpha=1[m{k}];{ult}[m{k}]overlay=x='{x}+{-50 if col == 0 else 50}*max(0,1-(t-{st:.2f})/0.3)':y={y}[o{k}]")
        ult = f"[o{k}]"
    fc.append(f"{ult}null[v]")
    C["sh"](["ffmpeg", "-v", "error", "-y"] + ent + ["-filter_complex", ";".join(fc)] + _enc(n, out))

def encerramento(d, out, tmp, titulo, linha="Bons projetos!"):
    """Cartao final: logo crescendo, titulo do video e uma linha; tudo some em preto no fim."""
    n = int(round(d * C["FPS"])); lg = tmp / "fim_logo.png"; tp = tmp / "fim_tit.png"; lp = tmp / "fim_lin.png"
    lw, lh = C["logo_png"](190, lg); C["png_texto"](titulo, C["F_BOLD"], 54, caminho=tp)
    C["png_texto"](linha, C["F_REG"], 40, (242, 165, 65), sombra=False, caminho=lp)
    H = C["H"]; yl = int(H * 0.5 - lh - 30)
    fc = [_fundo(d, 6.0),
          f"[1:v]format=rgba,scale=w='{lw}*(0.85+0.15*min(1,t/0.6))':h=-1:eval=frame,fade=t=in:st=0:d=0.5:alpha=1[lg];"
          f"[bg][lg]overlay=x=(W-w)/2:y='{yl}+({lh}-h)/2'[a];"
          f"[2:v]format=rgba,fade=t=in:st=0.5:d=0.5:alpha=1[ti];[a][ti]overlay=x=(W-w)/2:y={int(H * 0.5 + 10)}[b];"
          f"[3:v]format=rgba,fade=t=in:st=1.0:d=0.5:alpha=1[li];[b][li]overlay=x=(W-w)/2:y={int(H * 0.5 + 100)},fade=t=out:st={d - 1.0:.2f}:d=1.0[v]"]
    C["sh"](["ffmpeg", "-v", "error", "-y", "-i", C["GIRO"], "-loop", "1", "-i", lg, "-loop", "1", "-i", tp, "-loop", "1", "-i", lp,
             "-filter_complex", ";".join(fc)] + _enc(n, out))

# ---------------------------------------------------------------- musica
MUSICA_DB = -21.0     # trilha em relacao a voz (faixas normalizadas a -16 LUFS; o sidechain abaixa mais na fala); "volume sutil"
def _dur(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)

def leito(faixas, total, out, xf=6.0):
    """Encadeia as faixas (em ordem, repetindo) com fusao de `xf` s ate cobrir `total` s."""
    seq, acc = [], 0.0
    while acc < total + 5:
        f = faixas[len(seq) % len(faixas)]; seq.append(f); acc += _dur(f) - (xf if len(seq) > 1 else 0)
    ent = sum((["-i", str(f)] for f in seq), []); fc, ult = [], "[n0]"
    for i in range(len(seq)): fc.append(f"[{i}:a]loudnorm=I=-16:LRA=7:TP=-2,aresample=48000[n{i}]")   # faixas no mesmo volume da voz antes do MUSICA_DB
    for i in range(1, len(seq)): fc.append(f"{ult}[n{i}]acrossfade=d={xf}:c1=qsin:c2=qsin[x{i}]"); ult = f"[x{i}]"
    fc.append(f"{ult}aresample=48000,aformat=channel_layouts=stereo[m]")
    C["sh"](["ffmpeg", "-v", "error", "-y"] + ent + ["-filter_complex", ";".join(fc), "-map", "[m]", "-c:a", "pcm_s16le", str(out)])

def _medir(arq, filtro_pre):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(arq), "-af", filtro_pre + "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    return json.loads(re.findall(r"\{[^{}]*\}", r.stderr)[-1])

def trilha(capitulos, bed, destino):
    """Mistura a musica sob a voz de cada capitulo (video copiado). A trilha continua de um capitulo para o outro
    (cada um pega o trecho do leito a partir do seu inicio no video completo). Volume: mede a mistura e aplica um ganho fixo ate -16 LUFS, com limitador de picos."""
    destino.mkdir(parents=True, exist_ok=True); off = 0.0; total = sum(_dur(c) for c in capitulos)
    for i, c in enumerate(capitulos):
        d = _dur(c); out = destino / c.name
        fade = []
        if i == 0: fade.append("afade=t=in:st=0:d=2.5")
        if i == len(capitulos) - 1: fade.append(f"afade=t=out:st={max(0, d - 3.5):.2f}:d=3.5")
        mus = f"[1:a]atrim=start={off:.3f}:duration={d:.3f},asetpts=PTS-STARTPTS,volume={MUSICA_DB}dB" + "".join("," + x for x in fade) + "[mu];"
        voz = "[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[vz][sc];"
        duck = "[mu][sc]sidechaincompress=threshold=0.015:ratio=5:attack=40:release=900:makeup=1[md];"
        mix = "[vz][md]amix=inputs=2:normalize=0:duration=first"
        fc = voz + mus + duck + mix
        # 1a passagem: medir a mistura; 2a: ganho fixo (linear=true)
        tmpw = destino / (c.stem + "_mix.wav")
        C["sh"](["ffmpeg", "-v", "error", "-y", "-i", c, "-i", bed, "-filter_complex", fc + "[a]", "-map", "[a]", "-c:a", "pcm_s16le", tmpw])
        g = -16.0 - float(_medir(tmpw, "")["input_i"])   # ganho fixo ate -16 LUFS; o limitador so segura os picos
        C["sh"](["ffmpeg", "-v", "error", "-y", "-i", c, "-i", tmpw, "-map", "0:v", "-map", "1:a",
                 "-af", f"volume={g:.2f}dB,alimiter=limit=0.84:attack=5:release=80:level=false,aresample=48000",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
        tmpw.unlink(); off += d; print(f"  trilha {c.name}: {d:.1f} s", flush=True)
    return total
