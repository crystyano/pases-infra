def gerar_relatorio(estoque) -> str:
    linhas = ["SKU | Descrição | Total | Reservado | Disp."]
    for chapa in estoque.listar():
        total = estoque.quantidade(chapa.sku)
        reservado = estoque.reservado(chapa.sku)
        disponivel = estoque.disponivel(chapa.sku)
        linhas.append(f"{chapa.sku} | {chapa.descricao} | {total} | {reservado} | {disponivel}")
    return "\n".join(linhas)