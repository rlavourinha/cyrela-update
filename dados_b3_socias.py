# -*- coding: utf-8 -*-
"""Cotações diárias de CURY3, PLPL3 e LAVV3 desde os IPOs (set/2020) via B3 COTAHIST anual (PREULT, mercado à vista 010), e número de
ações por trimestre pela CVM (ITR/DFP: lucro atribuível 3.11.01 ÷ LPA básico 3.99.01.01, zips já em fontes/cvm/), para o market cap
histórico. Saída: _cotacao_socias.json {ticker: {"px": {data: preço}, "acoes": {trimestre: milhões}}}."""
import io, os, re, csv, json, zipfile, requests
here = os.path.dirname(os.path.abspath(__file__)); B3 = os.path.join(here, "fontes", "b3"); CV = os.path.join(here, "fontes", "cvm"); os.makedirs(B3, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
TICK = ("CURY3", "PLPL3", "LAVV3")
px = {t: {} for t in TICK}
for ano in range(2020, 2027):
    p = os.path.join(B3, f"COTAHIST_A{ano}.ZIP")
    if not os.path.exists(p) or os.path.getsize(p) < 1e6:
        r = requests.get(f"https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP", headers=H, timeout=900, stream=True, verify=False)
        with open(p, "wb") as f:
            for ch in r.iter_content(1 << 20): f.write(ch)
    z = zipfile.ZipFile(p); name = z.namelist()[0]
    with z.open(name) as f:
        for line in io.TextIOWrapper(f, encoding="latin-1"):
            if line[:2] != "01" or line[24:27] != "010": continue
            cod = line[12:24].strip()
            if cod in px: px[cod][f"{line[2:6]}-{line[6:8]}-{line[8:10]}"] = int(line[108:121]) / 100
    print(ano, {t: len(px[t]) for t in TICK}, flush=True)
# ações por trimestre via CVM (lucro ÷ LPA); Cury: DENOM 'CURY'
EMP = {"CURY3": r"^CURY", "PLPL3": r"PLANO\s*&\s*PLANO|PLANO E PLANO", "LAVV3": r"LAVVI"}
ll = {t: {} for t in TICK}; eps = {t: {} for t in TICK}
for fn in sorted(os.listdir(CV)):
    if not re.match(r"(itr|dfp)_cia_aberta_20\d\d\.zip", fn): continue
    z = zipfile.ZipFile(os.path.join(CV, fn)); kind = fn[:3]; ano = fn[-8:-4]
    with z.open(f"{kind}_cia_aberta_DRE_con_{ano}.csv") as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            t = next((k for k, rx in EMP.items() if re.search(rx, r["DENOM_CIA"], re.I)), None)
            if not t or r["ORDEM_EXERC"] != "ÚLTIMO": continue
            ini, fim = r["DT_INI_EXERC"], r["DT_FIM_EXERC"]
            if ini[5:7] != "01": continue          # só acumulado no ano (mesma base do LPA)
            q = f"{(int(fim[5:7]) - 1) // 3 + 1}T{fim[2:4]}"; v = float(r["VL_CONTA"]) * (1000 if r["ESCALA_MOEDA"] == "MIL" else 1)
            if r["CD_CONTA"] == "3.11.01": ll[t][q] = v
            elif r["CD_CONTA"] in ("3.99.01.01", "3.99.01"): eps[t].setdefault(q, v) if r["CD_CONTA"] == "3.99.01" else eps[t].__setitem__(q, v)
acoes = {t: {q: round(ll[t][q] / eps[t][q] / 1e6, 2) for q in ll[t] if q in eps[t] and eps[t][q]} for t in TICK}
json.dump({t: {"px": px[t], "acoes": acoes[t]} for t in TICK}, io.open(os.path.join(here, "_cotacao_socias.json"), "w", encoding="utf-8"))
for t in TICK: print(t, "primeiro pregão:", min(px[t]) if px[t] else None, "último:", max(px[t]) if px[t] else None, "| ações:", acoes[t])
