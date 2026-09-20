# -*- coding: utf-8 -*-
"""Alonga para trás as séries por banco do IF.data (BCB) usadas nos slides 'bancos' do deck enxuto.
Passivo (relatório 3: LCI c1, Depósitos de Poupança a2, Obrigações por Empréstimos e Repasses d) existe desde mar/2000;
carteira por modalidade (rel. 11 PF grupo Habitação, rel. 13 PJ grupo Habitacional) só existe a partir de jun/2014.
Tipo 2 (conglomerado financeiro). Códigos estáveis desde 2000: Caixa 00360305, Bradesco C0010045, Itaú C0010069,
Santander C0030379, BB C0049906 (Inter C0051884 só recente). 'Sistema' = soma de todas as instituições do relatório.
Acrescenta trimestres faltantes em _funding_emissor_trimestral.json e _funding_emissor_hab_trimestral.json (R$ mi)."""
import io, json, os, sys, time, requests
here = os.path.dirname(os.path.abspath(__file__))
B = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/"
CODES = {"00360305": "Caixa", "C0010045": "Bradesco", "C0010069": "Itaú", "C0030379": "Santander", "C0049906": "Banco do Brasil", "C0051884": "Inter"}
def get(am, rel, tries=40):   # a API devolve 500 em surtos; espera até ~40 min
    u = B + f"IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,Relatorio=@Relatorio)?@AnoMes={am}&@TipoInstituicao=2&@Relatorio='{rel}'&$format=json"
    for k in range(tries):
        try:
            r = requests.get(u, timeout=300)
            if r.status_code != 200: raise RuntimeError(f"HTTP {r.status_code}")
            return r.json()["value"]
        except Exception as e:
            print("  retry", am, rel, str(e)[:60], flush=True); time.sleep(60)
    return None
def load(n):
    p = os.path.join(here, n); return json.load(io.open(p, encoding="utf-8")), p
F, pF = load("_funding_emissor_trimestral.json"); H, pH = load("_funding_emissor_hab_trimestral.json")
def col(rows, key, grupo=None):
    out = {}
    for x in rows:
        nc = (x.get("NomeColuna") or "").replace("\n", " "); g = x.get("Grupo") or ""
        if key in nc and (grupo is None or grupo in g) and x.get("Saldo") is not None:
            out[x["CodInst"]] = out.get(x["CodInst"], 0) + x["Saldo"]
    return out
quarters = [f"{y}-{m:02d}" for y in range(2000, 2015) for m in (3, 6, 9, 12)]
for q in quarters:
    am = q.replace("-", "")
    if q not in F["serie"]:
        rows = get(am, "3")
        if rows is None: print("sem passivo", q); continue
        lci = col(rows, "Letras de Crédito Imobiliário"); poup = col(rows, "Depósitos de Poupança"); rep = col(rows, "Obrigações por Empréstimos e Repasses")
        d = {}
        for c, n in CODES.items():
            if c in poup or c in lci: d[n] = {"lci": lci.get(c, 0) / 1e6, "poup": poup.get(c, 0) / 1e6, "hab": 0, "repasses": rep.get(c, 0) / 1e6}
        d["Sistema"] = {"lci": sum(lci.values()) / 1e6, "poup": sum(poup.values()) / 1e6, "hab": 0, "repasses": sum(rep.values()) / 1e6}
        F["serie"][q] = d; json.dump(F, io.open(pF, "w", encoding="utf-8"), ensure_ascii=False)
        print(q, "passivo ok:", {k: round(v["poup"] / 1000, 1) for k, v in d.items()})
    if q >= "2014-06" and q not in H["serie"]:
        r11 = get(am, "11"); r13 = get(am, "13")
        if r11 is None or r13 is None: print("sem carteira", q); continue
        pf = col(r11, "Total", "Habita"); pj = col(r13, "Total", "Habita")
        d = {n: {"hab_pf": pf.get(c, 0) / 1e6, "hab_pj": pj.get(c, 0) / 1e6} for c, n in CODES.items() if c in pf}
        d["Sistema"] = {"hab_pf": sum(pf.values()) / 1e6, "hab_pj": sum(pj.values()) / 1e6}; d["_tipo"] = 2
        H["serie"][q] = d; json.dump(H, io.open(pH, "w", encoding="utf-8"), ensure_ascii=False)
        print(q, "carteira ok:", {k: round(v["hab_pf"] / 1000, 1) for k, v in d.items() if k != "_tipo"})
print("fim", len(F["serie"]), len(H["serie"]))
