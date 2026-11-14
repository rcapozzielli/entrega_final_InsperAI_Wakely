"""Segunda tentativa do Laya (docs/protocolo_laya.md, "Laya com espera de 1 s"): alarme só com 2 janelas seguidas.

Etapas:
    python experimentos/laya_espera.py janelas_uta     # janelas da classe alerta do UTA-RLDD (teste confirmatório)
    python experimentos/laya_espera.py prever_uta      # Laya semente 0 e logística nessas janelas
    python experimentos/laya_espera.py avaliar         # UTA (confirmatório) + BINUS, Eyeblink8, FL3D (exploratórios)
"""
import json
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "experimentos"))
from janelas import janelas, como_json  # noqa: E402
from laya_cerebro import PASTA, contar, dados, verdade  # noqa: E402

ESPERA = 2          # janelas seguidas (2 x 0,5 s = 1 s, o T da regra); fixado antes de rodar
ARQ_UTA = PASTA / "janelas_uta.npz"


def alarmes_espera(fins, mic, k):
    """Alarme no fim da k-ésima janela microssono seguida; um alarme por sequência."""
    al, seguidas = [], 0
    for f, m in zip(fins, mic):
        seguidas = seguidas + 1 if m else 0
        if seguidas == k:
            al.append(f)
    return al


def uta_alerta():
    """(pessoa, t, sinais, canais) da classe alerta, minutos em ordem, como em testes_bases_novas.py."""
    for npz in sorted((RAIZ / "data/cache/rldd_rico").glob("pessoa_*.npz")):
        d = np.load(npz)
        meta, ser = d["meta"], d["series"]
        idx = [i for i in np.argsort(meta[:, 1]) if meta[i, 0] == 0]
        if idx:
            s = np.concatenate([ser[i, :meta[i, 2]] for i in idx])
            yield npz.stem, np.arange(len(s)) / 10.0, s, d["canais"]


def janelas_uta():
    vid, fim, Xs = [], [], []
    for p, t, s, canais in uta_alerta():
        f, X = janelas(t, s, canais)
        vid += [p] * len(f)
        fim += list(f)
        Xs.append(X)
    np.savez_compressed(ARQ_UTA, video=np.array(vid), fim=np.array(fim), X=np.concatenate(Xs))
    print(len(fim), "janelas de", len(set(vid)), "pessoas")


def prever_uta():
    import laya
    from sklearn.linear_model import LogisticRegression
    from perguntas_laya import ESTADO, ROTULOS
    u, d = np.load(ARQ_UTA), dados()
    # logística: mesmo treino e mesma padronização de laya_cerebro.logistica()
    tr = d["papel"] == "treino"
    X = d["X"].astype(np.float64)
    mu, sd = np.nanmean(X[tr], axis=0), np.nanstd(X[tr], axis=0) + 1e-9
    m = LogisticRegression(max_iter=2000, random_state=0).fit(np.nan_to_num((X[tr] - mu) / sd), d["y"][tr])
    np.save(PASTA / "uta_prev_logistica.npy", m.predict_proba(np.nan_to_num((u["X"] - mu) / sd)))
    ag = laya.load(str(PASTA / "laya_ft_s0"), device="cuda")
    estados = [como_json(x) for x in u["X"]]
    proba = np.zeros((len(estados), 3))
    for k in range(0, len(estados), 64):
        for j, r in enumerate(ag.predict_batch(estados[k:k + 64], ESTADO)):
            p = r["answers"]["estado"]["probabilities"]
            proba[k + j] = [p.get(c, 0.0) for c in ROTULOS]
        if k % 6400 == 0:
            print(k, "de", len(estados), flush=True)
    np.save(PASTA / "uta_prev_laya_s0.npy", proba)


def e_micro(p):
    return (p[:, 1] > 0.5) if p.shape[1] == 2 else (np.argmax(p, axis=1) == 2)


def avaliar():
    from avaliar import alarmes
    from testes_bases_novas import metricas, soma
    rng = np.random.default_rng(42)
    modelos = {"logistica": "logistica", "laya": "laya_s0"}
    saida = {}

    # ---------------- confirmatório: UTA alerta (todo alarme é falso)
    u = np.load(ARQ_UTA)
    prev = {k: np.load(PASTA / f"uta_prev_{v}.npy") for k, v in modelos.items()}
    linhas = []
    for p, t, s, _ in uta_alerta():
        m = u["video"] == p
        lin = dict(pessoa=p, horas=t[-1] / 3600)
        for nome in ("yolo", "fusao"):
            lin[f"regra_{nome}"] = len(alarmes(nome, t, s)["microssono"])
        for k, pr in prev.items():
            for esp in (1, ESPERA):
                lin[f"{k}_{esp}"] = len(alarmes_espera(u["fim"][m], e_micro(pr[m]), esp))
        linhas.append(lin)
    sistemas = [c for c in linhas[0] if c not in ("pessoa", "horas")]
    h = sum(l["horas"] for l in linhas)
    print(f"\nUTA alerta (CONFIRMATÓRIO): {len(linhas)} pessoas, {h:.2f} h, alarmes falsos por hora")
    for sname in sistemas:
        print(f"  {sname:14s} {sum(l[sname] for l in linhas) / h:7.2f}/h")
        saida[f"uta_{sname}"] = sum(l[sname] for l in linhas) / h
    n = len(linhas)
    for a, b in ((f"laya_{ESPERA}", "regra_yolo"), (f"laya_{ESPERA}", "regra_fusao"), (f"laya_{ESPERA}", f"logistica_{ESPERA}")):
        difs = []
        for _ in range(5000):
            i = rng.integers(0, n, n)
            hh = sum(linhas[k]["horas"] for k in i)
            difs.append((sum(linhas[k][a] for k in i) - sum(linhas[k][b] for k in i)) / hh)
        lo, hi = np.percentile(difs, [2.5, 97.5])
        dif = (sum(l[a] for l in linhas) - sum(l[b] for l in linhas)) / h
        print(f"  {a} − {b}: {dif:+.2f}/h (IC95% {lo:+.2f} a {hi:+.2f})")
        saida[f"uta_dif_{a}_menos_{b}"] = (dif, float(lo), float(hi))

    # ---------------- exploratório: bases já vistas
    d = dados()
    prev = {k: np.load(PASTA / f"prev_{v}.npy") for k, v in modelos.items()}
    por = {}
    for b, v, longos, eps, horas, t, s in verdade():
        m = (d["base"] == b) & (d["video"] == v)
        for k, pr in prev.items():
            for esp in (1, ESPERA):
                por.setdefault((f"{k}_{esp}", b), []).append(contar(alarmes_espera(d["fim"][m], e_micro(pr[m]), esp), longos, eps, horas))
    print("\nBases já vistas (EXPLORATÓRIO)")
    for base in ("BINUS", "FL3D", "Eyeblink8"):
        for k in modelos:
            for esp in (1, ESPERA):
                c = soma(por[(f"{k}_{esp}", base)])
                r = dict(**c, **metricas(c), fa_h=c["falsos"] / c["horas"])
                saida[f"{base}_{k}_{esp}"] = r
                print(f"  {base:9s} {k}_{esp:<2d} achados {r['ac']:3d}/{r['ep']:3d} falsos {r['falsos']:3d} ({r['fa_h']:5.1f}/h)"
                      f" recall {r['recall']:.3f} precisão {r['precisao']:.3f} F2 {r['f2']:.3f}")
    json.dump(saida, open(PASTA / "avaliacao_espera.json", "w", encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    {"janelas_uta": janelas_uta, "prever_uta": prever_uta, "avaliar": avaliar}[sys.argv[1]]()
