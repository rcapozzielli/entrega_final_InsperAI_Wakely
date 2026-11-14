"""Extrai os 61 sinais da demo (ExtratorRosto) em todos os quadros do FL3D, na mesma ordem da tabela `fl3d` do notebook (seção 1).

A extração da seção 2 guardou só EAR, olhos e pontos; a pose e os blendshapes, que o protocolo do Laya usa, não estavam
no cache do FL3D. Nada aqui treina ou escolhe limiar.
Saída: data/cache/sinais/fl3d.npz com video, frame, estado, grupo (calibração/teste), sinais e canais.
"""
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "demo"))
from sonolencia import ExtratorRosto  # noqa: E402

PASTA_FL3D = RAIZ / "data/kagglehub/datasets/matjazmuc/frame-level-driver-drowsiness-detection-fl3d/versions/1/classification_frames"
SAIDA = RAIZ / "data" / "cache" / "sinais" / "fl3d.npz"


def tabela_fl3d():
    # igual à célula da seção 1 do notebook
    linhas = []
    for pasta in sorted(p for p in PASTA_FL3D.iterdir() if p.is_dir()):
        anot = json.load(open(pasta / "annotations_final.json"))
        for nome, info in anot.items():
            if info["driver_state"] is not None:
                linhas.append((pasta.name, int(re.findall(r"\d+", nome)[0]), nome, info["driver_state"]))
    linhas.sort(key=lambda r: (r[0], r[1]))
    teste = sorted({k.split("/")[2] for k in json.load(open(PASTA_FL3D / "annotations_holdout.json"))})
    return linhas, teste


if __name__ == "__main__":
    if SAIDA.exists():
        sys.exit("já existe: " + str(SAIDA))
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    linhas, teste = tabela_fl3d()
    ext = ExtratorRosto()
    sinais, ini = [], time.time()
    for i, (video, frame, nome, estado) in enumerate(linhas):
        rgb = np.asarray(Image.open(PASTA_FL3D / video / nome).convert("RGB"))
        sinais.append(ext.linha(rgb[:, :, ::-1].copy()))      # ExtratorRosto recebe BGR
        if (i + 1) % 5000 == 0:
            print(f"  {i + 1}/{len(linhas)} quadros, {(i + 1) / (time.time() - ini):.0f} q/s", flush=True)
    ext.fechar()
    v, f, n, e = zip(*linhas)
    np.savez_compressed(SAIDA, video=np.array(v), frame=np.array(f), estado=np.array(e),
                        grupo=np.where(np.isin(v, teste), "teste", "calibracao"),
                        sinais=np.stack(sinais).astype(np.float32), canais=np.array(ext.canais), fps=25)
    print(f"ok fl3d: {len(linhas)} quadros em {len(set(v))} vídeos ({time.time() - ini:.0f} s)", flush=True)
