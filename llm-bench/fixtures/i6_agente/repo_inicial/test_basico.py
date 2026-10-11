import pytest
from estoque import Estoque
from modelos import Chapa
from relatorio import gerar_relatorio


def novo():
    e = Estoque()
    e.adicionar(Chapa("MDF-15", "MDF 15mm branco", 10))
    return e


def test_adicionar_soma_quantidades():
    e = novo()
    e.adicionar(Chapa("MDF-15", "MDF 15mm branco", 5))
    assert e.quantidade("MDF-15") == 15


def test_retirar():
    e = novo()
    e.retirar("MDF-15", 4)
    assert e.quantidade("MDF-15") == 6


def test_retirar_demais():
    with pytest.raises(ValueError):
        novo().retirar("MDF-15", 11)


def test_relatorio():
    assert gerar_relatorio(novo()) == "SKU | Descrição | Qtd\nMDF-15 | MDF 15mm branco | 10"
