from estoque import Estoque
from modelos import Chapa
from relatorio import gerar_relatorio


def test_relatorio_novo_formato():
    e = Estoque()
    e.adicionar(Chapa("MDF-15", "MDF 15mm branco", 10))
    e.adicionar(Chapa("COMP-6", "Compensado 6mm", 4))
    e.reservar("MDF-15", 3)
    assert gerar_relatorio(e) == ("SKU | Descrição | Total | Reservado | Disp.\n"
                                  "COMP-6 | Compensado 6mm | 4 | 0 | 4\n"
                                  "MDF-15 | MDF 15mm branco | 10 | 3 | 7")


def test_relatorio_vazio():
    assert gerar_relatorio(Estoque()) == "SKU | Descrição | Total | Reservado | Disp."
