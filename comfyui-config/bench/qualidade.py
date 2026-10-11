"""Metricas objetivas de qualidade de video (sem opiniao): detecta o 'piscar' / borrao periodico.
Foi criada depois que um erro de configuracao do VAE (blocos temporais de 16 quadros com sobreposicao de 8)
produziu uma queda de nitidez a cada 8 quadros em todos os videos do LTX 2.5 sem que o benchmark acusasse nada.

piscar(arquivo) -> {"osc_nitidez_pct", "autocorr_lag8", "quedas"}:
  osc_nitidez_pct: desvio da nitidez (variancia do laplaciano, cinza) em relacao a media movel de 9 quadros, em %.
                   Video limpo: ~1-6%. Com o defeito do VAE: 10-28%.
  autocorr_lag8:   autocorrelacao dessa oscilacao em 8 quadros. ~0 = sem periodicidade; ~0.8-0.9 = piscar a cada 8 quadros.
  quedas:          quadros com nitidez >15% abaixo da media movel.
Vale para UM plano (sem cortes de edicao: cortes e fades geram quedas legitimas)."""
import numpy as np


def _lap(a):
    l = a[1:-1, 1:-1] * 4 - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    return float(l.var())


def piscar(caminho, k=9, max_dim=640):
    import av
    q = []
    for fr in av.open(str(caminho)).decode(video=0):
        im = fr.to_image().convert("L"); im.thumbnail((max_dim, max_dim))
        q.append(np.asarray(im, dtype=np.float32))
    if len(q) < 3 * k:
        return {"osc_nitidez_pct": None, "autocorr_lag8": None, "quedas": None}
    sh = np.array([_lap(x) for x in q])
    m = np.convolve(sh, np.ones(k) / k, mode="same")
    rel = ((sh - m) / m)[k:-k]
    r = rel - rel.mean()
    ac = np.correlate(r, r, "full")[len(r) - 1:]
    ac = ac / ac[0] if ac[0] else ac
    quedas = sum(1 for i in range(k, len(q) - k) if sh[i] < 0.85 * m[i])
    return {"osc_nitidez_pct": round(float(rel.std() * 100), 1), "autocorr_lag8": round(float(ac[8]), 2) if len(ac) > 8 else None, "quedas": int(quedas)}
