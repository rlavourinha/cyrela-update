# -*- coding: utf-8 -*-
"""Geoimovel 'Mercado Completo' (SP capital, res. vertical; foto de mai/2026; uma linha
por tipo de unidade). Agrega por empreendimento (RGI) e compara Cyrela (CYRELA, LIVING,
VIVAZ) com o mercado: curva de vendas cross-section (% vendido x meses desde o
lancamento), preco/m2 no lancamento e na pesquisa, share de lancamentos.
Saida: _geoimovel.json + resumo no console."""
import io, json, os, collections, datetime, statistics as st
import openpyxl
here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "geoimovel", "mercado_completo_geoimovel.xlsx"), read_only=True, data_only=True)
ws = wb["plan"]; rows = list(ws.iter_rows(values_only=True)); H = list(rows[0]); R = rows[1:]
ix = {n: i for i, n in enumerate(H)}
def g(r, n): return r[ix[n]]
def f(v):
    try: return float(v)
    except (TypeError, ValueError): return None
CYR = {"CYRELA": "Cyrela", "LIVING": "Living", "VIVAZ RESIDENCIAL": "Vivaz"}
JV = {"CURY": "Cury", "PLANO E PLANO": "Plano&Plano", "LAVVI": "Lavvi"}
P = {}
for r in R:
    k = g(r, "RGI"); d = P.setdefault(k, {"nome": g(r, "Empreendimento"), "lanc": g(r, "Data Lançamento"), "entrega": g(r, "Data Entrega"),
        "padrao": g(r, "Padrão"), "status": g(r, "Status"), "grupo": g(r, "Grupo Incorporador Apelido"), "regiao": g(r, "Região"), "distrito": g(r, "Distrito"),
        "pesq": g(r, "Data Pesquisa"), "un": 0, "vend": 0, "est": 0, "vgv": 0.0, "area_pv": 0.0, "pv0": 0.0, "pv1": 0.0, "modal": g(r, "Modalidade")})
    un, vd, es = f(g(r, "Unidades")) or 0, f(g(r, "Unidades Vendidas")) or 0, f(g(r, "Qtd em Estoque")) or 0
    ap, v0, v1 = f(g(r, "Área Privativa")), f(g(r, "(VUV) Preço m2 privativo no lançamento")), f(g(r, "(VUV) Preço m2 privativo na data pesquisa"))
    d["un"] += un; d["vend"] += vd; d["est"] += es; d["vgv"] += f(g(r, "VGV")) or 0
    if ap and v0 and un: d["area_pv"] += ap * un; d["pv0"] += v0 * ap * un; d["pv1"] += (v1 or v0) * ap * un
for d in P.values():
    d["pct"] = d["vend"] / d["un"] * 100 if d["un"] else None
    d["m2_lanc"] = d["pv0"] / d["area_pv"] if d["area_pv"] else None
    d["m2_hoje"] = d["pv1"] / d["area_pv"] if d["area_pv"] else None
    d["meses"] = ((d["pesq"].year - d["lanc"].year) * 12 + d["pesq"].month - d["lanc"].month) if isinstance(d["lanc"], datetime.datetime) and isinstance(d["pesq"], datetime.datetime) else None
    d["quem"] = CYR.get(d["grupo"], JV.get(d["grupo"], "mercado"))
    d["tk"] = d["vgv"] / d["un"] if d["un"] else None
lanc = [d["lanc"] for d in P.values() if isinstance(d["lanc"], datetime.datetime)]
print("empreendimentos:", len(P), "| lançamento de", min(lanc).date(), "a", max(lanc).date(), "| pesquisa:", collections.Counter(str(d["pesq"])[:7] for d in P.values()).most_common(3))
print("por grupo (empreendimentos, unidades):", {q: (sum(1 for d in P.values() if d["quem"] == q), int(sum(d["un"] for d in P.values() if d["quem"] == q))) for q in ("Cyrela", "Living", "Vivaz", "Cury", "Plano&Plano", "Lavvi", "mercado")})
# curva cross-section: % vendido por faixa de meses desde o lancamento, ponderado por unidades
BINS = [(0, 6), (6, 12), (12, 24), (24, 36), (36, 60)]  # faixas largas: a foto e cross-section e a Cyrela tem poucos projetos por faixa
def curva(sel):
    out = []
    for a, b in BINS:
        s = [d for d in sel if d["meses"] is not None and a <= d["meses"] < b and d["un"]]
        u = sum(d["un"] for d in s); out.append({"faixa": f"{a}-{b}", "n": len(s), "un": int(u), "pct": round(sum(d["vend"] for d in s) / u * 100, 1) if u else None})
    return out
GR = {"cyrela_ap": lambda d: d["quem"] == "Cyrela", "living": lambda d: d["quem"] == "Living", "vivaz": lambda d: d["quem"] == "Vivaz",
      "mercado_luxo": lambda d: d["quem"] == "mercado" and d["padrao"] == "Luxo", "mercado_medioalto": lambda d: d["quem"] == "mercado" and d["padrao"] == "Médio Alto",
      "mercado_econ": lambda d: d["quem"] == "mercado" and d["padrao"] == "Econômico", "cury": lambda d: d["quem"] == "Cury", "pp": lambda d: d["quem"] == "Plano&Plano", "lavvi": lambda d: d["quem"] == "Lavvi"}
CUR = {k: curva([d for d in P.values() if fn(d)]) for k, fn in GR.items()}
print("\ncurva cross-section (% vendido por meses desde o lançamento):")
for k, c in CUR.items(): print(f"  {k:18s}", " | ".join(f"{x['faixa']}: {x['pct']} (n={x['n']})" for x in c))
# padrao da Cyrela
print("\npadrão por grupo:", {q: collections.Counter(d["padrao"] for d in P.values() if d["quem"] == q).most_common(3) for q in ("Cyrela", "Living", "Vivaz")})
# preco m2 lancamento por ano e grupo (mediana) e reprecificacao
def med(v): v = [x for x in v if x]; return round(st.median(v)) if v else None
print("\npreço/m² no lançamento (mediana por ano): Cyrela AP | mercado Luxo | mercado Médio Alto | Vivaz | mercado Econômico")
for a in range(2019, 2027):
    s = [d for d in P.values() if isinstance(d["lanc"], datetime.datetime) and d["lanc"].year == a]
    print(a, med([d["m2_lanc"] for d in s if d["quem"] == "Cyrela"]), med([d["m2_lanc"] for d in s if d["quem"] == "mercado" and d["padrao"] == "Luxo"]),
          med([d["m2_lanc"] for d in s if d["quem"] == "mercado" and d["padrao"] == "Médio Alto"]), med([d["m2_lanc"] for d in s if d["quem"] == "Vivaz"]),
          med([d["m2_lanc"] for d in s if d["quem"] == "mercado" and d["padrao"] == "Econômico"]))
print("\nreprecificação (preço hoje ÷ lançamento, mediana) por grupo:", {q: round(st.median([d["m2_hoje"] / d["m2_lanc"] for d in P.values() if d["quem"] == q and d["m2_lanc"] and d["m2_hoje"]]), 3) for q in ("Cyrela", "Living", "Vivaz", "mercado")})
# share de lancamentos por ano (unidades e VGV)
print("\nshare Cyrela+Living+Vivaz nos lançamentos de SP (unidades | VGV) por ano:")
SH = {}
for a in range(2019, 2027):
    s = [d for d in P.values() if isinstance(d["lanc"], datetime.datetime) and d["lanc"].year == a]
    u = sum(d["un"] for d in s); v = sum(d["vgv"] for d in s)
    uc = sum(d["un"] for d in s if d["quem"] in ("Cyrela", "Living", "Vivaz")); vc = sum(d["vgv"] for d in s if d["quem"] in ("Cyrela", "Living", "Vivaz"))
    SH[a] = {"un": int(u), "vgv": round(v / 1e9, 2), "share_un": round(uc / u * 100, 1) if u else None, "share_vgv": round(vc / v * 100, 1) if v else None}
    print(a, SH[a])
json.dump({"_meta": {"fonte": "Geoimóvel, Mercado Completo, SP capital, residencial vertical, foto de mai/2026 (uma linha por tipo; agregado por RGI)", "grupos": "Cyrela = CYRELA; Living = LIVING; Vivaz = VIVAZ RESIDENCIAL; JVs separadas"},
           "curvas": CUR, "share": SH, "n_emp": len(P)}, io.open(os.path.join(here, "_geoimovel.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
