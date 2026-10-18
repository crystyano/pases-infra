#!/usr/bin/env python3
"""Gera as fixtures SINTETICAS de visao do PASES-Bench (itens 3 e 4 + tarefas gerais), com gabarito conhecido.
Saida: fixtures/visao/*.png e fixtures/visao/gabarito.json. Deterministico (sementes fixas). Requer Pillow (python3 do sistema)."""
import json, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent / "fixtures" / "visao"
OUT.mkdir(parents=True, exist_ok=True)
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def fonte(t, b=False): return ImageFont.truetype(FB if b else F, t)


def nota_fiscal():
    im = Image.new("RGB", (1240, 1000), "white"); d = ImageDraw.Draw(im)
    d.rectangle([30, 30, 1210, 970], outline="black", width=3)
    d.text((60, 50), "NOTA FISCAL DE VENDA", font=fonte(40, True), fill="black")
    d.text((60, 110), "Nº 000.123.456   Série 1", font=fonte(26), fill="black")
    d.text((60, 160), "Emitente: Marcenaria Bom Encaixe Ltda", font=fonte(28), fill="black")
    d.text((60, 205), "CNPJ: 12.345.678/0001-95", font=fonte(28), fill="black")
    d.text((60, 250), "Data de emissão: 14/10/2026", font=fonte(28), fill="black")
    y = 320; d.line([60, y, 1180, y], fill="black", width=2)
    for x, t in ((60, "Descrição"), (640, "Qtd"), (760, "Valor unit."), (980, "Valor total")):
        d.text((x, y + 10), t, font=fonte(26, True), fill="black")
    itens = [("Chapa MDF branco 18 mm", 12, "189,90", "2.278,80"),
             ("Dobradiça 35 mm com amortecedor", 40, "12,50", "500,00"),
             ("Corrediça telescópica 450 mm", 10, "38,90", "389,00")]
    y += 60
    for desc, q, u, t in itens:
        d.text((60, y), desc, font=fonte(26), fill="black"); d.text((650, y), str(q), font=fonte(26), fill="black")
        d.text((760, y), "R$ " + u, font=fonte(26), fill="black"); d.text((980, y), "R$ " + t, font=fonte(26), fill="black"); y += 55
    d.line([60, y + 10, 1180, y + 10], fill="black", width=2)
    d.text((760, y + 30), "TOTAL: R$ 3.167,80", font=fonte(32, True), fill="black")
    # aparencia de digitalizada: leve rotacao, desfoque, ruido e JPEG
    im = im.rotate(1.3, resample=Image.BICUBIC, fillcolor="white").filter(ImageFilter.GaussianBlur(0.8))
    rnd = random.Random(4); px = im.load()
    for _ in range(25000):
        x, y2 = rnd.randrange(im.width), rnd.randrange(im.height); v = rnd.randrange(150, 255); px[x, y2] = (v, v, v)
    im.save(OUT / "i4_nota_fiscal.jpg", quality=60)
    return {"emitente": "Marcenaria Bom Encaixe Ltda", "cnpj": "12.345.678/0001-95", "data": "14/10/2026", "numero": "000.123.456",
            "itens_total": ["2.278,80", "500,00", "389,00"], "total": "3.167,80"}


def cota(d, x1, x2, y, texto, vertical=False):
    if not vertical:
        d.line([x1, y, x2, y], fill="black", width=2); d.line([x1, y - 10, x1, y + 10], fill="black", width=2); d.line([x2, y - 10, x2, y + 10], fill="black", width=2)
        w = d.textlength(texto, font=fonte(24)); d.text(((x1 + x2) / 2 - w / 2, y - 34), texto, font=fonte(24), fill="black")
    else:
        d.line([y, x1, y, x2], fill="black", width=2); d.line([y - 10, x1, y + 10, x1], fill="black", width=2); d.line([y - 10, x2, y + 10, x2], fill="black", width=2)
        d.text((y + 12, (x1 + x2) / 2 - 12), texto, font=fonte(24), fill="black")


def armario_frente(nome, portas):
    im = Image.new("RGB", (1200, 1000), "white"); d = ImageDraw.Draw(im)
    d.text((40, 20), "Guarda-roupa — vista frontal (cotas em mm)", font=fonte(30, True), fill="black")
    X0, X1, Y0, Y1 = 150, 1050, 180, 900; YM = 270
    d.rectangle([X0, Y0, X1, Y1], outline="black", width=4); d.line([X0, YM, X1, YM], fill="black", width=3)
    xs = [X0, X0 + 300, X0 + 600, X1]
    for x in xs[1:-1]: d.line([x, YM, x, Y1], fill="black", width=3)
    for i in range(3): d.ellipse([xs[i + 1] - 30, 560, xs[i + 1] - 18, 572], outline="black", width=2)
    cota(d, X0, X1, 130, "1800")
    for i, p in enumerate(portas): cota(d, xs[i], xs[i + 1], 950, str(p))
    cota(d, Y0, Y1, 1100, "2400", vertical=True); cota(d, Y0, YM, 80, "300", vertical=True); cota(d, YM, Y1, 80, "2100", vertical=True)
    im.save(OUT / f"{nome}.png")


def gaveteiro_lateral():
    im = Image.new("RGB", (1200, 900), "white"); d = ImageDraw.Draw(im)
    d.text((40, 20), "Gaveteiro — vista lateral em corte (cotas em mm)", font=fonte(30, True), fill="black")
    X0, X1, Y0, Y1 = 200, 900, 180, 760
    d.rectangle([X0, Y0, X1, Y1], outline="black", width=4)
    for k in range(3):
        y = Y0 + 30 + k * 190; d.rectangle([X0 + 20, y, X1 - 20, y + 150], outline="black", width=2)
        d.text((X0 + 40, y + 55), f"Gaveta {k + 1}", font=fonte(24), fill="black")
    cota(d, X0, X1, 130, "Profundidade do móvel: 550")
    cota(d, X0 + 20, X1 - 20, 820, "Profundidade da gaveta: 600")
    cota(d, Y0, Y1, 980, "720", vertical=True)
    im.save(OUT / "i3_gaveteiro_lateral.png")


def grafico():
    im = Image.new("RGB", (1100, 800), "white"); d = ImageDraw.Draw(im)
    d.text((40, 20), "Vendas de armários por mês (unidades)", font=fonte(30, True), fill="black")
    X0, Y0, Y1 = 140, 120, 700; esc = 3.0
    d.line([X0, Y0, X0, Y1], fill="black", width=3); d.line([X0, Y1, 1050, Y1], fill="black", width=3)
    for v in range(0, 181, 20):
        y = Y1 - v * esc; d.line([X0 - 10, y, X0, y], fill="black", width=2); d.text((X0 - 70, y - 14), str(v), font=fonte(22), fill="black")
        d.line([X0, y, 1050, y], fill=(225, 225, 225), width=1)
    dados = [("Jan", 120), ("Fev", 95), ("Mar", 160), ("Abr", 140), ("Mai", 110)]
    for i, (m, v) in enumerate(dados):
        x = X0 + 60 + i * 170; d.rectangle([x, Y1 - v * esc, x + 100, Y1 - 2], fill=(70, 110, 180))
        d.text((x + 28, Y1 + 15), m, font=fonte(24), fill="black")
    im.save(OUT / "geral_grafico.png")
    return {"mes_maior": "Mar", "valor_marco": 160, "valor_fevereiro": 95}


def contagem():
    im = Image.new("RGB", (1000, 800), "white"); d = ImageDraw.Draw(im); rnd = random.Random(7); usados = []
    def lugar():
        while True:
            x, y = rnd.randrange(80, 920), rnd.randrange(80, 720)
            if all((x - a) ** 2 + (y - b) ** 2 > 130 ** 2 for a, b in usados): usados.append((x, y)); return x, y
    for _ in range(7): x, y = lugar(); d.ellipse([x - 40, y - 40, x + 40, y + 40], fill=(210, 40, 40))
    for _ in range(4): x, y = lugar(); d.rectangle([x - 38, y - 38, x + 38, y + 38], fill=(40, 70, 200))
    for _ in range(2): x, y = lugar(); d.polygon([(x, y - 45), (x - 42, y + 35), (x + 42, y + 35)], fill=(40, 160, 60))
    im.save(OUT / "geral_contagem.png")
    return {"circulos_vermelhos": 7, "quadrados_azuis": 4, "triangulos_verdes": 2}


def texto():
    t = ("A marcenaria entregou três armários de cozinha na última sexta-feira. "
         "O cliente elogiou o acabamento em laca fosca, mas pediu ajustes nas dobradiças "
         "e na altura da prateleira superior, que ficou 2 cm abaixo do previsto.")
    im = Image.new("RGB", (1200, 420), (250, 248, 240)); d = ImageDraw.Draw(im)
    linhas, atual = [], ""
    for w in t.split():
        if d.textlength(atual + " " + w, font=fonte(30)) > 1120: linhas.append(atual); atual = w
        else: atual = (atual + " " + w).strip()
    linhas.append(atual)
    for i, l in enumerate(linhas): d.text((40, 40 + i * 50), l, font=fonte(30), fill=(30, 30, 30))
    im.save(OUT / "geral_texto_pt.png")
    return t


if __name__ == "__main__":
    gab = {"i4_nota_fiscal": nota_fiscal()}
    armario_frente("i3_armario_erro", [600, 600, 700]); armario_frente("i3_armario_controle", [600, 600, 600])
    gaveteiro_lateral()
    gab["i3_armario_erro"] = {"tem_erro": True, "pistas": ["1900", "1.900", "700"]}
    gab["i3_armario_controle"] = {"tem_erro": False}
    gab["i3_gaveteiro_lateral"] = {"tem_erro": True, "pistas": ["600", "550"]}
    gab["geral_grafico"] = grafico(); gab["geral_contagem"] = contagem(); gab["geral_texto_pt"] = texto()
    gab["geral_cena"] = {"imagem": "/srv/pases/comfyui/input/texugo3_n1.png", "animal": ["texugo", "honey badger", "ratel"], "quantos": 1, "cenario": ["savana", "savanna"], "quatro_patas": True}
    (OUT / "gabarito.json").write_text(json.dumps(gab, ensure_ascii=False, indent=1), encoding="utf-8")
    print("fixtures em", OUT, sorted(p.name for p in OUT.iterdir()))
