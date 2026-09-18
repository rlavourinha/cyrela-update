# -*- coding: utf-8 -*-
"""Fontes e usos do funding imobiliario (BCB - Estatisticas do Mercado Imobiliario, Olinda).

Dataset: fontes/mercado/bcb_mercadoimob.csv (baixar de
https://olinda.bcb.gov.br/olinda/servico/MercadoImobiliario/versao/v1/odata/mercadoimobiliario?$format=text/csv
com User-Agent). Chaves usadas:
- fontes_sbpe_saldo_br, fontes_lci_br, fontes_lig_br, fontes_cri_br  (estoques, R$)
- direcionamento_aplicacao_imobiliario_br (aplicacoes computadas no direcionamento)
Exigibilidade = 65% x saldo SBPE (Res. CMN 4.676). Cumprimento = aplicacoes / exigibilidade.
Saida: _funding_bcb.json (R$ bi). fontes_lci/lig/cri atualizam com defasagem maior que sbpe.
"""
import csv
import io
import json
import os
from collections import defaultdict

here = os.path.dirname(os.path.abspath(__file__))
rows = csv.DictReader(io.open(os.path.join(here, "fontes", "mercado", "bcb_mercadoimob.csv"),
                              encoding="utf-8-sig"))
CHAVES = {"fontes_sbpe_saldo_br": "sbpe", "fontes_lci_br": "lci", "fontes_lig_br": "lig",
          "fontes_cri_br": "cri", "direcionamento_aplicacao_imobiliario_br": "aplic"}
serie = defaultdict(dict)
for r in rows:
    ch = CHAVES.get(r["Info"])
    if ch:
        serie[ch][r["Data"][:7]] = round(float(r["Valor"].replace(",", ".")) / 1e9, 1)

meses = sorted(serie["sbpe"])
out = {"meses": meses}
for ch in CHAVES.values():
    out[ch] = [serie[ch].get(m) for m in meses]
out["exig"] = [round(0.65 * v, 1) if v else None for v in out["sbpe"]]
io.open(os.path.join(here, "_funding_bcb.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))

for m in (meses[0], "2018-12", "2020-12", "2022-12", "2024-12", meses[-1]):
    if m in serie["sbpe"]:
        a, e = serie["aplic"].get(m), 0.65 * serie["sbpe"][m]
        cump = f"{100*a/e:.0f}%" if a else "-"
        print(f"{m}: SBPE {serie['sbpe'][m]:6.0f} | exig(65%) {e:5.0f} | aplic {a or 0:5.0f} ({cump}) | "
              f"LCI {serie['lci'].get(m, 0) or 0:5.0f} | LIG {serie['lig'].get(m, 0) or 0:5.0f} | CRI {serie['cri'].get(m, 0) or 0:5.0f}")
