# -*- coding: utf-8 -*-
"""Nota 'Informacoes por Segmento' COMPLETA (1T20-2T26): alem de rec/custo/LB,
extrai desp. operacionais, lucro operacional, ativo, passivo e PL por segmento.
Metodo identico ao dados_segmentos_itr (triades em stride constante ancoradas
no consolidado da planilha RI) + extensao por identidades:
  LB + desp_op = lucro_op (+-3)   e   ativo - passivo = PL (+-3)
Saida: _segmentos_full.json {tri: {seg: {rec, lb, desp, lop, ativo, passivo, pl}}}"""
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
    tri = []
    n = len(V)
    for k in range(1, 9):
        for i in range(0, n - 2 * k):
            r, c, l = V[i], V[i + k], V[i + 2 * k]
            if None in (r, c, l) or r < -5 or abs(r) + abs(c) < 1.0:
                continue
            if r < 1.0 and abs(r) + abs(c) + abs(l) > 15:
                continue
            if abs(r + c - l) <= 3 and (r < 60 or abs(l) < r * 1.6 + 5):
                tri.append((i, k, r, c, l))
    return tri


def estende(V, i1, k, lb):
    """Linhas seguintes do MESMO segmento ficam a multiplos de k da triade
    (linhas em branco da tabela tambem ocupam k tokens). Busca presa ao stride."""
    n = len(V)
    def em(j):
        return V[j] if 0 <= j < n else None
    par = None
    for offd in (3, 4, 5):
        for dj in (0, 1, -1):
            jd = i1 + offd * k + dj
            d = em(jd)
            if d is None: continue
            for offl in (1, 2):
                for dl in (0, 1, -1):
                    jl = jd + offl * k + dl
                    l2 = em(jl)
                    if l2 is None: continue
                    if abs(lb + d - l2) <= 3:
                        par = (jl, d, l2); break
                if par: break
            if par: break
        if par: break
    if not par:
        return None
    jl, desp, lop = par
    for offa in (1, 2, 3):
        for da in (0, 1, -1):
            ja = jl + offa * k + da
            a = em(ja)
            if a is None or a < 5: continue
            for dp in (0, 1, -1):
                jp = ja + k + dp
                p = em(jp)
                if p is None: continue
                for dq in (0, 1, -1):
                    jq = jp + k + dq
                    pl = em(jq)
                    if pl is None: continue
                    if abs(a - p - pl) <= 3 and a >= abs(pl) - 3 and abs(pl) > 5:
                        return {"desp": round(desp, 1), "lop": round(lop, 1),
                                "ativo": round(a, 1), "passivo": round(p, 1), "pl": round(pl, 1)}
    return {"desp": round(desp, 1), "lop": round(lop, 1)}


SP2 = SP + "2"
def config(a, t):
    # ate 2T19 a nota tem 3 segmentos (MCMV dentro do Living); de 3T19 em diante, 4
    if a < 19 or (a == 19 and t <= 2):
        return ["cyrela", "living", "demais"], SP2
    if a == 19:
        return ["cyrela", "living", "mcmv", "demais"], SP2
    return ["cyrela", "living", "mcmv", "demais"], SP

out = {}
for a in range(13, 27):
    for t in range(1, 5):
        q = f"{t}T{a}"
        NOMES, pasta = config(a, t)
        f = os.path.join(pasta, f"{q}_0.txt")
        if not os.path.exists(f):
            f = os.path.join(pasta, f"{q}_0.lay.txt")
        if not os.path.exists(f) or q not in REC:
            continue
        s = io.open(f, encoding="utf-8", errors="ignore").read()
        i = s.find("POR SEGMENTO")
        if i < 0:
            print(f"  {q}: sem nota"); continue
        seg = s[i:i + 9000]
        rec_a, lb_a = acum(q)
        melhor = None
        for ph in (True, False):
            V = toks(seg, ph)
            tri = triades(V)
            cand = [x for x in tri if abs(x[2] - rec_a) > 4]
            NS = len(NOMES)
            for combo in itertools.combinations(cand, NS):
                recs = sum(x[2] for x in combo)
                lbs = sum(x[4] for x in combo)
                if abs(recs - rec_a) > 4 or abs(lbs - lb_a) > 4:
                    continue
                if len({x[0] for x in combo}) < NS:
                    continue
                err = abs(recs - rec_a) + abs(lbs - lb_a)
                sc = (round(err, 1), 0)
                if melhor is None or sc < melhor[0]:
                    melhor = (sc, sorted(combo, key=lambda x: x[0]), V)
            if melhor:
                break
        if not melhor:
            print(f"  {q}: SEM SOLUCAO"); continue
        _, combo, V = melhor
        d = {}
        for nome, (i1, k, rc, cu, lu) in zip(NOMES, combo):
            reg = {"rec": round(rc, 1), "lb": round(lu, 1)}
            ext = estende(V, i1, k, lu)
            if ext: reg.update(ext)
            d[nome] = reg
        # fallback p/ layout row-major (2024+): pares (desp,lop) e trincas
        # (ativo,passivo,pl) ADJACENTES, na ordem dos segmentos
        if any("lop" not in d[nm] for nm in NOMES):
            j_min = min(x[0] for x in combo)
            usados = set()
            for nome, (i1, k, rc, cu, lu) in zip(NOMES, combo):
                if "lop" in d[nome]:
                    continue
                for j in range(j_min, len(V) - 1):
                    if j in usados: continue
                    a_, b_ = V[j], V[j + 1]
                    if a_ is None or b_ is None: continue
                    if abs(lu + a_ - b_) <= 3 and abs(a_) > 0.5:
                        d[nome]["desp"] = round(a_, 1); d[nome]["lop"] = round(b_, 1)
                        usados.add(j); usados.add(j + 1)
                        break
        if any("pl" not in d[nm] for nm in NOMES):
            trincas = []
            for j in range(len(V) - 2):
                a_, p_, pl_ = V[j], V[j + 1], V[j + 2]
                if None in (a_, p_, pl_) or a_ < 5 or abs(pl_) < 3: continue
                if abs(a_ - p_ - pl_) <= 3:
                    if trincas and j <= trincas[-1][0] + 2: continue
                    trincas.append((j, a_, p_, pl_))
            faltam = [nm for nm in NOMES if "pl" not in d[nm]]
            if len(trincas) >= len(faltam):
                for nm, (_, a_, p_, pl_) in zip(faltam, trincas):
                    d[nm]["ativo"] = round(a_, 1); d[nm]["passivo"] = round(p_, 1); d[nm]["pl"] = round(pl_, 1)
        out[q] = d
        info = " | ".join(f"{n}: lop {d[n].get('lop','—')} pl {d[n].get('pl','—')}" for n in NOMES[:3])
        print(f"  {q}: {info}")

io.open(os.path.join(here, "_segmentos_full.json"), "w", encoding="utf-8").write(json.dumps(out))
