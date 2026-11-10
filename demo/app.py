"""Demo do Wakely: webcam -> MediaPipe -> YOLO (P de olho fechado) -> regra de alerta + sonolência -> painel.

Uso (na raiz do repositório):
    uv run python demo/app.py                    # webcam 0, abre o painel no navegador
    uv run python demo/app.py --camera 1         # outra câmera (por exemplo, o celular como webcam)
    uv run python demo/app.py --video arquivo.mp4 --log demo/eventos.csv

O painel fica em http://localhost:8765. Teclas no painel: F = "foi alarme falso" (só registra), R = recalibrar,
P = o que aparece por cima do vídeo (contornos, entradas da MIL ou vídeo limpo), C = câmera em tela cheia.

Nada é gravado além dos eventos (horário e tipo), e só se --log for passado. O vídeo não é salvo.
O Wakely é um protótipo acadêmico: nunca usar dirigindo.
"""
import argparse
import csv
import json
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from alerta import LIMIAR_OLHO, MaquinaEstados  # noqa: E402
from sonolencia import (BOCA_H, BOCA_V, CONTORNO_D, CONTORNO_E, EAR_D, EAR_E,  # noqa: E402
                        ExtratorRosto, MonitorSonolencia, caixa_olho)

# o que aparece por cima do vídeo; a tecla P passa para o próximo
MODOS_PONTOS = ["contornos", "entradas", "limpo"]
BOCA_CONTORNO = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]


def num(x):
    """numpy/NaN -> número JSON ou None."""
    if x is None:
        return None
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(x) else x


def lista(a, casas=4):
    """array numpy (com NaN) -> lista JSON, com None no lugar de NaN."""
    if a is None:
        return None
    return [lista(v, casas) if np.ndim(v) else (None if num(v) is None else round(float(v), casas)) for v in a]


class Demo:
    def __init__(self, args):
        self.args = args
        print("Carregando MediaPipe, YOLO e a rede MIL...", flush=True)
        self.extrator = ExtratorRosto()
        self.monitor = MonitorSonolencia()
        self.maquina = MaquinaEstados()
        self.trava = threading.Lock()
        self.estado = {"nivel": "calibrando", "texto": "Iniciando a câmera...", "iniciado": False}
        self.jpeg = None
        self.sons, self.seq = [], 0
        self.eventos_vistos = 0
        self.log = None
        if args.log:
            novo = not Path(args.log).exists()
            self.log = open(args.log, "a", newline="", encoding="utf-8")
            self.csv = csv.writer(self.log)
            if novo:
                self.csv.writerow(["hora", "t_s", "tipo", "detalhe"])
        self.rodando = True
        self.pedido_recalibrar = False
        self.modo_pontos = MODOS_PONTOS.index(args.pontos)

    # ------------------------------------------------------------------ ações do painel
    def registrar(self, t, tipo, detalhe):
        if self.log:
            self.csv.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), f"{t:.2f}", tipo, detalhe])
            self.log.flush()
        print(f"[{t:7.1f} s] {tipo}: {detalhe}", flush=True)

    def acao(self, tipo):
        with self.trava:
            t = self.estado.get("t", 0.0)
            if tipo == "falso":
                self.maquina.eventos.append((t, "marcado como falso", "tecla F"))
            elif tipo == "recalibrar":
                self.pedido_recalibrar = True     # o laço da câmera reinicia no próximo quadro
            elif tipo == "pontos":
                self.modo_pontos = (self.modo_pontos + 1) % len(MODOS_PONTOS)
                self.estado["modo_pontos"] = MODOS_PONTOS[self.modo_pontos]

    # ------------------------------------------------------------------ laço da câmera
    def abrir(self):
        if self.args.video:
            cap = cv2.VideoCapture(self.args.video)
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            return cap, fps
        cap = cv2.VideoCapture(self.args.camera, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        return cap, None

    def desenhar(self, bgr, est):
        """Quadro para o painel, já na largura do painel (vídeos pequenos, como os de 224 px do UTA, são ampliados
        para o desenho ficar legível). Webcam espelhada, como um espelho. Não é gravado.

        Modos (tecla P): "contornos" (olhos e boca), "entradas" (o que vira entrada da MIL) e "limpo" (só o vídeo)."""
        h, w = bgr.shape[:2]
        escala = self.args.largura_video / w
        img = cv2.resize(bgr, (self.args.largura_video, round(h * escala)),
                         interpolation=cv2.INTER_AREA if escala < 1 else cv2.INTER_LINEAR)
        espelhar = self.args.espelhar and not self.args.video
        if espelhar:
            img = cv2.flip(img, 1)
        modo = MODOS_PONTOS[self.modo_pontos]
        p = self.extrator.pontos
        if p is not None and modo != "limpo":
            p = p * escala
            if espelhar:
                p[:, 0] = img.shape[1] - p[:, 0]
            pi = lambda idx: p[idx].astype(np.int32)                                  # noqa: E731
            pt = lambda i: (int(p[i, 0]), int(p[i, 1]))                               # noqa: E731
            cor = (60, 60, 230) if est.get("fechado") else (90, 200, 90)          # BGR: vermelho fechado, verde aberto
            cor_boca = (40, 180, 240) if est.get("bocejo") else (200, 200, 200)  # âmbar durante bocejo
            if modo == "contornos":
                for contorno in (CONTORNO_E, CONTORNO_D):
                    cv2.polylines(img, [pi(contorno).reshape(-1, 1, 2)], True, cor, 2)
                cv2.polylines(img, [pi(BOCA_CONTORNO).reshape(-1, 1, 2)], True, cor_boca, 2)
            else:
                # malha inteira, clarinha: a pose da cabeça e as 7 expressões usadas pela MIL vêm do rosto todo
                for x, y in p[:468].astype(np.int32):
                    cv2.circle(img, (int(x), int(y)), 1, (150, 150, 150), -1, cv2.LINE_AA)
                # recorte de cada olho que vai para o YOLO -> P(olho fechado)
                for contorno in (CONTORNO_E, CONTORNO_D):
                    x0, y0, x1, y1 = caixa_olho(p[contorno])
                    cv2.rectangle(img, (x0, y0), (x1, y1), (230, 200, 60), 1, cv2.LINE_AA)
                cv2.putText(img, "YOLO", (x0, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (230, 200, 60), 1, cv2.LINE_AA)
                # EAR: 6 pontos por olho, duas alturas sobre a largura
                for idx in (EAR_E, EAR_D):
                    for a, b in ((0, 3), (1, 5), (2, 4)):
                        cv2.line(img, pt(idx[a]), pt(idx[b]), cor, 1, cv2.LINE_AA)
                    for i in idx:
                        cv2.circle(img, pt(i), 3, cor, -1, cv2.LINE_AA)
                # abertura da boca: 3 alturas sobre a largura
                cv2.line(img, pt(BOCA_H[0]), pt(BOCA_H[1]), cor_boca, 1, cv2.LINE_AA)
                for a, b in BOCA_V:
                    cv2.line(img, pt(a), pt(b), cor_boca, 1, cv2.LINE_AA)
                for i in [*BOCA_H, *[k for par in BOCA_V for k in par]]:
                    cv2.circle(img, pt(i), 3, cor_boca, -1, cv2.LINE_AA)
        ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return jpg.tobytes() if ok else None

    def laco(self):
        cap, fps_video = self.abrir()
        if not cap.isOpened():
            with self.trava:
                self.estado = {"nivel": "sem rosto", "texto": "Não consegui abrir a câmera", "iniciado": False}
            print("Não consegui abrir a câmera/vídeo.", flush=True)
            return
        t0, i, fps_ema, ms_ema = time.monotonic(), 0, None, None
        t_ant = None
        while self.rodando:
            ok, bgr = cap.read()
            if not ok:
                if self.args.video:
                    print("Fim do vídeo.", flush=True)
                    break
                time.sleep(0.01)
                continue
            if self.args.video:
                t = i / fps_video
                if not self.args.rapido:                       # reproduz no tempo real do vídeo
                    espera = t0 + t - time.monotonic()
                    if espera > 0:
                        time.sleep(espera)
            else:
                t = time.monotonic() - t0
            i += 1
            if self.pedido_recalibrar:
                with self.trava:
                    self.pedido_recalibrar = False
                    self.monitor.reiniciar()
                    self.maquina.reiniciar()
                    self.eventos_vistos = 0
                    self.maquina.eventos.append((t, "recalibrar", "tecla R"))
            inicio = time.perf_counter()
            linha = self.extrator.linha(bgr)
            rosto = bool(linha[5] == 1)
            p_fech = num(np.nanmean(linha[:2])) if rosto else None
            boca = num(linha[4]) if rosto else None
            mon = self.monitor.adicionar(t * 1000, linha)
            with self.trava:
                est = self.maquina.passo(t, rosto, p_fech, boca, mon)
                ms = (time.perf_counter() - inicio) * 1000
                ms_ema = ms if ms_ema is None else 0.9 * ms_ema + 0.1 * ms
                if t_ant is not None and t > t_ant:
                    f = 1 / (t - t_ant)
                    fps_ema = f if fps_ema is None else 0.9 * fps_ema + 0.1 * f
                t_ant = t
                for s in est["sons"]:
                    self.seq += 1
                    self.sons = (self.sons + [{"id": self.seq, "tipo": s}])[-20:]
                for ev in self.maquina.eventos[self.eventos_vistos:]:
                    self.registrar(*ev)
                self.eventos_vistos = len(self.maquina.eventos)
                ent = self.monitor.entradas_ao_vivo()
                self.estado = {
                    "iniciado": True, "t": t, "nivel": est["nivel"], "texto": est["texto"],
                    "rosto": rosto, "p_fech": p_fech, "limiar_olho": LIMIAR_OLHO, "boca": boca,
                    "bocejo": est["bocejo"], "fechado": est["fechado"], "fechado_ha": est["fechado_ha"],
                    "micros_5min": est["micros_5min"],
                    "calibrando": mon["calibrando"], "seg_calibrar": num(mon["segundos_para_calibrar"]),
                    "seg_proxima_mil": num(mon["segundos_para_proxima_mil"]), "minutos_mil": mon["minutos_no_saco"],
                    "perclos": num(mon["perclos"]), "limiar_perclos": self.monitor.cfg["limiar_perclos"],
                    "p_mil": num(mon["p_mil"]), "limiar_mil": self.monitor.cfg["limiar_mil"],
                    "fps": num(fps_ema), "ms": num(ms_ema),
                    "eventos": [{"t": round(a, 1), "tipo": b, "detalhe": c} for a, b, c in self.maquina.eventos[-8:]][::-1],
                    "sons": self.sons, "video": not self.args.sem_video,
                    "modo_pontos": MODOS_PONTOS[self.modo_pontos],
                    "entradas": {"series": lista(ent["series"]), "segundos": ent["segundos"],
                                 "referencia": lista(ent["referencia"]), "atributos": ent["atributos"],
                                 "calibracao": lista(ent["atrib_calibracao"]), "ultimo": lista(ent["atrib_ultimo"])},
                }
            if not self.args.sem_video:
                jpg = self.desenhar(bgr, est)
                with self.trava:
                    self.jpeg = jpg
        cap.release()
        self.extrator.fechar()


def criar_servidor(demo, porta):
    painel = (AQUI / "painel.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _enviar(self, corpo, tipo, codigo=200):
            self.send_response(codigo)
            self.send_header("Content-Type", tipo)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._enviar(painel, "text/html; charset=utf-8")
            elif self.path.startswith("/estado"):
                with demo.trava:
                    corpo = json.dumps(demo.estado, ensure_ascii=False).encode("utf-8")
                self._enviar(corpo, "application/json; charset=utf-8")
            elif self.path.startswith("/quadro.jpg"):
                with demo.trava:
                    jpg = demo.jpeg
                if jpg:
                    self._enviar(jpg, "image/jpeg")
                else:
                    self._enviar(b"", "image/jpeg", 204)
            elif self.path.startswith("/acao/"):
                demo.acao(self.path.split("/")[-1])
                self._enviar(b"ok", "text/plain")
            elif self.path.startswith("/video"):
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=quadro")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    while demo.rodando:
                        with demo.trava:
                            jpg = demo.jpeg
                        if jpg:
                            self.wfile.write(b"--quadro\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n")
                        time.sleep(0.07)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
            else:
                self._enviar(b"nao encontrado", "text/plain", 404)

    return ThreadingHTTPServer(("127.0.0.1", porta), Handler)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--camera", type=int, default=0, help="índice da câmera (padrão 0)")
    ap.add_argument("--video", help="usar um arquivo de vídeo no lugar da câmera (para testar)")
    ap.add_argument("--rapido", action="store_true", help="com --video, processar o mais rápido possível")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--log", help="arquivo CSV para registrar só os eventos (sem vídeo)")
    ap.add_argument("--sem-video", action="store_true", help="não mostrar a imagem da câmera no painel")
    ap.add_argument("--largura-video", type=int, default=960, help="largura da imagem mostrada no painel (px)")
    ap.add_argument("--nao-espelhar", action="store_true", help="não espelhar a imagem da webcam no painel")
    ap.add_argument("--pontos", choices=MODOS_PONTOS, default="contornos",
                    help="o que desenhar por cima do vídeo ao abrir (a tecla P troca no painel)")
    ap.add_argument("--sem-navegador", action="store_true", help="não abrir o navegador sozinho")
    args = ap.parse_args()
    args.espelhar = not args.nao_espelhar

    demo = Demo(args)
    servidor = criar_servidor(demo, args.porta)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    url = f"http://localhost:{args.porta}"
    print(f"Painel em {url}  (Ctrl+C para sair)", flush=True)
    if not args.sem_navegador:
        webbrowser.open(url)
    try:
        demo.laco()
        if args.video:                       # mantém o painel no ar para ver o resultado final
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        demo.rodando = False
        servidor.shutdown()
        if demo.log:
            demo.log.close()


if __name__ == "__main__":
    main()
