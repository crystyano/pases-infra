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


def test_reservar():
    e = novo()
    e.reservar("MDF-15", 3)
    assert e.quantidade("MDF-15") == 10
    assert e.reservado("MDF-15") == 3
    assert e.disponivel("MDF-15") == 7


def test_reservar_sku_inexistente():
    with pytest.raises(KeyError):
        novo().reservar("XYZ", 1)


def test_reservar_qtd_invalida():
    with pytest.raises(ValueError):
        novo().reservar("MDF-15", 0)
    with pytest.raises(ValueError):
        novo().reservar("MDF-15", -2)


def test_reservar_estoque_insuficiente():
    with pytest.raises(ValueError, match="estoque insuficiente"):
        novo().reservar("MDF-15", 11)


def test_liberar_reserva():
    e = novo()
    e.reservar("MDF-15", 5)
    e.liberar_reserva("MDF-15", 2)
    assert e.reservado("MDF-15") == 3
    assert e.disponivel("MDF-15") == 7


def test_liberar_reserva_insuficiente():
    e = novo()
    e.reservar("MDF-15", 2)
    with pytest.raises(ValueError, match="reserva insuficiente"):
        e.liberar_reserva("MDF-15", 3)


def test_liberar_reserva_qtd_invalida():
    with pytest.raises(ValueError):
        novo().liberar_reserva("MDF-15", 0)


def test_retirar_respeita_reserva():
    e = novo()
    e.reservar("MDF-15", 6)
    with pytest.raises(ValueError, match="estoque insuficiente"):
        e.retirar("MDF-15", 5)
    e.retirar("MDF-15", 4)
    assert e.quantidade("MDF-15") == 6
    assert e.reservado("MDF-15") == 6
    assert e.disponivel("MDF-15") == 0


def test_reservado_e_disponivel_sku_inexistente():
    e = novo()
    assert e.reservado("XYZ") == 0
    assert e.disponivel("XYZ") == 0


def test_relatorio():
    assert gerar_relatorio(novo()) == (
        "SKU | Descrição | Total | Reservado | Disp.\n"
        "MDF-15 | MDF 15mm branco | 10 | 0 | 10"
    )


def test_relatorio_com_reserva():
    e = novo()
    e.reservar("MDF-15", 4)
    assert gerar_relatorio(e) == (
        "SKU | Descrição | Total | Reservado | Disp.\n"
        "MDF-15 | MDF 15mm branco | 10 | 4 | 6"
    )
