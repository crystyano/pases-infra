#!/srv/pases/tts/.venv/bin/python
"""Fala -> texto (faster-whisper `small`, MIT), local, em CPU. Aceita audio ou VIDEO (extrai o audio com ffmpeg).
Uso: transcrever.py arquivo.mp4 [--idioma pt] [--modelo small]
Imprime cada trecho e cada palavra com tempos. Serve para CONFERIR o que um modelo de video falou.
Obs.: o audio e passado ao Whisper como vetor porque a leitura direta de arquivo do faster-whisper 1.2.1 e incompativel com o PyAV 19 instalado."""
import argparse, os, subprocess, tempfile
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1"); os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
import soundfile as sf
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument("arquivo"); ap.add_argument("--idioma", default="pt"); ap.add_argument("--modelo", default="small")
a = ap.parse_args()
with tempfile.TemporaryDirectory() as d:
    wav = os.path.join(d, "a.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", a.arquivo, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    audio, _ = sf.read(wav, dtype="float32")
m = WhisperModel(a.modelo, device="cpu", compute_type="int8")
segs, info = m.transcribe(audio, language=a.idioma, word_timestamps=True, vad_filter=False, beam_size=5)
print(f"idioma: {info.language} ({info.language_probability:.2f}) | duracao: {len(audio)/16000:.1f} s")
# O Whisper ALUCINA texto em silencio/ruido (ja apareceu "O que voce tem..." depois do fim de uma fala real).
# Por isso cada trecho mostra a confianca e os suspeitos sao marcados: sem_fala>0.5 ou logprob medio < -1.0.
n = 0
for s in segs:
    n += 1; suspeito = s.no_speech_prob > 0.5 or s.avg_logprob < -1.0
    print(f"[{s.start:6.2f} - {s.end:6.2f}] {s.text.strip()}   (sem_fala={s.no_speech_prob:.2f} logprob={s.avg_logprob:.2f}){'  <- SUSPEITO (possivel alucinacao)' if suspeito else ''}")
    print("      " + " ".join(f"{w.word.strip()}@{w.start:.2f}" for w in (s.words or [])))
if not n: print("(nenhuma fala reconhecida)")
