"""EXPLORATÓRIO (seção 10.3: as gravações do Antônio só servem para achar onde o sistema falha, nunca dão o número final).

Para cada gravação com planilha de rótulos, compara os alarmes de microssono do YOLO com filtro e da fusão com os
trechos rotulados. Saída: data/cache/explorar_gravacoes.csv (um alarme por linha) e um resumo na tela.
"""
import csv
from pathlib import Path

import numpy as np

from avaliar import RAIZ, TOL, alarmes, carregar

GRAV = RAIZ / "data" / "gravacoes"
SIN = RAIZ / "data" / "cache" / "sinais"


def rotulos(arq):
    linhas = list(csv.DictReader(open(arq, encoding="utf-8-sig")))
    return [dict(ini=float(r["inicio_s"]), fim=float(r["fim_s"]), ev=r["evento"], st=r["status"])
            for r in linhas if r["status"] in ("confirmado", "ajustado") and r["evento"] not in ("alerta", "marca_inicio")]


def onde(ta, eventos):
    for e in eventos:
        if e["ini"] - TOL <= ta <= e["fim"] + TOL:
            return e
    return None


saida = []
for npz in sorted(SIN.glob("*antonio*.npz")):
    arq_csv = GRAV / (npz.stem + ".csv")
    if not arq_csv.exists():
        print(f"\n{npz.stem}: sem planilha de rótulos, pulado")
        continue
    t, s = carregar(npz)
    ev = rotulos(arq_csv)
    t_rot = (min(e["ini"] for e in ev), max(e["fim"] for e in ev)) if ev else (0, 0)
    print(f"\n=== {npz.stem} ({t[-1] / 60:.1f} min, {len(ev)} eventos confirmados)")
    for sistema in ("yolo", "fusao"):
        al = alarmes(sistema, t, s)["microssono"]
        micro = [e for e in ev if e["ev"].startswith("microssono")]
        longos = [e for e in micro if e["fim"] - e["ini"] >= 1.0]
        achados = sum(any(e["ini"] - TOL <= a <= e["fim"] + TOL for a in al) for e in longos)
        por_tipo = {}
        sem_rotulo = 0
        for a in al:
            e = onde(a, ev)
            tipo = e["ev"] if e else "sem rótulo"
            saida.append(dict(video=npz.stem, sistema=sistema, t=round(a, 2), trecho=tipo))
            if e is None:
                sem_rotulo += 1
            elif not e["ev"].startswith("microssono"):
                por_tipo[e["ev"]] = por_tipo.get(e["ev"], 0) + 1
        print(f"  {sistema:6s}: microssonos de 1 s ou mais achados {achados}/{len(longos)} | "
              f"alarmes em trechos sem microssono {por_tipo or '{}'} | alarmes fora de qualquer trecho rotulado {sem_rotulo}")

with open(RAIZ / "data" / "cache" / "explorar_gravacoes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["video", "sistema", "t", "trecho"])
    w.writeheader()
    w.writerows(saida)
