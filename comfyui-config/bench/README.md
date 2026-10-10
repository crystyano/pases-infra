# PASES-Bench Visual v1

Suite padronizada de imagem e video da estacao PASES (Cap. 8A.5b do manual).
Mesma ideia do PASES-Bench dos LLMs: prompts, sementes e parametros fixos para que modelos
de epocas diferentes sejam comparaveis em condicoes identicas.

| Arquivo | Funcao |
|---|---|
| `items.json` | Os 8 itens (I1-I4 imagem, V1-V4 video), parametros e metas provisorias. NAO alterar sem criar a v2 |
| `bench.py` | Runner: uma geracao por vez, mede VRAM/RAM/temperatura/potencia, relatorio e folhas de contato |
| `qwen.py` | Workflows do Qwen-Image 2.1 (so avaliacao: licenca Qwen Research, nao comercial) e do 2512 (Apache 2.0; testado e REMOVIDO do disco em 09/10/2026, ver Cap. 8A passo 6D para reinstalar) |
| `ltx.py` | Workflow do LTX 2.5 em formato de API (dois estagios, audio+video; versao imagem-para-video) |
| `fixtures/` | Quadros de entrada dos itens F1/F2 (primeiro e ultimo quadro), 896x512 |
| `results/` | JSON e relatorio de cada rodada, com versoes do ambiente e SHA-256 dos modelos |

```bash
cd /srv/pases/comfyui-config/bench
/srv/pases/comfyui/.venv/bin/python -I bench.py --dry-run         # valida o ambiente, nao gera nada
/srv/pases/comfyui/.venv/bin/python -I bench.py                   # suite completa (Z-Image + Wan), ~40 min
/srv/pases/comfyui/.venv/bin/python -I bench.py --modelo ltx      # so video + F1/F2 (primeiro e ultimo quadro), com o LTX 2.5, ~12 min
/srv/pases/comfyui/.venv/bin/python -I bench.py --imagem qwen     # so imagens (I1-I5) com o Qwen-Image 2.1, ~5 min
/srv/pases/comfyui/.venv/bin/python -I bench.py --imagem qwen2512  # Qwen-Image 2512: exige REINSTALAR os arquivos (Cap. 8A, 6D), ~55 min
/srv/pases/comfyui/.venv/bin/python -I bench.py --only I1 V1      # so alguns itens
```

Pre-requisitos: `ollama ps` vazio (o runner recusa rodar com modelo carregado), `comfyui.service` ativo,
modelos em `/dados/modelos/comfyui/`. Seguranca: aborta a suite se a 5060 Ti passar de 82 C.
Saidas: `results/<rodada>.json|.md` (versionados) e folhas de contato em `/scratch/bench/<rodada>/` (descartaveis).

A qualidade e avaliada por humano (0 a 2 por criterio); a ficha esta em branco no relatorio de cada rodada.
As metas operacionais sao provisorias ate a primeira revisao humana.
