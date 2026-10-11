import copy, json, pathlib, pytest
from producao import resumo_producao

CASOS = json.loads((pathlib.Path(__file__).parent / "casos.json").read_text(encoding="utf-8"))


def igual(a, b):
    if isinstance(b, dict):
        return isinstance(a, dict) and set(a) == set(b) and all(igual(a[k], b[k]) for k in b)
    if isinstance(b, list):
        return isinstance(a, list) and len(a) == len(b) and all(igual(x, y) for x, y in zip(a, b))
    if isinstance(b, float) or isinstance(a, float):
        return abs(a - b) <= 0.06
    return a == b


@pytest.mark.parametrize("i", range(len(CASOS)), ids=lambda i: f"caso{i:03d}-{len(CASOS[i]['entrada'])}ordens")
def test_comportamento_preservado(i):
    assert igual(resumo_producao(CASOS[i]["entrada"]), CASOS[i]["saida"])


def test_nao_altera_a_entrada():
    ordens = CASOS[5]["entrada"]
    copia = copy.deepcopy(ordens)
    resumo_producao(ordens)
    assert ordens == copia
