# -*- coding: utf-8 -*-
"""Oferta e demanda do mercado (Abrainc-Fipe, fontes/mercado/abrainc.xlsx).

Mensal jan/2014-atual, unidades: lancadas, vendidas, distratadas e em oferta,
split Total / MAP / MCMV. Gera acumulados 12m e meses de estoque
(oferta / media mensal de vendas 12m). Saida: _mercado_liquidez.json.
"""
import datetime
import io
import json
import os

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "mercado", "abrainc.xlsx"),
                            read_only=True, data_only=True)
ws = wb["Indicadores Abrainc-Fipe"]
grid = [r for r in ws.iter_rows(values_only=True) if isinstance(r[2], datetime.datetime)]
wb.close()

COL = {"tot": {"lanc": 3, "vend": 8, "dist": 18, "ofer": 23},
       "map": {"lanc": 4, "vend": 9, "dist": 19, "ofer": 24},
       "mcmv": {"lanc": 5, "vend": 10, "dist": 20, "ofer": 25}}


def num(v):
    return float(v) if isinstance(v, (int, float)) else None


meses = [f"{r[2]:%Y-%m}" for r in grid]
raw = {seg: {k: [num(r[j]) for r in grid] for k, j in cols.items()} for seg, cols in COL.items()}


def m12(v):  # soma móvel 12m (None enquanto não há 12 obs válidas)
    out = []
    for i in range(len(v)):
        jan = v[i - 11:i + 1] if i >= 11 else None
        out.append(round(sum(jan) / 1000, 1) if jan and all(x is not None for x in jan) else None)
    return out


out = {"meses": meses, "seg": {}}
for seg in COL:
    lanc12, vend12 = m12(raw[seg]["lanc"]), m12(raw[seg]["vend"])
    dist12 = m12(raw[seg]["dist"])
    ofer = [round(v / 1000, 1) if v is not None else None for v in raw[seg]["ofer"]]
    mest = [round(ofer[i] / (vend12[i] / 12), 1) if ofer[i] and vend12[i] else None
            for i in range(len(meses))]
    vso12 = [round(100 * vend12[i] / (vend12[i] + ofer[i]), 1) if ofer[i] and vend12[i] else None
             for i in range(len(meses))]
    out["seg"][seg] = {"lanc12": lanc12, "vend12": vend12, "dist12": dist12,
                       "ofer": ofer, "mest": mest, "vso12": vso12}
    vals = [(meses[i], lanc12[i], vend12[i], ofer[i], mest[i], vso12[i])
            for i in range(len(meses)) if mest[i]]
    ini = next(meses[i] for i in range(len(meses)) if lanc12[i] is not None)
    m, l, v, o, me, vs = vals[-1]
    print(f"{seg:4s} (12m desde {ini}): {m} | lanç 12m {l} mil | vendas 12m {v} mil | oferta {o} mil "
          f"| {me} meses de estoque | VSO12m {vs}%")
    # ha 24m p/ comparacao
    m2 = vals[-25] if len(vals) > 25 else vals[0]
    print(f"     24m antes ({m2[0]}): lanç {m2[1]} | vendas {m2[2]} | oferta {m2[3]} | {m2[4]} meses | VSO {m2[5]}%")

io.open(os.path.join(here, "_mercado_liquidez.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))
