def gerar_relatorio(estoque) -> str:
    linhas = ["SKU | Descrição | Total | Reservado | Disp."]
    for chapa in estoque.listar():
        total = chapa.quantidade
        reservado = chapa.reservado
        disponivel = total - reservado
        linhas.append(f"{chapa.sku} | {chapa.descricao} | {total} | {reservado} | {disponivel}")
    return "\n".join(linhas)
