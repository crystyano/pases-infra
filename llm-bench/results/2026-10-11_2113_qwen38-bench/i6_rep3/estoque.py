from modelos import Chapa


class Estoque:
    def __init__(self):
        self._chapas = {}

    def adicionar(self, chapa: Chapa):
        if chapa.quantidade <= 0:
            raise ValueError("quantidade invalida")
        atual = self._chapas.get(chapa.sku)
        if atual is not None:
            atual.quantidade += chapa.quantidade
        else:
            self._chapas[chapa.sku] = Chapa(chapa.sku, chapa.descricao, chapa.quantidade)

    def reservar(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        chapa = self._chapas[sku]
        if qtd > chapa.quantidade - chapa.reservado:
            raise ValueError("estoque insuficiente")
        chapa.reservado += qtd

    def liberar_reserva(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        chapa = self._chapas[sku]
        if qtd > chapa.reservado:
            raise ValueError("reserva insuficiente")
        chapa.reservado -= qtd

    def retirar(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        chapa = self._chapas[sku]
        if qtd > chapa.quantidade - chapa.reservado:
            raise ValueError("estoque insuficiente")
        chapa.quantidade -= qtd

    def quantidade(self, sku: str) -> int:
        chapa = self._chapas.get(sku)
        return chapa.quantidade if chapa else 0

    def reservado(self, sku: str) -> int:
        chapa = self._chapas.get(sku)
        return chapa.reservado if chapa else 0

    def disponivel(self, sku: str) -> int:
        chapa = self._chapas.get(sku)
        return chapa.quantidade - chapa.reservado if chapa else 0

    def listar(self):
        return sorted(self._chapas.values(), key=lambda c: c.sku)
