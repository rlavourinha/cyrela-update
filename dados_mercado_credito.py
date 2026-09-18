# -*- coding: utf-8 -*-
"""Custo do credito, LTV, preco do imovel financiado e renda — insumos do affordability.

Fontes: BCB Olinda mercadoimobiliario (fontes/mercado/bcb_mercadoimob.csv):
taxas de contratacao PF (sfh/livre/fgts) e PJ sfh (plano empresario), LTV de contratacao,
valor de compra mediano (BR e SP) e valor de avaliacao (BR). Renda media nominal PNADC
(SGS 24381). Saida: _mercado_credito.json (mensal).
"""
import csv
import io
import json
import os
import urllib.request
from collections import defaultdict

here = os.path.dirname(os.path.abspath(__file__))
CH = {
    "credito_contratacao_taxa_pf_sfh_br": "tx_sfh",
    "credito_contratacao_taxa_pf_livre_br": "tx_livre",
    "credito_contratacao_taxa_pf_fgts_br": "tx_fgts",
    "credito_contratacao_taxa_pj_sfh_br": "tx_pj",
    "credito_contratacao_ltv_pf_sfh_br": "ltv_sfh",
    "credito_contratacao_ltv_pf_fgts_br": "ltv_fgts",
    "credito_contratacao_ltv_pf_livre_br": "ltv_livre",
    "imoveis_valor_compra_br": "vc_br",
    "imoveis_valor_compra_sp": "vc_sp",
    "imoveis_valor_avaliacao_br": "va_br",
}
S = defaultdict(dict)
for r in csv.DictReader(io.open(os.path.join(here, "fontes", "mercado", "bcb_mercadoimob.csv"),
                                encoding="utf-8-sig")):
    ch = CH.get(r["Info"])
    if ch:
        S[ch][r["Data"][:7]] = float(r["Valor"].replace(",", "."))

def sgs(cod):
    req = urllib.request.Request(
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json&dataInicial=01/01/2011",
        headers={"User-Agent": "Mozilla/5.0"})
    out = {}
    for x in json.load(urllib.request.urlopen(req, timeout=60)):
        dd, mm, aa = x["data"].split("/")
        out[f"{aa}-{mm}"] = float(x["valor"])
    return out

renda_real = sgs(24381)   # REAL a precos de hoje (SGS re-deflaciona)
ipca = sgs(433)
idx, acc = {}, 1.0
for k in sorted(ipca):
    acc *= 1 + ipca[k] / 100
    idx[k] = acc
ult = idx[max(idx)]
renda_pt = {k: v * idx[k] / ult for k, v in renda_real.items() if k in idx}  # NOMINAL derivada
_rk = sorted(renda_pt)
renda = {}
for _i in range(11, len(_rk)):
    renda[_rk[_i]] = sum(renda_pt[_rk[_j]] for _j in range(_i - 11, _i + 1)) / 12  # MM12

meses = sorted(S["tx_sfh"])
out = {"meses": meses}
for ch in set(CH.values()):
    out[ch] = [round(S[ch][m], 1) if m in S[ch] else None for m in meses]
out["ca"] = [round(100 * S["vc_br"][m] / S["va_br"][m], 1)
             if m in S["vc_br"] and m in S["va_br"] else None for m in meses]
base_m = min(m for m in meses if m in S["vc_br"] and m in renda)
base_p = S["vc_br"][base_m]
base_r = renda[base_m]
out["idx_preco"] = [round(100 * S["vc_br"][m] / base_p, 1) if m in S["vc_br"] else None for m in meses]
out["idx_renda"] = [round(100 * renda[m] / base_r, 1) if m in renda else None for m in meses]
# IGMI-R SP (transacao financiada) x FipeZap SP (anuncio), 100 = jan/2014
import openpyxl, datetime
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "mercado", "igmi-r-serie-historica-maio2026.xlsx"), read_only=True)
ws = wb[wb.sheetnames[0]]
igmi = {}
for r in ws.iter_rows(values_only=True):
    if isinstance(r[0], str) and len(r[0]) == 7 and r[0][:4].isdigit() and isinstance(r[1], (int, float)):
        igmi[r[0].replace(" ", "-")] = float(r[1])
wb.close()
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "mercado", "fipezap.xlsx"), read_only=True)
ws = wb["São Paulo"]
fz = {f"{r[1]:%Y-%m}": r[2] for r in ws.iter_rows(values_only=True)
      if isinstance(r[1], datetime.datetime) and isinstance(r[2], (int, float))}
wb.close()
com = sorted(set(igmi) & set(fz))
b_i, b_f = igmi[com[0]], fz[com[0]]
out["igmi_sp"] = [round(100 * igmi[m] / b_i, 1) if m in igmi else None for m in meses]
out["fz_sp"] = [round(100 * fz[m] / b_f, 1) if m in fz else None for m in meses]
io.open(os.path.join(here, "_mercado_credito.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))

for m in (meses[0], "2019-12", "2021-12", "2024-12", meses[-1]):
    i = meses.index(m) if m in meses else -1
    if i >= 0:
        print(f"{m}: tx sfh {out['tx_sfh'][i]} livre {out['tx_livre'][i]} fgts {out['tx_fgts'][i]} pj {out['tx_pj'][i]} | "
              f"ltv sfh {out['ltv_sfh'][i]} fgts {out['ltv_fgts'][i]} | compra BR {S['vc_br'].get(m, 0)/1000:.0f}k SP {S['vc_sp'].get(m, 0)/1000:.0f}k | "
              f"c/a {out['ca'][i]} | idx preço {out['idx_preco'][i]} renda {out['idx_renda'][i]}")
