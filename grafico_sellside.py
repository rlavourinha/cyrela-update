# -*- coding: utf-8 -*-
"""Anexo sell-side: o que o Itaú BBA assume nos modelos de Cyrela (1Q26, 25/05/26, TP R$ 35) e Cury (2Q26, TP R$ 44), transcrito
das planilhas em fontes/sellside/ (abas Operating, IS, BS & FCF, Valuation, SOTP). Nada aqui entra nas séries primárias do deck.
Saída: _sellside_frag.json {svg, table, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
Y = ["2024", "2025", "2026E", "2027E", "2028E", "2029E", "2030E"]
CY = {"lanc": [13.02, 18.57, 15.69, 16.28, 16.85, 17.43, 18.05], "vendas": [12.62, 13.16, 13.63, 15.27, 16.36, 17.12, 17.29], "estoque": [10.55, 16.26, 18.25, 19.25, 19.74, 20.05, 20.80],
      "rec": [7.97, 9.42, 10.02, 11.37, 12.68, 13.77, 14.75], "ll": [1.74, 2.01, 1.89, 2.36, 2.62, 2.82, 3.11], "div": [0.22, 1.39, 0.00, 0.94, 1.89, 2.10, 2.26], "roe": [19.3, 17.5, 16.5, 18.4, 19.5, 20.0, 20.9],
      "vso_lanc": [56.8, 37.5, 35.2, 35.0, 37.5, 37.5, 37.5], "vso_est": [70.7, 62.1, 63.4, 68.0, 72.0, 76.0, 76.0], "cancel": [12.7, 13.1, 14.2, 13.0, 12.7, 12.5, 12.3], "dl_pl": [8.0, 16.0, 7.0, 3.6, 5.5, 4.7, 2.0],
      "lanc_map": [7.66, 10.25, 6.10, 5.68, 5.86, 6.06, 6.27], "lanc_viv": [3.04, 5.41, 6.06, 6.93, 7.17, 7.42, 7.68], "ll_viv": [0.09, 0.16, 0.41, 0.59, 0.70, 0.77, 0.77], "ll_map": [1.03, 1.22, 0.95, 1.24, 1.38, 1.45, 1.67]}
YC = ["2023", "2024", "2025", "2026E", "2027E", "2028E", "2029E", "2030E"]
CU = {"lanc": [4.44, 6.58, 8.28, 9.16, 10.53, 10.95, 11.39, 11.84], "vendas": [4.15, 6.16, 7.75, 8.69, 10.19, 10.59, 11.21, 11.68], "rec": [2.89, 3.93, 5.40, 6.83, 8.25, 9.16, 9.93, 10.55], "ll": [0.48, 0.65, 0.98, 1.22, 1.53, 1.81, 1.91, 2.02],
      "cr": [1.09, 1.44, 2.16, 2.81, 3.45, 3.83, 4.15, 4.41], "div": [0.33, 0.48, 1.35, 0.70, 1.10, 1.57, 1.70, 1.79], "roe": [53.6, 63.4, 74.6, 70.8, 70.8, 72.7, 70.9, 69.1], "vso_lanc": [52.5, 56.5, 52.9, 51.5, 50, 50, 50, 50], "cancel": [11.4, 8.4, 8.7, 8.1, 8.5, 8.5, 8.5, 8.5], "cf": [0] * 8}
VAL = {"cy": {"tp": 35, "px": 20.68, "ke": 16.3, "g": 3.5, "roe_est": 18.6, "ptbv": 1.18, "viv": 2.50, "viv_pb": 2.73, "stand_roe": 12.8, "stand_ptbv": 0.47, "stand_fair": 0.73, "gw_pp": 385, "gw_lv": 113},
       "cu": {"tp": 44, "px": 30.0, "ke": 16.6, "g": 4.0, "roe_est": 71.3, "ptbv": 5.34}}
# ---- svg: (1) Cyrela lançamentos × vendas × estoque; (2) Cyrela lucro e dividendos; (3) Cury receita × recebível × lucro
g = []; Y0, Y1 = 46, 226
def frame(X0, X1, title, sub, ymax, ticks, labels, tf=lambda t: fmt(t)):
    y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for t in ticks: g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    n = len(labels); xc = lambda i: X0 + (X1 - X0) * (i + 0.5) / n
    for i, l in enumerate(labels): g.append(f'<text x="{xc(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{l[2:4] + ("E" if l.endswith("E") else "")}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>'); return y, xc, (X1 - X0) / n
def bars(y, xc, gw, series):
    k = len(series); bw = gw * 0.78 / k
    for i in range(len(series[0][0])):
        for j, (vals, col, op) in enumerate(series):
            x = xc(i) - gw * 0.39 + j * bw; v = vals[i]; g.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw-1:.1f}" height="{Y1-y(v):.1f}" fill="{col}" fill-opacity="{op if i < 2 else op * 0.55}"/>')
def line(y, xc, vals, col, lab, d=1, dash=""):
    g.append(f'<polyline points="{" ".join(f"{xc(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))}" fill="none" stroke="{col}" stroke-width="2.2"{f" stroke-dasharray=\"{dash}\"" if dash else ""}/><text x="{xc(len(vals)-1)+8:.1f}" y="{y(vals[-1])+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(vals[-1], d)}</text>')
y, xc, gw = frame(44, 330, "Cyrela: lançamentos e vendas, R$ bi", "IBBA 1Q26; claras = estimativa; linha = estoque a mercado (100%)", 24, (0, 6, 12, 18, 24), Y)
bars(y, xc, gw, [(CY["lanc"], S3, .9), (CY["vendas"], S1, .9)]); line(y, xc, CY["estoque"], I2, "estoque", 1, "4 3")
y, xc, gw = frame(440, 700, "Cyrela: lucro e dividendo, R$ bi", "IBBA: dividendo zero em 2026, payout de 72% de 2028 em diante", 3.5, (0, 1, 2, 3), Y, lambda t: fmt(t, 1))
bars(y, xc, gw, [(CY["ll"], MU, .6), (CY["div"], S1, .9)]); line(y, xc, CY["ll_viv"], S2, "lucro Vivaz", 2)
y, xc, gw = frame(800, 1080, "Cury: receita, lucro e recebível, R$ bi", "IBBA 2Q26; 'client financing (direct sales)' = zero em todos os anos", 12, (0, 3, 6, 9, 12), YC)
bars(y, xc, gw, [(CU["rec"], S3, .9), (CU["ll"], MU, .6)]); line(y, xc, CU["cr"], S1, "recebível", 1)
svg = '<svg viewBox="0 0 1180 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: premissa IBBA × este deck
rows = [("Ke / g", f"{fmt(VAL['cy']['ke'], 1)}% / {fmt(VAL['cy']['g'], 1)}%", "17% / 4%", f"{fmt(VAL['cu']['ke'], 1)}% / {fmt(VAL['cu']['g'], 1)}%", "17% / 4%"),
        ("preço-alvo (1 ano) e método", f"R$ {VAL['cy']['tp']}: {fmt(VAL['cy']['ptbv'], 2)}x TBV 2T27 com ROE {fmt(VAL['cy']['roe_est'], 1)}%", "sem alvo; P/B 1,0x (0,89x ex-Cury)", f"R$ {VAL['cu']['tp']}: {fmt(VAL['cu']['ptbv'], 2)}x TBV com ROE {fmt(VAL['cu']['roe_est'], 0)}%", "5,4x de mercado, 5,5x justo (slide 50)"),
        ("lançamentos 2026", f"R$ {fmt(CY['lanc'][2], 1)} bi ({fmt(100 * (CY['lanc'][2] / CY['lanc'][1] - 1), 0)}%); alto padrão {fmt(CY['lanc_map'][2], 1)}, Vivaz {fmt(CY['lanc_viv'][2], 1)}", "não projetamos; LTM 17,0 bi", f"R$ {fmt(CU['lanc'][3], 1)} bi (+{fmt(100 * (CU['lanc'][3] / CU['lanc'][2] - 1), 0)}%)", "—"),
        ("VSO de lançamento / de estoque", f"{fmt(CY['vso_lanc'][2], 0)}% / {fmt(CY['vso_est'][2], 0)}% → {fmt(CY['vso_est'][-1], 0)}% ao ano em 2030", "estoque: 11%/tri = 38%/ano (slide 60)", f"{fmt(CU['vso_lanc'][3], 0)}% / n.d.", "45% reportada; 25-36% sem venda direta"),
        ("distratos, % das vendas brutas", f"{fmt(CY['cancel'][2], 0)}%", "provisão = 7% do recebível (slide 62)", f"{fmt(CU['cancel'][3], 0)}%", "n.d."),
        ("receita líquida 2026E / 2027E", f"R$ {fmt(CY['rec'][2], 1)} / {fmt(CY['rec'][3], 1)} bi", "consenso 10,1 / 11,6; R$ 5,6 bi contratados", f"R$ {fmt(CU['rec'][3], 1)} / {fmt(CU['rec'][4], 1)} bi", "—"),
        ("lucro 2026E / 2027E", f"R$ {fmt(CY['ll'][2], 2)} / {fmt(CY['ll'][3], 2)} bi (ROE {fmt(CY['roe'][2], 1)}% / {fmt(CY['roe'][3], 1)}%)", "LTM 2,04 bi; ROE 19,5% (ajustado 16,7%)", f"R$ {fmt(CU['ll'][3], 2)} / {fmt(CU['ll'][4], 2)} bi (ROE {fmt(CU['roe'][3], 0)}%)", "ROE 75% (slide 50)"),
        ("dividendo 2026E / 2027E", f"R$ {fmt(CY['div'][2], 2)} / {fmt(CY['div'][3], 2)} bi", "2025 pagou 1,39 bi (slide 53)", f"R$ {fmt(CU['div'][3], 2)} / {fmt(CU['div'][4], 2)} bi", "—"),
        ("Vivaz", f"lucro R$ {fmt(CY['ll_viv'][2], 2)} bi em 2026, ROE 42%; vale R$ {fmt(VAL['cy']['viv'], 1)} bi ({fmt(VAL['cy']['viv_pb'], 1)}x book)", "0,29 bi hoje; 2,3-3,3 bi (slide 50)", "—", "—"),
        ("Cyrela ex-sócias e ex-Vivaz", f"ROE {fmt(VAL['cy']['stand_roe'], 1)}%, negocia a {fmt(VAL['cy']['stand_ptbv'], 2)}x TBV, justo {fmt(VAL['cy']['stand_fair'], 2)}x", "ex-Cury: ROE 15,4%, 0,89x (slide 46)", "—", "—"),
        ("goodwill das sócias", f"deduz R$ {VAL['cy']['gw_pp']} mi (P&P) e {VAL['cy']['gw_lv']} mi (Lavvi) do book", "R$ 528 + 175 mi na nota (slide 48)", "—", "—"),
        ("venda direta / crédito ao cliente", "—", "—", "linha 'client financing' zerada; recebível de 2,2 para 4,4 bi", "21% das vendas; carteira R$ 2,2 bi (slide 34)")]
BB = {'Ke / g': '—', 'preço-alvo (1 ano) e método': 'sem alvo; P/B 4,8x e P/L 7,2x em 2026E; DY 9,1%', 'lançamentos 2026': '—', 'VSO de lançamento / de estoque': '—', 'distratos, % das vendas brutas': '—', 'receita líquida 2026E / 2027E': 'R$ 6,8 / 8,0 bi (11 estimativas)', 'lucro 2026E / 2027E': 'R$ 1,24 / 1,46 bi (ROE 79% / 76%)', 'dividendo 2026E / 2027E': 'DPS 2,66 / 3,48 = R$ 0,82 / 1,07 bi', 'Vivaz': '—', 'Cyrela ex-sócias e ex-Vivaz': '—', 'goodwill das sócias': '—', 'venda direta / crédito ao cliente': 'não aparece nas linhas do consenso'}
table = ('<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">premissa</th><th style="text-align:left">Itaú BBA · Cyrela (1Q26)</th><th style="text-align:left;color:var(--ink-2)">este deck</th><th style="text-align:left">Itaú BBA · Cury (2Q26)</th><th style="text-align:left">Bloomberg · Cury (21/09)</th><th style="text-align:left;color:var(--ink-2)">este deck</th></tr></thead><tbody>'
         + "".join(f'<tr><td>{a}</td><td>{b}</td><td style="color:var(--ink-2)">{c}</td><td>{d}</td><td>{BB.get(a, "—")}</td><td style="color:var(--ink-2)">{e}</td></tr>' for a, b, c, d, e in rows) + "</tbody></table>")
num = {"vso_est_26": CY["vso_est"][2], "vso_est_30": CY["vso_est"][-1], "lanc_26": CY["lanc"][2], "lanc_var": 100 * (CY["lanc"][2] / CY["lanc"][1] - 1), "div_26": CY["div"][2], "cancel_26": CY["cancel"][2], "viv": VAL["cy"]["viv"], "cu_cr_30": CU["cr"][-1], "cu_cr_25": CU["cr"][2], "tp": VAL["cy"]["tp"], "tp_cu": VAL["cu"]["tp"]}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_sellside_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", num)
