# -*- coding: utf-8 -*-
"""Marcacao a mercado do estoque (ponte 'Var. Preco/Ajustes' dos releases, base %CBR):
1a ocorrencia = estoque total, 2a = estoque pronto. Percentuais sobre o estoque %CBR
do TRIMESTRE ANTERIOR (planilha op: Estoque r45 e Estoque Pronto r46, com permuta).
Saida: _marcacao.json {tri: {var_tot, var_pro, pct_tot, pct_pro, pct_con}}."""
import glob
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
PAT = re.compile(r"(-?\d{1,3}(?:\.\d{3})*)\s*\n\s*Var\.?\s*Pre", re.I)

# estoque %CBR (com permuta) da planilha op
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_dados_operacionais.xlsx"),
                            read_only=True, data_only=True)
def total_cbr(aba, row1):
    ws = wb[aba]
    grid = list(ws.iter_rows(min_row=1, max_row=60, values_only=True))
    hdr = next(r for r in grid[:6] if sum(1 for c in r if isinstance(c, str) and len(str(c)) == 4 and str(c)[1] == "T") > 4)
    qc = {c: j for j, c in enumerate(hdr) if isinstance(c, str) and len(c) == 4 and c[1] == "T"}
    return {q: grid[row1 - 1][j] / 1000 for q, j in qc.items()
            if isinstance(grid[row1 - 1][j], (int, float))}

est = total_cbr("Estoque", 45)
pro = total_cbr("Estoque Pronto", 46)
wb.close()


def tri_ant(q):
    t, a = int(q[0]), int(q[2:])
    return f"{t-1}T{a:02d}" if t > 1 else f"4T{a-1:02d}"


out = {}
for f in sorted(glob.glob(os.path.join(here, "fontes", "release_????.txt"))):
    tri = os.path.basename(f)[8:12]
    hits = []
    for cand in (f, f.replace(".txt", ".raw.txt")):
        if os.path.exists(cand):
            s = io.open(cand, encoding="utf-8", errors="ignore").read()
            hits = [float(m.group(1).replace(".", "")) for m in PAT.finditer(s)]
            if len(hits) >= 2:
                break
    if len(hits) < 1:
        print(tri, "SEM ponte")
        continue
    ant = tri_ant(tri)
    e0, p0 = est.get(ant), pro.get(ant)
    d = {"var_tot": hits[0], "var_pro": hits[1] if len(hits) > 1 else None}
    if e0:
        d["pct_tot"] = round(100 * hits[0] / e0, 2)
    if len(hits) > 1 and p0:
        d["pct_pro"] = round(100 * hits[1] / p0, 2)
        if e0:
            d["pct_con"] = round(100 * (hits[0] - hits[1]) / (e0 - p0), 2)
    # sanidade: marcacao raramente passa de 6% do estoque
    if e0 and abs(hits[0]) > 0.08 * e0 * 1000:
        print(tri, "SUSPEITO", d)
    out[tri] = d

io.open(os.path.join(here, "_marcacao.json"), "w", encoding="utf-8").write(json.dumps(out))
for tri in sorted(out, key=lambda q: (q[2:], q[0])):
    print(tri, out[tri])
print("n:", len(out))
