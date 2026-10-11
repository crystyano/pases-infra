def gerar_relatorio(estoque) -> str:
    linhas = ["SKU | Descrição | Total | Reservado | Disp."]
    for c in estoque.listar():
        linhas.append(f"{c.sku} | {c.descricao} | {c.quantidade} | {estoque.reservado(c.sku)} | {estoque.disponivel(c.sku)}")
    return "\n".join(linhas)
