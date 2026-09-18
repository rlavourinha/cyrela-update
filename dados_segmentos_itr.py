# -*- coding: utf-8 -*-
"""Margem bruta por segmento (nota 'Informacoes por segmento' dos ITR/DFP,
1T20-2T26). Layouts variam (blocos por segmento, row-major, embaralhado);
extracao por RESTRICAO, no padrao validado no bloco financeiro:

  triade (rec, custo, lucro) em stride constante com rec + custo = lucro (+-3)
  4 triades (Cyrela, Living, MCMV/CVA, Demais) somando ao consolidado da
  planilha do RI (receita e lucro bruto acumulados do periodo, +-4)

Nota e acumulada no ano (3M/6M/9M/12M); o trimestre sai por diferenca.
Ordem de aparicao no doc atribui os rotulos (Cyrela -> Living -> MCMV -> Demais).
"""
import datetime
import io
import itertools
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
SP = r"C:\Users\RLAVOU~1\AppData\Local\Temp\claude\D--rlavourinha-Pictures-OneDrive--rea-de-Trabalho-Claude\e4e1cc5f-6e04-4e22-ba8b-ce88f93cdefb\scratchpad\itrdocs"

wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True, data_only=True)
G = list(wb["CYRELA"].iter_rows(min_row=1, max_row=100, values_only=True))
wb.close()
REC, LB = {}, {}
for j in range(1, len(G[3])):
    if isinstance(G[3][j], datetime.datetime) and isinstance(G[70][j], (int, float)):
        d = G[3][j]
        q = f"{(d.month-1)//3+1}T{d.year%100:02d}"
        REC[q] = G[70][j] / 1000
        LB[q] = G[72][j] / 1000


def acum(q):
    t, a = int(q[0]), q[2:]
    return (sum(REC[f"{i}T{a}"] for i in range(1, t + 1)),
            sum(LB[f"{i}T{a}"] for i in range(1, t + 1)))


VAL = re.compile(r"^\(?-?\d{1,3}(?:\.\d{3})*\)?$")


def toks(seg, ph):
    out = []
    for w in seg.split():
        if VAL.match(w):
            v = float(w.strip("()").replace(".", "")) / 1000
            out.append(-v if w.startswith("(") else v)
        elif ph:
            out.append(None)
    return out


def triades(V):
    """Todas as triades (rec, custo, lucro) em stride constante, rec+custo=lucro."""
    tri = []
    n = len(V)
    for k in range(1, 9):
        for i in range(0, n - 2 * k):
            r, c, l = V[i], V[i + k], V[i + 2 * k]
            if None in (r, c, l) or r < -5 or abs(r) + abs(c) < 1.0:
                continue
            if r < 1.0 and abs(r) + abs(c) + abs(l) > 15:  # rec ~0 so p/ Demais pequeno
                continue
            # teto de plausibilidade so p/ segmentos grandes: o Demais e pequeno
            # e tem custo positivo em varios periodos (margem >100%)
            if abs(r + c - l) <= 3 and (r < 60 or abs(l) < r * 1.6 + 5):
                tri.append((i, k, r, c, l))
    return tri


def extrai(s, rec_a, lb_a):
    i = s.find("POR SEGMENTO")
    if i < 0:
        return None
    seg = s[i:i + 9000]
    melhor = None
    for ph in (True, False):
        tri = triades(toks(seg, ph))
        # descarta a triade "Total" (rec ~ consolidado) das candidatas a segmento
        cand = [t for t in tri if abs(t[2] - rec_a) > 4]
        # 4 segmentos somando ao consolidado
        for combo in itertools.combinations(cand, 4):
            recs = sum(t[2] for t in combo)
            lucs = sum(t[4] for t in combo)
            if abs(recs - rec_a) > 4 or abs(lucs - lb_a) > 4:
                continue
            pos = sorted(t[0] for t in combo)
            if len({t[0] for t in combo}) < 4:
                continue
            err = abs(recs - rec_a) + abs(lucs - lb_a)
            score = (round(err, 1), pos[-1] - pos[0])
            if melhor is None or score < melhor[0]:
                melhor = (score, sorted(combo, key=lambda t: t[0]), ph)
        if melhor:
            break
    return melhor


NOMES = ["cyrela", "living", "mcmv", "demais"]
out = {}
for a in range(20, 27):
    for t in range(1, 5):
        q = f"{t}T{a}"
        f = os.path.join(SP, f"{q}_0.txt")
        if not os.path.exists(f) or q not in REC:
            continue
        s = io.open(f, encoding="utf-8", errors="ignore").read()
        rec_a, lb_a = acum(q)
        r = extrai(s, rec_a, lb_a)
        if not r:
            print(f"  {q}: SEM SOLUCAO (rec_a {rec_a:.0f}, lb_a {lb_a:.0f})")
            continue
        score, combo, ph = r
        d = {}
        for nome, (i, k, rc, cu, lu) in zip(NOMES, combo):
            d[nome] = {"rec": round(rc, 1), "lb": round(lu, 1),
                       "mg": round(lu / rc, 4)}
        out[q] = d
        print(f"  {q}: " + " | ".join(
            f"{n} {d[n]['rec']:7.0f} mg {100*d[n]['mg']:5.1f}%" for n in NOMES)
            + f"  (err {score[0]}, ph {ph})")

io.open(os.path.join(here, "_segmentos.json"), "w", encoding="utf-8").write(json.dumps(out))
