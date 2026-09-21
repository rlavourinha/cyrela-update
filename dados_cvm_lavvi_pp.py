# -*- coding: utf-8 -*-
"""Lavvi (LAVV3) e Plano & Plano (PLPL3): DRE e balanço consolidados trimestrais via dados abertos da CVM (ITR e DFP, arquivos
anuais zip: itr_cia_aberta_AAAA.zip / dfp_cia_aberta_AAAA.zip, tabelas DRE_con e BPP_con). ITR traz acumulado no ano (1T, 6M, 9M) e
trimestre corrente; a DFP traz o ano. Extrai: lucro líquido atribuível aos controladores (3.11), lucro consolidado (3.11 total),
PL dos controladores (2.03 menos 2.03.09), resultado financeiro (3.06). Saída: _cvm_lavvi_pp.json {empresa: {trimestre: {...}}}.
Cache dos zips em fontes/cvm/."""
import io, os, re, json, zipfile, csv, requests
here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "fontes", "cvm"); os.makedirs(D, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
EMP = {"lavvi": r"LAVVI", "pp": r"PLANO\s*&\s*PLANO|PLANO E PLANO"}
out = {k: {} for k in EMP}
def get(kind, ano):
    p = os.path.join(D, f"{kind}_cia_aberta_{ano}.zip")
    if not os.path.exists(p) or os.path.getsize(p) < 1e6:
        r = requests.get(f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{kind.upper()}/DADOS/{kind}_cia_aberta_{ano}.zip", headers=H, timeout=900, stream=True)
        with open(p, "wb") as f:
            for ch in r.iter_content(1 << 20): f.write(ch)
    return zipfile.ZipFile(p)
def rows(z, name):
    with z.open(name) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"): yield r
def qof(dt_fim, kind):
    y, m = int(dt_fim[:4]), int(dt_fim[5:7]); return f"{(m - 1) // 3 + 1}T{str(y)[2:]}"
for ano in (2021, 2022, 2023, 2024, 2025, 2026):
    for kind in ("itr", "dfp"):
        if kind == "dfp" and ano == 2026: continue
        try: z = get(kind, ano)
        except Exception as e: print(kind, ano, "ERR", e, flush=True); continue
        for tab, codes in (("DRE", {"3.11": "ll_cons", "3.11.01": "ll_ctrl", "3.06": "fin", "3.01": "rec", "3.03": "lb", "3.05": "ebit"}), ("BPP", {"2.03": "pl_total", "2.03.09": "pl_minor"})):
            name = f"{kind}_cia_aberta_{tab}_con_{ano}.csv"
            for r in rows(z, name):
                emp = next((k for k, rx in EMP.items() if re.search(rx, r["DENOM_CIA"], re.I)), None)
                if not emp or r["ORDEM_EXERC"] != "ÚLTIMO": continue
                cd = r["CD_CONTA"]
                if cd not in codes: continue
                if tab == "DRE":
                    ini, fim = r["DT_INI_EXERC"], r["DT_FIM_EXERC"]; span = (int(fim[:4]) - int(ini[:4])) * 12 + int(fim[5:7]) - int(ini[5:7]) + 1
                    q = qof(fim, kind); key = codes[cd] + ("_ytd" if span > 3 else "_tri")
                else:
                    q = qof(r["DT_FIM_EXERC"], kind); key = codes[cd]
                out[emp].setdefault(q, {})[key] = float(r["VL_CONTA"]) * (1000 if r["ESCALA_MOEDA"] == "MIL" else 1) / 1e6
        print(kind, ano, "ok", flush=True)
# trimestre a partir do acumulado quando falta (DFP: ano = 4T ytd; 4T tri = ano − 9M)
ORD = lambda q: (int(q[2:]), int(q[0]))
for emp, d in out.items():
    for q in sorted(d, key=ORD):
        for f in ("ll_cons", "ll_ctrl", "fin", "rec", "lb", "ebit"):
            if f + "_tri" not in d[q] and f + "_ytd" in d[q]:
                t = int(q[0]); prev = f"{t - 1}T{q[2:]}"
                if t == 1: d[q][f + "_tri"] = d[q][f + "_ytd"]
                elif prev in d and f + "_ytd" in d[prev]: d[q][f + "_tri"] = d[q][f + "_ytd"] - d[prev][f + "_ytd"]
        if "pl_total" in d[q]: d[q]["pl_ctrl"] = d[q]["pl_total"] - d[q].get("pl_minor", 0)
json.dump(out, io.open(os.path.join(here, "_cvm_lavvi_pp.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for emp, d in out.items():
    print("==", emp)
    for q in sorted(d, key=ORD): print("  ", q, {k: round(v, 1) for k, v in d[q].items() if k.endswith("_tri") or k.startswith("pl")})
