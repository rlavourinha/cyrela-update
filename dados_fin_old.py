# -*- coding: utf-8 -*-
"""Resultado financeiro dos releases ANTIGOS (1T20-4T22), cujo pdftotext -layout
sai embaralhado. Usa o .raw.txt e busca por RESTRICAO, ancorada no DRE:

  a (Rend.Aplic) + v (Var.Mon) + o (Outras) = t (Total Receitas)  [+-1.5]
  existe d<0 antes de a com d + t = rf                            [+-1.5]
  rf (Resultado Financeiro) = FIN_DRE da planilha do RI           [+-1.0]

A ancora no FIN do PROPRIO trimestre e o que evita casar a coluna comparativa
(o erro do scan numerico anterior). Entre solucoes, prefere strides regulares
(colunas em passo constante) e janelas curtas.
"""
import datetime
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))

wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True, data_only=True)
G = list(wb["CYRELA"].iter_rows(min_row=1, max_row=100, values_only=True))
wb.close()
H = G[3]
FIN = {}
for j in range(1, len(H)):
    if isinstance(H[j], datetime.datetime) and isinstance(G[81][j], (int, float)):
        d = H[j]
        FIN[f"{(d.month-1)//3+1}T{d.year%100:02d}"] = G[81][j] / 1000

VAL = re.compile(r"^\(?-?\d{1,3}(?:\.\d{3})*\)?$")


def toks(seg):
    """TODOS os tokens viram posicoes (pct/traco = None): assim as colunas da
    tabela ficam em stride CONSTANTE mesmo com celulas vazias, e o stride vira
    restricao dura (o que mata as combinacoes cruzando colunas)."""
    out = []
    for w in seg.split():
        if VAL.match(w):
            v = float(w.strip("()").replace(".", ""))
            out.append(-v if w.startswith("(") else v)
        else:
            out.append(None)
    return out


def _busca_1(V, fin, esp):
    """Linhas RendAplic/VarMon/Outras/Total/ResultFin em stride constante k:
    a+v+o=t (+-1.5), rf~fin (+-1.0), existe d<0 antes com d+t~rf (+-1.5)."""
    melhor = None
    n = len(V)
    for k in range(1, 11):
        for i1 in range(0, n - 4 * k):
            a, v, o, t, rf = (V[i1], V[i1 + k], V[i1 + 2 * k], V[i1 + 3 * k], V[i1 + 4 * k])
            if None in (a, v, o, t, rf) or a < 0 or t <= 0:
                continue
            if abs(rf - fin) > 1.0 or abs(a + v + o - t) > 1.5:
                continue
            if not any(V[j] is not None and V[j] < 0 and abs(V[j] + t - rf) <= 1.5
                       for j in range(0, i1)):
                continue
            # coluna comparativa (proximo token da linha), p/ validacao cruzada
            comp = [V[i + 1] if i + 1 < n else None for i in
                    (i1, i1 + k, i1 + 2 * k, i1 + 3 * k, i1 + 4 * k)]
            score = (round(abs(a + v + o - t), 1), esp, i1)
            cand = (score, {"aplic": a, "var_mon": v, "outras": o, "tot_rec": t,
                            "rf": rf, "idx": (i1, k, esp), "comp": comp,
                            "r28": round(v + o, 1)})
            if melhor is None or cand[0] < melhor[0]:
                melhor = cand
    return melhor


def busca(seg, fin):
    """Roda nos dois espacos de tokens (com e sem placeholders): cada release
    quebra num deles; o menor erro da soma decide (empate -> com placeholders)."""
    cands = [c for c in (_busca_1(toks(seg), fin, 0),
                         _busca_1([x for x in toks(seg) if x is not None], fin, 1))
             if c]
    return min(cands, key=lambda c: c[0])[1] if cands else None


ORD = lambda q: (int(q[2:]), int(q[0]))
out = {}
for a in (20, 21, 22):
    for t in (1, 2, 3, 4):
        tri = f"{t}T{a}"
        f = os.path.join(here, "fontes", f"release_{tri}.raw.txt")
        if not os.path.exists(f):
            f = f.replace(".raw", "")
        s = io.open(f, encoding="utf-8", errors="ignore").read()
        m = re.search(r"Rendimentos?\s+de\s+[Aa]plica", s)
        if not m:
            print(f"  {tri}: sem ancora de rotulo")
            continue
        r = busca(s[m.end():m.end() + 4000], FIN[tri])
        if r:
            out[tri] = r
            print(f"  {tri}: aplic {r['aplic']:6.0f} | var {r['var_mon']:5.0f} | outras {r['outras']:5.0f} | "
                  f"tot {r['tot_rec']:5.0f} | RF {r['rf']:5.0f} (DRE {FIN[tri]:6.1f}) | r28 {r['r28']:6.1f} | idx {r['idx']} | comp {r['comp']}")
        else:
            print(f"  {tri}: SEM SOLUCAO (DRE {FIN[tri]:.1f})")

io.open(os.path.join(here, "_fin_old.json"), "w", encoding="utf-8").write(json.dumps(out))
