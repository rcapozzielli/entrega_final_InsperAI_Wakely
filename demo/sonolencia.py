"""Estimativa de sonolência para a demo do Wakely: rede MIL da seção 8.7 e PERCLOS do último minuto.

O que este módulo faz, quadro a quadro:
1. ExtratorRosto: roda o MediaPipe (com blendshapes e pose) e o YOLO de olho e devolve a mesma linha de 61 sinais
   da extração da seção 8.5: P(fechado) de cada olho, EAR de cada olho, abertura da boca, rosto, pitch, yaw, roll
   e os 52 blendshapes. A linha também serve à regra de alerta (P(fechado) e boca), com um MediaPipe só por quadro.
2. MonitorSonolencia: reamostra a webcam para 10 fps (o quadro mais próximo de cada 100 ms), junta minutos de 600
   amostras e, a cada minuto completo, devolve:
   - o PERCLOS do último minuto, comparado com o limiar escolhido no UTA;
   - a probabilidade de sonolência da MIL, com o 1º minuto como calibração e os minutos seguintes no "saco".

Os pesos vêm de data/modelos/mil_gru4_uta.pt, gravado pela seção 8.7 do notebook (fora do Git, como todo peso).
A rede é a MIL-GRU-4 híbrida treinada no UTA inteiro, a média das 5 sementes. As contas repetem as do notebook
(canais_14, atributos_16, normalizar_videos e preparar_87).

Limites:
- A calibração supõe que a pessoa começa acordada: quem já começa sonolento fica com o sono "descontado".
- O treino teve vídeos de cerca de 10 minutos, então o saco usa no máximo os últimos 9 minutos. Esse corte é uma
  escolha da demo, não foi validado.
- O limiar do PERCLOS foi escolhido com a média dos minutos de cada vídeo do UTA, e aqui vale para 1 minuto.
- A webcam precisa entregar pelo menos 10 fps. Nada disso é dispositivo de segurança.

Uso:
    extrator = ExtratorRosto()
    monitor = MonitorSonolencia()
    while True:
        ok, bgr = cap.read()
        linha = extrator.linha(bgr)
        estado = monitor.adicionar(time.monotonic() * 1000, linha)
"""
import math
import os
import warnings
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

PASTA_MODELOS = Path(__file__).resolve().parent.parent / "data" / "modelos"
TAM = 64                                                  # lado do recorte de olho da CNN
EAR_E = [33, 160, 158, 133, 153, 144]
EAR_D = [362, 385, 387, 263, 373, 380]
CONTORNO_E = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
CONTORNO_D = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
BOCA_V = [(81, 178), (13, 14), (311, 402)]
BOCA_H = (78, 308)


# ---------------------------------------------------------------- extração por quadro (seções 2 e 8.5)

def ear(p, idx):
    p1, p2, p3, p4, p5, p6 = (p[i] for i in idx)
    return (np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)) / (2 * np.linalg.norm(p1 - p4))


def abertura_boca(p):
    v = sum(np.linalg.norm(p[a] - p[b]) for a, b in BOCA_V) / len(BOCA_V)
    return v / np.linalg.norm(p[BOCA_H[0]] - p[BOCA_H[1]])


def caixa_olho(contorno, fator=1.4):
    """Quadrado (x0, y0, x1, y1) em volta do contorno do olho: a região que vai para o YOLO."""
    cx, cy = contorno.mean(axis=0)
    lado = fator * (contorno[:, 0].max() - contorno[:, 0].min())
    return (int(cx - lado / 2), int(cy - lado / 2), int(cx + lado / 2), int(cy + lado / 2))


def recortar_olho(cinza, contorno, fator=1.4):
    from PIL import Image
    return np.asarray(Image.fromarray(cinza).crop(caixa_olho(contorno, fator)).resize((TAM, TAM), Image.BILINEAR))


def angulos(matriz):
    R = np.asarray(matriz)[:3, :3]
    return (math.degrees(math.atan2(R[2, 1], R[2, 2])), math.degrees(math.asin(max(-1, min(1, -R[2, 0])))),
            math.degrees(math.atan2(R[1, 0], R[0, 0])))


def carregar_yolo_olho(arq=PASTA_MODELOS / "yolo26n_por_pessoa_s42.pt", device="cpu"):
    """YOLO26n-cls de olho da seção 5 (semente 42, a mesma das seções 6.2 e 8). Devolve f(olhos uint8) -> P(fechado)."""
    os.environ.setdefault("YOLO_VERBOSE", "False")
    from ultralytics import YOLO
    aqui = os.getcwd()
    os.chdir(PASTA_MODELOS)                               # o yolo26n-cls.pt base fica em data/modelos
    try:
        rede = YOLO("yolo26n-cls.pt").model
    finally:
        os.chdir(aqui)
    cabeca = rede.model[-1]
    cabeca.linear = nn.Linear(cabeca.linear.in_features, 1)

    class YoloBinario(nn.Module):                         # mesma estrutura do notebook, para as chaves baterem
        def __init__(self):
            super().__init__()
            self.rede = rede

        def forward(self, x):
            saida = self.rede(x)
            return saida if torch.is_tensor(saida) else saida[1]

    modelo = YoloBinario()
    modelo.load_state_dict(torch.load(arq, map_location="cpu")["pesos"])
    modelo.to(device).eval()

    @torch.no_grad()
    def p_fechado(olhos):
        x = torch.from_numpy(np.ascontiguousarray(olhos)).to(device).float().div(255).unsqueeze(1).repeat(1, 3, 1, 1)
        return torch.sigmoid(modelo(x)).squeeze(1).cpu().numpy()
    return p_fechado


class ExtratorRosto:
    """Um quadro BGR -> linha de 61 sinais, na ordem de `canais` (NaN sem rosto, rosto = 0)."""

    def __init__(self, arq_mediapipe=PASTA_MODELOS / "face_landmarker.task", arq_mil=PASTA_MODELOS / "mil_gru4_uta.pt",
                 p_fechado=None, device=None):
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision
        self.mp = mp
        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.canais = torch.load(arq_mil, map_location="cpu")["canais_rico"]
        self.pos_bs = {n: i for i, n in enumerate(self.canais)}
        # modo IMAGE, como na extração do UTA; o MediaPipe não abre caminhos com acento no Windows
        self.detector = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_buffer=Path(arq_mediapipe).read_bytes()),
            running_mode=vision.RunningMode.IMAGE, num_faces=1,
            output_face_blendshapes=True, output_facial_transformation_matrixes=True))
        self.p_fechado = p_fechado or carregar_yolo_olho(device=device)
        self.pontos = None                                # 478 pontos do último quadro, para desenhar na demo

    def linha(self, bgr):
        import cv2
        s = np.full(len(self.canais), np.nan, np.float32)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        r = self.detector.detect(self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
        s[5] = bool(r.face_landmarks)
        self.pontos = None
        if not r.face_landmarks:
            return s
        h, w = rgb.shape[:2]
        p = np.array([[q.x * w, q.y * h] for q in r.face_landmarks[0]])
        self.pontos = p
        cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        olhos = np.stack([recortar_olho(cinza, p[CONTORNO_E]), recortar_olho(cinza, p[CONTORNO_D])])
        s[:2] = self.p_fechado(olhos)
        s[2:5] = ear(p, EAR_E), ear(p, EAR_D), abertura_boca(p[:478])
        if r.facial_transformation_matrixes:
            s[6:9] = angulos(r.facial_transformation_matrixes[0])
        if r.face_blendshapes:
            for c in r.face_blendshapes[0]:
                if c.category_name in self.pos_bs:
                    s[self.pos_bs[c.category_name]] = c.score
        return s

    def fechar(self):
        self.detector.close()


# ---------------------------------------------------------------- sinais por minuto (seções 8.3, 8.5 e 8.7)

def trechos(mascara):
    m = np.r_[False, mascara, False].astype(int)
    d = np.diff(m)
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0] - 1))


def unir(lista, buraco):
    saida = []
    for a, b in lista:
        if saida and a - saida[-1][1] - 1 <= buraco:
            saida[-1] = (saida[-1][0], b)
        else:
            saida.append((a, b))
    return saida


def bocejo_ativo(boca, lim, persistencia, margem):
    # boca aberta por `persistencia` amostras seguidas, e mais `margem` amostras depois (só amostras passadas)
    alta = np.nan_to_num(boca, nan=-np.inf) >= lim
    soma = np.convolve(alta.astype(int), np.ones(persistencia, int))[:len(alta)]
    firme = soma == persistencia
    firme[:persistencia - 1] = False
    return np.convolve(firme.astype(int), np.ones(margem + 1, int))[:len(firme)] > 0


def _media(v):
    v = v[~np.isnan(v)]
    return float(v.mean()) if len(v) else np.nan


def atributos_minuto(s, cfg):
    """Os 16 atributos da seção 8.5 de um minuto [600, 61], na ordem de cfg['atributos']."""
    fps = cfg["fps"]
    with np.errstate(all="ignore"):
        p_fech, ear_m, boca, rosto = s[:, :2].mean(axis=1), s[:, 2:4].mean(axis=1), s[:, 4], s[:, 5] == 1
    fechado = np.nan_to_num(p_fech, nan=-1) >= cfg["lim_fech"]
    dur = np.array([(b - a + 1) / fps for a, b in unir(trechos(fechado), cfg["buraco"])])
    a = {"PERCLOS": fechado[rosto].mean() if rosto.any() else np.nan,
         "piscadas": int((dur <= 0.5).sum()),
         "duração mediana (s)": np.median(dur) if len(dur) else 0.0,
         "fechamentos de 1 s+": int((dur >= cfg["t_alerta"]).sum()),
         "bocejos": len(trechos(bocejo_ativo(boca, **cfg["filtro_bocejo"]))),
         "EAR médio": _media(ear_m)}
    ic = {n: i for i, n in enumerate(cfg["canais_rico"])}
    for j, eixo in enumerate(["pitch", "yaw", "roll"]):
        v = s[:, 6 + j][~np.isnan(s[:, 6 + j])]
        a[f"desvio do {eixo}"] = float(v.std()) if len(v) else np.nan
    for b in cfg["blendshapes"]:
        lados = [n for n in (b + "Left", b + "Right") if n in ic] or [b]
        a[f"{b} médio"] = _media(s[:, [ic[n] for n in lados]].mean(axis=1))
    return np.array([a[n] for n in cfg["atributos"]], np.float64)


def canais_4(s):
    """[minutos, 600, 61] -> [minutos, 600, 4]: P(fechado), EAR, boca e rosto (os 4 primeiros de canais_14)."""
    with np.errstate(all="ignore"):
        return np.concatenate([s[:, :, :2].mean(axis=2, keepdims=True), s[:, :, 2:4].mean(axis=2, keepdims=True),
                               s[:, :, 4:6]], axis=2).astype(np.float32)


# ---------------------------------------------------------------- rede MIL (seção 8.7)

class CodificadorGRU(nn.Module):
    def __init__(self, canais, d=32):
        super().__init__()
        self.gru = nn.GRU(canais, d, batch_first=True)

    def forward(self, x):
        return self.gru(x)[1][-1]


class MILSono(nn.Module):
    """A MILSono do notebook, só com o codificador GRU, para um vídeo por vez."""

    def __init__(self, codificador, canais, n_attr=16, d=32, interno=16, atencao=True):
        super().__init__()
        assert codificador == "gru"
        self.cod = CodificadorGRU(canais, d)
        self.minuto = nn.Linear(d + n_attr, d)
        self.atencao = atencao
        self.V, self.U, self.w = nn.Linear(d, interno), nn.Linear(d, interno), nn.Linear(interno, 1)
        self.saida = nn.Linear(d, 1)

    def forward(self, x, a):
        h = self.minuto(torch.cat([self.cod(x), a], dim=1))                    # [minutos, d]
        e = self.w(torch.tanh(self.V(h)) * torch.sigmoid(self.U(h))).squeeze(1) if self.atencao \
            else torch.zeros(len(h))
        peso = torch.softmax(e, dim=0)
        return self.saida((peso.unsqueeze(1) * h).sum(dim=0)).squeeze(), peso


class ModeloMIL:
    """Carrega mil_gru4_uta.pt e estima P(sonolento) de um vídeo: minuto de calibração + minutos seguintes."""

    def __init__(self, arq=PASTA_MODELOS / "mil_gru4_uta.pt"):
        self.cfg = torch.load(arq, map_location="cpu")
        self.redes = []
        for estado in self.cfg["estados"]:
            rede = MILSono(**self.cfg["arquitetura"])
            rede.load_state_dict(estado)
            self.redes.append(rede.eval())
        self.c = self.cfg["arquitetura"]["canais"]
        self.media_c, self.desvio_c = self.cfg["media_canais"].numpy(), self.cfg["desvio_canais"].numpy()
        self.mediana_a = self.cfg["mediana_atrib"].numpy()
        self.media_a, self.escala_a = self.cfg["media_atrib"].numpy(), self.cfg["escala_atrib"].numpy()

    @staticmethod
    def referencia(calibracao):
        """Mediana de P(fechado), EAR e boca no 1º minuto (com rosto); o 4º canal (rosto) não é deslocado."""
        x_cal = canais_4(calibracao[None])[0]
        rosto = x_cal[:, 3] == 1
        med = np.zeros(4, np.float32)
        if rosto.any():
            med[:3] = [np.nanmedian(x_cal[rosto, c]) if not np.isnan(x_cal[rosto, c]).all() else 0.0
                       for c in range(3)]
        return med

    def entradas(self, calibracao, minutos):
        """calibracao: [600, 61]; minutos: [m, 600, 61] -> tensores normalizados pelo 1º minuto e padronizados."""
        x, med = canais_4(np.asarray(minutos)), self.referencia(calibracao)
        x = x - np.nan_to_num(med)
        z = np.nan_to_num((x[:, :, :self.c] - self.media_c) / self.desvio_c, nan=0.0).astype(np.float32)
        a_cal = atributos_minuto(calibracao, self.cfg)
        a = np.stack([atributos_minuto(m, self.cfg) for m in minutos]) - a_cal
        a = np.where(np.isnan(a), self.mediana_a, a)
        a = ((a - self.media_a) / self.escala_a).astype(np.float32)
        return torch.from_numpy(z), torch.from_numpy(a)

    @torch.no_grad()
    def prever(self, calibracao, minutos):
        """-> (P(sonolento), média das 5 sementes; pesos da atenção por minuto)"""
        z, a = self.entradas(calibracao, minutos)
        saidas = [rede(z, a) for rede in self.redes]
        p = float(np.mean([torch.sigmoid(l).item() for l, _ in saidas]))
        return p, np.mean([w.numpy() for _, w in saidas], axis=0)


# ---------------------------------------------------------------- uso ao vivo

class MonitorSonolencia:
    """Recebe (tempo em ms, linha de 61 sinais) a cada quadro e mantém o estado de sonolência."""

    def __init__(self, arq=PASTA_MODELOS / "mil_gru4_uta.pt", max_minutos=9, max_buraco_ms=250):
        self.mil = ModeloMIL(arq)
        self.cfg = self.mil.cfg
        self.passo = 1000.0 / self.cfg["fps"]
        self.n = self.cfg["amostras_minuto"]
        self.max_minutos, self.max_buraco = max_minutos, max_buraco_ms
        self.reiniciar()

    def reiniciar(self):
        self.t0 = self.anterior = None
        self.k = 0                                       # próxima amostra de 10 fps a preencher
        self.amostras, self.minutos = [], []             # minuto atual e minutos completos (o 1º é a calibração)
        self.ultimas = []                                # últimas 600 amostras, para o PERCLOS deslizante
        self.p_mil, self.pesos = None, None
        self.p_ultimo = None                             # P(sonolento) com só o último minuto no saco (para o painel)
        self.primeiro_do_saco = None                     # número do minuto mais antigo do saco (1 = calibração)
        self.ref_canais = None                          # mediana do 1º minuto (P(fechado), EAR, boca), para o painel
        self.atrib_cal = self.atrib_ultimo = None        # 16 atributos do 1º minuto e do último minuto completo

    def _sem_rosto(self):
        s = np.full(len(self.cfg["canais_rico"]), np.nan, np.float32)
        s[5] = 0
        return s

    def adicionar(self, t_ms, linha):
        if self.t0 is None:
            self.t0, self.anterior = t_ms, (t_ms, linha)
        while self.t0 + self.k * self.passo <= t_ms:      # quadro mais próximo de cada 100 ms
            alvo = self.t0 + self.k * self.passo
            perto = min([self.anterior, (t_ms, linha)], key=lambda q: abs(q[0] - alvo))
            self._guardar(perto[1] if abs(perto[0] - alvo) <= self.max_buraco else self._sem_rosto())
            self.k += 1
        self.anterior = (t_ms, linha)
        return self.estado()

    def _guardar(self, s):
        self.amostras.append(s)
        self.ultimas = (self.ultimas + [s])[-self.n:]
        if len(self.amostras) == self.n:
            self.minutos.append(np.stack(self.amostras))
            self.amostras = []
            # só para mostrar no painel; a MIL refaz essas contas em ModeloMIL.entradas
            if len(self.minutos) == 1:
                self.ref_canais = ModeloMIL.referencia(self.minutos[0])
                self.atrib_cal = atributos_minuto(self.minutos[0], self.cfg)
            else:
                self.atrib_ultimo = atributos_minuto(self.minutos[-1], self.cfg)
            if len(self.minutos) >= 2:
                saco = np.stack(self.minutos[1:][-self.max_minutos:])
                self.p_mil, self.pesos = self.mil.prever(self.minutos[0], saco)
                self.primeiro_do_saco = len(self.minutos) - len(saco) + 1
                # o saco "lembra" o minuto mais sonolento; o último minuto sozinho mostra como a pessoa está agora
                self.p_ultimo = self.p_mil if len(saco) == 1 else self.mil.prever(self.minutos[0], saco[-1:])[0]

    def perclos(self):
        if len(self.ultimas) < self.n:
            return None
        s = np.stack(self.ultimas)
        rosto = s[:, 5] == 1
        if not rosto.any():
            return None
        return float((np.nan_to_num(s[rosto, :2].mean(axis=1), nan=-1) >= self.cfg["lim_fech"]).mean())

    def estado(self):
        per = self.perclos()
        return {"calibrando": not self.minutos,
                "segundos_para_calibrar": 0.0 if self.minutos else (self.n - len(self.amostras)) / self.cfg["fps"],
                "segundos_para_proxima_mil": (self.n - len(self.amostras)) / self.cfg["fps"],
                "minutos_no_saco": max(0, min(len(self.minutos) - 1, self.max_minutos)),
                "perclos": per,
                "perclos_alto": None if per is None else per >= self.cfg["limiar_perclos"],
                "p_mil": self.p_mil,
                "sonolento_mil": None if self.p_mil is None else self.p_mil >= self.cfg["limiar_mil"],
                "pesos_atencao": self.pesos,
                "p_ultimo_minuto": self.p_ultimo,
                "primeiro_minuto_do_saco": self.primeiro_do_saco}

    def entradas_ao_vivo(self, pontos=120):
        """O que a MIL recebe, para o painel: os 4 canais por quadro do último minuto (reduzidos a `pontos`
        médias), a referência do 1º minuto e os 16 atributos do 1º e do último minuto completo."""
        series = None
        if self.ultimas:
            x = canais_4(np.stack(self.ultimas)[None])[0]              # [<=600, 4]
            blocos = np.array_split(x, min(pontos, len(x)))
            with np.errstate(all="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)          # bloco sem rosto: média vazia
                series = np.stack([np.nanmean(b, axis=0) for b in blocos])  # [pontos, 4], NaN sem rosto
        return {"series": series, "segundos": len(self.ultimas) / self.cfg["fps"],
                "referencia": self.ref_canais, "atributos": list(self.cfg["atributos"]),
                "atrib_calibracao": self.atrib_cal, "atrib_ultimo": self.atrib_ultimo}
