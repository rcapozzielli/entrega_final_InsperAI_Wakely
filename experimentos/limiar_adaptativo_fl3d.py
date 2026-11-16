"""Frente C, parte do FL3D (docs/protocolo_limiar_adaptativo.md, com o adendo de 14/11).

Roda DENTRO do kernel do notebook, depois das células até a seção 6.3, porque usa o estado dele (fl3d, cols_modelo,
contagens, deixar_um_video_de_fora, limiar_na_calibracao, diferenca_pareada, por_video, AJ_COM, ...).
Saída: tabelas na tela e data/cache/limiar_adaptativo/fl3d.json (inclui os limiares da semente 42 para as bases de teste).
"""
import json
from pathlib import Path

SAIDA_LA = Path("data/cache/limiar_adaptativo")
SAIDA_LA.mkdir(parents=True, exist_ok=True)
JANELA_S, MIN_ROSTO_S, B_MAX, PCT = 30, 5, 0.5, 0.25


def linha_de_base(d, col):
    """b = percentil 25 do P(fechado) nos primeiros 30 s (janela da `referencia`, seção 2.1), só quadros com rosto.

    Recusa (b = 0) com menos de 5 s com rosto na janela ou b > 0,5.
    """
    inicio = d.frame.min()
    p = d.loc[(d.frame < inicio + JANELA_S * FPS) & d.rosto, col].astype(float).dropna()
    if len(p) < MIN_ROSTO_S * FPS:
        return 0.0, True
    b = float(p.quantile(PCT))
    return (0.0, True) if b > B_MAX else (b, False)


def sinal_adaptativo(col_p, b_por_video):
    bv = fl3d.video.map(b_por_video).astype(float)
    return ((fl3d[col_p].astype(float) - bv) / (1 - bv)).clip(0, 1)


# ------------------------------------------------------------------ linha de base e sinais adaptativos
bases_la = {}
for s in SEMENTES:
    col = cols_modelo["YOLO26n-cls", s]
    bases_la[s] = {v: linha_de_base(d, col) for v, d in fl3d.groupby("video")}
    ya = sinal_adaptativo(col, {v: b for v, (b, _) in bases_la[s].items()})
    fl3d[f"yolo_adapt_{s}"] = ya
    fl3d[f"fus_adapt_{s}"] = (fl3d["fech_ear"].astype(float) + ya) / 2

    # conferência 3: com b = 0 em tudo, os sinais adaptativos são exatamente Y e F
    y0 = sinal_adaptativo(col, {v: 0.0 for v in VIDEOS})
    f0 = (fl3d["fech_ear"].astype(float) + y0) / 2
    assert np.array_equal(y0.values, fl3d[col].astype(float).values, equal_nan=True), s
    assert np.array_equal(f0.values, fl3d[f"fus_media_{s}"].astype(float).values, equal_nan=True), s
print("conferência 3: com b = 0, Y-A = Y e F-A = F nas 5 sementes (OK)")

print("\nLinha de base b no FL3D (44 vídeos), por semente")
resumo_b = {}
for s in SEMENTES:
    bs = np.array([b for b, _ in bases_la[s].values()])
    rec = sum(r for _, r in bases_la[s].values())
    resumo_b[s] = {"mediana": float(np.median(bs)), "p90": float(np.percentile(bs, 90)), "máximo": float(bs.max()),
                   "vídeos com b > 0,05": int((bs > 0.05).sum()), "recusadas": int(rec)}
display(pd.DataFrame(resumo_b).T.round(4))

tempo = {v: linha_do_tempo(d) for v, d in fl3d.groupby("video")}

# ------------------------------------------------------------------ validação cruzada (5 sementes)
SINAIS_LA = {"Y-A": [f"yolo_adapt_{s}" for s in SEMENTES], "F-A": [f"fus_adapt_{s}" for s in SEMENTES]}
for nome, cols in SINAIS_LA.items():
    foras_v = [deixar_um_video_de_fora(contagens(c, AJ_COM)).set_index("video")[COLS_CONTA].astype(float) for c in cols]
    por_video[nome, "com filtro"] = sum(foras_v) / len(foras_v)

NOMES_LA = {"Y": "YOLO26n-cls", "F": "Fusão: média", "Y-A": "Y-A", "F-A": "F-A"}
linhas_la = {}
for sigla, nome in NOMES_LA.items():
    m = por_video[nome, "com filtro"]
    linhas_la[sigla] = {"acertos 1 s+": m.ac_l.sum(), "episódios 1 s+": m.ep_l.sum(),
                        "recall 1 s+": m.ac_l.sum() / m.ep_l.sum(), "falsos": m.falsos.sum(),
                        "falsos em bocejo": m.falsos_boc.sum(), **metricas_f(m.ac_l.sum(), m.ep_l.sum(), m.falsos.sum())}
print("\nValidação cruzada nos 44 vídeos, T = 1 s, com filtro (média de 5 sementes)")
tab_cv_la = pd.DataFrame(linhas_la).T
display(tab_cv_la.round(3))

# conferência 1: números de hoje
y, f = linhas_la["Y"], linhas_la["F"]
print(f"conferência 1: Y {y['acertos 1 s+']:.1f}/{y['episódios 1 s+']:.0f}, {y['falsos']:.1f} falsos, F2 {y['F2']:.3f} "
      f"(esperado 143,2/165, 10,2, 0,880) | F {f['acertos 1 s+']:.1f}, {f['falsos']:.1f}, F2 {f['F2']:.3f} "
      f"(esperado 149,6, 6,0, 0,917)")

desafiante = max(["Y-A", "F-A"], key=lambda k: linhas_la[k]["F2"])
comparar_la = {"F − Y": ("F", "Y"), "Y-A − Y": ("Y-A", "Y"), "F-A − F": ("F-A", "F"),
               f"desafiante ({desafiante}) − F": (desafiante, "F")}
difs_la = {k: diferenca_pareada((NOMES_LA[a], "com filtro"), (NOMES_LA[b], "com filtro")) for k, (a, b) in comparar_la.items()}
print("\nDiferenças pareadas por vídeo (a − b), bootstrap de 5.000 sorteios")
display(pd.DataFrame(difs_la).T.round(3))

# ------------------------------------------------------------------ holdout (descrição) e limiares para as bases de teste
holdout_la, limiares_la = {}, {}
for sigla, cols in {"Y": [cols_modelo["YOLO26n-cls", s] for s in SEMENTES], "F": [f"fus_media_{s}" for s in SEMENTES],
                    **SINAIS_LA}.items():
    res = []
    for s, col in zip(SEMENTES, cols):
        lim = limiar_na_calibracao(col, AJ_COM)
        t_ = avaliar_eventos(videos_teste, col, lim, T_ALERTA, ajustes=AJ_COM)
        l_ = avaliar_eventos(videos_teste, col, lim, T_ALERTA, dur_min=T_ALERTA, ajustes=AJ_COM)
        res.append({"semente": s, "limiar": lim, "acertos 1 s+": l_["acertos"], "episódios 1 s+": l_["episódios"],
                    "falsos": t_["falsos alarmes"], **metricas_f(l_["acertos"], l_["episódios"], t_["falsos alarmes"])})
    limiares_la[sigla] = {r["semente"]: float(r["limiar"]) for r in res}
    holdout_la[sigla] = pd.DataFrame(res).drop(columns="semente").mean().to_dict()
print("\nHoldout (5 vídeos), limiar da calibração, média de 5 sementes (só descrição)")
display(pd.DataFrame(holdout_la).T.round(3))
print("limiares da semente 42 (usados nas bases de teste):", {k: v[42] for k, v in limiares_la.items()})

json.dump({"linha_de_base": {str(s): {v: list(x) for v, x in bases_la[s].items()} for s in SEMENTES},
           "resumo_b": {str(k): v for k, v in resumo_b.items()},
           "cv": tab_cv_la.to_dict(orient="index"), "difs": difs_la, "desafiante": desafiante,
           "holdout": holdout_la, "limiares": {k: {str(s): l for s, l in v.items()} for k, v in limiares_la.items()}},
          open(SAIDA_LA / "fl3d.json", "w", encoding="utf-8"), indent=1, default=float)
print("salvo em", SAIDA_LA / "fl3d.json")
