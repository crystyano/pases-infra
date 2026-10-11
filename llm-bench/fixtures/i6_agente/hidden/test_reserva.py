import pytest
from estoque import Estoque
from modelos import Chapa


def novo():
    e = Estoque()
    e.adicionar(Chapa("MDF-15", "MDF 15mm branco", 10))
    return e


def test_reservar_nao_altera_total():
    e = novo(); e.reservar("MDF-15", 4)
    assert e.quantidade("MDF-15") == 10 and e.reservado("MDF-15") == 4 and e.disponivel("MDF-15") == 6


def test_reservar_acumula():
    e = novo(); e.reservar("MDF-15", 4); e.reservar("MDF-15", 3)
    assert e.reservado("MDF-15") == 7 and e.disponivel("MDF-15") == 3


def test_reservar_alem_do_disponivel():
    e = novo(); e.reservar("MDF-15", 8)
    with pytest.raises(ValueError, match="estoque insuficiente"):
        e.reservar("MDF-15", 3)


def test_reservar_invalidos():
    e = novo()
    with pytest.raises(KeyError): e.reservar("XXX", 1)
    with pytest.raises(ValueError): e.reservar("MDF-15", 0)
    with pytest.raises(ValueError): e.reservar("MDF-15", -2)


def test_liberar_reserva():
    e = novo(); e.reservar("MDF-15", 6); e.liberar_reserva("MDF-15", 2)
    assert e.reservado("MDF-15") == 4 and e.disponivel("MDF-15") == 6


def test_liberar_alem_do_reservado():
    e = novo(); e.reservar("MDF-15", 2)
    with pytest.raises(ValueError, match="reserva insuficiente"):
        e.liberar_reserva("MDF-15", 3)
    with pytest.raises(ValueError): e.liberar_reserva("MDF-15", 0)


def test_retirar_so_do_disponivel():
    e = novo(); e.reservar("MDF-15", 7)
    e.retirar("MDF-15", 3)
    assert e.quantidade("MDF-15") == 7 and e.disponivel("MDF-15") == 0
    with pytest.raises(ValueError, match="estoque insuficiente"):
        e.retirar("MDF-15", 1)


def test_retirar_demais_continua_valendo():
    with pytest.raises(ValueError): novo().retirar("MDF-15", 11)


def test_sku_inexistente():
    e = Estoque()
    assert e.reservado("X") == 0 and e.disponivel("X") == 0 and e.quantidade("X") == 0


def test_adicionar_depois_de_reservar_mantem_reserva():
    e = novo(); e.reservar("MDF-15", 5); e.adicionar(Chapa("MDF-15", "MDF 15mm branco", 5))
    assert e.quantidade("MDF-15") == 15 and e.reservado("MDF-15") == 5 and e.disponivel("MDF-15") == 10
