# -*- coding: utf-8 -*-
"""Sócias listadas (Cury, Plano & Plano, Lavvi): market cap desde os IPOs de set/2020 (B3 COTAHIST × ações da CVM, _cotacao_socias.json)
com as ofertas marcadas, e o book da Cyrela contra a fatia do patrimônio e o valor de mercado da fatia em 2T26.
Book: nota de investimentos do ITR 2T26 (_invest_book.json); goodwill: nota (R$ 528 mi P&P, R$ 175 mi Lavvi; R$ 756 mi em 2020);
PL e lucro das investidas: CVM (_cvm_lavvi_pp.json) e planilha da Cury (_cury_dre.json); fatias: nota do ITR (Cury 15,08%, Lavvi 28,36%,
P&P 33,60%). Vendas da Cyrela na Cury: caixa da tabela de geração de caixa dos releases (3T22 183, 2T24 56, 3T24 115, 3T25 251).
Saída: _socias_frag.json {svg, table, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
C = J("_cotacao_socias.json"); IBA = J("_invest_book.json"); IB = IBA["2T26"]; CV = J("_cvm_lavvi_pp.json"); CD = J("_cury_dre.json")["serie"]
EQ = J("_equiv_investidas_v5.json")["trimestre"]   # equivalência reconhecida pela Cyrela por investida (nota do ITR), R$ mi por trimestre
ORD = lambda q: (int(q[2:]), int(q[0]))
STK = {"CURY3": 0.1508, "PLPL3": 0.3360, "LAVV3": 0.2836}; NOME = {"CURY3": "Cury", "PLPL3": "Plano&Plano", "LAVV3": "Lavvi"}; COR = {"CURY3": S3, "PLPL3": S1, "LAVV3": S2}
BOOK = {"CURY3": IB["cury"], "PLPL3": IB["pp"], "LAVV3": IB["lavvi"]}; GW = {"CURY3": 0.0, "PLPL3": 528.0, "LAVV3": 175.0}
def acoes(t, d):   # milhões de ações: totais da B3 (GetListedSupplementCompany, set/26; sem desdobramentos desde os IPOs); Cury tinha 291,5 mi até 2025 (lucro ÷ LPA na CVM: 0,29 → 0,31 bi no 1T26)
    if t == "CURY3": return 291.5 if d < "2026-01-01" else 308.05
    return {"PLPL3": 202.91, "LAVV3": 195.43}[t]
# ---- market cap mensal (último pregão do mês)
mens = {}
for t in STK:
    px = C[t]["px"]; last = {}
    for d in sorted(px): last[d[:7]] = d
    mens[t] = {m: px[d] * acoes(t, d) / 1000 for m, d in last.items()}   # R$ bi
meses = sorted(set().union(*[set(v) for v in mens.values()]))
# PL das investidas e lucro 12m
def inv(t):   # PL dos controladores no fim, PL médio de 5 pontas, lucro atribuível 12m (mesma régua do ROE da Cyrela no deck)
    if t == "CURY3":
        qa = sorted([k for k in CD if "T" in k], key=ORD); qs = qa[-4:]; return CD[qs[-1]]["pl_ctrl"] / 1e3, sum(CD[q]["pl_ctrl"] for q in qa[-5:]) / 5e3, sum(CD[q]["ll_ctrl"] for q in qs) / 1e3   # planilha em R$ mil
    d = CV["pp" if t == "PLPL3" else "lavvi"]; qa = sorted(d, key=ORD); qs = qa[-4:]; return d[qs[-1]]["pl_ctrl"], sum(d[q]["pl_ctrl"] for q in qa[-5:]) / 5, sum(d[q]["ll_ctrl_tri"] for q in qs)
EQK = {"CURY3": "cury", "PLPL3": "pp", "LAVV3": "lavvi"}; _bq = sorted(IBA, key=ORD); _l4 = ["3T25", "4T25", "1T26", "2T26"]
EQ12 = {t: sum(EQ[q][EQK[t]] for q in _l4) for t in EQK}; BOOKM = {t: sum(IBA[q][EQK[t]] for q in _bq) / len(_bq) for t in EQK}   # equivalência 12m e book médio (5 fechamentos)
PL, PLM, LL, MC, PXU = {}, {}, {}, {}, {}
for t in STK:
    PL[t], PLM[t], LL[t] = inv(t); du = max(C[t]["px"]); PXU[t] = (du, C[t]["px"][du]); MC[t] = mens[t][max(mens[t])] * 1000
# ---- svg
g = []; Y0, Y1 = 46, 226; X0, X1 = 44, 640; n = len(meses); x = lambda i: X0 + (X1 - X0) * i / (n - 1)
ymax = 2 * (int(max(max(v.values()) for v in mens.values()) / 2) + 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
g.append(f'<text x="{X0}" y="17" class="gtit">Market cap das sócias desde o IPO, R$ bi</text><text x="{X0}" y="32" class="gsub">fechamento do mês × ações (CVM); triângulos = vendas de ações da Cury pela Cyrela (R$ mi em caixa)</text>')
for tck in range(0, ymax + 1, 2): g.append(f'<line x1="{X0}" y1="{y(tck):.1f}" x2="{X1}" y2="{y(tck):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(tck)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tck}</text>')
for i, m in enumerate(meses):
    if m.endswith("-01"): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{m[:4]}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
i0 = meses.index("2020-09"); g.append(f'<line x1="{x(i0):.1f}" y1="{Y0}" x2="{x(i0):.1f}" y2="{Y1}" stroke="{MU}" stroke-dasharray="3 3"/><text x="{x(i0)+4:.1f}" y="{Y0+10}" class="axq" fill="{I2}">IPOs (set/20)</text>')
ends = []
for t in STK:
    pts = " ".join(f"{x(meses.index(m)):.1f},{y(v):.1f}" for m, v in sorted(mens[t].items()))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{COR[t]}" stroke-width="2.4" stroke-linejoin="round"/>'); ends.append([y(mens[t][max(mens[t])]), COR[t], f"{NOME[t]} {fmt(mens[t][max(mens[t])], 1)}"])
ends.sort(key=lambda e: e[0])
for k in range(1, len(ends)):
    if ends[k][0] - ends[k - 1][0] < 13: ends[k][0] = ends[k - 1][0] + 13
for yy, col, lab in ends: g.append(f'<text x="{X1+5}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab}</text>')
for m, v in (("2022-09", 183), ("2024-06", 56), ("2024-09", 115), ("2025-09", 251)):
    if m in mens["CURY3"]:
        xi, yi = x(meses.index(m)), y(mens["CURY3"][m]); g.append(f'<polygon points="{xi:.1f},{yi-12:.1f} {xi-5:.1f},{yi-3:.1f} {xi+5:.1f},{yi-3:.1f}" fill="{S3}"/><text x="{xi:.1f}" y="{yi-16:.1f}" text-anchor="middle" class="axq" fill="{I2}">{v}</text>')
# painel 2: barras por sócia em 2T26: fatia do PL, book na Cyrela, valor de mercado da fatia
Xb0, Xb1 = 800, 1070; gw = (Xb1 - Xb0) / 3; bw = gw * 0.8 / 3; ymax2 = 1600; yb = lambda v: Y1 - (Y1 - Y0) * v / ymax2
g.append(f'<text x="{Xb0}" y="17" class="gtit">A fatia da Cyrela em 2T26, R$ mi</text><text x="{Xb0}" y="32" class="gsub">cinza: fatia do PL; cor: book na Cyrela; contorno: bolsa</text>')
for tck in (0, 400, 800, 1200, 1600): g.append(f'<line x1="{Xb0}" y1="{yb(tck):.1f}" x2="{Xb1}" y2="{yb(tck):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{Xb0-6}" y="{yb(tck)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(tck)}</text>')
MKT = {}
for j, t in enumerate(("CURY3", "PLPL3", "LAVV3")):
    fatia_pl = STK[t] * PL[t]; MKT[t] = STK[t] * MC[t]; xg = Xb0 + gw * j + gw * 0.1
    for i, (v, fill, extra) in enumerate(((fatia_pl, MU, 'fill-opacity=".5"'), (BOOK[t], COR[t], 'fill-opacity=".9"'), (MKT[t], "none", f'stroke="{COR[t]}" stroke-width="2"'))):
        vv = min(v, ymax2 * 1.5); g.append(f'<rect x="{xg + i * bw:.1f}" y="{yb(vv):.1f}" width="{bw-1:.1f}" height="{Y1-yb(vv):.1f}" fill="{fill}" {extra}/>')
        if v > ymax2: g.append(f'<text x="{xg + i * bw + bw/2:.1f}" y="{Y0-2}" text-anchor="middle" class="axq" fill="{I2}">{fmt(v)}</text>')
    g.append(f'<text x="{Xb0 + gw * (j + 0.5):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{NOME[t]}</text>')
g.append(f'<line x1="{Xb0}" y1="{Y1}" x2="{Xb1}" y2="{Y1}" stroke="var(--baseline)"/>')
svg = '<svg viewBox="0 0 1150 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela
cols = ("CURY3", "PLPL3", "LAVV3")
def row(lab, f, cls="", d=0, pct=False): return f'<tr class="{cls}"><td>{lab}</td>' + "".join(f'<td style="text-align:right">{fmt(f(t), d)}{"%" if pct else ""}</td>' for t in cols) + "</tr>"
table = ('<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">2T26, R$ mi</th>' + "".join(f'<th style="text-align:right;color:{COR[t]}">{NOME[t]} ({fmt(100 * STK[t], 1)}%)</th>' for t in cols) + '</tr></thead><tbody>'
         + row("PL da sócia (controladores)", lambda t: PL[t]) + row("fatia da Cyrela no PL", lambda t: STK[t] * PL[t]) + row("goodwill dos IPOs de 2020 ainda no book", lambda t: GW[t]) + row("book na Cyrela (nota de investimentos)", lambda t: BOOK[t], cls="total")
         + row("valor em bolsa da fatia", lambda t: MKT[t], cls="total") + row("book ÷ fatia do PL", lambda t: BOOK[t] / (STK[t] * PL[t]), d=2) + row("book ÷ valor em bolsa", lambda t: BOOK[t] / MKT[t], d=2)
         + row("ROE da sócia: lucro 12m ÷ PL médio dela", lambda t: 100 * LL[t] / PLM[t], pct=True) + row("retorno sobre o book da Cyrela: equivalência 12m ÷ book médio", lambda t: 100 * EQ12[t] / BOOKM[t], pct=True, cls="total") + "</tbody></table>")
gw_tot = sum(GW.values()); DU = J("_dupont.json")["dados"]["2026-06"]
num = {"gw_tot": gw_tot, "gw_2020": 756.0, "pp_book": BOOK["PLPL3"], "pp_mkt": MKT["PLPL3"], "pp_fatia_pl": STK["PLPL3"] * PL["PLPL3"], "lv_book": BOOK["LAVV3"], "lv_mkt": MKT["LAVV3"], "cy_book": BOOK["CURY3"], "cy_mkt": MKT["CURY3"],
       "roe_pp": 100 * LL["PLPL3"] / PLM["PLPL3"], "ret_pp": 100 * EQ12["PLPL3"] / BOOKM["PLPL3"], "roe_lv": 100 * LL["LAVV3"] / PLM["LAVV3"], "ret_lv": 100 * EQ12["LAVV3"] / BOOKM["LAVV3"], "roe_cu": 100 * LL["CURY3"] / PLM["CURY3"], "ret_cu": 100 * EQ12["CURY3"] / BOOKM["CURY3"],
       "roe_cy": DU["roe"], "roe_ex_gw": 100 * DU["ll_ltm"] / (DU["pl_med"] - gw_tot), "pl_med": DU["pl_med"], "gw_pl": 100 * gw_tot / DU["pl_med"], "mc": {t: MC[t] for t in cols}, "px": PXU, "ipo_mc": {t: mens[t].get("2020-09") for t in cols}, "exc_mkt": (BOOK["PLPL3"] - MKT["PLPL3"]) + (BOOK["LAVV3"] - MKT["LAVV3"])}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_socias_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()})
