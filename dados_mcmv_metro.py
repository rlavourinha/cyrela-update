# -*- coding: utf-8 -*-
"""MCid, MCMV Financiado (FGTS/FS) sintético por município e mês (fontes/mercado/raw_fontes/mcmv_financ_sintetico_20260724_v2.zip):
agrega SP + RJ por mês em unidades (qtd_uh_financiadas), valor financiado e subsídio (R$ mi), para estados, regiões metropolitanas
(RMSP 39 municípios, RMRJ 22) e capitais; faixas 1 e 4 em unidades. Saída: _mcmv_sprj_metro.json {ano-mês: {est, rm, rmsp, rmrj, cap,
f1, f4, fin_est, fin_rmsp, fin_rmrj, fin_cap, sub_rmsp, sub_rmrj, ...}}. Códigos IBGE de 6 dígitos (o arquivo não traz o dígito verificador)."""
import zipfile, io, csv, collections, json, os
here = os.path.dirname(os.path.abspath(__file__))
RMSP = {c // 10 for c in {3503901, 3505708, 3506607, 3509007, 3509205, 3510609, 3513009, 3513801, 3515004, 3515103, 3515707, 3516309, 3516408, 3518305, 3518800, 3522208, 3522505, 3523107, 3525003, 3526209, 3528502, 3529401, 3530607, 3534401, 3539103, 3539806, 3543303, 3544103, 3545001, 3546801, 3547304, 3547809, 3548708, 3548807, 3549953, 3550308, 3552502, 3556453, 3505005}}
RMRJ = {c // 10 for c in {3300100, 3300456, 3300902, 3301702, 3301850, 3301900, 3302007, 3302270, 3302502, 3302700, 3302858, 3303203, 3303302, 3303500, 3303609, 3303906, 3304144, 3304557, 3304904, 3305109, 3305554, 3305752}}
CAP = {355030, 330455}
z = zipfile.ZipFile(os.path.join(here, "fontes", "mercado", "raw_fontes", "mcmv_financ_sintetico_20260724_v2.zip"))
txt = z.read(z.namelist()[0]).decode("utf-8", "replace")
agg = collections.defaultdict(collections.Counter)
for r in csv.DictReader(io.StringIO(txt), delimiter=";"):
    if r["mcmv_fgts_txt_uf"] not in ("SP", "RJ"): continue
    ym = f'{r["num_ano"]}-{int(r["num_mes"]):02d}'; n = int(r["qtd_uh_financiadas"]); c = int(r["cod_ibge"][:6]); fx = r["txt_compatibilidade_faixa_renda"]
    fin = float(r["vlr_financiamento"] or 0) / 1e6; sub = float(r["vlr_subsidio"] or 0) / 1e6
    a = agg[ym]; a["est"] += n; a["fin_est"] += fin; a["sub_est"] += sub
    for key, ok in (("rmsp", c in RMSP), ("rmrj", c in RMRJ), ("cap", c in CAP)):
        if ok: a[key] += n; a["fin_" + key] += fin; a["sub_" + key] += sub
    if c in RMSP or c in RMRJ: a["rm"] += n; a["fin_rm"] += fin
    if fx == "4": a["f4"] += n
    if fx == "1": a["f1"] += n
json.dump({k: dict(v) for k, v in sorted(agg.items())}, io.open(os.path.join(here, "_mcmv_sprj_metro.json"), "w", encoding="utf-8"), indent=0)
t25 = collections.Counter()
for k, v in agg.items():
    if k[:4] == "2025": t25.update(v)
print("2025:", {k: round(v) for k, v in t25.items()})
