# -*- coding: utf-8 -*-
"""Demanda e affordability (mercado).

- Affordability: PRIMEIRA PARCELA SAC (financiamento de 80% de um apto de 60 m² ao preco
  medio FipeZap-SP, 360 meses, taxa media BCB 20772) dividida pela renda media nominal
  PNADC (SGS 24381). Serie mensal desde 2012.
- Yield de aluguel SP: aluguel medio R$/m2 (FipeZap locacao) x preco medio venda R$/m2.
- Credito: concessoes imobiliarias PF (SGS 20661, acum 12m); poupanca: saldo (1835) e
  captacao liquida anual SBPE (24421). LCI/CRI: pontos citados (B3) no patch, nao aqui.
Saida: _mercado_demanda.json.
"""
import datetime
import io
import json
import os
import urllib.request

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))


def sgs(cod, ini="01/01/2008"):
    req = urllib.request.Request(
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json&dataInicial={ini}",
        headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    out = {}
    for x in d:
        dd, mm, aa = x["data"].split("/")
        out[f"{aa}-{mm}"] = float(x["valor"])
    return out


taxa = sgs(20772)       # % a.a., financiamento aquisicao PF
renda_real = sgs(24381)  # PNADC habitual, REAL a precos de hoje (SGS re-deflaciona a serie)
conc = sgs(20661)       # concessoes imobiliarias PF, R$ mi/mes
poup_saldo = sgs(1835)  # poupanca total, R$ mil
sbpe = sgs(24439, '01/01/2011')  # saldo poupanca SBPE, R$ mi
ipca_m = sgs(433, '01/01/2011')  # IPCA % mensal -> indice
idx, acc = {}, 1.0
for k in sorted(ipca_m):
    acc *= 1 + ipca_m[k] / 100
    idx[k] = acc
ult_idx = idx[max(idx)]
renda_pt = {k: v * idx[k] / ult_idx for k, v in renda_real.items() if k in idx}  # nominal derivada
_rk = sorted(renda_pt)
renda = {}
for _i in range(11, len(_rk)):
    renda[_rk[_i]] = sum(renda_pt[_rk[_j]] for _j in range(_i - 11, _i + 1)) / 12  # MM12
dep = sgs(24443, '01/01/2011')   # depositos poupanca (total), R$ mi/mes
ret = sgs(24444, '01/01/2011')   # retiradas poupanca (total), R$ mi/mes
capliq_m = {k: dep[k] - ret[k] for k in sorted(set(dep) & set(ret))}
capliq_ano = {}
for k, v in capliq_m.items():
    capliq_ano[k[:4]] = capliq_ano.get(k[:4], 0.0) + v

wb = openpyxl.load_workbook(os.path.join(here, "fontes", "mercado", "fipezap.xlsx"), read_only=True)
ws = wb["São Paulo"]
pv, pl = {}, {}
for r in ws.iter_rows(values_only=True):
    if isinstance(r[1], datetime.datetime):
        m = f"{r[1]:%Y-%m}"
        if isinstance(r[17], (int, float)):
            pv[m] = r[17]     # preco medio venda R$/m2
        if isinstance(r[37], (int, float)):
            pl[m] = r[37]     # aluguel medio R$/m2/mes
wb.close()

AREA, LTV = 60, 0.8
meses_a = sorted(set(taxa) & set(renda) & set(pv))
afford = {}
for m in meses_a:
    im = (1 + taxa[m] / 100) ** (1 / 12) - 1
    parcela1 = pv[m] * AREA * LTV * (1 / 360 + im)
    afford[m] = round(100 * parcela1 / renda[m], 1)   # % da renda media
meses_y = sorted(set(pv) & set(pl))
yield_sp = {m: round(100 * pl[m] * 12 / pv[m], 2) for m in meses_y}
conc12 = {}
mk = sorted(conc)
for i in range(11, len(mk)):
    conc12[mk[i]] = round(sum(conc[mk[j]] for j in range(i - 11, i + 1)) / 1000, 1)  # R$ bi 12m

out = {"afford": afford, "yield_sp": yield_sp, "taxa": taxa, "conc12": conc12,
       "poup_saldo_bi": {k: round(v / 1e6, 1) for k, v in poup_saldo.items()},
       "capliq_anual_bi": {k: round(v / 1e3, 1) for k, v in capliq_ano.items()},
       "capliq_mensal_bi": {k: round(v / 1e3, 1) for k, v in capliq_m.items()},
       "poup_real_bi": {k: round(v / 1e6 * idx[max(idx)] / idx[k], 1) for k, v in poup_saldo.items() if k in idx},
       "premissas": {"area_m2": AREA, "ltv": LTV, "prazo_meses": 360, "sistema": "SAC (1a parcela)"}}
io.open(os.path.join(here, "_mercado_demanda.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))

print("afford (1a parcela SAC apto 60m2 SP, % da renda media):")
for m in ("2012-03", "2014-08", "2019-12", "2020-12", "2022-12", "2024-12", meses_a[-1]):
    if m in afford:
        print(f"  {m}: {afford[m]}% da renda | taxa {taxa[m]:.2f}% | apto R$ {pv[m]*AREA/1000:,.0f} mil | renda R$ {renda[m]:,.0f}")
pior = max(afford, key=afford.get); melhor = min(afford, key=afford.get)
print(f"  pior {pior} ({afford[pior]}%) | melhor {melhor} ({afford[melhor]}%)")
print("\nyield aluguel SP (% a.a.):")
for m in ("2008-06", "2010-12", "2014-08", "2017-12", "2020-12", "2022-12", meses_y[-1]):
    if m in yield_sp:
        print(f"  {m}: {yield_sp[m]}%")
print(f"\nconcessoes imob PF 12m: {list(conc12.items())[-1]} | dez/24: {conc12.get('2024-12')} | dez/22: {conc12.get('2022-12')}")
print("capliq anual poupanca (R$ bi):", {k: round(v/1e3,1) for k, v in sorted(capliq_ano.items())})
