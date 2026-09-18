# -*- coding: utf-8 -*-
"""Marcacao a mercado do estoque — serie longa 4T12-2T26, BASE 100% (a mesma do
bloco r201-r209 do CYREMod, cujas formulas dividem por 'Estoque 100%').

- TOTAL: identidade var = dEstoque - lancamentos + vendas (100%). Reproduz
  exatamente os 46 valores historicos digitados pela JGP (diferenca = 0).
- PRONTO: a ponte tem entrada de entrega (VGV entregue nao vendido, nao
  publicado como serie), entao vem do proprio release:
    * formato novo (1T23+): numero imediatamente antes do rotulo 'Var. Preco'
      (2a ocorrencia = grafico do pronto);
    * formato antigo (1T20-4T22): resolve a ponte ini - vendas + entregue + var
      = fim usando ini/fim conhecidos (%CBR da planilha do RI).
  Converte %CBR -> 100% pelo fator do trimestre anterior.
Saida: _marcacao.json {tri: {tot, pct_tot, pro, pct_pro, con, pct_con, fonte}}
"""
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
wo = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_dados_operacionais.xlsx"),
                            read_only=True, data_only=True)


def serie(aba, row1):
    w = wo[aba]
    grid = list(w.iter_rows(min_row=1, max_row=170, values_only=True))
    h = next(r for r in grid[:6]
             if sum(1 for c in r if isinstance(c, str) and len(str(c)) == 4 and str(c)[1] == "T") > 4)
    qc = {c: j for j, c in enumerate(h) if isinstance(c, str) and len(c) == 4 and c[1] == "T"}
    return {q: grid[row1 - 1][j] / 1000 for q, j in qc.items()
            if isinstance(grid[row1 - 1][j], (int, float)) and grid[row1 - 1][j]}


E1, L1, V1 = serie("Estoque", 14), serie("Lçtos", 14), serie("Vendas", 14)   # 100%
P1 = serie("Estoque Pronto", 14)                                             # 100%
PCB = serie("Estoque Pronto", 46)                                            # %CBR
wo.close()

ORD = lambda q: (int(q[2:]), int(q[0]))
def ant(q):
    t, a = int(q[0]), int(q[2:])
    return f"{t-1}T{a:02d}" if t > 1 else f"4T{a-1:02d}"


NUM = re.compile(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?")
PAT_NOVO = re.compile(r"(-?\d{1,3}(?:\.\d{3})*)\s*\n\s*Var\.?\s*Pre", re.I)


def le(tri):
    for arq in (f"release_{tri}.txt", f"release_{tri}.raw.txt"):
        cam = os.path.join(here, "fontes", arq)
        if os.path.exists(cam):
            yield io.open(cam, encoding="utf-8", errors="ignore").read()


def var_pronto_cbr(tri):
    """Retorna a marcacao do estoque pronto em %CBR, ou None."""
    ini, fim = PCB.get(ant(tri)), PCB.get(tri)
    for s in le(tri):
        hits = [float(m.group(1).replace(".", "")) for m in PAT_NOVO.finditer(s)]
        if len(hits) >= 2:                       # formato novo
            return hits[1]
        if not (ini and fim):
            continue
        pos = [m.start() for m in re.finditer(r"Var\.?\s*Pre", s, re.I)]
        if len(pos) < 2:
            continue
        jan = s[max(0, pos[1] - 900):pos[1] + 200]
        nums = [float(m.group(0).replace(".", "").replace(",", "."))
                for m in NUM.finditer(jan)]
        # ponte: ini - |vendas| + entregue + var = fim
        for ve in nums:
            if ve >= 0:
                continue
            for en in nums:
                if en < 0:
                    continue
                var = fim - ini - ve - en
                if abs(var) < 0.12 * ini and any(abs(x - var) < 1.5 for x in nums):
                    return round(var, 1)
    return None


out = {}
tris = sorted(E1, key=ORD)
for q in tris:
    a0 = ant(q)
    if a0 not in E1 or q not in L1 or q not in V1:
        continue
    tot = round(E1[q] - E1[a0] - L1[q] + V1[q], 1)
    d = {"tot": tot, "pct_tot": round(tot / E1[a0], 5), "fonte": "identidade"}
    vp = var_pronto_cbr(q)
    if vp is not None and PCB.get(a0) and P1.get(a0):
        pro = round(vp * P1[a0] / PCB[a0], 1)             # %CBR -> 100%
        base_con = E1[a0] - P1[a0]
        d.update(pro=pro, pct_pro=round(pro / P1[a0], 5), con=round(tot - pro, 1),
                 pct_con=round((tot - pro) / base_con, 5) if base_con > 0 else None,
                 fonte="identidade+release")
    out[q] = d

io.open(os.path.join(here, "_marcacao.json"), "w", encoding="utf-8").write(json.dumps(out))
com = sum(1 for v in out.values() if "pro" in v)
ks = sorted(out, key=ORD)
print(f"{len(out)} tris ({ks[0]}..{ks[-1]}) | com pronto: {com}")
for q in ks:
    v = out[q]
    if ORD(q) <= (14, 2) or ORD(q) >= (23, 1):
        print(f"  {q}: tot {v['tot']:+8.1f} ({100*v['pct_tot']:+5.2f}%)" +
              (f" | pronto {v['pro']:+7.1f} ({100*v['pct_pro']:+6.2f}%)" if "pro" in v else ""))
