#!/srv/pases/tts-voxcpm/.venv/bin/python
"""Narracao do treinamento Ardus v4 com o VoxCPM2 (OpenBMB, Apache 2.0, 48 kHz), clonando a voz aprovada
(/srv/pases/tts-config/vozes/narrador_ptbr_qwen_design2.wav + a transcricao dela). Escolhido pelo responsavel em 20/10/2026
contra o Chatterbox pt-BR (comparacao em /home/pases/Treinamento-video/comparacao-voxcpm). Texto: `narracaoVoz`, frase por frase,
pausa de 0,25 s; cada frase conferida pelo Whisper contra `narracao` (semelhanca, ultima palavra, fim cortado) e regerada ate 5 vezes.
Video "A aba Propriedades em detalhe" (22/10/2026). Saida: <OUT>/voz/voxcpm/<pasta>/<id>.wav + <id>.json (inicio/fim de cada frase).
Uso: gerar_voz_voxcpm.py [--caps 0 1 ...]   (capitulo 0 = abertura)"""
import argparse, difflib, json, os, re, sys
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
from pathlib import Path
import numpy as np, soundfile as sf, torch
SRC = Path("/home/pases/Treinamento-Propriedades"); OUT = Path("/home/pases/Treinamento-video/propriedades")
REF = "/srv/pases/tts-config/vozes/narrador_ptbr_qwen_design2.wav"; PAUSA = 0.25; LIMIAR = 0.80
# Revisao de 20/10/2026 (avaliacao: "barulhos e chiados" e "palavras incompletas"). Medido:
#  - 22 de 183 frases terminavam com o som ainda alto (geracao parando no meio da ultima palavra). Terminar o texto
#    com uma pausa (" ...  ") reduziu de 8/22 para 1/22; alem disso a frase e conferida e regerada se cortar.
#  - o "chiado" nao e ruido de fundo nem a marca d'agua: e excesso de energia em 4-8 kHz (-13,5 dB contra -21 dB da
#    referencia limpa). A equalizacao abaixo leva a -19 dB sem mudar a clareza (Whisper igual).
SUFIXO = ""      # o VoxCPM2 nao cortou fins de frase no teste; a conferencia continua
EQ = None        # sem chiado no teste (-17 a -24 dB em 4-8 kHz, referencia -21): nao precisa de equalizacao
TENTATIVAS = 5
ABERTURA_FALA = ("Bem-vindo ao treinamento do Ardus. Nos próximos capítulos você vai ver, passo a passo, como criar um projeto de móveis planejados: "
                 "do ambiente às medidas, dos materiais ao orçamento, da proposta para o cliente ao caderno executivo da obra. "
                 "Você vai montar uma cozinha do zero, capítulo por capítulo.")
# Voz propria do responsavel (fora do Git). Terceira gravacao, de 24/10/2026: os primeiros 59 s (sem a parte do
# alfabeto), com os respiros atenuados (referencia3_limpa.wav), e um trecho limpo com a transcricao exata como guia de entonacao.
PROPRIA = "/home/pases/Treinamento-video/voz-propria"
PROPRIA_REF = f"{PROPRIA}/referencia3_limpa.wav"; PROPRIA_TRECHO = f"{PROPRIA}/referencia3_trecho.wav"
PROPRIA_TRECHO_TXT = "Gostaria que dessa vez o áudio ficasse ainda melhor do que da última vez."
# grafias que a voz propria acerta melhor (teste de 24/10/2026, conferido pelo Whisper)
PROPRIA_GRAFIAS = [("quê érre Codes", "quiú ár côudis"), ("quê érre Code", "quiú ár côude")]
MAPA_FALA = "São doze capítulos curtos, seguindo as seis categorias do painel. Assista em sequência ou vá direto ao que precisa."  # a mesma de montar_treinamento_props.py
REF_TXT = open("/home/pases/Treinamento-video/amostras-vozes-novas/texto.txt", encoding="utf-8").read().strip()  # o que a referencia fala

def db(x): return 20 * np.log10(np.sqrt((np.asarray(x, dtype=np.float64) ** 2).mean()) + 1e-12)

def aparar(w, sr):
    """Corta o rabo depois da ultima fala (abaixo de pico-40 dB) e aplica esmaecimento de 5 ms na entrada e 25 ms na saida."""
    f = int(0.02 * sr); en = np.array([db(w[i:i + f]) for i in range(0, max(1, len(w) - f), f)])
    if len(en) > 3:
        lim = np.percentile(en, 95) - 40; ult = np.where(en > lim)[0]
        if len(ult): w = w[: min(len(w), (ult[-1] + 3) * f)]
    fi, fo = int(0.005 * sr), int(0.025 * sr)
    w = w.copy(); w[:fi] *= np.linspace(0, 1, fi); w[-fo:] *= np.linspace(1, 0, fo); return w

def aparar_inicio(w, sr):
    """Corta o som fraco antes da primeira palavra (respiro, estalo); usado com a voz propria.
    Acha a primeira vogal forte (pico-22 dB) e volta enquanto ainda ha som (acima de pico-50 dB), para nao comer a
    consoante inicial ("F" de "Fica", "S" de "Selecionar"); o respiro fica antes, separado por um trecho de silencio."""
    f = int(0.01 * sr); en = np.array([db(w[i:i + f]) for i in range(0, max(1, len(w) - f), f)])
    if len(en) < 8: return w
    p = np.percentile(en, 95); k = int(np.argmax(en > p - 22))
    while k > 0 and en[k - 1] > p - 50: k -= 1
    w = w[max(0, (k - 3) * f):].copy(); r = int(0.01 * sr); w[:r] *= np.linspace(0, 1, r); return w

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
    ap = argparse.ArgumentParser(); ap.add_argument("--caps", nargs="*", type=int)
    ap.add_argument("--voz", default="narrador", choices=["narrador", "propria"]); a = ap.parse_args()
    PASTA_VOZ = "voxcpm"; PROMPT_WAV, PROMPT_TXT, REF_WAV = REF, REF_TXT, REF
    if a.voz == "propria":   # voz do responsavel (23/10/2026), aprovada com respiros atenuados e inicio aparado
        PASTA_VOZ = "voz-propria3"; PROMPT_WAV, PROMPT_TXT, REF_WAV = PROPRIA_TRECHO, PROPRIA_TRECHO_TXT, PROPRIA_REF
    # carga do modelo (mesmo procedimento de chatterbox_ptbr.py)
    from voxcpm import VoxCPM
    vx = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False); SR = vx.tts_model.sample_rate
    from faster_whisper import WhisperModel
    wm = WhisperModel("small", device="cpu", compute_type="int8")
    rot = json.loads((SRC / "roteiro.json").read_text(encoding="utf-8"))
    ab = [dict(s, id="P-" + s["id"]) for s in rot["abertura"]["cenas"]]
    ab.append({"id": "P-00-MAPA", "narracao": MAPA_FALA})   # v5: fala do mapa do treinamento (fora do roteiro)   # abertura do proprio pacote (ja e de treinamento)
    todos = [(0, "00-abertura", ab)] + \
            [(c["numero"], c["pasta"], c["cenas"]) for c in rot["capitulos"]]
    relatorio = []
    for num, pasta, cenas in todos:
        if a.caps is not None and num not in a.caps: continue
        d = OUT / "voz" / PASTA_VOZ / pasta; d.mkdir(parents=True, exist_ok=True)
        for s in cenas:
            voz = (s.get("narracaoVoz") or s.get("narracao") or "").strip()
            if a.voz == "propria":
                for x, y in PROPRIA_GRAFIAS: voz = voz.replace(x, y)
            ref_txt = (s.get("narracao") or "").strip()
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
                    bruto = np.asarray(vx.generate(text=f + SUFIXO, prompt_wav_path=PROMPT_WAV, prompt_text=PROMPT_TXT, reference_wav_path=REF_WAV,
                                                   cfg_value=2.0, inference_timesteps=10), dtype=np.float32)
                    cortada = termina_cortada(bruto, SR); w = aparar(bruto, SR)
                    if a.voz == "propria": w = aparar_inicio(w, SR)
                    x16 = np.interp(np.arange(0, len(w), SR / 16000), np.arange(len(w)), w).astype(np.float32)
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
                partes += [w, np.zeros(int(PAUSA * SR), dtype=np.float32)]; tempos.append((t, t + len(w) / SR)); t += len(w) / SR + PAUSA
            tmp_w = w_out.with_suffix(".bruto.wav"); sf.write(str(tmp_w), np.concatenate(partes[:-1]), SR)
            import subprocess
            if EQ: subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp_w), "-af", EQ, str(w_out)], check=True); tmp_w.unlink()
            else: tmp_w.replace(w_out)
            (d / f"{s['id']}.json").write_text(json.dumps(tempos))
        print(pasta, "ok", flush=True)
    rel = OUT / "voz" / PASTA_VOZ / "relatorio.json"
    antigo = json.loads(rel.read_text()) if rel.exists() else []
    rel.write_text(json.dumps(antigo + relatorio, ensure_ascii=False, indent=1))
    if relatorio: print("frases:", len(relatorio), "| semelhanca media %.3f" % np.mean([r["semelhanca"] for r in relatorio]),
                       "| abaixo de", LIMIAR, ":", sum(r["semelhanca"] < LIMIAR for r in relatorio))
