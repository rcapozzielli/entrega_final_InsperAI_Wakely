"""Frente C, parte das bases de teste (docs/protocolo_limiar_adaptativo.md, com o adendo de 14/11).

Precisa de data/cache/limiar_adaptativo/fl3d.json (limiares da semente 42 de Y-A e F-A), gerado por
limiar_adaptativo_fl3d.py dentro do kernel do notebook.
Uso: python experimentos/limiar_adaptativo.py
Saída: tabelas na tela e data/cache/limiar_adaptativo/bases_teste.json.
"""
import json

import numpy as np

from avaliar import alerta
from avaliar import LIMIARES, RAIZ, carregar, referencia_ear, sinais_basicos  # noqa: E402

SIN = RAIZ / "data" / "cache" / "sinais"
SAIDA = RAIZ / "data" / "cache" / "limiar_adaptativo"
JANELA_S, MIN_ROSTO_S, B_MAX, PCT = 30.0, 5.0, 0.5, 25
CAND = ("Y", "F", "Y-A", "F-A")
B, SEM = 5000, 42


def sequencias():
    """(base, unidade, t, sinais): Eyeblink8 (vídeo), UTA alerta e UTA sonolenta (pessoa, minutos em ordem)."""
    for npz in sorted(SIN.glob("eyeblink8_*.npz")):
        t, s = carregar(npz)
        yield "Eyeblink8", npz.stem, t, s
    for classe, base in ((0, "UTA alerta"), (10, "UTA sonolenta")):   # classe 10 = sonolento no UTA-RLDD
        for npz in sorted((RAIZ / "data/cache/rldd_rico").glob("pessoa_*.npz")):
            d = np.load(npz)
            meta, ser = d["meta"], d["series"]
            idx = [i for i in np.argsort(meta[:, 1]) if meta[i, 0] == classe]
            if idx:
                s = np.concatenate([ser[i, :meta[i, 2]] for i in idx])
                yield base, npz.stem, np.arange(len(s)) / 10.0, s


def linha_de_base(t, p, rosto):
    ok = rosto & (t < t[0] + JANELA_S) & ~np.isnan(p)
    dt = float(np.median(np.diff(t)))
    if ok.sum() * dt < MIN_ROSTO_S - 1e-9:
        return 0.0, True
    b = float(np.percentile(p[ok], PCT))
    return (0.0, True) if b > B_MAX else (b, False)


def sinais_candidatos(t, s):
    p, ear, boca, rosto, _ = sinais_basicos(s, t)
    b, recusada = linha_de_base(t, p, rosto)
    fech = np.clip(1 - ear / referencia_ear(t, ear, rosto), 0, 1)
    ya = np.clip((p - b) / (1 - b), 0, 1)
    x = {"Y": p, "F": (fech + p) / 2, "Y-A": ya, "F-A": (fech + ya) / 2}
    x = {k: np.where(rosto, v, np.nan) for k, v in x.items()}
    aberto = ear[rosto & (p < 0.5)]
    return x, boca, b, recusada, float(np.nanmedian(aberto)) if aberto.size else np.nan


def alarmes(t, x, boca, lim):
    """Avisos de microssono da regra da demo (a mesma de avaliar.alarmes), com o limiar dado."""
    antes, alerta.LIMIAR_OLHO = alerta.LIMIAR_OLHO, lim
    r, n = alerta.RegraAlerta(), 0
    try:
        for ti, xi, bi in zip(t, x, boca):
            novos, _ = r.passo(float(ti), None if np.isnan(xi) else float(xi), None if np.isnan(bi) else float(bi))
            n += sum(1 for k in novos if k == "microssono")
    finally:
        alerta.LIMIAR_OLHO = antes
    return n


def taxa(linhas, idx=None):
    sel = linhas if idx is None else [linhas[i] for i in idx]
    h = sum(l["horas"] for l in sel)
    return {c: sum(l["alarmes"][c] for l in sel) / h for c in CAND}


if __name__ == "__main__":
    fl = json.load(open(SAIDA / "fl3d.json", encoding="utf-8"))
    lim = {"Y": LIMIARES["yolo"], "F": LIMIARES["fusao"], "Y-A": fl["limiares"]["Y-A"]["42"], "F-A": fl["limiares"]["F-A"]["42"]}
    desafiante = fl["desafiante"]
    print("limiares:", lim, "| desafiante (maior F2 no FL3D):", desafiante)

    por = {}
    for base, uni, t, s in sequencias():
        x, boca, b, rec, ear_aberto = sinais_candidatos(t, s)
        por.setdefault(base, []).append(dict(unidade=uni, horas=t[-1] / 3600, b=b, recusada=rec, ear_aberto=ear_aberto,
                                             alarmes={c: alarmes(t, x[c], boca, lim[c]) for c in CAND}))

    # conferência: Y e F reproduzem a condição 2 já reportada (testes_bases_novas.py)
    tb = json.load(open(RAIZ / "data/cache/testes_bases_novas.json", encoding="utf-8"))["acordados_por_video"]
    ref = {(l["base"], l["video"]): (l["falsos"], tb["fusao"][i]["falsos"]) for i, l in enumerate(tb["yolo"])}
    for base in ("Eyeblink8", "UTA alerta"):
        for l in por[base]:
            assert (l["alarmes"]["Y"], l["alarmes"]["F"]) == ref[(base, l["unidade"])], (base, l["unidade"])
    print("conferência: Y e F dão os mesmos alarmes da condição 2 em todas as unidades (OK)")

    saida = {"limiares": lim, "desafiante": desafiante}
    print("\nLinha de base b nas bases de teste")
    for base, linhas in por.items():
        bs = np.array([l["b"] for l in linhas])
        r = dict(unidades=len(bs), mediana=float(np.median(bs)), p90=float(np.percentile(bs, 90)), maximo=float(bs.max()),
                 acima_005=int((bs > 0.05).sum()), recusadas=int(sum(l["recusada"] for l in linhas)))
        saida[f"b_{base}"] = r
        print(f"  {base:13s} {r}")

    print("\nAlarmes de microssono por hora (todo alarme é falso nas bases de pessoas acordadas)")
    teste = ["Eyeblink8", "UTA alerta"]
    for base in teste + ["UTA sonolenta"]:
        linhas = por[base]
        tx = taxa(linhas)
        h = sum(l["horas"] for l in linhas)
        zero = {c: sum(l["alarmes"][c] == 0 for l in linhas) for c in CAND}
        top5 = {}
        for c in CAND:
            v = sorted((l["alarmes"][c] for l in linhas), reverse=True)
            top5[c] = sum(v[:5]) / max(sum(v), 1)
        print(f"  {base:13s} {len(linhas):2d} unidades {h:5.2f} h | " +
              " | ".join(f"{c} {tx[c]:5.2f}/h (sem alarme {zero[c]}, 5 maiores {top5[c]:.0%})" for c in CAND))
        saida[f"taxa_{base}"] = dict(horas=h, taxa=tx, sem_alarme=zero, fracao_5_maiores=top5,
                                     alarmes={c: sum(l["alarmes"][c] for l in linhas) for c in CAND})

    # soma das bases de teste e bootstrap estratificado por base
    juntas = por["Eyeblink8"] + por["UTA alerta"]
    soma = taxa(juntas)
    saida["taxa_soma"] = soma
    print(f"\n  SOMA (Eyeblink8 + UTA alerta, {sum(l['horas'] for l in juntas):.2f} h): " +
          " | ".join(f"{c} {soma[c]:.2f}/h" for c in CAND))
    rng = np.random.default_rng(SEM)
    comparar = {"F − Y": ("F", "Y"), "Y-A − Y": ("Y-A", "Y"), "F-A − F": ("F-A", "F"),
                f"desafiante ({desafiante}) − F": (desafiante, "F")}
    amostras = {k: {b: [] for b in teste + ["SOMA"]} for k in comparar}
    for _ in range(B):
        sorteio = {b: [por[b][i] for i in rng.integers(0, len(por[b]), len(por[b]))] for b in teste}
        sorteio["SOMA"] = sorteio["Eyeblink8"] + sorteio["UTA alerta"]
        for b, linhas in sorteio.items():
            tx = taxa(linhas)
            for k, (a, c) in comparar.items():
                amostras[k][b].append(tx[a] - tx[c])
    print("\nDiferenças em alarmes por hora (a − b), bootstrap pareado por unidade, estratificado por base na soma")
    for k, (a, c) in comparar.items():
        for b in teste + ["SOMA"]:
            ponto = (soma if b == "SOMA" else taxa(por[b]))
            lo, hi = np.percentile(amostras[k][b], [2.5, 97.5])
            print(f"  {k:24s} {b:10s} {ponto[a] - ponto[c]:+6.2f}/h (IC95% {lo:+.2f} a {hi:+.2f})")
            saida[f"dif_{k}_{b}"] = (ponto[a] - ponto[c], float(lo), float(hi))

    # viés do olho pequeno (classe alerta do UTA), só descrição
    uta = [l for l in por["UTA alerta"] if not np.isnan(l["ear_aberto"])]
    cortes = np.percentile([l["ear_aberto"] for l in uta], [100 / 3, 200 / 3])
    print(f"\nViés do olho pequeno, UTA alerta (terços do EAR de olho aberto; cortes {cortes[0]:.3f} e {cortes[1]:.3f})")
    for nome, sel in (("terço menor", lambda e: e < cortes[0]), ("terço do meio", lambda e: cortes[0] <= e < cortes[1]),
                      ("terço maior", lambda e: e >= cortes[1])):
        linhas = [l for l in uta if sel(l["ear_aberto"])]
        tx = taxa(linhas)
        print(f"  {nome:13s} {len(linhas):2d} pessoas | " + " | ".join(f"{c} {tx[c]:5.2f}/h" for c in CAND))
        saida[f"olho_{nome}"] = dict(pessoas=len(linhas), taxa=tx)
    top = sorted(por["UTA alerta"], key=lambda l: -l["alarmes"]["Y"])[:5]
    print("  5 pessoas com mais alarmes no Y: " +
          "; ".join(f"{l['unidade']} (EAR aberto {l['ear_aberto']:.3f}, b {l['b']:.3f}): " +
                    "/".join(str(l["alarmes"][c]) for c in CAND) for l in top) + "  [Y/F/Y-A/F-A]")
    saida["top5_Y"] = [dict(unidade=l["unidade"], ear_aberto=l["ear_aberto"], b=l["b"], alarmes=l["alarmes"]) for l in top]

    # critério da 10.4, etapa 2
    d_f2 = fl["difs"][f"desafiante ({desafiante}) − F"]
    c1 = d_f2["F2 IC95% inf."] > 0
    c2 = soma[desafiante] <= soma["F"]
    print(f"\nEtapa 2: {desafiante} − F no FL3D, F2 {d_f2['dif. F2']:+.3f} (IC95% {d_f2['F2 IC95% inf.']:+.3f} a "
          f"{d_f2['F2 IC95% sup.']:+.3f}) -> condição 1 {'PASSA' if c1 else 'NÃO PASSA'} | soma {soma[desafiante]:.2f} contra "
          f"{soma['F']:.2f}/h -> condição 2 {'PASSA' if c2 else 'NÃO PASSA'} | {desafiante} "
          f"{'VIRA' if c1 and c2 else 'NÃO VIRA'} o sistema final")
    saida["etapa2"] = dict(desafiante=desafiante, cond1=bool(c1), cond2=bool(c2))
    saida["por_unidade"] = por
    json.dump(saida, open(SAIDA / "bases_teste.json", "w", encoding="utf-8"), indent=1, default=float)
