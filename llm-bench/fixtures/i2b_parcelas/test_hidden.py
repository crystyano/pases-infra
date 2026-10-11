import json, pathlib, pytest
from parcelas import calcular_parcelas

CASOS = json.loads((pathlib.Path(__file__).parent / "casos.json").read_text(encoding="utf-8"))


def igual(a, b):
    if isinstance(b, dict):
        return isinstance(a, dict) and set(a) == set(b) and all(igual(a[k], b[k]) for k in b)
    if isinstance(b, list):
        return isinstance(a, list) and len(a) == len(b) and all(igual(x, y) for x, y in zip(a, b))
    if isinstance(b, float) or isinstance(a, float):
        return abs(a - b) <= 0.006
    return a == b


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: f'{c["entrada"]["forma"]}-{c["entrada"]["parcelas"]}x-{c["entrada"]["valor"]}-e{c["entrada"]["entrada"]}-s{c["entrada"]["cliente_score"]}')
def test_comportamento_preservado(caso):
    if "erro" in caso:
        with pytest.raises(ValueError):
            calcular_parcelas(caso["entrada"])
    else:
        assert igual(calcular_parcelas(caso["entrada"]), caso["saida"])


def test_nao_altera_a_entrada():
    v = {"valor": 1500.0, "entrada": 300.0, "parcelas": 5, "forma": "CARTAO", "cliente_score": 650}
    copia = json.loads(json.dumps(v))
    calcular_parcelas(v)
    assert v == copia
