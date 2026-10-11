FAIXAS = [(85, "OTIMO"), (70, "BOM"), (50, "REGULAR")]


def _aproveitamento(ordem):
    area_chapa = ordem["chapa_w"] * ordem["chapa_h"]
    area_pecas = sum(p["w"] * p["h"] * p["qtd"] for p in ordem["pecas"])
    return round(area_pecas / area_chapa * 100, 1) if area_chapa > 0 else 0


def _status(aprov):
    if aprov > 100:
        return "INVALIDA"
    return next((nome for minimo, nome in FAIXAS if aprov >= minimo), "RUIM")


def resumo_producao(ordens):
    revisar, validas, dados = [], [], []
    for o in ordens:
        aprov = _aproveitamento(o)
        status = _status(aprov)
        prioridade = o.get("prioridade", 3)
        if prioridade == 1 and aprov < 70:
            revisar.append(o["id"])
        if status != "INVALIDA":
            validas.append(aprov)
        dados.append((prioridade, -aprov, o["id"], status, aprov))
    dados.sort()
    linhas = [f"{id_} | {status} | {aprov}%" for _, _, id_, status, aprov in dados]
    media = round(sum(validas) / len(validas), 1) if validas else 0
    return {"linhas": linhas, "media_aproveitamento": media, "total_ordens": len(ordens), "revisar": revisar}
