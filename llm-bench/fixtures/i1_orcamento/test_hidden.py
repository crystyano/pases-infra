import pytest
from decimal import Decimal as D
from orcamento import Item, Orcamento

def novo(frete="0"): return Orcamento("Maria", D(frete))

def test_cliente_vazio():
    with pytest.raises(ValueError): Orcamento("   ")

def test_cliente_strip():
    assert Orcamento("  Maria ").to_dict()["cliente"] == "Maria"

def test_frete_negativo():
    with pytest.raises(ValueError): Orcamento("Maria", D("-1"))

def test_subtotal_basico():
    o = novo(); o.adicionar_item(Item("Armário", 2, D("1250.50"))); o.adicionar_item(Item("Puxador", 10, D("12.90")))
    assert o.subtotal() == D("2630.00") and str(o.subtotal()) == "2630.00"

def test_agrupa_mesma_descricao():
    o = novo(); o.adicionar_item(Item("Dobradiça", 4, D("3.25"))); o.adicionar_item(Item("  dobradiça ", 6, D("3.25")))
    d = o.to_dict()
    assert len(d["itens"]) == 1 and d["itens"][0]["quantidade"] == 10 and d["itens"][0]["descricao"] == "Dobradiça" and o.subtotal() == D("32.50")

def test_preco_diferente_no_agrupamento():
    o = novo(); o.adicionar_item(Item("Parafuso", 1, D("1.00")))
    with pytest.raises(ValueError): o.adicionar_item(Item("parafuso", 1, D("1.10")))

@pytest.mark.parametrize("item", [
    lambda: Item("x", 0, D("1")), lambda: Item("x", -1, D("1")), lambda: Item("x", 1.5, D("1")),
    lambda: Item("x", 1, D("-0.01")), lambda: Item("   ", 1, D("1")), lambda: Item("x", 1, 2.5)])
def test_item_invalido(item):
    o = novo()
    with pytest.raises(ValueError): o.adicionar_item(item())

def test_arredondamento_half_up_no_subtotal():
    o = novo(); o.adicionar_item(Item("Fita", 3, D("0.335")))
    assert o.subtotal() == D("1.01")

def test_arredondamento_unico_no_final():
    o = novo(); o.adicionar_item(Item("A", 1, D("0.333"))); o.adicionar_item(Item("B", 1, D("0.333"))); o.adicionar_item(Item("C", 1, D("0.333")))
    assert o.subtotal() == D("1.00")   # 0.999 -> 1.00 (se arredondasse item a item daria 0.99)

def test_desconto_percentual():
    o = novo(); o.adicionar_item(Item("Mesa", 1, D("1000"))); o.aplicar_desconto(D("10"))
    d = o.to_dict()
    assert o.total() == D("900.00") and d["desconto_valor"] == "100.00" and d["desconto_percentual"] == "10.00"

def test_desconto_exige_aprovacao_acima_de_15():
    o = novo(); o.adicionar_item(Item("Mesa", 1, D("1000")))
    with pytest.raises(PermissionError): o.aplicar_desconto(D("15.01"))
    o.aplicar_desconto(D("15"))
    assert o.total() == D("850.00")
    o.aplicar_desconto(D("30"), aprovado=True)
    assert o.total() == D("700.00")

def test_desconto_invalido():
    o = novo(); o.adicionar_item(Item("Mesa", 1, D("100")))
    for p in (D("-1"), D("100.01")):
        with pytest.raises(ValueError): o.aplicar_desconto(p, aprovado=True)
    o.aplicar_desconto(D("100"), aprovado=True)
    assert o.total() == D("0.00")

def test_desconto_substitui():
    o = novo(); o.adicionar_item(Item("Mesa", 1, D("200"))); o.aplicar_desconto(D("10")); o.aplicar_desconto(D("5"))
    assert o.total() == D("190.00")

def test_frete_nao_sofre_desconto():
    o = novo("50"); o.adicionar_item(Item("Mesa", 1, D("200"))); o.aplicar_desconto(D("10"))
    assert o.total() == D("230.00")

def test_desconto_arredondamento():
    o = novo(); o.adicionar_item(Item("X", 1, D("99.99"))); o.aplicar_desconto(D("12.5"))
    d = o.to_dict()
    assert d["desconto_valor"] == "12.50" and o.total() == D("87.49")

def test_orcamento_vazio():
    assert novo().subtotal() == D("0.00") and novo().total() == D("0.00") and str(novo("35").total()) == "35.00"

def test_to_dict_completo():
    o = Orcamento("Maria", D("80")); o.adicionar_item(Item("Armário", 2, D("1250.50"))); o.aplicar_desconto(D("10"))
    assert o.to_dict() == {"cliente": "Maria",
        "itens": [{"descricao": "Armário", "quantidade": 2, "preco_unitario": "1250.50", "subtotal": "2501.00"}],
        "subtotal": "2501.00", "desconto_percentual": "10.00", "desconto_valor": "250.10", "frete": "80.00", "total": "2330.90"}

def test_to_dict_sem_desconto():
    d = novo().to_dict()
    assert d["desconto_percentual"] == "0.00" and d["desconto_valor"] == "0.00" and d["itens"] == []
