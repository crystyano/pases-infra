def gerar_relatorio(estoque) -> str:
    linhas = ["SKU | Descrição | Qtd"]
    for chapa in estoque.listar():
        linhas.append(f"{chapa.sku} | {chapa.descricao} | {chapa.quantidade}")
    return "\n".join(linhas)
