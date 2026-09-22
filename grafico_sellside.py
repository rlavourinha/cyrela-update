# -*- coding: utf-8 -*-
"""Anexo sell-side: o que Itaú BBA e BTG Pactual assumem nos modelos de Cyrela e Cury, transcrito das planilhas em fontes/sellside/:
 - Itaú BBA: CYRE_Model_1Q26_IBBA.xlsx (25/05/26, TP R$ 35) e CURY_Model_2Q26_IBBA.xlsx (TP R$ 44), abas Operating, IS, BS & FCF, Valuation, SOTP.
 - BTG Pactual: Cyrela_Model_2Q26.xlsx (TP R$ 35; abas Forecasts, Income Statement, Balance Sheet, Cash Flow, TP Calculation, DCF, FCF build up;
   a casa aparece nas abas Tags) e Cury_Model_2Q26_v2.xlsx (TP R$ 48; mesmo template, sem aba Tags: atribuído ao BTG pelo template e pelo envio conjunto).
 - Consenso Bloomberg da Cury: fontes/consenso_bloomberg_cury_set26.md.
Nada aqui entra nas séries primárias do deck. Saída: _sellside_frag.json {svg, table, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
Y = ["2024", "2025", "2026E", "2027E", "2028E", "2029E", "2030E"]
# Itaú BBA · Cyrela (1Q26)
CY = {"lanc": [13.02, 18.57, 15.69, 16.28, 16.85, 17.43, 18.05], "vendas": [12.62, 13.16, 13.63, 15.27, 16.36, 17.12, 17.29], "estoque": [10.55, 16.26, 18.25, 19.25, 19.74, 20.05, 20.80],
      "rec": [7.97, 9.42, 10.02, 11.37, 12.68, 13.77, 14.75], "ll": [1.74, 2.01, 1.89, 2.36, 2.62, 2.82, 3.11], "div": [0.22, 1.39, 0.00, 0.94, 1.89, 2.10, 2.26], "roe": [19.3, 17.5, 16.5, 18.4, 19.5, 20.0, 20.9],
      "vso_lanc": [56.8, 37.5, 35.2, 35.0, 37.5, 37.5, 37.5], "vso_est": [70.7, 62.1, 63.4, 68.0, 72.0, 76.0, 76.0], "cancel": [12.7, 13.1, 14.2, 13.0, 12.7, 12.5, 12.3],
      "lanc_map": [7.66, 10.25, 6.10, 5.68, 5.86, 6.06, 6.27], "lanc_viv": [3.04, 5.41, 6.06, 6.93, 7.17, 7.42, 7.68], "ll_viv": [0.09, 0.16, 0.41, 0.59, 0.70, 0.77, 0.77]}
# BTG Pactual · Cyrela (2Q26): Forecasts / Income Statement / Balance Sheet / Cash Flow (2024 = reportado, mesma base)
BY = {"lanc": [13.02, 18.57, 17.18, 16.15, 16.88, 17.64, 18.43], "vendas": [12.62, 13.16, 14.61, 15.62, 15.89, 16.51, 17.32], "estoque": [10.55, 16.26, 18.76, 19.30, 20.28, 21.41, 22.52], "pronto": [1.51, 2.24, 2.19, 2.47, 3.03, 3.45, 3.67],
      "rec": [7.97, 9.42, 10.22, 12.22, 13.44, 14.52, 15.52], "ll": [1.74, 2.01, 1.89, 2.22, 2.36, 2.47, 2.72], "div": [0.22, 1.39, 0.50, 0.95, 1.77, 1.89, 1.98], "roe": [19.4, 18.0, 16.7, 17.5, 18.5, 18.6, 19.5], "roe_exjv": [10.7, 16.5, 13.4, 13.6, 14.3, 14.3, 15.3],
      "vso_lanc": [56.9, 37.5, 35.0, 33.4, 33.4, 33.4, 33.4], "vso_est": [70.6, 60.9, 63.5, 68.0, 68.0, 68.0, 68.0], "cancel": [12.7, 12.1, 11.4, 9.7, 9.5, 9.3, 9.2], "cr": [4.78, 6.11, 7.06, 8.91, 10.88, 11.59, 11.90], "dl_pl": [8.0, 16.0, 9.3, 12.9, 19.7, 21.5, 19.1], "fcfe": [0.74, 2.58, 1.06, -0.35, 0.09, 1.76, 2.58]}
YC = ["2023", "2024", "2025", "2026E", "2027E", "2028E", "2029E", "2030E"]
# Itaú BBA · Cury (2Q26)
CU = {"lanc": [4.44, 6.58, 8.28, 9.16, 10.53, 10.95, 11.39, 11.84], "rec": [2.89, 3.93, 5.40, 6.83, 8.25, 9.16, 9.93, 10.55], "ll": [0.48, 0.65, 0.98, 1.22, 1.53, 1.81, 1.91, 2.02],
      "cr": [1.09, 1.44, 2.16, 2.81, 3.45, 3.83, 4.15, 4.41], "div": [0.33, 0.48, 1.35, 0.70, 1.10, 1.57, 1.70, 1.79], "roe": [53.6, 63.4, 74.6, 70.8, 70.8, 72.7, 70.9, 69.1], "vso_lanc": [52.5, 56.5, 52.9, 51.5, 50, 50, 50, 50], "cancel": [11.4, 8.4, 8.7, 8.1, 8.5, 8.5, 8.5, 8.5]}
# BTG Pactual · Cury (2Q26)
BU = {"lanc": [4.44, 6.58, 8.28, 9.15, 9.59, 10.02, 10.47, 10.94], "rec": [2.89, 3.93, 5.40, 6.81, 7.78, 8.52, 9.13, 9.70], "ll": [0.48, 0.65, 0.98, 1.24, 1.53, 1.70, 1.80, 1.88], "cr": [1.09, 1.44, 2.16, 2.95, 3.16, 3.42, 3.66, 3.87],
      "div": [0.33, 0.48, 1.35, 0.71, 0.99, 1.23, 1.53, 1.62], "vso_lanc": [52.5, 56.5, 52.9, 51.5, 50, 50, 50, 50], "cancel": [11.4, 12.3, 10.6, 8.8, 8.4, 8.3, 8.2, 8.2], "pronto": [0.03, 0.03, 0.06, 0.25, 0.59, 0.89, 1.17, 1.42]}
VAL = {"cy": {"tp": 35, "ke": 16.3, "g": 3.5}, "by": {"tp": 35, "ke": 16.1, "g": 4.3}, "cu": {"tp": 44, "ke": 16.6, "g": 4.0}, "bu": {"tp": 48, "ke": 15.7, "g": 4.3}}
# ---- svg: (1) Cyrela lançamentos e vendas (IBBA barras, BTG linhas); (2) Cyrela lucro e dividendo; (3) Cury recebível de clientes
g = []; Y0, Y1 = 46, 226
def frame(X0, X1, title, sub, ymax, ticks, labels, tf=lambda t: fmt(t)):
    y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for t in ticks: g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    n = len(labels); xc = lambda i: X0 + (X1 - X0) * (i + 0.5) / n
    for i, l in enumerate(labels): g.append(f'<text x="{xc(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{l[2:4] + ("E" if l.endswith("E") else "")}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>'); return y, xc, (X1 - X0) / n
def bars(y, xc, gw, series, nact=2):
    k = len(series); bw = gw * 0.78 / k
    for i in range(len(series[0][0])):
        for j, (vals, col, op) in enumerate(series):
            x = xc(i) - gw * 0.39 + j * bw; v = vals[i]; g.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw-1:.1f}" height="{Y1-y(v):.1f}" fill="{col}" fill-opacity="{op if i < nact else op * 0.55}"/>')
def line(y, xc, vals, col, lab, d=1, dash="", dy=0):
    g.append(f'<polyline points="{" ".join(f"{xc(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))}" fill="none" stroke="{col}" stroke-width="2.2"{f" stroke-dasharray=\"{dash}\"" if dash else ""}/><text x="{xc(len(vals)-1)+8:.1f}" y="{y(vals[-1])+4+dy:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(vals[-1], d)}</text>')
y, xc, gw = frame(44, 330, "Cyrela: lançamentos e vendas, R$ bi", "barras: IBBA; tracejado: BTG; pontilhado: estoque BTG", 24, (0, 6, 12, 18, 24), Y)
bars(y, xc, gw, [(CY["lanc"], S3, .9), (CY["vendas"], S1, .9)]); line(y, xc, BY["estoque"], I2, "estoque", 1, "2 3", -8); line(y, xc, BY["lanc"], S3, "lanç. BTG", 1, "5 3", 4); line(y, xc, BY["vendas"], S1, "vendas BTG", 1, "5 3", 14)
y, xc, gw = frame(440, 700, "Cyrela: lucro e dividendo, R$ bi", "barras: IBBA; tracejado: BTG", 3.5, (0, 1, 2, 3), Y, lambda t: fmt(t, 1))
bars(y, xc, gw, [(CY["ll"], MU, .6), (CY["div"], S1, .9)]); line(y, xc, BY["ll"], I2, "lucro BTG", 2, "5 3", -6); line(y, xc, BY["div"], S1, "div. BTG", 2, "5 3", 8)
y, xc, gw = frame(800, 1080, "Cury: recebível de clientes, R$ bi", "IBBA cheia, BTG tracejada; pontilhado: estoque pronto BTG", 5, (0, 1, 2, 3, 4, 5), YC, lambda t: fmt(t, 1))
line(y, xc, CU["cr"], S1, "IBBA", 1, "", -4); line(y, xc, BU["cr"], S1, "BTG", 1, "5 3", 10); line(y, xc, BU["pronto"], I2, "pronto", 1, "2 3", 4)
svg = '<svg viewBox="0 0 1180 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: premissa × casas × este deck
def bi(v, d=1): return fmt(v, d)
rows = [("Ke / g", f"{fmt(VAL['cy']['ke'], 1)}% / {fmt(VAL['cy']['g'], 1)}%", f"{fmt(VAL['by']['ke'], 1)}% / {fmt(VAL['by']['g'], 1)}% (alvo com g 5%)", "17% / 4%", f"{fmt(VAL['cu']['ke'], 1)}% / {fmt(VAL['cu']['g'], 1)}%", f"{fmt(VAL['bu']['ke'], 1)}% / {fmt(VAL['bu']['g'], 1)}%", "—", "17% / 4%"),
        ("alvo e método", "R$ 35: 1,18x TBV 2T27, ROE 18,6%", "R$ 35: 1,28x TBV 4T26, ROE 18%", "sem alvo; P/B 1,0x", "R$ 44: 5,3x TBV, ROE 71%", "R$ 48: 6,1x TBV 3T27", "P/B 4,8x 2026E; DY 9,1%", "5,4x mercado, 5,5x justo (sl. 50)"),
        ("lançamentos 2026", f"R$ {bi(CY['lanc'][2])} bi ({fmt(100 * (CY['lanc'][2] / CY['lanc'][1] - 1), 0)}%)", f"R$ {bi(BY['lanc'][2])} bi ({fmt(100 * (BY['lanc'][2] / BY['lanc'][1] - 1), 0)}%)", "LTM 17,0 bi", f"R$ {bi(CU['lanc'][3])} bi (+{fmt(100 * (CU['lanc'][3] / CU['lanc'][2] - 1), 0)}%)", f"R$ {bi(BU['lanc'][3])} bi (+{fmt(100 * (BU['lanc'][3] / BU['lanc'][2] - 1), 0)}%)", "—", "—"),
        ("VSO lançamento / estoque (ano)", f"{fmt(CY['vso_lanc'][2], 0)}% / {fmt(CY['vso_est'][2], 0)}% → {fmt(CY['vso_est'][-1], 0)}%", f"{fmt(BY['vso_lanc'][2], 0)}% / {fmt(BY['vso_est'][2], 0)}% → {fmt(BY['vso_est'][-1], 0)}%", "estoque: 38%/ano (sl. 60)", f"{fmt(CU['vso_lanc'][3], 0)}% / n.d.", f"{fmt(BU['vso_lanc'][3], 0)}% / n.d.", "—", "45%; 25-36% sem venda direta"),
        ("distratos, % das vendas brutas", f"{fmt(CY['cancel'][2], 0)}%", f"{fmt(BY['cancel'][2], 0)}% → {fmt(BY['cancel'][-1], 0)}%", "provisão 7% do recebível (sl. 62)", f"{fmt(CU['cancel'][3], 0)}%", f"{fmt(BU['cancel'][3], 0)}%", "—", "n.d."),
        ("receita 2026E / 2027E", f"R$ {bi(CY['rec'][2])} / {bi(CY['rec'][3])} bi", f"R$ {bi(BY['rec'][2])} / {bi(BY['rec'][3])} bi", "consenso 10,1 / 11,6; 5,6 bi contratados", f"R$ {bi(CU['rec'][3])} / {bi(CU['rec'][4])} bi", f"R$ {bi(BU['rec'][3])} / {bi(BU['rec'][4])} bi", "R$ 6,8 / 8,0 bi (11 est.)", "—"),
        ("lucro 2026E / 2027E (ROE)", f"R$ {bi(CY['ll'][2], 2)} / {bi(CY['ll'][3], 2)} bi ({fmt(CY['roe'][2], 0)}% / {fmt(CY['roe'][3], 0)}%)", f"R$ {bi(BY['ll'][2], 2)} / {bi(BY['ll'][3], 2)} bi ({fmt(BY['roe'][2], 0)}% / {fmt(BY['roe'][3], 0)}%; ex-JVs 13%)", "LTM 2,04 bi; 19,5% (aj. 16,7%)", f"R$ {bi(CU['ll'][3], 2)} / {bi(CU['ll'][4], 2)} bi ({fmt(CU['roe'][3], 0)}%)", f"R$ {bi(BU['ll'][3], 2)} / {bi(BU['ll'][4], 2)} bi", "R$ 1,24 / 1,46 bi (79% / 76%)", "ROE 75% (sl. 50)"),
        ("dividendo 2026E / 2027E", f"R$ {bi(CY['div'][2], 2)} / {bi(CY['div'][3], 2)} bi", f"R$ {bi(BY['div'][2], 2)} / {bi(BY['div'][3], 2)} bi", "2025 pagou 1,39 bi (sl. 53)", f"R$ {bi(CU['div'][3], 2)} / {bi(CU['div'][4], 2)} bi", f"R$ {bi(BU['div'][3], 2)} / {bi(BU['div'][4], 2)} bi", "R$ 0,82 / 1,07 bi", "—"),
        ("recebível de clientes 2030E", "—", f"R$ {bi(BY['cr'][-1])} bi (de {bi(BY['cr'][1])}); FCFE negativo em 2027", "R$ 6,5 bi hoje (sl. 47)", f"R$ {bi(CU['cr'][-1])} bi (de {bi(CU['cr'][2])})", f"R$ {bi(BU['cr'][-1])} bi; pronto de 0,06 para {bi(BU['pronto'][-1])} bi", "não aparece", "venda direta 21% das vendas (sl. 34)"),
        ("Vivaz e sócias", "Vivaz R$ 2,5 bi (2,7x book); goodwill 385 + 113 deduzido", "só ROE ex-JVs (13,4% em 2026)", "Vivaz 2,3-3,3 bi (sl. 50); goodwill 528 + 175 (sl. 48)", "—", "—", "—", "—")]
H = ["premissa", "Itaú BBA · Cyrela", "BTG · Cyrela", "este deck", "Itaú BBA · Cury", "BTG · Cury", "Bloomberg · Cury", "este deck"]
DK = {3, 7}
table = ('<table class="tl compact" style="width:100%;margin-top:0;font-size:10.5px"><thead><tr>' + "".join(f'<th style="text-align:left{";color:var(--ink-2)" if i in DK else ""}">{h}</th>' for i, h in enumerate(H)) + '</tr></thead><tbody>'
         + "".join("<tr>" + "".join(f'<td style="{"color:var(--ink-2)" if i in DK else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows) + "</tbody></table>")
num = {"vso_est_26": CY["vso_est"][2], "vso_est_30": CY["vso_est"][-1], "btg_vso_30": BY["vso_est"][-1], "lanc_var": 100 * (CY["lanc"][2] / CY["lanc"][1] - 1), "btg_lanc_var": 100 * (BY["lanc"][2] / BY["lanc"][1] - 1), "div_26": CY["div"][2], "btg_div_26": BY["div"][2],
       "cancel_26": CY["cancel"][2], "btg_cancel_26": BY["cancel"][2], "tp": 35, "tp_cu": VAL["cu"]["tp"], "tp_bu": VAL["bu"]["tp"], "btg_cr_30": BY["cr"][-1], "btg_cr_25": BY["cr"][1], "cu_cr_30": CU["cr"][-1], "cu_cr_25": CU["cr"][2], "bu_pronto_30": BU["pronto"][-1], "btg_roe_exjv": BY["roe_exjv"][2]}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_sellside_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", num)
