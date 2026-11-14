"""Monta as janelas rotuladas do protocolo do Laya: FL3D (microssono) e, quando os sinais existirem, Drive&Act (distração).

Saída: data/cache/laya/janelas.npz com base, video, papel (treino/teste/holdout), fim, X (campos) e y (0 normal,
1 distraido, 2 microssono). Nenhum modelo é treinado aqui.
"""
import csv
import sys
from pathlib import Path

import numpy as np

from janelas import CAMPOS, janelas

RAIZ = Path(__file__).resolve().parent.parent
SIN = RAIZ / "data" / "cache" / "sinais"
SAIDA = RAIZ / "data" / "cache" / "laya" / "janelas.npz"
DA_ANOT = RAIZ / "data/bases_novas/Bases Novas Wakely/Microssono/driveandact/iccv_activities_3s_x/activities_3s/a_column_driver"
DISTRAIDO = {"interacting_with_phone", "reading_magazine", "reading_newspaper", "working_on_laptop", "writing",
             "using_multimedia_display", "fetching_an_object", "placing_an_object",
             "looking_or_moving_around (e.g. searching)", "looking_back_left_shoulder", "looking_back_right_shoulder"}
NORMAL = {"sitting_still"}
ROT = {"normal": 0, "distraido": 1, "microssono": 2}


def fl3d():
    d = np.load(SIN / "fl3d.npz")
    vid, frame, estado, grupo, s, canais = d["video"], d["frame"], d["estado"], d["grupo"], d["sinais"], d["canais"]
    for v in np.unique(vid):
        m = vid == v
        t = frame[m] / 25.0
        # episódios de microssono: quadros "microsleep" juntando buracos de até 0,5 s; só os de 1 s ou mais contam
        mic = t[estado[m] == "microsleep"]
        eps, ini, ult = [], None, None
        for ti in mic:
            if ini is None or ti - ult > 0.5 + 1 / 25 + 1e-6:
                if ini is not None:
                    eps.append((ini, ult + 1 / 25))
                ini = ti
            ult = ti
        if ini is not None:
            eps.append((ini, ult + 1 / 25))
        longos = [e for e in eps if e[1] - e[0] >= 1.0 - 1e-6]
        fins, X = janelas(t, s[m], canais)
        y = np.array([ROT["microssono"] if any(a <= f <= b for a, b in longos) else ROT["normal"] for f in fins])
        papel = "treino" if grupo[m][0] == "calibracao" else "holdout"
        yield "FL3D", str(v), papel, fins, X, y


def driveandact():
    split = {}
    for papel, arq in (("treino", "train"), ("treino", "val"), ("teste", "test")):
        for r in csv.DictReader(open(DA_ANOT / f"midlevel.chunks_90.split_0.{arq}.csv", encoding="utf-8")):
            split[r["file_id"].split("/")[-1]] = papel
    anot = {}
    for r in csv.DictReader(open(DA_ANOT / "midlevel.chunks_90.csv", encoding="utf-8")):
        a = r["activity"]
        if a in DISTRAIDO or a in NORMAL:
            anot.setdefault(r["file_id"].split("/")[-1], []).append(
                (int(r["frame_start"]) / 30.0, int(r["frame_end"]) / 30.0, ROT["distraido"] if a in DISTRAIDO else ROT["normal"]))
    for npz in sorted(SIN.glob("da_*.npz")):
        nome = npz.stem.removeprefix("da_")
        if nome not in split or nome not in anot:
            print("sem divisão ou anotação:", nome)
            continue
        d = np.load(npz)
        fins, X = janelas(d["t"], d["sinais"], d["canais"])
        y = np.full(len(fins), -1)
        for a, b, rot in anot[nome]:
            y[(fins >= a) & (fins <= b)] = rot
        k = y >= 0
        yield "Drive&Act", nome, split[nome], fins[k], X[k], y[k]


def binus():
    from testes_bases_novas import BINUS as PASTA, episodios, rotulo_binus
    for npz in sorted(SIN.glob("binus_*.npz")):
        d = np.load(npz)
        tr, fr = rotulo_binus(PASTA / npz.stem.removeprefix("binus_"))
        longos = [e for e in episodios(tr, fr) if e[1] - e[0] >= 1.0 - 1e-6]
        fins, X = janelas(d["t"], d["sinais"], d["canais"])
        y = np.array([ROT["microssono"] if any(a <= f <= b for a, b in longos) else ROT["normal"] for f in fins])
        yield "BINUS", npz.stem, "teste", fins, X, y


def eyeblink8():
    for npz in sorted(SIN.glob("eyeblink8_*.npz")):
        d = np.load(npz)
        fins, X = janelas(d["t"], d["sinais"], d["canais"])
        yield "Eyeblink8", npz.stem, "teste", fins, X, np.zeros(len(fins), int)


if __name__ == "__main__":
    bases = sys.argv[1:] or ["fl3d", "driveandact", "binus", "eyeblink8"]
    partes = []
    for nome in bases:
        partes += list({"fl3d": fl3d, "driveandact": driveandact, "binus": binus, "eyeblink8": eyeblink8}[nome]())
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    cols = dict(base=[], video=[], papel=[], fim=[], y=[])
    Xs = []
    for base, v, papel, fins, X, y in partes:
        n = len(fins)
        cols["base"] += [base] * n
        cols["video"] += [v] * n
        cols["papel"] += [papel] * n
        cols["fim"] += list(fins)
        cols["y"] += list(y)
        Xs.append(X)
    np.savez_compressed(SAIDA, X=np.concatenate(Xs), campos=np.array(CAMPOS), **{k: np.array(v) for k, v in cols.items()})
    y, base, papel = np.array(cols["y"]), np.array(cols["base"]), np.array(cols["papel"])
    for b in np.unique(base):
        for pp in np.unique(papel[base == b]):
            m = (base == b) & (papel == pp)
            print(f"{b:10s} {pp:8s} {m.sum():6d} janelas | normal {np.sum(y[m] == 0)} distraído {np.sum(y[m] == 1)} microssono {np.sum(y[m] == 2)}")
