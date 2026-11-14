"""Funções comuns para medir os sistemas de microssono em sinais já extraídos (data/cache/sinais/*.npz).

Sistemas (nenhum parâmetro é escolhido aqui; todos vêm do notebook e da demo):
- "yolo": P(fechado) médio dos dois olhos, limiar 0,4, filtro de bocejo e T = 1 s (demo/alerta.py, seção 7);
- "fusao": média entre o fechamento pelo EAR (1 - EAR / referência, cortado em [0, 1]; referência = mediana do EAR
  nos primeiros 30 s com rosto) e o P(fechado) do YOLO, limiar 0,35 (escolhido na calibração do FL3D, seção 6.3),
  mesmo filtro e mesmo T.
A regra é a da demo, quadro a quadro, que repete a do notebook (163 de 163 avisos nos 44 vídeos, seção 6).
"""
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "demo"))
import alerta  # noqa: E402

LIMIARES = {"yolo": 0.4, "fusao": 0.35}
TOL = 0.5          # s de tolerância antes do início e depois do fim de um episódio (frente B)


def sinais_basicos(s, t):
    """Da matriz de 61 sinais: P(fechado) médio, EAR médio, boca, rosto e pitch da cabeça."""
    p = np.nanmean(s[:, :2], axis=1)
    ear = np.nanmean(s[:, 2:4], axis=1)
    boca, rosto, pitch = s[:, 4], s[:, 5] > 0.5, s[:, 6]
    return p, ear, boca, rosto, pitch


def referencia_ear(t, ear, rosto, segundos=30.0):
    ok = rosto & (t <= t[rosto][0] + segundos) if rosto.any() else rosto
    return float(np.nanmedian(ear[ok])) if ok.any() else np.nan


def sinal(sistema, t, s):
    p, ear, boca, rosto, _ = sinais_basicos(s, t)
    if sistema == "yolo":
        x = p
    elif sistema == "fusao":
        fech = np.clip(1 - ear / referencia_ear(t, ear, rosto), 0, 1)
        x = (fech + p) / 2
    else:
        raise ValueError(sistema)
    x = np.where(rosto, x, np.nan)
    return x, boca


def alarmes(sistema, t, s):
    """Instantes (s) dos avisos de microssono, sono e sem resposta da regra da demo."""
    x, boca = sinal(sistema, t, s)
    alerta.LIMIAR_OLHO = LIMIARES[sistema]
    r = alerta.RegraAlerta()
    saida = {"microssono": [], "sono": [], "sem resposta": []}
    for ti, xi, bi in zip(t, x, boca):
        novos, _ = r.passo(float(ti), None if np.isnan(xi) else float(xi), None if np.isnan(bi) else float(bi))
        for n in novos:
            saida[n].append(float(ti))
    alerta.LIMIAR_OLHO = 0.4
    return saida


def carregar(npz):
    d = np.load(npz, allow_pickle=False)
    return d["t"], d["sinais"]
