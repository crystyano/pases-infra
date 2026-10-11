# tts-config — voz local da estacao PASES (Cap. 8A do manual)

Ferramentas de fala em CPU (a GPU fica livre para o ComfyUI). O ambiente em si, `/srv/pases/tts/.venv` (1,6 GB), NAO e versionado
(esta no .gitignore); reconstroi-se assim:

```bash
export PATH="$HOME/.local/bin:$PATH" UV_HTTP_TIMEOUT=300
mkdir -p /srv/pases/tts && cd /srv/pases/tts && uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu
uv pip install --python .venv/bin/python "kokoro==0.9.4" soundfile faster-whisper
```

| Script | Funcao |
|---|---|
| `falar.py "texto" saida.wav [--voz pm_santa] [--grave 0.85]` | Kokoro-82M (Apache 2.0), pt-BR. Modelo ~0,33 GB baixado na 1a execucao |
| `transcrever.py arquivo.mp4` | faster-whisper `small` (MIT), pt. Modelo ~0,48 GB baixado na 1a execucao. Confere o que um video falou |

Modelos ficam em `~/.cache/huggingface/hub` (disco do sistema, ~0,8 GB). Nao precisa de sudo nem de `espeak-ng` (o pacote `misaki` traz a biblioteca).
Os scripts definem `HF_HUB_DISABLE_IMPLICIT_TOKEN=1`: um token revogado em `~/.cache/huggingface/token` faz o Hub recusar ate repositorios publicos.

**Cuidado:** o Whisper pode *alucinar* texto em silencio ou ruido (ja aconteceu: frases inventadas depois do fim de uma fala real, e nao se repetiram na execucao seguinte). `transcrever.py` mostra `sem_fala` e `logprob` por trecho e marca os suspeitos; confie na transcricao so quando o trecho tiver `sem_fala` baixo (< 0,5) e `logprob` razoavel (> -1,0).
