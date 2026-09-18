# -*- coding: utf-8 -*-
"""Series de margem para a aba REF.

- Margem bruta reportada: planilha de demonstracoes do RI (3T05-2T26, trimestral).
- Margem REF (bruta a apropriar) e margem bruta ajustada (ex-juros capitalizados):
  valor do TRIMESTRE CORRENTE de cada release (a ordem dos comparativos varia entre
  releases; so o corrente e confiavel por regex). REF de 2022 vem dos comparativos
  cross-verificados em dois releases (1T23-4T23).
Saida: _ref_series.json {lbl, mb, ref, aj} — ref/aj alinhados por rotulo de trimestre.
"""
import datetime
import glob
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))

# ---------- margem bruta reportada (planilha RI) ----------
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True)
ws = wb["CYRELA"]
rows = list(ws.iter_rows(min_row=1, max_row=100, values_only=True))
hdr = rows[3]


def acha(nome):
    for i, r in enumerate(rows):
        if r[0] and nome in str(r[0]):
            return i
    raise KeyError(nome)


r_rec, r_lb = acha("+Receita liquida operac"), acha("=Lucro Bruto")
lbl, mb = [], []
for j in range(1, len(hdr)):
    d = hdr[j]
    if isinstance(d, datetime.datetime):
        rec, lb_ = rows[r_rec][j], rows[r_lb][j]
        if isinstance(rec, (int, float)) and isinstance(lb_, (int, float)) and rec:
            lbl.append(f"{(d.month - 1) // 3 + 1}T{d.year % 100:02d}")
            mb.append(round(100 * lb_ / rec, 1))
wb.close()

# ---------- REF e ajustada (releases, trimestre corrente) ----------
ref = {"1T22": 36.5, "2T22": 35.8, "3T22": 36.0, "4T22": 36.0}  # comparativos verificados
aj = {}
for f in glob.glob(os.path.join(here, "fontes", "release_*.txt")):
    tri = os.path.basename(f)[8:-4]
    raw = io.open(f, encoding="utf-8").read()
    m1 = re.search(r"Margem Bruta a Apropriar\s+([\d,]+)%", raw)
    m2 = re.search(r"Margem Bruta Ajustada\s+([\d,]+)%", raw)
    if m1:
        ref[tri] = float(m1.group(1).replace(",", "."))
    if m2:
        aj[tri] = float(m2.group(1).replace(",", "."))

print("mb :", len(mb), "tri |", lbl[0], "->", lbl[-1])
print("ref:", {k: ref[k] for k in sorted(ref)})
print("aj :", {k: aj[k] for k in sorted(aj)})
io.open(os.path.join(here, "_ref_series.json"), "w", encoding="utf-8").write(
    json.dumps({"lbl": lbl, "mb": mb, "ref": ref, "aj": aj}, ensure_ascii=False))
