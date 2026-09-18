# -*- coding: utf-8 -*-
"""Precos de imoveis nas pracas da Cyrela.

FipeZap (fontes/mercado/fipezap.xlsx, aba por cidade, coluna Total de venda) para
SP / RJ / POA / Indice nacional, mensal desde jan/2008; deflaciona pelo IPCA (SGS 433)
e rebase 100 = jan/2008 nas duas visoes. IVG-R (SGS 21340) como serie de conferencia.
Saida: _mercado_precos.json {meses, nom:{...}, real:{...}, stats}.
"""
import datetime
import io
import json
import os
import urllib.request

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
PRACAS = {"sp": "São Paulo", "rj": "Rio de Janeiro", "br": "Índice FipeZAP"}
EXTRA = {"poa": "Porto Alegre"}   # entra tarde na serie; so estatisticas, fora das curvas

wb = openpyxl.load_workbook(os.path.join(here, "fontes", "mercado", "fipezap.xlsx"), read_only=True)
series = {}
for ch, aba in PRACAS.items():
    ws = wb[aba]
    dados = [(r[1], r[2]) for r in ws.iter_rows(values_only=True)
             if isinstance(r[1], datetime.datetime) and isinstance(r[2], (int, float))]
    series[ch] = dados
wb.close()

# IPCA mensal (%) -> indice acumulado desde jan/2008
req = urllib.request.Request(
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01/01/2008",
    headers={"User-Agent": "Mozilla/5.0"})
ipca = json.load(urllib.request.urlopen(req, timeout=60))
idx_ipca, acc = {}, 1.0
for x in ipca:
    d, m, a = x["data"].split("/")
    acc *= 1 + float(x["valor"]) / 100
    idx_ipca[f"{a}-{m}"] = acc

meses = [f"{d:%Y-%m}" for d, _ in series["br"]]
meses = [m for m in meses if m in idx_ipca]
out = {"meses": meses, "nom": {}, "real": {}}
stats = {}
for ch in PRACAS:
    d = {f"{dt:%Y-%m}": v for dt, v in series[ch]}
    base = d[meses[0]]
    base_r = d[meses[0]] / idx_ipca[meses[0]]
    nom = [round(100 * d[m] / base, 1) if m in d else None for m in meses]
    rea = [round(100 * (d[m] / idx_ipca[m]) / base_r, 1) if m in d else None for m in meses]
    out["nom"][ch] = nom
    out["real"][ch] = rea
    vr = [(meses[i], v) for i, v in enumerate(rea) if v]
    pico = max(vr, key=lambda x: x[1])
    stats[ch] = dict(nom_ult=nom[-1], real_ult=rea[-1], real_pico=pico[1], pico_quando=pico[0],
                     dd_real=round(100 * (rea[-1] / pico[1] - 1), 1),
                     var12_nom=round(100 * (nom[-1] / nom[-13] - 1), 1),
                     var12_real=round(100 * (rea[-1] / rea[-13] - 1), 1))
    print(f"{ch}: nominal {nom[-1]} | real {rea[-1]} (pico {pico[1]} em {pico[0]}, drawdown {stats[ch]['dd_real']}%) "
          f"| 12m nom {stats[ch]['var12_nom']}% real {stats[ch]['var12_real']}%")
# extras (rebase no proprio inicio, so p/ stats)
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "mercado", "fipezap.xlsx"), read_only=True)
for ch, aba in EXTRA.items():
    ws = wb[aba]
    dados = [(f"{r[1]:%Y-%m}", r[2]) for r in ws.iter_rows(values_only=True)
             if isinstance(r[1], datetime.datetime) and isinstance(r[2], (int, float))]
    dados = [(m, v) for m, v in dados if m in idx_ipca]
    rea = [(m, v / idx_ipca[m]) for m, v in dados]
    pico = max(rea, key=lambda x: x[1])
    stats[ch] = dict(inicio=dados[0][0], var12_nom=round(100 * (dados[-1][1] / dados[-13][1] - 1), 1),
                     var12_real=round(100 * (rea[-1][1] / rea[-13][1] - 1), 1),
                     dd_real=round(100 * (rea[-1][1] / pico[1] - 1), 1), pico_quando=pico[0])
    print(f"{ch} (desde {dados[0][0]}): 12m nom {stats[ch]['var12_nom']}% real {stats[ch]['var12_real']}% | dd real {stats[ch]['dd_real']}% (pico {pico[0]})")
wb.close()
# INCC-DI (FGV, SGS 192) -> indice acumulado alinhado aos meses
req = urllib.request.Request(
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.192/dados?formato=json&dataInicial=01/01/2008",
    headers={"User-Agent": "Mozilla/5.0"})
incc_raw = json.load(urllib.request.urlopen(req, timeout=60))
idx_incc, acc2 = {}, 1.0
for x in incc_raw:
    dd, mm, aa = x["data"].split("/")
    acc2 *= 1 + float(x["valor"]) / 100
    idx_incc[f"{aa}-{mm}"] = acc2
base_i = idx_incc[meses[0]]
out["incc"] = [round(100 * idx_incc[m] / base_i, 1) if m in idx_incc else None for m in meses]
# spread preco x INCC nas janelas do ciclo
for jan in (36, 48):
    sp_a = 100 * (out["nom"]["sp"][-1] / out["nom"]["sp"][-1 - jan] - 1)
    rj_a = 100 * (out["nom"]["rj"][-1] / out["nom"]["rj"][-1 - jan] - 1)
    ic_a = 100 * (out["incc"][-1] / out["incc"][-1 - jan] - 1)
    print(f"janela {jan}m (ate jul/26): SP +{sp_a:.1f}% | RJ +{rj_a:.1f}% | INCC +{ic_a:.1f}% | spread SP {sp_a-ic_a:+.1f}pp RJ {rj_a-ic_a:+.1f}pp")
out["stats"] = stats
io.open(os.path.join(here, "_mercado_precos.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))
print("meses:", len(meses), meses[0], "a", meses[-1])
