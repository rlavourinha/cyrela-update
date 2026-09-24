# -*- coding: utf-8 -*-
"""Dias de recebível dos pares (pedido de 23/09/26): contas a receber (balanço consolidado, circulante 1.01.03 + não circulante
'Contas a Receber'/'Clientes' em 1.02.01.xx) e receita líquida (3.01, trimestre corrente) via dados abertos da CVM (ITR/DFP 2021-26,
tabelas BPA_con e DRE_con; cache em fontes/cvm/). Empresas: Lavvi, Trisul, EZTEC, Even, Moura Dubeux (MAP); Cury, Plano & Plano, Direcional, Tenda, MRV (MCMV); Cyrela (controle).
Dias = contas a receber ÷ receita 12 meses × 365. Saída: _cvm_cr_pares.json {empresa: {tri: {cr_cp, cr_lp, cr, rec_tri, rec12, dias}}}."""
import io, os, re, json, zipfile, csv
here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "fontes", "cvm")
EMP = {"lavvi": r"^LAVVI", "trisul": r"^TRISUL", "eztec": r"^EZ ?TEC", "even": r"^EVEN CONSTRUTORA", "mdne": r"^MOURA DUBEUX", "cury": r"^CURY", "pp": r"^PLANO & PLANO", "direcional": r"^DIRECIONAL", "tenda": r"^CONSTRUTORA TENDA", "mrv": r"^MRV ENGENHARIA", "cyrela": r"^CYRELA BRAZIL"}
def rows(z, name):
    with z.open(name) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"): yield r
def qof(dt): y, m = int(dt[:4]), int(dt[5:7]); return f"{(m - 1) // 3 + 1}T{str(y)[2:]}"
BS = {k: {} for k in EMP}; DRE = {k: {} for k in EMP}; SEEN = {k: {} for k in EMP}
for ano in (2021, 2022, 2023, 2024, 2025, 2026):
    for kind in ("itr", "dfp"):
        p = os.path.join(D, f"{kind}_cia_aberta_{ano}.zip")
        if not os.path.exists(p): continue
        z = zipfile.ZipFile(p)
        for r in rows(z, f"{kind}_cia_aberta_BPA_con_{ano}.csv"):
            emp = next((k for k, rx in EMP.items() if re.search(rx, r["DENOM_CIA"], re.I)), None)
            if not emp or r["ORDEM_EXERC"] != "ÚLTIMO": continue
            cd, ds = r["CD_CONTA"], r["DS_CONTA"]; q = qof(r["DT_FIM_EXERC"]); v = float(r["VL_CONTA"]) / (1000 if r["ESCALA_MOEDA"] == "MIL" else 1e6)
            if cd == "1.01.03": BS[emp].setdefault(q, {})["cr_cp"] = v; SEEN[emp].setdefault(q, []).append((cd, ds))
            elif re.fullmatch(r"1\.02\.01\.\d\d", cd) and re.search(r"contas a receber|clientes", ds, re.I): BS[emp].setdefault(q, {})["cr_lp"] = BS[emp].get(q, {}).get("cr_lp", 0) + v; SEEN[emp].setdefault(q, []).append((cd, ds))
        for r in rows(z, f"{kind}_cia_aberta_DRE_con_{ano}.csv"):
            emp = next((k for k, rx in EMP.items() if re.search(rx, r["DENOM_CIA"], re.I)), None)
            if not emp or r["ORDEM_EXERC"] != "ÚLTIMO" or r["CD_CONTA"] != "3.01": continue
            ini, fim = r["DT_INI_EXERC"], r["DT_FIM_EXERC"]; span = (int(fim[:4]) - int(ini[:4])) * 12 + int(fim[5:7]) - int(ini[5:7]) + 1
            v = float(r["VL_CONTA"]) / (1000 if r["ESCALA_MOEDA"] == "MIL" else 1e6); q = qof(fim)
            DRE[emp].setdefault(q, {})["ytd" if span > 3 else "tri"] = v
ORD = lambda q: (int(q[2:]), int(q[0]))
OUT = {}
for emp in EMP:
    qs = sorted(set(BS[emp]) | set(DRE[emp]), key=ORD); rec = {}
    for q in qs:
        d = DRE[emp].get(q, {})
        if "tri" in d: rec[q] = d["tri"]
        elif "ytd" in d:   # DFP: ano inteiro → 4T = ano − 9M (3T ytd)
            n = int(q[0]); prev = DRE[emp].get(f"{n-1}T{q[2:]}", {}).get("ytd") if n > 1 else 0
            if n == 1: rec[q] = d["ytd"]
            elif prev is not None: rec[q] = d["ytd"] - prev
    o = {}
    for i, q in enumerate(qs):
        b = BS[emp].get(q, {})
        if "cr_cp" not in b: continue
        r12 = sum(rec.get(qs[j], 0) for j in range(i - 3, i + 1)) if i >= 3 and all(qs[j] in rec for j in range(i - 3, i + 1)) else None
        cr = b["cr_cp"] + b.get("cr_lp", 0)
        o[q] = {"cr_cp": b["cr_cp"], "cr_lp": b.get("cr_lp", 0), "cr": cr, "rec_tri": rec.get(q), "rec12": r12, "dias": 365 * cr / r12 if r12 else None}
    OUT[emp] = o
json.dump(OUT, io.open(os.path.join(here, "_cvm_cr_pares.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for emp, o in OUT.items():
    print(f"== {emp}: contas da nota:", sorted({ds for v in SEEN[emp].values() for cd, ds in v})[:6])
    print("   " + " ".join(f"{q}:{v['dias']:.0f}" for q, v in o.items() if v["dias"]))
    if not o: print("   sem dados"); continue
    q = list(o)[-1]; v = o[q]; print(f"   {q}: CR {v['cr']:,.0f} (cp {v['cr_cp']:,.0f} + lp {v['cr_lp']:,.0f}), rec12 {v['rec12']:,.0f}" if v["rec12"] else f"   {q}: sem rec12")
