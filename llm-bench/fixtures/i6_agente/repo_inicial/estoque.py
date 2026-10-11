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

    def retirar(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0 or qtd > self._chapas[sku].quantidade:
            raise ValueError("estoque insuficiente")
        self._chapas[sku].quantidade -= qtd

    def quantidade(self, sku: str) -> int:
        chapa = self._chapas.get(sku)
        return chapa.quantidade if chapa else 0

    def listar(self):
        return sorted(self._chapas.values(), key=lambda c: c.sku)
