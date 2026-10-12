# llm-bench — PASES-Bench v1 (LLM) com fixtures SINTETICAS (Cap. 8.9 do manual)

Mede um LLM do Ollama contra as metas do Cap. 8.2. As fixtures **oficiais** do manual (modulo real do Moventus, imagens do Promob, PDF escaneado)
nunca existiram; esta versao usa **fixtures sinteticas de marcenaria**, com testes automaticos escritos aqui.

```bash
cd /srv/pases/llm-bench
./bench_llm.py --validar                         # confere as fixtures contra as solucoes de referencia (nao chama o modelo)
./bench_llm.py --modelo qwen-cline --reps 3      # roda tudo; precisa do Ollama no ar e do ComfyUI parado (VRAM livre)
./bench_llm.py --modelo qwen-cline --reps 5 --refatoracao   # so o item 2, nas 3 fixtures de refatoracao
BENCH_THINK=off ./bench_llm.py --modelo qwen38-bench --reps 3   # modelos com raciocinio (ex.: Qwen3.8): off/on forca o modo; sem a variavel vale o padrao do modelo
```

Ambiente de teste (pytest, venv proprio; fora do Git): `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python pytest`.
Resultados e saidas cruas do modelo em `results/<rodada>/` (`resultado.json`, `i1_rep*.txt`, `i2_rep*.txt`, `i5_rep*.txt`, `i6_rep*/`).

| Item | O que testa | Como pontua |
|---|---|---|
| 1 | Gerar um modulo Python (orcamento) a partir de uma especificacao fixa | 23 testes ocultos (pytest) |
| 2 | Refatorar um modulo bagunçado sem mudar o comportamento (3 fixtures: pedido, parcelas, producao) | 193 + 241 + 141 testes de caracterizacao (comportamento congelado do original) + metricas de estrutura (AST) + causa do primeiro erro |
| 5 | Pergunta de negocio em portugues com resposta numerica (lucro R$ 1.116,50; margem 23,02%) | numeros corretos, portugues e limite de linhas (automatico); a avaliacao do portugues e HUMANA |
| 6 | Tarefa de agente com ferramentas (list/read/write/run_tests) em um repositorio de 3 modulos | 12 testes ocultos depois do agente terminar |

Itens 3 e 4 (visao) nao se aplicam a modelos so de texto. As fixtures foram validadas: os testes passam nas solucoes de referencia, falham no codigo inicial e
detectam erros plantados (mutantes). Os testes ocultos nao sao mostrados ao modelo.
Cuidado: o codigo gerado pelo modelo e EXECUTADO localmente (pasta temporaria, sem rede nem segredos no ambiente, timeout de 120 s).
