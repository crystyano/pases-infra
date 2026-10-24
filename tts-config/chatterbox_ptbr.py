#!/srv/pases/tts-chatterbox/.venv/bin/python
"""Chatterbox Multilingual (MIT), versao afinada para portugues do Brasil (ResembleAI/Chatterbox-Multilingual-pt-br).
Monta um diretorio local com o T3 pt-BR + S3Gen v3 + arquivos comuns do repositorio base e gera a fala.
Uso: chatterbox_ptbr.py texto.txt saida.wav [--ref voz.wav] [--exag 0.5] [--cfg 0.5]
Obs.: todo audio gerado leva a marca d'agua inaudivel Perth (da Resemble AI)."""
import argparse, os, shutil, sys
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
from pathlib import Path
from huggingface_hub import hf_hub_download
CK = Path("/srv/pases/tts-chatterbox/ckpt-ptbr")
def preparar():
    CK.mkdir(parents=True, exist_ok=True)
    pares = [("ResembleAI/chatterbox", f, f) for f in ("ve.pt", "conds.pt", "Cangjie5_TC.json", "grapheme_mtl_merged_expanded_v1.json")] + \
            [("ResembleAI/Chatterbox-Multilingual-pt-br", "s3gen_v3.pt", "s3gen.pt"), ("ResembleAI/Chatterbox-Multilingual-pt-br", "t3_pt_br.safetensors", "t3_mtl23ls_v2.safetensors")]
    for repo, f, alvo in pares:
        if not (CK / alvo).exists(): shutil.copy(hf_hub_download(repo, f), CK / alvo)
ap = argparse.ArgumentParser(); ap.add_argument("texto"); ap.add_argument("saida"); ap.add_argument("--ref"); ap.add_argument("--exag", type=float, default=0.5); ap.add_argument("--cfg", type=float, default=0.5)
a = ap.parse_args(); preparar()
import torch, torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
# O S3Gen v3 do pacote pt-BR nao traz 2 buffers fixos (filtros mel e janela) que o S3Gen calcula no __init__:
# carrega com strict=False so para eles (qualquer outra chave faltando interrompe).
from chatterbox.models.s3gen import S3Gen
_orig = S3Gen.load_state_dict
def _load(self, sd, strict=True, **kw):
    r = _orig(self, sd, strict=False, **kw)
    falta = [k for k in r.missing_keys if k not in ("tokenizer._mel_filters", "tokenizer.window")]
    if falta or r.unexpected_keys: sys.exit(f"S3Gen: chaves inesperadas {falta[:5]} {r.unexpected_keys[:5]}")
    return r
S3Gen.load_state_dict = _load
m = ChatterboxMultilingualTTS.from_local(CK, "cuda")
t = Path(a.texto).read_text(encoding="utf-8").strip() if os.path.exists(a.texto) else a.texto
w = m.generate(t, language_id="pt", audio_prompt_path=a.ref, exaggeration=a.exag, cfg_weight=a.cfg)
import soundfile as sf; sf.write(a.saida, w.squeeze(0).cpu().numpy(), m.sr); print(a.saida, round(w.shape[-1] / m.sr, 2), "s")
