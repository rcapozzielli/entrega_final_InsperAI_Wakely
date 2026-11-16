"""Protocolo do Laya (docs/protocolo_laya.md): treina nas janelas de treino e mede nas de teste.

Etapas (rodar em ordem):
    python experimentos/laya_cerebro.py logistica          # linha de base: regressão logística nos mesmos campos
    python experimentos/laya_cerebro.py finetune 0         # Laya com fine-tuning, semente 0 (repetir com 1 e 2)
    python experimentos/laya_cerebro.py prever_laya 0      # previsões do Laya da semente 0 nas janelas de teste
    python experimentos/laya_cerebro.py avaliar            # tabelas finais com intervalos
NaN dos campos (sem rosto): na logística, viram a média do treino (0 depois de padronizar); no Laya, viram null.
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "experimentos"))
from janelas import PASSO, como_json  # noqa: E402
from perguntas_laya import ESTADO, ROTULOS  # noqa: E402

PASTA = RAIZ / "data" / "cache" / "laya"
TOL = 0.5


def dados():
    d = np.load(PASTA / "janelas.npz")
    return {k: d[k] for k in d.files}


# ---------------------------------------------------------------- linha de base
def logistica():
    from sklearn.linear_model import LogisticRegression
    d = dados()
    tr = d["papel"] == "treino"
    X = d["X"].astype(np.float64)
    mu, sd = np.nanmean(X[tr], axis=0), np.nanstd(X[tr], axis=0) + 1e-9
    Z = np.nan_to_num((X - mu) / sd)
    m = LogisticRegression(max_iter=2000, random_state=0).fit(Z[tr], d["y"][tr])   # a logística não depende da semente
    proba = m.predict_proba(Z)
    np.save(PASTA / "prev_logistica.npy", proba)
    print("logística treinada em", tr.sum(), "janelas; classes", m.classes_)


# ---------------------------------------------------------------- Laya
def checkpoint():
    import glob
    return glob.glob(str(RAIZ / "data/cache/hf/hub/models--convaiinnovations--laya/snapshots/*"))[0]


def finetune(semente):
    from laya.train import TrainConfig, finetune as ft
    d = dados()
    tr = np.flatnonzero(d["papel"] == "treino")
    arq = PASTA / "treino_laya.csv"
    if not arq.exists():
        with open(arq, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["text", "label"])
            for i in tr:
                w.writerow([json.dumps(como_json(d["X"][i])), ROTULOS[d["y"][i]]])
    cfg = TrainConfig(epochs=4, micro_batch=1, grad_accum=32, seed=semente, question_id="estado",
                      instructions=ESTADO["estado"]["instructions"])
    ini = time.time()
    resumo = ft(str(arq), checkpoint(), str(PASTA / f"laya_ft_s{semente}"), cfg, device="cuda")
    print(f"fine-tuning semente {semente}: {(time.time() - ini) / 60:.0f} min")
    json.dump(resumo, open(PASTA / f"laya_ft_s{semente}_resumo.json", "w"), indent=1, default=str)


def prever_laya(semente):
    import laya
    d = dados()
    ag = laya.load(str(PASTA / f"laya_ft_s{semente}"), device="cuda")
    te = np.flatnonzero(d["papel"] != "treino")
    proba = np.full((len(d["y"]), 3), np.nan)
    estados = [como_json(d["X"][i]) for i in te]
    for k in range(0, len(te), 64):
        rs = ag.predict_batch(estados[k:k + 64], ESTADO)
        for i, r in zip(te[k:k + 64], rs):
            p = r["answers"]["estado"]["probabilities"]
            proba[i] = [p.get(c, 0.0) for c in ROTULOS]
    np.save(PASTA / f"prev_laya_s{semente}.npy", proba)


# ---------------------------------------------------------------- avaliação
def alarmes_de_janelas(fins, classe):
    """Janelas microssono seguidas = um alarme, no fim da primeira."""
    al, antes = [], False
    for f, c in zip(fins, classe):
        if c == 2 and not antes:
            al.append(f)
        antes = c == 2
    return al


def eventos(fins, y):
    """Episódios de microssono rotulados, reconstruídos das janelas (fim de janela dentro do episódio)."""
    eps, ini, ult = [], None, None
    for f, c in zip(fins, y):
        if c == 2:
            if ini is None:
                ini = f
            ult = f
        elif ini is not None:
            eps.append((ini - 2.0, ult)); ini = None
    if ini is not None:
        eps.append((ini - 2.0, ult))
    return eps


def verdade():
    """Por vídeo de teste: (base, vídeo, episódios de 1 s+, todos os episódios, horas, t, sinais).

    Mesmas definições dos protocolos: BINUS como em testes_bases_novas.py; FL3D como em construir_janelas.py
    (quadros "microsleep", buracos de até 0,5 s juntados); Eyeblink8 sem nenhum episódio.
    """
    from avaliar import carregar
    from testes_bases_novas import BINUS, SIN, episodios, rotulo_binus
    d = dados()
    vids = dict.fromkeys((str(b), str(v)) for b, v, pp in zip(d["base"], d["video"], d["papel"]) if pp != "treino")
    fl = np.load(SIN / "fl3d.npz")
    fl_vid = fl["video"].astype(str)
    for b, v in vids:
        if b == "BINUS":
            t, s = carregar(SIN / f"{v}.npz")
            tr, fr = rotulo_binus(BINUS / v.removeprefix("binus_"))
            eps = episodios(tr, fr)
            yield b, v, [e for e in eps if e[1] - e[0] >= 1 - 1e-6], eps, (t[-1] + 1 / 6) / 3600, t, s
        elif b == "Eyeblink8":
            t, s = carregar(SIN / f"{v}.npz")
            yield b, v, [], [], t[-1] / 3600, t, s
        elif b == "FL3D":
            m = fl_vid == v
            t = fl["frame"][m] / 25.0
            mic = t[fl["estado"][m] == "microsleep"]
            eps = episodios(mic, np.ones(len(mic), bool), buraco=0.5 + 1 / 25, passo=1 / 25)
            yield b, v, [e for e in eps if e[1] - e[0] >= 1 - 1e-6], eps, (t[-1] + 1 / 25) / 3600, t, fl["sinais"][m]


def contar(al, longos, eps, horas):
    """Frente B: acerto = episódio de 1 s+ com alarme a até 0,5 s; falso = alarme longe de qualquer episódio anotado."""
    dentro = lambda a, e: e[0] - TOL <= a <= e[1] + TOL  # noqa: E731
    return dict(ep=len(longos), ac=sum(any(dentro(a, e) for a in al) for e in longos),
                falsos=sum(not any(dentro(a, e) for e in eps) for a in al), horas=horas)


def avaliar():
    """Tabelas do protocolo: F2 na BINUS e no holdout do FL3D, alarmes por hora no Eyeblink8, bootstrap por vídeo."""
    from avaliar import alarmes
    from testes_bases_novas import metricas, soma
    d = dados()
    sistemas = {"logistica": np.load(PASTA / "prev_logistica.npy")}
    for s in (0, 1, 2):
        if (PASTA / f"prev_laya_s{s}.npy").exists():
            sistemas[f"laya_s{s}"] = np.load(PASTA / f"prev_laya_s{s}.npy")
    sementes = [k for k in sistemas if k.startswith("laya")]
    por = {}       # por[(sistema, base)] = contagens por vídeo, na mesma ordem para todos os sistemas
    for b, v, longos, eps, horas, t, s in verdade():
        m = (d["base"] == b) & (d["video"] == v)
        fins = d["fim"][m]
        for nome in ("yolo", "fusao"):
            por.setdefault((f"regra_{nome}", b), []).append(contar(alarmes(nome, t, s)["microssono"], longos, eps, horas))
        for nome, p in sistemas.items():
            pm = p[m]
            mic = (pm[:, 1] > 0.5) if pm.shape[1] == 2 else (np.argmax(pm, axis=1) == 2)   # logística: classes [0, 2]
            por.setdefault((nome, b), []).append(contar(alarmes_de_janelas(fins, np.where(mic, 2, 0)), longos, eps, horas))
    nomes = ["regra_yolo", "regra_fusao", "logistica"] + sementes

    def resumo(nome, base, idx=None):
        lin = por[(nome, base)]
        c = soma([lin[k] for k in idx] if idx is not None else lin)
        return dict(**c, **metricas(c), fa_h=c["falsos"] / c["horas"])

    def val(nome, base, chave, idx=None):
        if nome == "laya":   # média das sementes, como manda o protocolo
            return float(np.mean([resumo(s, base, idx)[chave] for s in sementes]))
        return resumo(nome, base, idx)[chave]

    saida = {}
    for base in ("BINUS", "FL3D", "Eyeblink8"):
        print(f"\n{base} ({len(por[('regra_yolo', base)])} vídeos)")
        for nome in nomes:
            r = resumo(nome, base)
            saida[f"{base}_{nome}"] = r
            print(f"  {nome:12s} ep {r['ep']:3d} achados {r['ac']:3d} falsos {r['falsos']:3d} ({r['fa_h']:5.1f}/h) | "
                  f"recall {r['recall']:.3f} precisão {r['precisao']:.3f} F1 {r['f1']:.3f} F2 {r['f2']:.3f}")
        if sementes:
            print(f"  {'laya média':12s} F2 {val('laya', base, 'f2'):.3f}  falsos/h {val('laya', base, 'fa_h'):.1f}")
    rng = np.random.default_rng(42)
    comparar = [("laya", "regra_yolo"), ("laya", "logistica"), ("laya", "regra_fusao"), ("logistica", "regra_yolo")]
    print("\nDiferenças com IC95% (bootstrap pareado por vídeo, 5000 sorteios; laya = média das sementes)")
    for base, chave in (("BINUS", "f2"), ("FL3D", "f2"), ("Eyeblink8", "fa_h"), ("BINUS", "fa_h")):
        n = len(por[("regra_yolo", base)])
        for a, b in comparar:
            if "laya" in (a, b) and not sementes:
                continue
            difs = []
            for _ in range(5000):
                i = rng.integers(0, n, n)
                difs.append(val(a, base, chave, i) - val(b, base, chave, i))
            lo, hi = np.percentile(difs, [2.5, 97.5])
            dif = val(a, base, chave) - val(b, base, chave)
            print(f"  {base:9s} {chave:4s} {a} − {b}: {dif:+.3f} (IC95% {lo:+.3f} a {hi:+.3f})")
            saida[f"dif_{base}_{chave}_{a}_menos_{b}"] = (dif, float(lo), float(hi))
    json.dump(saida, open(PASTA / "avaliacao.json", "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    etapa = sys.argv[1]
    if etapa == "logistica":
        logistica()
    elif etapa == "finetune":
        finetune(int(sys.argv[2]))
    elif etapa == "prever_laya":
        prever_laya(int(sys.argv[2]))
    elif etapa == "avaliar":
        avaliar()
    else:
        raise SystemExit("etapa desconhecida: " + etapa)
