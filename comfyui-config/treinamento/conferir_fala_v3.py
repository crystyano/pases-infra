#!/srv/pases/tts/.venv/bin/python
"""Confere a narracao de cada capitulo montado: transcreve com faster-whisper e compara com o texto do roteiro (similaridade de palavras)."""
import json, re, difflib, os, sys, subprocess
import numpy as np
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
from faster_whisper import WhisperModel
SRC="/home/pases/Treinamento-v2/Treinamento-v2"; OUT="/home/pases/Treinamento-video/v3"
rot=json.load(open(f"{SRC}/roteiro.json",encoding="utf-8")); m=WhisperModel("small",device="cpu",compute_type="int8")
norm=lambda t: re.sub(r"[^a-záéíóúâêôãõçà0-9 ]"," ",t.lower()).split()
for c in [{"pasta":"00-abertura","numero":0,"cenas":[{"narracao":"Bem-vindo ao treinamento do Ardus. Nos próximos capítulos você vai ver, passo a passo, como criar um projeto de móveis planejados: do ambiente às medidas, dos materiais ao orçamento, da proposta para o cliente ao caderno executivo da obra."}]}]+rot["capitulos"]:
    ref=" ".join(s.get("narracao","") for s in c["cenas"])

    pcm=subprocess.run(["ffmpeg","-v","error","-i",f"{OUT}/capitulos/{c['pasta']}.mp4","-ac","1","-ar","16000","-f","s16le","-"],capture_output=True).stdout
    segs,_=m.transcribe(np.frombuffer(pcm,np.int16).astype(np.float32)/32768,language="pt",vad_filter=True)
    hip=" ".join(s.text for s in segs)
    r=difflib.SequenceMatcher(None,norm(ref),norm(hip)).ratio()
    print(f"{c['pasta']}: similaridade {r:.3f}",flush=True)
    a,b=norm(ref),norm(hip); sm=difflib.SequenceMatcher(None,a,b)
    dif=[f"{' '.join(a[i1:i2])} -> {' '.join(b[j1:j2])}" for t,i1,i2,j1,j2 in sm.get_opcodes() if t!="equal"]
    print("   diferencas:", "; ".join(dif[:8]))
