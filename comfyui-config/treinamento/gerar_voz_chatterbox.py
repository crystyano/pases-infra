#!/srv/pases/tts-chatterbox/.venv/bin/python
"""Gera a narracao do treinamento Ardus com o Chatterbox Multilingual pt-BR, clonando a voz de referencia aprovada
(/srv/pases/tts-config/vozes/narrador_ptbr_qwen_design2.wav). Texto: `narracaoVoz` (grafia para a voz), frase por frase,
pausa de 0,25 s. Cada frase e conferida pelo Whisper contra `narracao`; se a semelhanca for baixa, regera com outra semente
(ate 4 tentativas) e fica a melhor. Saida: <OUT>/voz/chatterbox-qwen2/<pasta>/<id>.wav + <id>.json (inicio/fim de cada frase).
Uso: gerar_voz_chatterbox.py [--caps 0 1 ...]   (capitulo 0 = abertura)"""
import argparse, difflib, json, os, re, sys
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
from pathlib import Path
import numpy as np, soundfile as sf, torch
SRC = Path("/home/pases/Treinamento-v2/Treinamento-v2"); OUT = Path("/home/pases/Treinamento-video/v3")
REF = "/srv/pases/tts-config/vozes/narrador_ptbr_qwen_design2.wav"; PAUSA = 0.25; LIMIAR = 0.80
# Revisao de 20/10/2026 (avaliacao: "barulhos e chiados" e "palavras incompletas"). Medido:
#  - 22 de 183 frases terminavam com o som ainda alto (geracao parando no meio da ultima palavra). Terminar o texto
#    com uma pausa (" ...  ") reduziu de 8/22 para 1/22; alem disso a frase e conferida e regerada se cortar.
#  - o "chiado" nao e ruido de fundo nem a marca d'agua: e excesso de energia em 4-8 kHz (-13,5 dB contra -21 dB da
#    referencia limpa). A equalizacao abaixo leva a -19 dB sem mudar a clareza (Whisper igual).
SUFIXO = " ...  "
EQ = "equalizer=f=6000:t=q:w=1.0:g=-8,lowpass=f=10500"
TENTATIVAS = 5
ABERTURA_FALA = ("Bem-vindo ao treinamento do Ardus. Nos próximos capítulos você vai ver, passo a passo, como criar um projeto de móveis planejados: "
                 "do ambiente às medidas, dos materiais ao orçamento, da proposta para o cliente ao caderno executivo da obra.")

def db(x): return 20 * np.log10(np.sqrt((np.asarray(x, dtype=np.float64) ** 2).mean()) + 1e-12)

def aparar(w, sr):
    """Corta o rabo depois da ultima fala (abaixo de pico-40 dB) e aplica esmaecimento de 5 ms na entrada e 25 ms na saida."""
    f = int(0.02 * sr); en = np.array([db(w[i:i + f]) for i in range(0, max(1, len(w) - f), f)])
    if len(en) > 3:
        lim = np.percentile(en, 95) - 40; ult = np.where(en > lim)[0]
        if len(ult): w = w[: min(len(w), (ult[-1] + 3) * f)]
    fi, fo = int(0.005 * sr), int(0.025 * sr)
    w = w.copy(); w[:fi] *= np.linspace(0, 1, fi); w[-fo:] *= np.linspace(1, 0, fo); return w

def termina_cortada(w, sr):
    f = int(0.03 * sr); en = np.array([db(w[i:i + f]) for i in range(0, len(w) - f, f)])
    return len(en) > 4 and en[-2:].mean() > np.percentile(en, 90) - 18

def frases(t): return [f.strip() for f in re.split(r"(?<=[.!?;])\s+", t.strip()) if f.strip()]
NUMEROS = {"um","uma","dois","duas","três","quatro","cinco","seis","sete","oito","nove","dez","quinze","vinte","trinta","quarenta","cinquenta","sessenta","setenta","oitenta","noventa","cem","e"}
def norm(t):
    """Normaliza para comparar: o Whisper escreve "Ardus" como "ar dos"/"Ardos" e numeros por extenso como digitos;
    tira o nome e os numeros dos dois lados para nao punir a voz por isso."""
    t = re.sub(r"\b(ar ?d[ou][sz]|ad[ou]s|árdus|ardus)\b", " ", t.lower())
    return [w for w in re.sub(r"[^a-záéíóúâêôãõçà0-9 ]", " ", t).split() if not w.isdigit() and w not in NUMEROS]

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--caps", nargs="*", type=int); a = ap.parse_args()
    # carga do modelo (mesmo procedimento de chatterbox_ptbr.py)
    from chatterbox.models.s3gen import S3Gen
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    CK = Path("/srv/pases/tts-chatterbox/ckpt-ptbr")
    _orig = S3Gen.load_state_dict
    def _load(self, sd, strict=True, **kw):
        r = _orig(self, sd, strict=False, **kw)
        falta = [k for k in r.missing_keys if k not in ("tokenizer._mel_filters", "tokenizer.window")]
        if falta or r.unexpected_keys: sys.exit(f"S3Gen: chaves inesperadas {falta[:5]} {r.unexpected_keys[:5]}")
        return r
    S3Gen.load_state_dict = _load
    m = ChatterboxMultilingualTTS.from_local(CK, "cuda")
    from faster_whisper import WhisperModel
    wm = WhisperModel("small", device="cpu", compute_type="int8")
    rot = json.loads((SRC / "roteiro.json").read_text(encoding="utf-8"))
    todos = [(0, "00-abertura", [{"id": "A-02", "narracao": ABERTURA_FALA, "narracaoVoz": ABERTURA_FALA.replace("Ardus", "Árdus")}])] + \
            [(c["numero"], c["pasta"], c["cenas"]) for c in rot["capitulos"]]
    relatorio = []
    for num, pasta, cenas in todos:
        if a.caps is not None and num not in a.caps: continue
        d = OUT / "voz" / "chatterbox-qwen2" / pasta; d.mkdir(parents=True, exist_ok=True)
        for s in cenas:
            voz = (s.get("narracaoVoz") or s.get("narracao") or "").strip(); ref_txt = (s.get("narracao") or "").strip()
            if not voz: continue
            w_out = d / f"{s['id']}.wav"
            if w_out.exists() and (d / f"{s['id']}.json").exists(): continue
            fv, fr = frases(voz), frases(ref_txt)
            if len(fr) != len(fv): fr = fv
            partes, tempos, t = [], [], 0.0
            for i, (f, fref) in enumerate(zip(fv, fr)):
                melhor = None
                for tent in range(TENTATIVAS):
                    torch.manual_seed(1000 * tent + i + 7)
                    bruto = m.generate(f + SUFIXO, language_id="pt", audio_prompt_path=REF, exaggeration=0.5, cfg_weight=0.5).squeeze(0).cpu().numpy()
                    cortada = termina_cortada(bruto, m.sr); w = aparar(bruto, m.sr)
                    x16 = np.interp(np.arange(0, len(w), m.sr / 16000), np.arange(len(w)), w).astype(np.float32)
                    hip = " ".join(x.text for x in wm.transcribe(x16, language="pt")[0])
                    sim = difflib.SequenceMatcher(None, norm(fref), norm(hip)).ratio()
                    nr, nh = norm(fref), norm(hip)
                    fim_ok = (not nr) or (nr[-1] in nh[-3:])                     # a ultima palavra saiu?
                    nota = sim - 0.3 * cortada - 0.3 * (not fim_ok)
                    if melhor is None or nota > melhor[0]: melhor = (nota, w, hip, tent, sim, cortada, fim_ok)
                    if sim >= LIMIAR and not cortada and fim_ok: break
                nota, w, hip, tent, sim, cortada, fim_ok = melhor
                if cortada or not fim_ok: print(f"  ATENCAO fim {s['id']} f{i}: cortada={cortada} ultima_palavra_ok={fim_ok} | {hip.strip()[-60:]}", flush=True)
                relatorio.append({"cena": s["id"], "frase": f, "ouvido": hip.strip(), "semelhanca": round(sim, 3), "tentativas": tent + 1, "cortada": bool(cortada), "ultima_palavra_ok": bool(fim_ok)})
                if sim < LIMIAR: print(f"  ATENCAO {s['id']} f{i}: {sim:.2f} | {fref} | ouvido: {hip.strip()}", flush=True)
                partes += [w, np.zeros(int(PAUSA * m.sr), dtype=np.float32)]; tempos.append((t, t + len(w) / m.sr)); t += len(w) / m.sr + PAUSA
            tmp_w = w_out.with_suffix(".bruto.wav"); sf.write(str(tmp_w), np.concatenate(partes[:-1]), m.sr)
            import subprocess
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp_w), "-af", EQ, str(w_out)], check=True); tmp_w.unlink()
            (d / f"{s['id']}.json").write_text(json.dumps(tempos))
        print(pasta, "ok", flush=True)
    rel = OUT / "voz" / "chatterbox-qwen2" / "relatorio.json"
    antigo = json.loads(rel.read_text()) if rel.exists() else []
    rel.write_text(json.dumps(antigo + relatorio, ensure_ascii=False, indent=1))
    if relatorio: print("frases:", len(relatorio), "| semelhanca media %.3f" % np.mean([r["semelhanca"] for r in relatorio]),
                       "| abaixo de", LIMIAR, ":", sum(r["semelhanca"] < LIMIAR for r in relatorio))
