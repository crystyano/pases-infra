from modelos import Chapa


class Estoque:
    def __init__(self):
        self._chapas = {}
        self._reservas = {}

    def adicionar(self, chapa: Chapa):
        if chapa.quantidade <= 0:
            raise ValueError("quantidade invalida")
        atual = self._chapas.get(chapa.sku)
        if atual is not None:
            atual.quantidade += chapa.quantidade
        else:
            self._chapas[chapa.sku] = Chapa(chapa.sku, chapa.descricao, chapa.quantidade)

    def quantidade(self, sku):
        c = self._chapas.get(sku)
        return c.quantidade if c else 0

    def reservado(self, sku):
        return self._reservas.get(sku, 0)

    def disponivel(self, sku):
        return self.quantidade(sku) - self.reservado(sku)

    def reservar(self, sku, qtd):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        if qtd > self.disponivel(sku):
            raise ValueError("estoque insuficiente")
        self._reservas[sku] = self.reservado(sku) + qtd

    def liberar_reserva(self, sku, qtd):
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        if qtd > self.reservado(sku):
            raise ValueError("reserva insuficiente")
        self._reservas[sku] -= qtd

    def retirar(self, sku, qtd):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0 or qtd > self.disponivel(sku):
            raise ValueError("estoque insuficiente")
        self._chapas[sku].quantidade -= qtd

    def listar(self):
        return sorted(self._chapas.values(), key=lambda c: c.sku)
