from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

_C = Decimal("0.01")
def _q(v): return v.quantize(_C, rounding=ROUND_HALF_UP)

@dataclass(frozen=True)
class Item:
    descricao: str
    quantidade: int
    preco_unitario: Decimal

class Orcamento:
    def __init__(self, cliente, frete=Decimal("0")):
        cliente = cliente.strip() if isinstance(cliente, str) else ""
        if not cliente: raise ValueError("cliente vazio")
        if not isinstance(frete, Decimal) or frete < 0: raise ValueError("frete invalido")
        self._cliente, self._frete = cliente, frete
        self._itens = {}  # chave -> [descricao, qtd, preco]
        self._pct = Decimal("0")

    def adicionar_item(self, item):
        desc = item.descricao.strip() if isinstance(item.descricao, str) else ""
        if not desc: raise ValueError("descricao vazia")
        if type(item.quantidade) is not int or item.quantidade <= 0: raise ValueError("quantidade invalida")
        if not isinstance(item.preco_unitario, Decimal) or item.preco_unitario < 0: raise ValueError("preco invalido")
        k = desc.lower()
        if k in self._itens:
            if self._itens[k][2] != item.preco_unitario: raise ValueError("preco diferente")
            self._itens[k][1] += item.quantidade
        else:
            self._itens[k] = [desc, item.quantidade, item.preco_unitario]

    def _bruto(self): return sum((q * p for _, q, p in self._itens.values()), Decimal("0"))
    def subtotal(self): return _q(self._bruto())
    def _desc(self): return _q(self.subtotal() * self._pct / 100)

    def aplicar_desconto(self, percentual, aprovado=False):
        if not (0 <= percentual <= 100): raise ValueError("percentual invalido")
        if percentual > 15 and not aprovado: raise PermissionError("desconto exige aprovacao")
        self._pct = percentual

    def total(self): return _q(self.subtotal() - self._desc() + self._frete)

    def to_dict(self):
        return {"cliente": self._cliente,
                "itens": [{"descricao": d, "quantidade": q, "preco_unitario": str(_q(p)), "subtotal": str(_q(q * p))} for d, q, p in self._itens.values()],
                "subtotal": str(self.subtotal()), "desconto_percentual": str(_q(self._pct)), "desconto_valor": str(self._desc()),
                "frete": str(_q(self._frete)), "total": str(self.total())}
