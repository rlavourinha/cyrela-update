# -*- coding: utf-8 -*-
"""Releases 1T20-4T22 (layout antigo, texto raw do pdftotext): extrai REF (liquida/
custo com validacao bruta-impostos=liquida), custos orcados (vendidas/estoque),
contas a receber constr/construidas (quando a tabela existe, validada por soma) e
juros no custo DERIVADO da prosa 'margem bruta ajustada foi de X%' x DF planilha.
Saida: _modelo_releases_old.json."""
import datetime
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
TRIS = [f"{t}T{a}" for a in (20, 21, 22) for t in (1, 2, 3, 4)]
NUM = re.compile(r"\((\d{1,3}(?:\.\d{3})*)\)|(?<![\d,.])(\d{1,3}(?:\.\d{3})+|\d{3,4})(?![\d,.%])")


def nums(trecho, n=12):
    out = []
    for m in NUM.finditer(trecho):
        if m.group(1):
            out.append(-float(m.group(1).replace(".", "")))
        else:
            out.append(float(m.group(2).replace(".", "")))
        if len(out) >= n:
            break
    return out


# lucro bruto e receita da planilha de DFs (p/ derivar juros)
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True, data_only=True)
ws = wb["CYRELA"]
G = list(ws.iter_rows(min_row=1, max_row=100, values_only=True))
wb.close()
H = G[3]
qcol = {}
for j in range(1, len(H)):
    if isinstance(H[j], datetime.datetime):
        d = H[j]
        qcol[f"{(d.month - 1) // 3 + 1}T{d.year % 100:02d}"] = j
df = lambda i, q: G[i][qcol[q]] / 1000

out = {}
for tri in TRIS:
    s = io.open(os.path.join(here, "fontes", f"release_{tri}.raw.txt"),
                encoding="utf-8", errors="ignore").read()
    d = {}
    # juros derivado: MBaj% (prosa) x receita - lucro bruto
    m = re.search(r"margem bruta ajustada do trimestre foi de\s*(\d+,\d)\s*%", s, re.I)
    if m:
        mbaj = float(m.group(1).replace(",", ".")) / 100
        d["juros"] = round(mbaj * df(70, tri) - df(72, tri), 1)
    # REF: apos o bloco de rotulos, sequencia [bruta, -impostos, liquida, -custo]
    i = s.find("Custo Or")
    if i > 0:
        seq = nums(s[i:i + 700])
        for k in range(len(seq) - 3):
            b, imp, liq, cus = seq[k:k + 4]
            if b > 1000 and imp < 0 and cus < 0 and abs(b + imp - liq) < 3:
                d["ref_liq"] = liq
                d["ref_custo"] = cus
                break
    # custos orcados
    for chave, rot in (("custo_vendidas", "referente a unidades vendidas"),
                       ("custo_estoque", "referente a unidades em estoque")):
        i = s.find(rot)
        if i > 0:
            seq = [v for v in nums(s[i + len(rot):i + len(rot) + 200], 3) if v < 0]
            if seq:
                d[chave] = seq[0]
    # contas a receber constr/construidas (tabela nem sempre existe)
    i = s.find("Total dos Receb")
    if i > 0:
        jan = s[max(0, i - 400):i + 900]
        if "constru" in jan.lower():
            seq = nums(jan, 20)
            for k in range(len(seq) - 2):
                a, b, c = seq[k:k + 3]
                if a > 2000 and 0 < b < a / 2 and abs(a + b - c) < 3:
                    d["car_constr"], d["car_prontas"], d["car_tot"] = a, b, c
                    break
    out[tri] = d

io.open(os.path.join(here, "_modelo_releases_old.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))
for tri, d in out.items():
    ok_ref = "ref_custo" in d and "custo_vendidas" in d and abs(d["ref_custo"] - d["custo_vendidas"]) < 3
    print(tri, d, "| ref==vendidas:" , ok_ref if "ref_custo" in d else "n/a")
# validacao do metodo dos juros com 1T23 (conhecido: 25)
s = io.open(os.path.join(here, "fontes", "release_1T23.txt"), encoding="utf-8", errors="ignore").read()
m = re.search(r"margem bruta ajustada do trimestre foi de\s*(\d+,\d)\s*%", s, re.I)
if m:
    mbaj = float(m.group(1).replace(",", ".")) / 100
    print("check 1T23: juros derivado =", round(mbaj * df(70, "1T23") - df(72, "1T23"), 1), "(real 25)")
