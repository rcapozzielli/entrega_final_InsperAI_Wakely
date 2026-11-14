"""Janelas de 2 s (passo de 0,5 s) com o resumo em JSON do protocolo do Laya (docs/protocolo_laya.md).

Só usa quadros passados. Os campos são exatamente os do protocolo; nenhum é acrescentado depois.
"""
import numpy as np

JANELA, PASSO, VOLTA = 2.0, 0.5, 8.0
LIM = 0.4
CAMPOS = ["p_fechado_media", "p_fechado_max", "fechado_max_s", "ear_rel_media", "ear_rel_min", "boca_max", "bocejo",
          "cabeca_pitch_media", "cabeca_pitch_min", "cabeca_yaw_abs_max", "olhar_baixo_media", "rosto_frac"]


def _maior_trecho(t, fechado, ate, desde):
    """Maior trecho seguido de olho fechado que termina em (desde, ate], olhando até VOLTA s para trás."""
    melhor, ini, ult = 0.0, None, None
    passo = np.median(np.diff(t)) if len(t) > 1 else 0.04
    for ti, f in zip(t, fechado):
        if f:
            if ini is None or ti - ult > 0.12 + passo + 1e-6:     # mesmo buraco da regra (BURACO_FECH)
                ini = ti
            ult = ti
            if ult > desde:
                melhor = max(melhor, ult - ini + passo)
    return melhor


def janelas(t, s, canais):
    """Devolve (fins das janelas, matriz de campos) para um vídeo. t em s, s = quadros x 61 sinais."""
    canais = list(canais)
    p = np.nanmean(s[:, :2], axis=1)
    ear = np.nanmean(s[:, 2:4], axis=1)
    boca, rosto, pitch, yaw = s[:, 4], s[:, 5] > 0.5, s[:, 6], s[:, 7]
    ld = np.nanmean(s[:, [canais.index("eyeLookDownLeft"), canais.index("eyeLookDownRight")]], axis=1)
    t0 = t[rosto][0] if rosto.any() else t[0]
    base = rosto & (t <= t0 + 30)
    ref_ear = np.nanmedian(ear[base]) if base.any() else np.nan
    ref_pitch = np.nanmedian(pitch[base]) if base.any() else 0.0
    ref_yaw = np.nanmedian(yaw[base]) if base.any() else 0.0
    # filtro de bocejo da demo, quadro a quadro (0,25; 0,12 s seguidos; vale 1 s depois)
    bocejo = np.zeros(len(t), bool)
    altas, ate = 0.0, -1.0
    for i in range(len(t)):
        dt = t[i] - t[i - 1] if i else 0.04
        altas = altas + dt if (not np.isnan(boca[i]) and boca[i] >= 0.25) else 0.0
        if altas >= 0.12 - 1e-6:
            ate = t[i] + 1.0
        bocejo[i] = t[i] <= ate
    fechado = rosto & (p >= LIM)
    fins, linhas = [], []
    fim = t[0] + JANELA
    while fim <= t[-1] + 1e-9:
        m = (t > fim - JANELA) & (t <= fim)
        mv = m & (t > fim - VOLTA)
        mr = m & rosto
        def med(x): return float(np.nanmean(x[mr])) if mr.any() else np.nan  # noqa: E731
        def mn(x): return float(np.nanmin(x[mr])) if mr.any() else np.nan   # noqa: E731
        def mx(x): return float(np.nanmax(x[mr])) if mr.any() else np.nan   # noqa: E731
        idx = np.flatnonzero((t > fim - VOLTA) & (t <= fim))
        linhas.append([
            med(p), mx(p), _maior_trecho(t[idx], fechado[idx], fim, fim - JANELA),
            med(ear / ref_ear), mn(ear / ref_ear), mx(boca), float(bocejo[m].any()),
            med(pitch - ref_pitch), mn(pitch - ref_pitch), mx(np.abs(yaw - ref_yaw)), med(ld),
            float(rosto[m].mean()) if m.any() else 0.0])
        fins.append(fim)
        fim += PASSO
    return np.array(fins), np.array(linhas, dtype=np.float32)


def como_json(linha, casas=2):
    return {c: (None if np.isnan(v) else round(float(v), casas)) for c, v in zip(CAMPOS, linha)}
