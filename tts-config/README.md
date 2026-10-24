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

## Vozes de narracao (Cap. 8A.15 do manual)
| Script | Funcao |
|---|---|
| `qwen_tts_falar.py` | Qwen3-TTS 1.7B (Apache 2.0): voz pronta ou criada por descricao (VoiceDesign). Ambiente `/srv/pases/tts-qwen` |
| `chatterbox_ptbr.py` | Chatterbox Multilingual pt-BR (MIT, marca d'agua Perth), clonando uma referencia. Ambiente `/srv/pases/tts-chatterbox` (Python 3.14, sem Triton) |
| `vozes/narrador_ptbr_qwen_design2.wav` | Voz de referencia do narrador do treinamento Ardus (criada no VoiceDesign) |

O VoxCPM2 (voz atual dos treinamentos) roda em `/srv/pases/tts-voxcpm`; os geradores estao em `comfyui-config/treinamento/gerar_voz_*.py`.
Os ambientes `tts-qwen/`, `tts-chatterbox/` e `tts-voxcpm/` nao sao versionados (.gitignore).
