# -*- coding: utf-8 -*-
"""Numero de acoes ON ex-tesouraria por trimestre (composicao de capital dos
ITRs/DFPs estruturados da CVM, 2020-2026). Cyrela e ON-only ate 2025; em 2026
ha PN resgatavel (bonificacao) que fica FORA desta serie (EPS sobre ON).
CSVs em <scratchpad>/; saida: _cvm_acoes.json {tri: acoes_mi}."""
import csv
import glob
import io
import json
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
pasta = sys.argv[1] if len(sys.argv) > 1 else here
out = {}
for f in glob.glob(os.path.join(pasta, "*composicao_capital*.csv")):
    for r in csv.DictReader(io.open(f, encoding="latin-1"), delimiter=";"):
        if "CYRELA BRAZIL" not in r["DENOM_CIA"]:
            continue
        dt = r["DT_REFER"]
        a, m = int(dt[:4]), int(dt[5:7])
        tri = f"{(m - 1) // 3 + 1}T{a % 100:02d}"
        on = float(r["QT_ACAO_ORDIN_CAP_INTEGR"]) - float(r["QT_ACAO_ORDIN_TESOURO"])
        # versoes: fica a maior VERSAO (reapresentacoes)
        v = int(r["VERSAO"])
        if tri not in out or v >= out[tri][1]:
            out[tri] = (round(on / 1000, 1), v)

out = {k: v[0] for k, v in sorted(out.items(), key=lambda x: (x[0][2:], x[0][0]))}
io.open(os.path.join(here, "_cvm_acoes.json"), "w", encoding="utf-8").write(json.dumps(out))
print(out)
print("n tris:", len(out))
