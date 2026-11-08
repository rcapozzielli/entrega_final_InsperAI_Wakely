"""Regra de alerta e máquina de estados da demo do Wakely.

RegraAlerta repete, quadro a quadro e em segundos, a regra das seções 6 e 7 do notebook:
- olho fechado quando a média do P(fechado) dos dois olhos passa de LIMIAR_OLHO (0,4, escolhido na calibração do
  FL3D com filtro, seção 7);
- trechos fechados separados por até 0,12 s viram um só (BURACO_FECH = 3 quadros a 25 fps);
- filtro de bocejo: boca aberta (abertura >= 0,25) por 0,12 s seguidos liga o bocejo, que vale até 1 s depois de a
  boca fechar (FILTRO = lim 0,25, persistência 3 e margem 25 quadros a 25 fps). Olho fechado durante bocejo não
  conta para o microssono;
- microssono: olho fechado por T = 1 s, sem bocejo (limite inferior da faixa do Euro NCAP);
- piso: olho fechado por 3 s ou mais avisa como sono MESMO durante bocejo, e 6 s ou mais como "sem resposta".

MaquinaEstados junta a regra com o MonitorSonolencia (PERCLOS do último minuto e MIL) e decide o que o painel
mostra. Os tempos da máquina (10 s sem rosto, 60 s de histerese, 5 min entre avisos de sonolência) são escolhas da
demo e NÃO foram validados em dados: servem para o painel não piscar nem repetir avisos.
"""
from collections import deque

LIMIAR_OLHO = 0.4          # P(fechado) médio dos dois olhos (seção 7, YOLO com filtro)
BURACO_FECH = 3 / 25       # s: trechos fechados separados por até isso viram um só
T_MICRO = 1.0              # s: microssono (Euro NCAP, limite inferior)
T_SONO = 3.0               # s: piso de sono, vale mesmo durante bocejo
T_SEM_RESPOSTA = 6.0       # s
BOCA_LIM = 0.25            # abertura da boca (vertical / largura)
BOCA_PERSIST = 3 / 25      # s de boca aberta para ligar o bocejo
BOCA_MARGEM = 25 / 25      # s que o bocejo continua depois de a boca fechar


class Trecho:
    """Um trecho de olho fechado, com buracos curtos juntados, como `unir(trechos(...), BURACO_FECH)` do notebook.

    A duração conta quadros, como no notebook: 25 quadros seguidos a 25 fps valem 1 s (último - primeiro + 1 quadro).
    """

    def __init__(self):
        self.ini = self.ultimo = None
        self.id = 0                  # muda a cada trecho novo

    def passo(self, t, ligado, dt):
        if ligado:
            # buraco de até BURACO_FECH (3 quadros a 25 fps) junta: a distância entre quadros fechados vai até 4 quadros
            if self.ini is None or t - self.ultimo > BURACO_FECH + dt + 1e-6:
                self.ini, self.id = t, self.id + 1
            self.ultimo = t
        elif self.ini is not None and t - self.ultimo > BURACO_FECH + dt + 1e-6:
            self.ini = None
        return 0.0 if self.ini is None else self.ultimo - self.ini + dt


class RegraAlerta:
    """Recebe (t em s, P(fechado) médio ou None sem rosto, abertura da boca) e devolve os avisos novos."""

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.bruto = Trecho()        # olho fechado, com ou sem bocejo: alimenta o piso de 3 s e 6 s
        self.filtrado = Trecho()     # olho fechado fora de bocejo: alimenta o microssono
        self.t_ant, self.dt = None, 1 / 25
        self.altas = 0               # quadros seguidos de boca aberta
        self.bocejo_ate = -1.0       # o bocejo vale até este instante
        self.avisados = set()        # (nível, id do trecho) já avisados
        self.fechado_ha = 0.0

    def _bocejo(self, t, boca):
        # como bocejo_ativo do notebook: boca aberta por BOCA_PERSIST seguidos, e vale por BOCA_MARGEM depois
        self.altas = self.altas + 1 if (boca is not None and boca >= BOCA_LIM) else 0
        if self.altas * self.dt >= BOCA_PERSIST - 1e-6:
            self.bocejo_ate = t + BOCA_MARGEM
        return t <= self.bocejo_ate + 1e-6

    def passo(self, t, p_fech, boca):
        if self.t_ant is not None and t > self.t_ant:
            self.dt = 0.8 * self.dt + 0.2 * (t - self.t_ant)     # intervalo típico entre quadros
        self.t_ant = t
        bocejo = self._bocejo(t, boca)
        fechado = p_fech is not None and p_fech >= LIMIAR_OLHO
        dur_bruta = self.bruto.passo(t, fechado, self.dt)
        dur_filtrada = self.filtrado.passo(t, fechado and not bocejo, self.dt)
        self.fechado_ha = dur_bruta if fechado else 0.0
        novos = []
        for nivel, dur, limite, trecho in [("microssono", dur_filtrada, T_MICRO, self.filtrado),
                                           ("sono", dur_bruta, T_SONO, self.bruto),
                                           ("sem resposta", dur_bruta, T_SEM_RESPOSTA, self.bruto)]:
            chave = (nivel, trecho.id)
            if trecho.ini is not None and dur >= limite - 1e-6 and chave not in self.avisados:
                self.avisados.add(chave)
                novos.append(nivel)
        return novos, {"fechado": fechado, "bocejo": bocejo, "fechado_ha": self.fechado_ha}


NIVEIS = ["calibrando", "normal", "atencao", "sonolento", "microssono", "sono", "sem resposta", "sem rosto"]
TEXTO = {
    "calibrando": "Calibrando: olhe para a frente por 1 minuto",
    "normal": "Tudo certo",
    "atencao": "Atenção: sinais de cansaço",
    "sonolento": "Sonolência: faça uma pausa",
    "microssono": "Olho fechado! Abra os olhos",
    "sono": "Pare em local seguro",
    "sem resposta": "PARE EM LOCAL SEGURO",
    "sem rosto": "Não estou vendo seu rosto",
}


class MaquinaEstados:
    """Decide o estado do painel a partir da regra rápida e do monitor de sonolência (PERCLOS e MIL)."""

    SEM_ROSTO_S = 10.0       # Euro NCAP: avisar em até 10 s que o sistema não está funcionando
    HISTERESE_S = 60.0       # sair de atenção/sonolento só depois de 60 s sem sinal
    MIN_ENTRE_AVISOS_S = 300.0
    MOSTRAR_ALERTA_S = 4.0   # quanto tempo o aviso rápido fica na tela
    JANELA_MICROS_S = 300.0  # 2 microssonos em 5 min também contam como sonolento

    def __init__(self):
        self.regra = RegraAlerta()
        self.reiniciar()

    def reiniciar(self):
        self.regra.reiniciar()
        self.sem_rosto_desde = None
        self.nivel_sono = 0                 # 0 normal, 1 atenção, 2 sonolento
        self.sinal_visto_em = None
        self.ultimo_aviso_sono = -1e9
        self.alerta_rapido, self.alerta_ate = None, -1.0
        self.micros = deque()
        self.eventos = []                   # (t, tipo, detalhe)

    def passo(self, t, linha_ok, p_fech, boca, monitor_estado):
        """-> dict com o estado do painel e a lista de sons a tocar neste quadro."""
        sons = []
        novos, info = self.regra.passo(t, p_fech if linha_ok else None, boca if linha_ok else None)
        for n in novos:
            self.eventos.append((t, n, f"olho fechado há {info['fechado_ha']:.1f} s"))
            self.alerta_rapido, self.alerta_ate = n, t + self.MOSTRAR_ALERTA_S
            sons.append(n)
            if n == "microssono":
                self.micros.append(t)
        while self.micros and t - self.micros[0] > self.JANELA_MICROS_S:
            self.micros.popleft()

        # sem rosto
        if linha_ok:
            self.sem_rosto_desde = None
        elif self.sem_rosto_desde is None:
            self.sem_rosto_desde = t
        sem_rosto = self.sem_rosto_desde is not None and t - self.sem_rosto_desde >= self.SEM_ROSTO_S
        if sem_rosto and not any(e[1] == "sem rosto" and e[0] >= self.sem_rosto_desde for e in self.eventos):
            self.eventos.append((t, "sem rosto", "câmera não vê o rosto há 10 s"))
            sons.append("sem rosto")

        # sonolência: PERCLOS do último minuto, MIL e microssonos repetidos
        m = monitor_estado or {}
        sinais = int(bool(m.get("perclos_alto"))) + int(bool(m.get("sonolento_mil")))
        alvo = 2 if (sinais == 2 or len(self.micros) >= 2) else sinais
        if alvo > 0:
            self.sinal_visto_em = t
        if alvo > self.nivel_sono:
            self.nivel_sono = alvo
            if t - self.ultimo_aviso_sono >= self.MIN_ENTRE_AVISOS_S or alvo == 2:
                self.ultimo_aviso_sono = t
                nome = "sonolento" if alvo == 2 else "atencao"
                self.eventos.append((t, nome, f"PERCLOS alto: {bool(m.get('perclos_alto'))}, "
                                              f"MIL: {bool(m.get('sonolento_mil'))}, microssonos em 5 min: {len(self.micros)}"))
                sons.append(nome)
        elif alvo < self.nivel_sono and self.sinal_visto_em is not None and t - self.sinal_visto_em >= self.HISTERESE_S:
            self.nivel_sono = alvo

        # o que o painel mostra, do mais urgente ao menos urgente
        if self.alerta_rapido and t <= self.alerta_ate:
            nivel = self.alerta_rapido
        elif sem_rosto:
            nivel = "sem rosto"
        elif m.get("calibrando", False):
            nivel = "calibrando"
        else:
            nivel = ["normal", "atencao", "sonolento"][self.nivel_sono]
        return {"nivel": nivel, "texto": TEXTO[nivel], "sons": sons, "bocejo": info["bocejo"],
                "fechado": info["fechado"], "fechado_ha": info["fechado_ha"], "micros_5min": len(self.micros)}
