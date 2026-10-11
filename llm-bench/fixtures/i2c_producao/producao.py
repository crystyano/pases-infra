def resumo_producao(ordens):
    linhas = []
    revisar = []
    total_aprov = 0
    contagem = 0
    dados = []
    for o in ordens:
        area_chapa = o["chapa_w"] * o["chapa_h"]
        area_pecas = 0
        for p in o["pecas"]:
            area_pecas = area_pecas + p["w"] * p["h"] * p["qtd"]
        if area_chapa <= 0:
            aprov = 0
        else:
            aprov = area_pecas / area_chapa * 100
        aprov = round(aprov, 1)
        if aprov > 100:
            status = "INVALIDA"
        elif aprov >= 85:
            status = "OTIMO"
        elif aprov >= 70:
            status = "BOM"
        elif aprov >= 50:
            status = "REGULAR"
        else:
            status = "RUIM"
        if o.get("prioridade", 3) == 1 and aprov < 70:
            revisar.append(o["id"])
        if status != "INVALIDA":
            total_aprov = total_aprov + aprov
            contagem = contagem + 1
        dados.append((o.get("prioridade", 3), -aprov, o["id"], status, aprov))
    dados.sort()
    for d in dados:
        linhas.append(str(d[2]) + " | " + d[3] + " | " + str(d[4]) + "%")
    if contagem > 0:
        media = round(total_aprov / contagem, 1)
    else:
        media = 0
    return {"linhas": linhas, "media_aproveitamento": media, "total_ordens": len(ordens), "revisar": revisar}
