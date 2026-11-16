"""Condição 2 da seção 10.4 e microssono na BINUS, como em docs/protocolo_testes_bases_novas.md (escrito antes de rodar).

Uso: python experimentos/testes_bases_novas.py   (usa os .npz que já existirem em data/cache/sinais)
Saída: tabelas na tela e data/cache/testes_bases_novas.json.
"""
import json
import re
from pathlib import Path

import numpy as np

from avaliar import RAIZ, TOL, alarmes, carregar

SIN = RAIZ / "data" / "cache" / "sinais"
BINUS = next((RAIZ / "data/bases_novas/Bases Novas Wakely/Microssono/binus_rpi5/binus_rpi5_x").glob("*/other_testing/x/other_testing"), None)
if BINUS is None and (RAIZ / "data/bases_novas/binus_rpi5/other_testing").is_dir():
    BINUS = RAIZ / "data/bases_novas/binus_rpi5/other_testing"      # só os output.labels, extraídos do zip da base
SISTEMAS = ("yolo", "fusao")
B, SEM = 5000, 42


# ---------------------------------------------------------------- bases só com pessoas acordadas
def videos_acordados():
    """(base, id do vídeo, t, sinais) de Eyeblink8, Drive&Act e UTA alerta."""
    for npz in sorted(SIN.glob("eyeblink8_*.npz")):
        t, s = carregar(npz)
        yield "Eyeblink8", npz.stem, t, s
    # Drive&Act fora (decisão do grupo em 13/11, antes de contar alarmes): o MediaPipe achou o rosto em 1% a 28%
    # dos quadros da câmera da coluna A, então a base não testa os sistemas. Ver o protocolo.
    for npz in sorted((RAIZ / "data/cache/rldd_rico").glob("pessoa_*.npz")):
        d = np.load(npz)
        meta, ser = d["meta"], d["series"]
        idx = [i for i in np.argsort(meta[:, 1]) if meta[i, 0] == 0]          # classe alerta, minutos em ordem
        if not idx:
            continue
        s = np.concatenate([ser[i, :meta[i, 2]] for i in idx])
        yield "UTA alerta", npz.stem, np.arange(len(s)) / 10.0, s


# ---------------------------------------------------------------- BINUS
def rotulo_binus(pasta):
    """Quadro fechado = todas as caixas de olho são "olho fechado" e há pelo menos uma (definido antes de rodar).

    Na base, "olho fechado" é `mata_terpejam` (indonésio). O protocolo citava `mata_tertutup` por engano; a primeira
    execução achou 0 episódios por isso, e o nome foi corrigido sem mudar a definição (ver o protocolo).
    """
    d = json.load(open(pasta / "output.labels", encoding="utf-8"))
    quadros = {}
    for f in d["files"]:
        n = int(re.findall(r"\d+", f["name"])[0])
        olhos = [b["label"].strip() for b in f.get("boundingBoxes", []) if b["label"].strip().startswith("mata_")]
        quadros[n] = bool(olhos) and all(o == "mata_terpejam" for o in olhos)
    ns = sorted(quadros)
    return np.array(ns) / 30.0, np.array([quadros[n] for n in ns])


def episodios(t, fechado, buraco=0.5, passo=1 / 6):
    eps, ini, ult = [], None, None
    for ti, f in zip(t, fechado):
        if f:
            if ini is None or ti - ult > buraco + 1e-6:
                if ini is not None:
                    eps.append((ini, ult + passo))
                ini = ti
            ult = ti
    if ini is not None:
        eps.append((ini, ult + passo))
    return eps


def contar_binus(sistema):
    linhas = []
    for npz in sorted(SIN.glob("binus_*.npz")):
        pasta = BINUS / npz.stem.removeprefix("binus_")
        t, s = carregar(npz)
        tr, fr = rotulo_binus(pasta)
        eps = episodios(tr, fr)
        longos = [e for e in eps if e[1] - e[0] >= 1.0 - 1e-6]
        al = alarmes(sistema, t, s)["microssono"]
        dentro = lambda a, e: e[0] - TOL <= a <= e[1] + TOL  # noqa: E731
        acertos = sum(any(dentro(a, e) for a in al) for e in longos)
        falsos = sum(not any(dentro(a, e) for e in eps) for a in al)
        linhas.append(dict(video=npz.stem, ep=len(longos), ac=acertos, falsos=falsos, horas=(t[-1] + 1 / 6) / 3600))
    return linhas


def metricas(c):
    ac, ep, fa = c["ac"], c["ep"], c["falsos"]
    r = ac / ep if ep else 0
    p = ac / (ac + fa) if ac + fa else 0
    f1 = 2 * p * r / (p + r) if p + r else 0
    f2 = 5 * p * r / (4 * p + r) if p + r else 0
    return dict(recall=r, precisao=p, f1=f1, f2=f2)


def soma(linhas, chaves=("ep", "ac", "falsos", "horas")):
    return {k: sum(l[k] for l in linhas) for k in chaves}


def bootstrap(dif_por_sorteio):
    v = np.array(dif_por_sorteio)
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


if __name__ == "__main__":
    rng = np.random.default_rng(SEM)
    saida = {}

    # ------------------------------------------------------------ condição 2
    acordados = {s: [] for s in SISTEMAS}
    for base, vid, t, s in videos_acordados():
        for sis in SISTEMAS:
            al = alarmes(sis, t, s)["microssono"]
            rosto = float(np.mean(s[:, 5] > 0.5))
            acordados[sis].append(dict(base=base, video=vid, falsos=len(al), horas=t[-1] / 3600, rosto=rosto))
    if acordados["yolo"]:
        print("\nCONDIÇÃO 2: alarmes de microssono por hora em pessoas acordadas (todo alarme é falso)")
        bases = sorted({l["base"] for l in acordados["yolo"]})
        for base in bases + ["TOTAL"]:
            lin = {s: [l for l in acordados[s] if base == "TOTAL" or l["base"] == base] for s in SISTEMAS}
            h = sum(l["horas"] for l in lin["yolo"])
            taxa = {s: sum(l["falsos"] for l in lin[s]) / h for s in SISTEMAS}
            n = len(lin["yolo"])
            difs = []
            for _ in range(B):
                i = rng.integers(0, n, n)
                hh = sum(lin["yolo"][k]["horas"] for k in i)
                difs.append((sum(lin["fusao"][k]["falsos"] for k in i) - sum(lin["yolo"][k]["falsos"] for k in i)) / hh)
            lo, hi = bootstrap(difs)
            rosto = np.mean([l["rosto"] for l in lin["yolo"]])
            print(f"  {base:12s} {n:3d} vídeos {h:6.2f} h  rosto {rosto:5.1%} | YOLO {taxa['yolo']:6.2f}/h  fusão {taxa['fusao']:6.2f}/h"
                  f"  | fusão − YOLO {taxa['fusao'] - taxa['yolo']:+6.2f}/h (IC95% {lo:+.2f} a {hi:+.2f})")
            saida[f"acordados_{base}"] = dict(videos=n, horas=h, taxa=taxa, dif_ic=(lo, hi), rosto=rosto)
        saida["acordados_por_video"] = acordados

    # ------------------------------------------------------------ BINUS
    if BINUS and list(SIN.glob("binus_*.npz")):
        por = {s: contar_binus(s) for s in SISTEMAS}
        print("\nBINUS (teste de microssono, 47 vídeos)")
        for s in SISTEMAS:
            c = soma(por[s])
            m = metricas(c)
            print(f"  {s:6s} episódios de 1 s+ {c['ep']} | achados {c['ac']} | falsos {c['falsos']} ({c['falsos'] / c['horas']:.1f}/h)"
                  f" | recall {m['recall']:.3f} precisão {m['precisao']:.3f} F1 {m['f1']:.3f} F2 {m['f2']:.3f}")
            saida[f"binus_{s}"] = dict(**c, **m)
        n = len(por["yolo"])
        d_f2, d_r, d_fa = [], [], []
        for _ in range(B):
            i = rng.integers(0, n, n)
            cs = {s: soma([por[s][k] for k in i]) for s in SISTEMAS}
            ms = {s: metricas(cs[s]) for s in SISTEMAS}
            d_f2.append(ms["fusao"]["f2"] - ms["yolo"]["f2"])
            d_r.append(ms["fusao"]["recall"] - ms["yolo"]["recall"])
            d_fa.append(cs["fusao"]["falsos"] - cs["yolo"]["falsos"])
        for nome, v in (("F2", d_f2), ("recall", d_r), ("falsos", d_fa)):
            lo, hi = bootstrap(v)
            print(f"  fusão − YOLO, {nome}: IC95% {lo:+.3f} a {hi:+.3f}")
            saida[f"binus_dif_{nome}"] = (lo, hi)
        saida["binus_por_video"] = por

    json.dump(saida, open(RAIZ / "data/cache/testes_bases_novas.json", "w", encoding="utf-8"), indent=1, default=float)
