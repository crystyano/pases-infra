Neste repositório (módulos `modelos.py`, `estoque.py`, `relatorio.py` e os testes `test_basico.py`) implemente a **reserva de chapas** no estoque.

Requisitos:

1. `Estoque.reservar(sku, qtd)` reserva `qtd` chapas **sem tirá-las do estoque físico**. `KeyError` se o sku não existir; `ValueError` se `qtd <= 0`; `ValueError("estoque insuficiente")` se `qtd` for maior que o disponível.
2. `Estoque.liberar_reserva(sku, qtd)` desfaz parte da reserva. `ValueError("reserva insuficiente")` se `qtd` for maior que o reservado; `ValueError` se `qtd <= 0`.
3. `Estoque.quantidade(sku)` continua sendo o **total físico**. Novos métodos: `Estoque.reservado(sku)` e `Estoque.disponivel(sku)` (disponível = total − reservado). Para sku inexistente os dois retornam `0`.
4. `Estoque.retirar(sku, qtd)` só pode retirar do **disponível** (a parte reservada fica protegida): se `qtd` for maior que o disponível, `ValueError("estoque insuficiente")`.
5. O relatório muda de formato. Cabeçalho exato: `SKU | Descrição | Total | Reservado | Disp.` e cada linha `sku | descrição | total | reservado | disponível` (separador ` | `, linhas unidas por `\n`, sem linha final em branco).

Atualize os testes existentes se o comportamento mudar. Use as ferramentas para ler e alterar os arquivos e **rode os testes antes de terminar**. Quando acabar, responda com um resumo curto.
