FORMAS = ("PIX", "BOLETO", "CARTAO")


def _validar(valor, entrada, n, forma):
    if n < 1 or n > 12:
        raise ValueError("parcelas invalidas")
    if entrada < 0 or entrada >= valor:
        raise ValueError("entrada invalida")
    if forma == "BOLETO" and n > 6 and entrada < valor * 0.2:
        raise ValueError("entrada minima")
    if forma not in FORMAS:
        raise ValueError("forma invalida")


def _taxa(forma, n, score):
    if forma == "PIX":
        return 0
    if forma == "BOLETO":
        return 0 if n <= 3 else (0.015 if n <= 6 else 0.025)
    if n <= 6:
        return 0 if score >= 700 else 0.0199
    return 0.0199 if score >= 700 else 0.0299


def _financiado(valor, entrada, forma):
    financiado = valor - entrada
    if forma == "PIX":
        desconto = 0.05 if valor >= 1000 else 0.03
        financiado -= financiado * desconto
    return financiado


def _dividir(total, n):
    valor_parcela = round(total / n, 2)
    parcelas = [valor_parcela] * n
    diferenca = round(total - round(valor_parcela * n, 2), 2)
    if diferenca != 0:
        parcelas[-1] = round(parcelas[-1] + diferenca, 2)
    return parcelas


def calcular_parcelas(venda):
    valor, entrada = venda["valor"], venda.get("entrada", 0)
    n, forma, score = venda["parcelas"], venda["forma"], venda.get("cliente_score", 0)
    _validar(valor, entrada, n, forma)
    financiado = _financiado(valor, entrada, forma)
    if forma == "PIX":
        n = 1
    taxa = _taxa(forma, n, score)
    total = round(financiado * ((1 + taxa) ** n) if taxa > 0 else financiado, 2)
    return {"forma": forma, "financiado": round(financiado, 2), "taxa_mensal": taxa, "parcelas": _dividir(total, n),
            "total_final": round(entrada + total, 2), "juros_total": round(total - financiado, 2)}
