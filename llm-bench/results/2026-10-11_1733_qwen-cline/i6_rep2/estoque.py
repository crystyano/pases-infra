from modelos import Chapa


class Estoque:
    def __init__(self):
        self._chapas = {}
        self._reservas = {}  # sku -> quantidade reservada

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
        disponivel = self.disponivel(sku)
        if qtd <= 0 or qtd > disponivel:
            raise ValueError("estoque insuficiente")
        self._chapas[sku].quantidade -= qtd

    def quantidade(self, sku: str) -> int:
        chapa = self._chapas.get(sku)
        return chapa.quantidade if chapa else 0

    def reservar(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        disponivel = self.disponivel(sku)
        if qtd > disponivel:
            raise ValueError("estoque insuficiente")
        if sku not in self._reservas:
            self._reservas[sku] = 0
        self._reservas[sku] += qtd

    def liberar_reserva(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        if sku not in self._reservas or self._reservas[sku] < qtd:
            raise ValueError("reserva insuficiente")
        self._reservas[sku] -= qtd
        if self._reservas[sku] == 0:
            del self._reservas[sku]

    def reservado(self, sku: str) -> int:
        return self._reservas.get(sku, 0)

    def disponivel(self, sku: str) -> int:
        return self.quantidade(sku) - self.reservado(sku)

    def listar(self):
        return sorted(self._chapas.values(), key=lambda c: c.sku)