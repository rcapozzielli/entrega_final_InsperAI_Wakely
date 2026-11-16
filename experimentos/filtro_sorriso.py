"""Filtro de sorriso no alerta de microssono, como em docs/protocolo_filtro_sorriso.md (aprovado antes de rodar).

Uso: python experimentos/filtro_sorriso.py
Bases: classe alerta do UTA-RLDD (data/cache/rldd_rico) e, se os .npz existirem em data/cache/sinais, o Eyeblink8.
A parte de segurança (FL3D e BINUS) fica para quando os sinais do Antônio estiverem no disco.
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


class RegraSorriso(alerta.RegraAlerta):
    """A regra da demo, com o sorriso somado ao bocejo: olho fechado durante sorriso não conta para o microssono.

    O sorriso liga e desliga como o bocejo (BOCA_PERSIST seguidos acima do limiar, vale BOCA_MARGEM depois).
    O piso de 3 s e 6 s continua usando o trecho bruto, então vale mesmo durante sorriso.
    """

    def __init__(self, lim):
        self.lim = lim
        super().__init__()

    def reiniciar(self):
        super().reiniciar()
        self.altas_s, self.sorriso_ate, self.sorriso = 0, -1.0, None

    def _bocejo(self, t, boca):
        bocejo = super()._bocejo(t, boca)
        if self.lim is None:
            return bocejo
        self.altas_s = self.altas_s + 1 if (self.sorriso is not None and self.sorriso >= self.lim) else 0
        if self.altas_s * self.dt >= alerta.BOCA_PERSIST - 1e-6:
            self.sorriso_ate = t + alerta.BOCA_MARGEM
        self.sorriso_ativo = t <= self.sorriso_ate + 1e-6
        return bocejo or self.sorriso_ativo


def alarmes(t, s, lim):
    """Avisos da fusão (limiar 0,35, filtro de bocejo, T = 1 s, piso) com o filtro de sorriso no limiar `lim`
    (None = sem filtro). Devolve os instantes por nível e, para cada microssono, se havia sorriso ativo
    (pelo limiar do protocolo) naquele instante."""
    x, boca = sinal("fusao", t, s)
    sorriso = np.nanmean(s[:, list(I_SORRISO)], axis=1)
    r, ref = RegraSorriso(lim), RegraSorriso(SORRISO_LIM)     # ref só observa o sorriso, não filtra nada
    saida = {"microssono": [], "sono": [], "sem resposta": [], "micro_com_sorriso": []}
    for ti, xi, bi, si in zip(t, x, boca, sorriso):
        xi = None if np.isnan(xi) else float(xi)
        bi = None if np.isnan(bi) else float(bi)
        r.sorriso = ref.sorriso = None if np.isnan(si) else float(si)
        novos, _ = r.passo(float(ti), xi, bi, LIMIARES["fusao"])
        ref.dt = r.dt                                        # mesmo intervalo entre quadros da regra
        ref._bocejo(float(ti), bi)
        for n in novos:
            saida[n].append(float(ti))
            if n == "microssono":
                saida["micro_com_sorriso"].append(bool(ref.sorriso_ativo))
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

    json.dump(saida, open(RAIZ / "data/cache/filtro_sorriso.json", "w", encoding="utf-8"), indent=1, default=float)
