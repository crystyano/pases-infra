def calcular_parcelas(venda):
    valor = venda["valor"]
    entrada = venda.get("entrada", 0)
    n = venda["parcelas"]
    forma = venda["forma"]
    score = venda.get("cliente_score", 0)
    if n < 1 or n > 12:
        raise ValueError("parcelas invalidas")
    if entrada < 0 or entrada >= valor:
        raise ValueError("entrada invalida")
    if forma == "BOLETO" and n > 6:
        if entrada < valor * 0.2:
            raise ValueError("entrada minima")
    financiado = valor - entrada
    if forma == "PIX":
        if valor >= 1000:
            financiado = financiado - financiado * 0.05
        else:
            financiado = financiado - financiado * 0.03
        n = 1
        taxa = 0
    elif forma == "BOLETO":
        if n <= 3:
            taxa = 0
        elif n <= 6:
            taxa = 0.015
        else:
            taxa = 0.025
    elif forma == "CARTAO":
        if n <= 6:
            if score >= 700:
                taxa = 0
            else:
                taxa = 0.0199
        else:
            if score >= 700:
                taxa = 0.0199
            else:
                taxa = 0.0299
    else:
        raise ValueError("forma invalida")
    if taxa > 0:
        total = financiado * ((1 + taxa) ** n)
    else:
        total = financiado
    total = round(total, 2)
    valor_parcela = round(total / n, 2)
    parcelas = []
    for i in range(n):
        parcelas.append(valor_parcela)
    soma = round(valor_parcela * n, 2)
    diferenca = round(total - soma, 2)
    if diferenca != 0:
        parcelas[n - 1] = round(parcelas[n - 1] + diferenca, 2)
    return {"forma": forma, "financiado": round(financiado, 2), "taxa_mensal": taxa, "parcelas": parcelas,
            "total_final": round(entrada + total, 2), "juros_total": round(total - financiado, 2)}
