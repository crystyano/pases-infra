FAIXAS_FRETE = [(5, 20, 35), (20, 45, 70), (float("inf"), 90, 140)]
ALIQUOTAS = {"SP": 0.18, "RJ": 0.20, "MG": 0.18}

def _totais(itens):
    subtotal = sum(i["preco"] * i["qtd"] for i in itens)
    peso = sum(i["peso_kg"] * i["qtd"] for i in itens)
    return round(subtotal, 2), peso

def _frete(peso, cliente, cupom):
    for limite, sp, outros in FAIXAS_FRETE:
        if peso <= limite:
            frete = sp if cliente["uf"] == "SP" else outros
            break
    if cliente["tipo"] == "VIP":
        frete *= 0.5
    if cupom == "FRETEGRATIS":
        frete = 30 if peso > 50 else 0
    return frete

def _desconto(subtotal, cliente, cupom):
    desconto = subtotal * 0.10 if cupom == "BEMVINDO10" and subtotal >= 200 else 0
    if cliente["tipo"] == "VIP":
        if subtotal >= 1000:
            desconto += (subtotal - desconto) * 0.05
        elif subtotal >= 500:
            desconto += (subtotal - desconto) * 0.02
    return round(desconto, 2)

def calcular_pedido(pedido):
    cliente, cupom = pedido["cliente"], pedido.get("cupom")
    subtotal, peso = _totais(pedido["itens"])
    frete = _frete(peso, cliente, cupom)
    desconto = _desconto(subtotal, cliente, cupom)
    base = subtotal - desconto
    imposto = round(base * ALIQUOTAS.get(cliente["uf"], 0.12), 2)
    total = round(base + imposto + frete, 2)
    return {"subtotal": subtotal, "desconto": desconto, "frete": round(frete, 2),
            "imposto": imposto, "total": total, "peso_kg": round(peso, 2)}
