from dataclasses import dataclass, field


@dataclass
class Chapa:
    sku: str
    descricao: str
    quantidade: int
    reservado: int = field(default=0)
