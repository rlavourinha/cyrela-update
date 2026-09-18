# -*- coding: utf-8 -*-
"""Anatomia da receita: vendas por origem (pontes de estoque dos releases, %CBR a valor
de mercado) + receita liquida consolidada (planilha RI).

Ponte de estoque de cada release: Estoque(t-1) - vendas estoque em construcao - vendas
estoque pronto + lancamentos - vendas de lancamentos +/- var. preco = Estoque(t).

BASE DA PONTE MUDOU NO 4T25: ate 3T25 os releases montam a ponte em VGV 100% (com socios
e permuta); do 4T25 em diante, em ex-permuta %CBR. Prova: a soma dos componentes bate
exato com a linha de vendas divulgada em cada base (4T24: 3.821+869+216=4.906 ~ vendas
100% 4.905; 2T26: 1.231+1.053+278=2.562 ~ ex-permuta %CBR 2.561). Este parser AUTODETECTA
a base pela soma e converte tudo para ex-permuta %CBR pelo fator de vendas do proprio
release (vcbr/v100, ~0,69-0,77). NAO e mudanca de perimetro societario: a DFP 2025 mostra
lista de investidas em equivalencia estavel e nenhuma nota de combinacao de negocios.
Saida: _receita_origem.json {tri, vec, vep, vl, rec, fator} — 1T23..2T26, base unica.
"""
import datetime
import glob
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))


def num(x):
    return float(x.replace(".", ""))


PONTE = re.compile(
    r"Estoque Total \dT\d\d\s*-([\d\.]+)\s*-([\d\.]+)\s*Vendas\s*Estoque.*?"
    r"([\d\.]+)\s*Lan[çc]amentos.*?-([\d\.]+)\s*Vendas\s*Lan[çc]amentos")

dados = {}
for f in glob.glob(os.path.join(here, "fontes", "release_*.txt")):
    tri = os.path.basename(f)[8:-4]
    raw = re.sub(r"\s+", " ", io.open(f, encoding="utf-8").read())
    m = PONTE.search(raw)
    if not m:
        print("SEM PONTE:", tri)
        continue
    vec, vep, lanc, vl = (num(g) for g in m.groups())
    # base da ponte: autodetecta pela soma dos componentes vs linhas de vendas divulgadas
    m1 = re.search(r"Vendas (?:Totais Contratadas|com Permuta) - R\$ milh.es \(100%\)\s+([\d\.]+)", raw)
    m2 = re.search(r"Vendas ex-permuta(?: - R\$ milh.es \(%\s?CBR\)| no %\s?CBR)\s+([\d\.]+)", raw)
    fator = 1.0
    if m1 and m2:
        v100, vcbr = num(m1.group(1)), num(m2.group(1))
        soma = vec + vep + vl
        if abs(soma - v100) < abs(soma - vcbr):   # ponte em 100% -> converte p/ %CBR ex-permuta
            fator = vcbr / v100
    dados[tri] = {"vec": round(vec * fator), "vep": round(vep * fator),
                  "vl": round(vl * fator), "fator": round(fator, 3)}

# receita liquida consolidada (planilha)
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True)
ws = wb["CYRELA"]
rows = list(ws.iter_rows(min_row=1, max_row=100, values_only=True))
hdr = rows[3]
r_rec = next(i for i, r in enumerate(rows) if r[0] and "+Receita liquida operac" in str(r[0]))
for j in range(1, len(hdr)):
    d = hdr[j]
    if isinstance(d, datetime.datetime):
        lab = f"{(d.month - 1) // 3 + 1}T{d.year % 100:02d}"
        if lab in dados and isinstance(rows[r_rec][j], (int, float)):
            dados[lab]["rec"] = round(rows[r_rec][j] / 1000.0)
wb.close()


def ordem(t):
    return (int(t[2:]), int(t[0]))


tris = sorted(dados, key=ordem)
out = {"tri": tris,
       "vec": [dados[t]["vec"] for t in tris],
       "vep": [dados[t]["vep"] for t in tris],
       "vl": [dados[t]["vl"] for t in tris],
       "rec": [dados[t]["rec"] for t in tris],
       "fator": [dados[t]["fator"] for t in tris]}
for t in tris:
    d = dados[t]
    tot = d["vec"] + d["vep"] + d["vl"]
    est = 0.9 * d["vep"] + 0.2 * d["vl"] + 0.5 * d["vec"]
    print(f"{t}: f={d['fator']:.3f} | lanc {d['vl']:6.0f} ({100*d['vl']/tot:4.1f}%) | obra {d['vec']:6.0f} ({100*d['vec']/tot:4.1f}%)"
          f" | pronto {d['vep']:5.0f} ({100*d['vep']/tot:4.1f}%) | receita {d['rec']:5.0f}"
          f" | backlog residual {100*(d['rec']-est)/d['rec']:5.1f}%")
io.open(os.path.join(here, "_receita_origem.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))
