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
    assert gerar_relatorio(novo()) == "SKU | Descrição | Total | Reservado | Disp.\nMDF-15 | MDF 15mm branco | 10 | 0 | 10"


def test_reservar():
    e = novo()
    e.reservar("MDF-15", 3)
    assert e.reservado("MDF-15") == 3
    assert e.disponivel("MDF-15") == 7


def test_reservar_demais():
    with pytest.raises(ValueError):
        novo().reservar("MDF-15", 11)


def test_reservar_inexistente():
    e = novo()
    with pytest.raises(KeyError):
        e.reservar("INEXISTENTE", 1)


def test_liberar_reserva():
    e = novo()
    e.reservar("MDF-15", 3)
    e.liberar_reserva("MDF-15", 2)
    assert e.reservado("MDF-15") == 1
    assert e.disponivel("MDF-15") == 9


def test_liberar_reserva_demais():
    e = novo()
    e.reservar("MDF-15", 3)
    with pytest.raises(ValueError):
        e.liberar_reserva("MDF-15", 5)


def test_liberar_reserva_inexistente():
    e = novo()
    with pytest.raises(KeyError):
        e.liberar_reserva("INEXISTENTE", 1)


def test_retirar_só_disponivel():
    e = novo()
    e.reservar("MDF-15", 3)
    e.retirar("MDF-15", 7)  # 10 - 3 = 7 disponível
    assert e.quantidade("MDF-15") == 3
    assert e.disponivel("MDF-15") == 0


def test_retirar_mais_do_disponivel():
    e = novo()
    e.reservar("MDF-15", 3)
    with pytest.raises(ValueError):
        e.retirar("MDF-15", 8)  # 10 - 3 = 7 disponível, mas tentando retirar 8