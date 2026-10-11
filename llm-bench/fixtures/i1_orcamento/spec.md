# Tarefa

Implemente o módulo Python **`orcamento.py`** (somente biblioteca padrão, Python 3.12) para o orçamento de uma marcenaria.
Responda com **um único bloco de código** ```python contendo o módulo completo, sem testes e sem explicações longas.

## API obrigatória

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Item:
    descricao: str
    quantidade: int
    preco_unitario: Decimal

class Orcamento:
    def __init__(self, cliente: str, frete: Decimal = Decimal("0")) -> None: ...
    def adicionar_item(self, item: Item) -> None: ...
    def subtotal(self) -> Decimal: ...
    def aplicar_desconto(self, percentual: Decimal, aprovado: bool = False) -> None: ...
    def total(self) -> Decimal: ...
    def to_dict(self) -> dict: ...
```

## Regras

1. **Cliente:** `cliente` é guardado sem espaços nas pontas. Se ficar vazio, levantar `ValueError`.
2. **Frete:** não pode ser negativo (`ValueError`). Frete **não sofre desconto**.
3. **Validação do item** (feita em `adicionar_item`, levantando `ValueError`): `descricao` não vazia depois de remover espaços; `quantidade` deve ser `int` e maior que zero; `preco_unitario` deve ser `Decimal` e maior ou igual a zero.
4. **Agrupamento:** itens com a mesma descrição (ignorando maiúsculas/minúsculas e espaços nas pontas) são **agrupados**: as quantidades são somadas e a descrição guardada é a **primeira recebida, sem espaços nas pontas**. Se o preço unitário for diferente do já registrado, levantar `ValueError`.
5. **Arredondamento:** todo valor monetário é arredondado para 2 casas decimais com `ROUND_HALF_UP`.
6. **Subtotal:** soma de `quantidade * preco_unitario` de todos os itens, arredondada **uma única vez, no final**. Orçamento sem itens tem subtotal `Decimal("0.00")`.
7. **Desconto:** `aplicar_desconto(percentual, aprovado=False)` define um desconto percentual sobre o subtotal.
   - `percentual` deve estar entre 0 e 100, inclusive; fora disso, `ValueError` (mesmo com `aprovado=True`).
   - Acima de **15** exige `aprovado=True`; sem aprovação, levantar `PermissionError`.
   - O desconto **substitui** o anterior (não acumula): vale a última chamada válida.
   - Valor do desconto = `subtotal * percentual / 100`, arredondado conforme a regra 5.
8. **Total:** `subtotal - valor_do_desconto + frete`, arredondado conforme a regra 5. Orçamento sem itens tem total igual ao frete.
9. `subtotal()` e `total()` retornam `Decimal` com **exatamente 2 casas decimais**.
10. **`to_dict()`** retorna um dicionário com **exatamente** estas chaves, todos os valores monetários como `str` com 2 casas decimais:
    ```python
    {
      "cliente": "Maria",
      "itens": [{"descricao": "Armário", "quantidade": 2, "preco_unitario": "1250.50", "subtotal": "2501.00"}],
      "subtotal": "2501.00",
      "desconto_percentual": "10.00",
      "desconto_valor": "250.10",
      "frete": "80.00",
      "total": "2330.90"
    }
    ```
    Os itens saem na ordem da primeira inserção; o `subtotal` de cada item é arredondado individualmente. Sem desconto aplicado, `desconto_percentual` e `desconto_valor` são `"0.00"`.
