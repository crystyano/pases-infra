import json, pathlib, pytest
from pedido import calcular_pedido

CASOS = json.loads((pathlib.Path(__file__).parent / "casos.json").read_text(encoding="utf-8"))

@pytest.mark.parametrize("caso", CASOS, ids=lambda c: f'{c["entrada"]["cliente"]["tipo"]}-{c["entrada"]["cliente"]["uf"]}-{c["entrada"]["cupom"]}-{len(c["entrada"]["itens"])}x{int(c["saida"]["subtotal"])}')
def test_comportamento_preservado(caso):
    r = calcular_pedido(caso["entrada"])
    assert set(r) == set(caso["saida"])
    for k, v in caso["saida"].items():
        assert r[k] == pytest.approx(v, abs=0.006), k

def test_nao_altera_a_entrada():
    ped = {"itens": [{"nome": "x", "preco": 10.0, "qtd": 2, "peso_kg": 1.0}], "cliente": {"tipo": "VIP", "uf": "SP"}, "cupom": "BEMVINDO10"}
    copia = json.loads(json.dumps(ped))
    calcular_pedido(ped)
    assert ped == copia
