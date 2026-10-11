from modelos import Chapa


class Estoque:
    def __init__(self):
        self._chapas = {}
        self._reservas = {}  # Para rastrear as reservas por SKU

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
        if qtd > self._chapas[sku].quantidade:
            raise ValueError("estoque insuficiente")
        
        # Atualiza a reserva
        if sku not in self._reservas:
            self._reservas[sku] = 0
        self._reservas[sku] += qtd

    def liberar_reserva(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        if qtd <= 0:
            raise ValueError("quantidade invalida")
        if sku not in self._reservas:
            raise ValueError("reserva insuficiente")
        if qtd > self._reservas[sku]:
            raise ValueError("reserva insuficiente")
        
        # Atualiza a reserva
        self._reservas[sku] -= qtd
        if self._reservas[sku] == 0:
            del self._reservas[sku]

    def retirar(self, sku: str, qtd: int):
        if sku not in self._chapas:
            raise KeyError(sku)
        # Verifica se há disponibilidade (total - reservado) para retirada
        disponivel = self._chapas[sku].quantidade - self._reservas.get(sku, 0)
        if qtd <= 0 or qtd > disponivel:
            raise ValueError("estoque insuficiente")
        self._chapas[sku].quantidade -= qtd

    def quantidade(self, sku: str) -> int:
        chapa = self._chapas.get(sku)
        return chapa.quantidade if chapa else 0

    def reservado(self, sku: str) -> int:
        return self._reservas.get(sku, 0)

    def disponivel(self, sku: str) -> int:
        total = self.quantidade(sku)
        reservado = self.reservado(sku)
        return total - reservado

    def listar(self):
        return sorted(self._chapas.values(), key=lambda c: c.sku)