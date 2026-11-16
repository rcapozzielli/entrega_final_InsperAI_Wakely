"""Filtro de sorriso no alerta de microssono, como em docs/protocolo_filtro_sorriso.md (aprovado antes de rodar).

Uso: python experimentos/filtro_sorriso.py
Bases: classe alerta do UTA-RLDD (data/cache/rldd_rico) e, se os .npz existirem em data/cache/sinais, o Eyeblink8.
A segurança no FL3D é medida no notebook (seção 11.5); aqui, a da BINUS. O filtro é o da demo (demo/alerta.py).
Saída: tabelas na tela e data/cache/filtro_sorriso.json.
"""
import json

import numpy as np

from avaliar import LIMIARES, RAIZ, carregar, sinal  # põe demo/ no caminho

import alerta  # noqa: E402

SIN = RAIZ / "data" / "cache" / "sinais"
SORRISO_LIM = 0.5                      # fixado no protocolo
SENSIBILIDADE = (0.3, 0.7)             # só descrição
I_SORRISO = (53, 54)                   # mouthSmileLeft e mouthSmileRight nos 61 sinais
B, SEM = 5000, 42


def alarmes(t, s, lim):
    """Avisos da fusão (limiar 0,35, filtro de bocejo, T = 1 s, piso) com o filtro de sorriso da demo
    (demo/alerta.py) no limiar `lim` (None = sem filtro). Devolve os instantes por nível e, para cada microssono,
    se havia sorriso ativo (pelo limiar do protocolo) naquele instante."""
    x, boca = sinal("fusao", t, s)
    sorriso = np.nanmean(s[:, list(I_SORRISO)], axis=1)
    r = alerta.RegraAlerta(sorriso=lim is not None, sorriso_lim=SORRISO_LIM if lim is None else lim)
    ref = alerta.RegraAlerta(sorriso=True, sorriso_lim=SORRISO_LIM)      # só observa o sorriso
    saida = {"microssono": [], "sono": [], "sem resposta": [], "micro_com_sorriso": []}
    for ti, xi, bi, si in zip(t, x, boca, sorriso):
        xi = None if np.isnan(xi) else float(xi)
        bi = None if np.isnan(bi) else float(bi)
        si = None if np.isnan(si) else float(si)
        novos, _ = r.passo(float(ti), xi, bi, LIMIARES["fusao"], si)
        _, info = ref.passo(float(ti), xi, bi, LIMIARES["fusao"], si)
        for n in novos:
            saida[n].append(float(ti))
            if n == "microssono":
                saida["micro_com_sorriso"].append(bool(info["sorriso"]))
    return saida


def videos_acordados():
    for npz in sorted(SIN.glob("eyeblink8_*.npz")):
        t, s = carregar(npz)
        yield "Eyeblink8", npz.stem, t, s
    for npz in sorted((RAIZ / "data/cache/rldd_rico").glob("pessoa_*.npz")):
        d = np.load(npz)
        meta, ser = d["meta"], d["series"]
        idx = [i for i in np.argsort(meta[:, 1]) if meta[i, 0] == 0]          # classe alerta, minutos em ordem
        if not idx:
            continue
        s = np.concatenate([ser[i, :meta[i, 2]] for i in idx])
        yield "UTA alerta", npz.stem, np.arange(len(s)) / 10.0, s


if __name__ == "__main__":
    rng = np.random.default_rng(SEM)
    versoes = {"sem filtro": None, "com filtro (0,5)": SORRISO_LIM,
               **{f"sensibilidade {l}": l for l in SENSIBILIDADE}}
    linhas = []
    for base, vid, t, s in videos_acordados():
        for nome, lim in versoes.items():
            a = alarmes(t, s, lim)
            linhas.append(dict(base=base, video=vid, versao=nome, micro=len(a["microssono"]), sono=len(a["sono"]),
                               micro_com_sorriso=int(sum(a["micro_com_sorriso"])), horas=t[-1] / 3600))

    saida = {"linhas": linhas}
    bases = sorted({l["base"] for l in linhas})
    print(f"Bases encontradas: {', '.join(bases)}")
    for base in bases + (["TOTAL"] if len(bases) > 1 else []):
        sel = {v: [l for l in linhas if l["versao"] == v and (base == "TOTAL" or l["base"] == base)] for v in versoes}
        sem, com = sel["sem filtro"], sel["com filtro (0,5)"]
        h = sum(l["horas"] for l in sem)
        print(f"\n{base}: {len(sem)} vídeos, {h:.2f} h (microssono por hora; todo alarme é falso)")
        for v in versoes:
            micro, sono = sum(l["micro"] for l in sel[v]), sum(l["sono"] for l in sel[v])
            print(f"  {v:20s} {micro:4d} avisos de microssono ({micro / h:5.2f}/h) | piso de 3 s: {sono}")
        n = len(sem)
        difs = []
        for _ in range(B):
            i = rng.integers(0, n, n)
            difs.append((sum(com[k]["micro"] for k in i) - sum(sem[k]["micro"] for k in i)) / sum(sem[k]["horas"] for k in i))
        dif = (sum(l["micro"] for l in com) - sum(l["micro"] for l in sem)) / h
        lo, hi = np.percentile(difs, [2.5, 97.5])
        com_sorriso = sum(l["micro_com_sorriso"] for l in sem)
        total = sum(l["micro"] for l in sem)
        pessoas = sum(1 for l in sem if l["micro_com_sorriso"] > 0)
        print(f"  com − sem filtro: {dif:+.2f}/h (IC95% {lo:+.2f} a {hi:+.2f})")
        print(f"  descrição: {com_sorriso} dos {total} avisos sem filtro tinham sorriso ativo, em {pessoas} vídeos")
        saida[base] = dict(videos=n, horas=h, dif=dif, ic=(float(lo), float(hi)), com_sorriso=com_sorriso, total=total)

    # ------------------------------------------------------------ segurança na BINUS (condição 1)
    from testes_bases_novas import BINUS, TOL, episodios, rotulo_binus
    if BINUS and list(SIN.glob("binus_*.npz")):
        por = {v: [] for v in versoes}
        for npz in sorted(SIN.glob("binus_*.npz")):
            t, s = carregar(npz)
            tr, fr = rotulo_binus(BINUS / npz.stem.removeprefix("binus_"))
            eps = episodios(tr, fr)
            longos = [e for e in eps if e[1] - e[0] >= 1.0 - 1e-6]
            for v, lim in versoes.items():
                al = alarmes(t, s, lim)["microssono"]
                dentro = lambda a, e: e[0] - TOL <= a <= e[1] + TOL  # noqa: E731
                por[v].append(dict(video=npz.stem, ep=len(longos), ac=sum(any(dentro(a, e) for a in al) for e in longos),
                                   falsos=sum(not any(dentro(a, e) for e in eps) for a in al)))
        print("\nBINUS, segurança (47 vídeos, fechamentos de 1 s ou mais)")
        for v in versoes:
            ep, ac, fa = (sum(l[k] for l in por[v]) for k in ("ep", "ac", "falsos"))
            print(f"  {v:20s} achados {ac} de {ep} | falsos {fa}")
        perdidos = sum(a["ac"] - b["ac"] for a, b in zip(por["sem filtro"], por["com filtro (0,5)"]))
        print(f"  microssonos perdidos com o filtro (0,5): {perdidos} (critério: no máximo 1)")
        saida["BINUS"] = dict(por_video=por, perdidos=perdidos)

    json.dump(saida, open(RAIZ / "data/cache/filtro_sorriso.json", "w", encoding="utf-8"), indent=1, default=float)
