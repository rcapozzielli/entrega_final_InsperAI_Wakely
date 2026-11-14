"""Extrai, quadro a quadro, os 61 sinais da demo (ExtratorRosto: P(fechado) do YOLO, EAR, boca, rosto, pose e blendshapes).

Uso (na raiz do repositório):
    python experimentos/extrair_sinais.py data/gravacoes/*.mp4
Saída: data/cache/sinais/<nome do vídeo>.npz com t (s), sinais (quadros x 61) e canais.
Já extraídos são pulados. Nada aqui escolhe limiar ou treina: só mede.
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "demo"))
from sonolencia import ExtratorRosto  # noqa: E402

SAIDA = RAIZ / "data" / "cache" / "sinais"


def extrair_pasta(pasta, ext, fps_origem=30.0, prefixo=""):
    """Pasta de quadros frame_NNNN.jpg (BINUS: um quadro a cada 5 do vídeo original de 30 fps)."""
    import re
    pasta = Path(pasta)
    destino = SAIDA / (prefixo + pasta.name + ".npz")
    if destino.exists():
        print("já existe:", destino.name, flush=True)
        return
    quadros = sorted(pasta.glob("frame_*.jpg"), key=lambda p: int(re.findall(r"\d+", p.stem)[0]))
    linhas, ts = [], []
    for q in quadros:
        bgr = cv2.imdecode(np.fromfile(str(q), np.uint8), cv2.IMREAD_COLOR)   # imdecode aceita caminho com acento
        linhas.append(ext.linha(bgr))
        ts.append(int(re.findall(r"\d+", q.stem)[0]) / fps_origem)
    s = np.stack(linhas).astype(np.float32)
    np.savez_compressed(destino, t=np.array(ts), sinais=s, canais=np.array(ext.canais), fps=len(ts) / (ts[-1] + 1e-9))
    print(f"ok {destino.name}: {len(ts)} quadros, rosto em {np.nanmean(s[:, 5]) * 100:.1f}%", flush=True)


def extrair(video, ext, prefixo=""):
    destino = SAIDA / (prefixo + Path(video).stem + ".npz")
    if destino.exists():
        print("já existe:", destino.name, flush=True)
        return
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    linhas, ts, i, ini = [], [], 0, time.time()
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        linhas.append(ext.linha(bgr))
        ts.append(i / fps)
        i += 1
        if i % 3000 == 0:
            print(f"  {Path(video).name}: {i} quadros, {i / (time.time() - ini):.0f} q/s", flush=True)
    cap.release()
    s = np.stack(linhas).astype(np.float32)
    np.savez_compressed(destino, t=np.array(ts), sinais=s, canais=np.array(ext.canais), fps=fps)
    print(f"ok {destino.name}: {i} quadros a {fps:.1f} fps, rosto em {np.nanmean(s[:, 5]) * 100:.1f}% ({time.time() - ini:.0f} s)", flush=True)


if __name__ == "__main__":
    SAIDA.mkdir(parents=True, exist_ok=True)
    ext = ExtratorRosto()
    args = sys.argv[1:]
    prefixo = ""
    if args and args[0].startswith("--prefixo="):
        prefixo, args = args[0].split("=", 1)[1], args[1:]
    for v in args:
        if Path(v).is_dir():
            extrair_pasta(v, ext, prefixo=prefixo)
        else:
            extrair(v, ext, prefixo)
    ext.fechar()
