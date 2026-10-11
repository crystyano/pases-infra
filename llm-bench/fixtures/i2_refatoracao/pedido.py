def calcular_pedido(pedido):
    itens = pedido["itens"]
    cliente = pedido["cliente"]
    cupom = pedido.get("cupom")
    subtotal = 0
    peso = 0
    for i in itens:
        subtotal = subtotal + i["preco"] * i["qtd"]
        peso = peso + i["peso_kg"] * i["qtd"]
    subtotal = round(subtotal, 2)
    # frete por faixa de peso e regiao
    if peso <= 5:
        if cliente["uf"] == "SP":
            frete = 20
        else:
            frete = 35
    elif peso <= 20:
        if cliente["uf"] == "SP":
            frete = 45
        else:
            frete = 70
    else:
        if cliente["uf"] == "SP":
            frete = 90
        else:
            frete = 140
    if cliente["tipo"] == "VIP":
        frete = frete * 0.5
    if cupom == "FRETEGRATIS":
        if peso > 50:
            frete = 30
        else:
            frete = 0
    # desconto
    desconto = 0
    if cupom == "BEMVINDO10":
        if subtotal >= 200:
            desconto = subtotal * 0.10
    if cliente["tipo"] == "VIP":
        if subtotal >= 1000:
            desconto = desconto + (subtotal - desconto) * 0.05
        elif subtotal >= 500:
            desconto = desconto + (subtotal - desconto) * 0.02
    desconto = round(desconto, 2)
    base = subtotal - desconto
    # imposto por estado
    if cliente["uf"] == "SP":
        aliq = 0.18
    elif cliente["uf"] == "RJ":
        aliq = 0.20
    elif cliente["uf"] == "MG":
        aliq = 0.18
    else:
        aliq = 0.12
    imposto = round(base * aliq, 2)
    total = round(base + imposto + frete, 2)
    return {"subtotal": subtotal, "desconto": desconto, "frete": round(frete, 2),
            "imposto": imposto, "total": total, "peso_kg": round(peso, 2)}
