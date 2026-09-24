# -*- coding: utf-8 -*-
"""Do lucro bruto ao caixa: reconciliação de baixo para cima (2021-2025 e LTM 2T26), versão com as quatro linhas que fecham a ponte
(pedido de 23/09/26): investimentos em JVs/SPEs/imobilizado, ajuste caixa do financeiro (variação monetária não caixa e juros/outros itens
pagos, do fluxo de caixa), minoritários e outros financiamentos, e recebível bruto (Δ provisão para distrato).
Terreno: o CPV reconhece o custo do terreno quando a unidade vira receita, mas o caixa saiu (ou sairá) em outra data; a linha
'terrenos = Δ terrenos a custo − Δ terrenos a pagar' devolve o que foi reconhecido sem ser pago no período e cobra o que foi comprado;
o resultado é o caixa da obra acima do lucro bruto quando o terreno é antigo ou a prazo.
Fontes: planilha de DFs do RI (Economatica: DRE, balanço, DFC trimestrais), notas de estoque dos ITR (_estoque_custo.json), balanço CVM
(_balanco_cvm.json), provisão para distrato (_prov_distrato_mov.json), releases (geração de caixa). R$ mi. Saída: _caixa_reconc_frag.json."""
import io, json, os, openpyxl
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0):
    v = v if abs(v) >= 0.5 * 10 ** (-d) else 0.0
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2, GR = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)", "#2e7d32"
ORD = lambda q: (int(q[2:]), int(q[0]))
# ---- planilha do RI (Economatica): DRE, balanço e DFC trimestrais
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"), read_only=True, data_only=True)
ws = wb.worksheets[0]; rows = list(ws.iter_rows(values_only=True)); hdr = rows[3]
ROW = {13: "cr_cp", 23: "cr_lp", 70: "rec", 71: "cpv", 74: "vendas", 75: "adm", 77: "outras_rec", 78: "outras_desp", 81: "fin", 86: "ir_corr", 94: "ll", 104: "dfc_varmon", 118: "dfc_outitens", 110: "dfc_naocx", 120: "dfc_capex", 124: "dfc_divrec", 134: "dfc_divpag", 135: "dfc_outfin", 131: "dfc_capital"}
E = {}
for i, c in enumerate(hdr):
    if hasattr(c, "year") and c.year >= 2010:
        q = f"{(c.month - 1) // 3 + 1}T{str(c.year)[2:]}"; E[q] = {n: (rows[r][i] / 1000 if isinstance(rows[r][i], (int, float)) else 0.0) for r, n in ROW.items()}
B = J("_balanco_cvm.json"); G = J("_ger_caixa_release_clean.json"); GH = J("_ger_caixa_hist.json")["tri"]; PD = J("_prov_distrato_mov.json")["trimestre"]
# CYREMod (_modelo_dump.tsv): 205 imóveis em construção, 206 prontos, 223 terrenos a custo, 220 terrenos a pagar; série desde 4T10 (mesma base das notas dos ITR)
_ml = io.open(os.path.join(here, "_modelo_dump.tsv"), encoding="utf-8").read().split(chr(10)); _mh = _ml[0].split(chr(9))[2].split(","); MR = {}
for _l in _ml[1:]:
    _p = _l.split(chr(9))
    if len(_p) >= 3: MR[int(_p[0])] = dict(zip(_mh, [None if x == "null" else float(x) for x in _p[2].split(",")]))
def dl(q): b = B[q]; return sum(b.get(k) or 0 for k in ("emp_cp", "deb_cp", "cri_cp", "emp_lp", "deb_lp", "cri_lp")) - sum(b.get(k) or 0 for k in ("caixa", "aplic_cp_vjr", "aplic_cp_vjora", "aplic_cp_ca", "aplic_lp_vjr", "aplic_lp_vjora", "aplic_lp_ca"))
tp = lambda q: (B[q].get("terr_cp") or 0) + (B[q].get("terr_lp") or 0); ad = lambda q: (B[q].get("adiant_cp") or 0) + (B[q].get("adiant_lp") or 0)
cr = lambda q: E[q]["cr_cp"] + E[q]["cr_lp"]; est_ex = lambda q: MR[205][q] + MR[206][q]; terr = lambda q: MR[223][q]; tp = lambda q: MR[220][q]
prov = lambda q: PD[q]["saldo"] if q in PD else (PD["1T20"]["saldo"] if ORD(q) >= (20, 1) else 0.0)   # antes de 2020 a provisão tinha outro conceito (Δ = 0)
def cia(qs):   # geração de caixa operacional da companhia: release 2020+ (ex-participações); antes, série dos releases (_ger_caixa_hist), que até 2016 era depois de dividendos (somamos de volta)
    if all(q in G["oper"] for q in qs): return sum(G["oper"][q] for q in qs)
    v = sum((GH.get(q) or 0) for q in qs)
    return v + (-flow(qs, "dfc_divpag") if int(qs[-1][2:]) <= 16 else 0)
def flow(qs, k): return sum(E[q][k] for q in qs)
def bloco(q0, qs):
    r = {"receita": flow(qs, "rec"), "cpv": -flow(qs, "cpv")}; r["lucro_bruto"] = r["receita"] + r["cpv"]
    r["d_cr"] = -(cr(qs[-1]) - cr(q0)); r["d_prov"] = -(prov(qs[-1]) - prov(q0)); r["d_est_ex"] = -(est_ex(qs[-1]) - est_ex(q0))
    r["terrenos"] = -((terr(qs[-1]) - terr(q0)) - (tp(qs[-1]) - tp(q0))); r["d_adiant"] = ad(qs[-1]) - ad(q0)
    r["sga"] = -(flow(qs, "vendas") + flow(qs, "adm")); r["impostos"] = -flow(qs, "ir_corr"); r["fin"] = flow(qs, "fin"); r["fin_cx"] = flow(qs, "dfc_varmon") + flow(qs, "dfc_outitens")
    r["outras_dre"] = flow(qs, "outras_rec") - flow(qs, "outras_desp"); r["ipo"] = -1335.0 if "3T20" in qs else 0.0   # marcação a valor justo dos IPOs de Cury, P&P e Lavvi (3T20), sem caixa: ledger _one_offs.json
    r["div_jv"] = flow(qs, "dfc_divrec"); r["invest"] = flow(qs, "dfc_capex"); r["minor"] = flow(qs, "dfc_outfin")
    r["caixa_rec"] = sum(r[k] for k in ("lucro_bruto", "d_cr", "d_prov", "d_est_ex", "terrenos", "d_adiant", "sga", "impostos", "fin", "fin_cx", "outras_dre", "ipo", "div_jv", "invest", "minor"))
    r["cia_oper"] = cia(qs); r["cia_ger"] = sum(G["ger"].get(q, 0) for q in qs); r["part"] = sum(-G["part"].get(q, 0) for q in qs)
    r["d_dl"] = -(dl(qs[-1]) - dl(q0)); r["div_pagos"] = flow(qs, "dfc_divpag"); r["ll"] = flow(qs, "ll"); r["outros"] = r["cia_oper"] - r["caixa_rec"]
    return r
Q = sorted([q for q in E if q in B and E[q]["rec"] and MR[205].get(q) is not None and MR[220].get(q) is not None], key=ORD); PER = {}
for a in range(2013, 2026):
    qs = [f"{i}T{str(a)[2:]}" for i in range(1, 5)]; q0 = f"4T{str(a - 1)[2:]}"
    if all(q in Q for q in qs) and q0 in Q: PER[str(a)] = bloco(q0, qs)
L4 = Q[-4:]; U = "LTM " + L4[-1]; PER[U] = bloco(Q[-5], L4); R = PER[U]
LAB = [("lucro_bruto", "lucro bruto (DRE)"), ("d_cr", "Δ contas a receber (balanço)"), ("d_prov", "Δ provisão p/ distrato (recebível bruto)"), ("d_est_ex", "Δ estoque a custo ex-terrenos"), ("terrenos", "terrenos: Δ a custo − Δ a pagar"), ("d_adiant", "Δ adiantamentos de clientes (permuta)"),
       ("sga", "despesas comerciais e G&A"), ("impostos", "IR/CS corrente"), ("fin", "resultado financeiro (DRE)"), ("fin_cx", "ajuste caixa do financeiro (DFC)"), ("outras_dre", "outras receitas/despesas (DRE)"), ("ipo", "marcação dos IPOs de 2020 (não caixa)"), ("div_jv", "dividendos recebidos das JVs"), ("invest", "investimentos: JVs, SPEs e imobilizado"), ("minor", "minoritários e outros financiamentos"),
       ("caixa_rec", "= caixa reconciliado"), ("cia_oper", "geração de caixa operacional (release)"), ("outros", "outros = release − reconciliado")]
# ---- svg: (1) cascata LTM; (2) reconciliado × companhia por ano
g = []; Y0, Y1 = 46, 176   # 25/09/26: 226 → 176 (viewBox 250 → 200); o slide passou de 880px com as 5 linhas de conversão/erro na tabela
steps = [(k, l) for k, l in LAB if k not in ("caixa_rec", "cia_oper", "outros")]
X0, X1 = 44, 700; n = len(steps) + 2; gw = (X1 - X0) / n; vmin, vmax = -1600, 3600; y = lambda v: Y1 - (Y1 - Y0) * (v - vmin) / (vmax - vmin)
g.append(f'<text x="{X0}" y="17" class="gtit">Do lucro bruto ao caixa, {U}, R$ mi</text><text x="{X0}" y="32" class="gsub">cascata: verde soma, vinho subtrai; barra final = caixa reconciliado contra a geração operacional do release</text>')
for t in (-1000, 0, 1000, 2000, 3000): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t)}</text>')
cum = 0.0; SHORT = {"lucro_bruto": "lucro br.", "d_cr": "Δ CR", "d_prov": "Δ prov.", "d_est_ex": "Δ obra", "terrenos": "terreno", "d_adiant": "Δ adiant.", "sga": "SG&A", "impostos": "IR", "fin": "fin. DRE", "fin_cx": "fin. cx", "outras_dre": "outras", "ipo": "IPOs 20", "div_jv": "div. JV", "invest": "invest.", "minor": "minor."}
for i, (k, l) in enumerate(steps):
    v = R[k]; x = X0 + gw * i + gw * 0.12; w = gw * 0.76
    if k == "lucro_bruto": top, base = v, 0.0
    else: top, base = cum + v, cum
    col = GR if v >= 0 else S1
    if k == "lucro_bruto": col = I2
    g.append(f'<rect x="{x:.1f}" y="{min(y(top), y(base)):.1f}" width="{w:.1f}" height="{abs(y(top) - y(base)):.1f}" fill="{col}" fill-opacity=".85"/><text x="{x + w/2:.1f}" y="{min(y(top), y(base)) - 4:.1f}" text-anchor="middle" class="axq" fill="{I2}">{fmt(v)}</text>')
    g.append(f'<text x="{x + w/2:.1f}" y="{Y1 + (11 if i % 2 == 0 else 21)}" text-anchor="middle" class="axq" opacity=".8" style="font-size:9px">{SHORT[k]}</text>')
    cum = top
for j, (k, lab, col) in enumerate((("caixa_rec", "reconc.", I2), ("cia_oper", "release", S3))):
    i = len(steps) + j; v = R[k]; x = X0 + gw * i + gw * 0.12; w = gw * 0.76
    g.append(f'<rect x="{x:.1f}" y="{min(y(v), y(0)):.1f}" width="{w:.1f}" height="{abs(y(v) - y(0)):.1f}" fill="{col}" fill-opacity=".9"/><text x="{x + w/2:.1f}" y="{min(y(v), y(0)) - 4:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(v)}</text><text x="{x + w/2:.1f}" y="{Y1 + (11 if i % 2 == 0 else 21)}" text-anchor="middle" class="axq" opacity=".8" style="font-size:9px">{lab}</text>')
g.append(f'<line x1="{X0}" y1="{y(0):.1f}" x2="{X1}" y2="{y(0):.1f}" stroke="var(--baseline)"/>')
# painel 2
anos = list(PER); Xb0, Xb1 = 790, 1090; gb = (Xb1 - Xb0) / len(anos); vmin2, vmax2 = -600, 1800; yb = lambda v: Y1 - (Y1 - Y0) * (v - vmin2) / (vmax2 - vmin2)
g.append(f'<text x="{Xb0}" y="17" class="gtit">Reconciliado × release, R$ mi por ano</text><text x="{Xb0}" y="32" class="gsub">cinza: reconciliado; dourado: release; diferença = "outros"</text>')
for t in (-500, 0, 500, 1000, 1500): g.append(f'<line x1="{Xb0}" y1="{yb(t):.1f}" x2="{Xb1}" y2="{yb(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{Xb0-6}" y="{yb(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t)}</text>')
for j, a in enumerate(anos):
    for i, (k, col, op) in enumerate((("caixa_rec", MU, .6), ("cia_oper", S3, .9))):
        v = PER[a][k]; x = Xb0 + gb * j + gb * 0.1 + i * gb * 0.4; g.append(f'<rect x="{x:.1f}" y="{min(yb(v), yb(0)):.1f}" width="{gb*0.38:.1f}" height="{abs(yb(v) - yb(0)):.1f}" fill="{col}" fill-opacity="{op}"/>')
    g.append(f'<text x="{Xb0 + gb * (j + 0.5):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{a[2:4] if a.startswith("20") else "LTM"}</text>')
g.append(f'<line x1="{Xb0}" y1="{yb(0):.1f}" x2="{Xb1}" y2="{yb(0):.1f}" stroke="var(--baseline)"/>')
svg = '<svg viewBox="0 0 1150 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela
table = ('<table class="tl compact" style="width:100%;margin-top:0;font-size:9.5px"><thead><tr><th style="text-align:left">R$ mi</th>' + "".join(f'<th style="text-align:right">{a}</th>' for a in anos) + '</tr></thead><tbody>'
         + "".join(f'<tr class="{"total" if k in ("lucro_bruto", "caixa_rec", "cia_oper") else ""}"><td>{l}</td>' + "".join(f'<td style="text-align:right">{fmt(PER[a][k])}</td>' for a in anos) + "</tr>" for k, l in LAB)
         # 24/09/26: conversão em caixa (release ÷ lucro bruto e ÷ lucro líquido) e erro da reconciliação (outros ÷ lucro bruto e ÷ lucro líquido)
         + f'<tr><td>lucro líquido (DRE, consolidado)</td>' + "".join(f'<td style="text-align:right">{fmt(PER[a]["ll"])}</td>' for a in anos) + '</tr>'
         + "".join(f'<tr style="{sty}"><td>{l}</td>' + "".join(f'<td style="text-align:right">{fmt(100 * PER[a]["cia_oper" if "conv" in k else "outros"] / PER[a][d], 0)}%</td>' for a in anos) + '</tr>'
                   for k, l, d, sty in (("conv_lb", "conversão em caixa: release ÷ lucro bruto", "lucro_bruto", "font-weight:700;color:var(--s3)"), ("conv_ll", "conversão em caixa: release ÷ lucro líquido", "ll", "font-weight:700;color:var(--s3)"), ("err_lb", "erro: outros ÷ lucro bruto", "lucro_bruto", "color:var(--muted)"), ("err_ll", "erro: outros ÷ lucro líquido", "ll", "color:var(--muted)")))
         + "</tbody></table>")
PAD = "padding:0 8px;font-size:9px"   # 25/09/26: 23 linhas a 9px e sem padding vertical na célula (o .compact fixa 10px/2px no td; o font-size da <table> não vale)
table = table.replace('<td>', f'<td style="{PAD}">').replace('style="text-align:right"', f'style="text-align:right;{PAD}"').replace('style="text-align:left"', f'style="text-align:left;{PAD}"')
num = {"u": U, "lb": R["lucro_bruto"], "cr": -R["d_cr"], "obra": -R["d_est_ex"], "terr": R["terrenos"], "sga": -R["sga"], "rec": R["caixa_rec"], "cia": R["cia_oper"], "outros": R["outros"], "invest": -R["invest"], "minor": -R["minor"], "fin_cx": R["fin_cx"],
       "outros_ano": {a: PER[a]["outros"] for a in anos}, "outros_abs_med": sum(abs(PER[a]["outros"]) for a in anos) / len(anos), "terr_2025": PER["2025"]["terrenos"], "cr_2025": -PER["2025"]["d_cr"], "obra_2025": -PER["2025"]["d_est_ex"], "lb_2025": PER["2025"]["lucro_bruto"], "cia_2025": PER["2025"]["cia_oper"],
       "ll": R["ll"], "conv_lb": 100 * R["cia_oper"] / R["lucro_bruto"], "conv_ll": 100 * R["cia_oper"] / R["ll"], "err_lb": 100 * R["outros"] / R["lucro_bruto"], "err_ll": 100 * R["outros"] / R["ll"],
       "err_lb_abs_med": sum(abs(PER[a]["outros"]) / PER[a]["lucro_bruto"] for a in anos if a[:2] == "20" and int(a[:4]) >= 2015) / len([a for a in anos if a[:2] == "20" and int(a[:4]) >= 2015]) * 100, "err_ll_abs_med": sum(abs(PER[a]["outros"]) / abs(PER[a]["ll"]) for a in anos if a[:2] == "20" and int(a[:4]) >= 2019) / len([a for a in anos if a[:2] == "20" and int(a[:4]) >= 2019]) * 100,   # desde 2019: em 2017-18 o lucro líquido foi ~0 e a razão explode
       "conv_lb_23_25": [100 * PER[a]["cia_oper"] / PER[a]["lucro_bruto"] for a in ("2023", "2024", "2025")], "conv_ll_23_25": [100 * PER[a]["cia_oper"] / PER[a]["ll"] for a in ("2023", "2024", "2025")]}
json.dump({"svg": svg, "table": table, "num": num, "per": PER, "lab": LAB}, io.open(os.path.join(here, "_caixa_reconc_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v) if isinstance(v, float) else v) for k, v in num.items() if k != "outros_ano"}); print({a: round(v) for a, v in num["outros_ano"].items()})
