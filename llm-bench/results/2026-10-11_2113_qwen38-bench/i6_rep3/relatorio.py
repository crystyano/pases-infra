def gerar_relatorio(estoque) -> str:
    linhas = ["SKU | Descrição | Total | Reservado | Disp."]
    for chapa in estoque.listar():
        disp = chapa.quantidade - chapa.reservado
        linhas.append(f"{chapa.sku} | {chapa.descricao} | {chapa.quantidade} | {chapa.reservado} | {disp}")
    return "\n".join(linhas)
