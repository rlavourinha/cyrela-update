# -*- coding: utf-8 -*-
"""Cury × Vivaz: velocidade de venda (Geoimóvel, SP capital, % vendido por idade do lançamento), VSO 12 meses (RI de cada uma) e
ticket médio lançado (RI). Saída: _cury_vivaz_frag.json {svg, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
G = json.load(io.open(os.path.join(here, "_geoimovel.json"), encoding="utf-8"))["curvas"]
O = json.load(io.open(os.path.join(here, "_operacional_ri.json"), encoding="utf-8")); L = json.load(io.open(os.path.join(here, "_lancamentos_ri.json"), encoding="utf-8"))
C = json.load(io.open(os.path.join(here, "_cury_hist.json"), encoding="utf-8"))
ORD = lambda q: (int(q[2:]), int(q[0])); Q = O["tris"]
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
# --- VSO trimestral (20/09/26: o usuário prefere a VSO do trimestre à de 12 meses). Cury: VSO líquida do trimestre (RI).
# Vivaz (MCMV 2 e 3 + Faixa 1): vendas do trimestre ÷ (estoque a valor de mercado no fim do trimestre anterior + lançamentos do trimestre), VGV 100%, bruta
mk = ["mcmv23", "mcmv1"]; lk = ["vgv_mcmv23", "vgv_mcmv1"]
def ss(d, q): return sum((d.get(k, {}).get(q) or 0) for k in mk)
VZ = {}
for i, q in enumerate(Q):
    if i < 1 or ORD(q) < (19, 2): continue   # 1T19 = primeiro trimestre pro forma ex-Cury; o estoque de 4T18 ainda inclui a Cury (VSO de 9% é artefato)
    v = ss(O["vendas"]["vgv100_seg"], q); l = sum((L[k].get(q) or 0) for k in lk) / 1000; e0 = ss(O["estoque"]["vgv100_seg"], Q[i - 1])
    VZ[q] = 100 * v / (e0 + l) if e0 + l else None
CU = {q: 100 * v for q, v in C["VENDAS E DISTRATOS · VSO Líquido"].items() if "T" in q and ORD(q) >= (19, 2)}
QV = [q for q in Q if q in VZ]
# --- ticket médio lançado por ano (R$ mil por unidade)
ct = {y: v for y, v in C["LANÇAMENTOS · Preço médio por unidade (em R$ mil)"].items() if "T" not in y}
vt = {}
for y in range(2017, 2026):
    yy = str(y)[2:]; v = sum(L["vgv_mcmv23"].get(f"{k}T{yy}") or 0 for k in range(1, 5)); u = sum(L["un_mcmv23"].get(f"{k}T{yy}") or 0 for k in range(1, 5)); vt[str(y)] = v / u if u else None
YS = [str(y) for y in range(2017, 2026)]
# --- svg: três painéis
g = []
# painel 1: curva Geoimóvel
X0, X1, Y0, Y1 = 44, 330, 46, 232; FX = ["0-6", "6-12", "12-24", "24-36", "36-60"]
x = lambda i: X0 + (X1 - X0) * (i + 0.5) / len(FX); y = lambda v: Y1 - (Y1 - Y0) * v / 100
g.append(f'<text x="{X0}" y="17" class="gtit">Velocidade de venda em SP capital</text><text x="{X0}" y="32" class="gsub">Geoimóvel, mai/26: % vendido por idade do lançamento (meses)</text>')
for t in (0, 25, 50, 75, 100): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
for i, f in enumerate(FX): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{f}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
ser = [("cury", S3, 2.8, "", "Cury"), ("vivaz", S1, 2.8, "", "Vivaz"), ("pp", S2, 1.8, "4 3", "Plano&Plano"), ("mercado_econ", MU, 1.8, "4 3", "mercado econômico")]
for key, col, w, dash, lab in ser:
    pts = " ".join(f"{x(i):.1f},{y(G[key][i]['pct']):.1f}" for i in range(len(FX)))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>')
    for i in (0, 1):
        if key in ("cury", "vivaz"): g.append(f'<text x="{x(i):.1f}" y="{y(G[key][i]["pct"]) + (14 if key == "vivaz" or G[key][i]["pct"] > 95 else -6):.1f}" text-anchor="middle" class="fw-t2" fill="{col}">{fmt(G[key][i]["pct"])}%</text>')
lg = 0
for key, col, w, dash, lab in ser:
    g.append(f'<rect x="{X0+lg}" y="{Y1+22}" width="10" height="3" fill="{col}"/><text x="{X0+lg+13}" y="{Y1+26}" class="axq" opacity=".85">{lab}</text>'); lg += 24 + 6.2 * len(lab)
# painel 2: VSO 12m
X0, X1 = 410, 672; xq = lambda i: X0 + (X1 - X0) * i / (len(QV) - 1)
g.append(f'<text x="{X0}" y="17" class="gtit">VSO do trimestre, %</text><text x="{X0}" y="32" class="gsub">Cury: RI, líquida; Vivaz: vendas ÷ (estoque inicial + lançamentos)</text>')
y = lambda v: Y1 - (Y1 - Y0) * v / 60   # painel 2: escala 0-60%
for t in (0, 20, 40, 60): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
for i, q in enumerate(QV):
    if q.startswith("4T"): g.append(f'<text x="{xq(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">20{q[2:]}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
for d, col, lab in ((CU, S3, "Cury"), (VZ, S1, "Vivaz")):
    pts = " ".join(f"{xq(i):.1f},{y(d[q]):.1f}" for i, q in enumerate(QV) if d.get(q) is not None)
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linejoin="round"/>')
    v = d[QV[-1]]; g.append(f'<circle cx="{X1}" cy="{y(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{y(v)+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v)}%</text>')
# painel 3: ticket
X0, X1 = 780, 980; xy_ = lambda i: X0 + (X1 - X0) * i / (len(YS) - 1); yt = lambda v: Y1 - (Y1 - Y0) * v / 400
g.append(f'<text x="{X0}" y="17" class="gtit">Ticket médio lançado, R$ mil</text><text x="{X0}" y="32" class="gsub">VGV lançado ÷ unidades, por ano (RI)</text>')
for t in (0, 100, 200, 300, 400): g.append(f'<line x1="{X0}" y1="{yt(t):.1f}" x2="{X1}" y2="{yt(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{yt(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}</text>')
for i, yv in enumerate(YS):
    if int(yv) % 2 == 1: g.append(f'<text x="{xy_(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{yv}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
for d, col, lab, dy in ((ct, S3, "Cury", -4), (vt, S1, "Vivaz", 8)):
    pts = " ".join(f"{xy_(i):.1f},{yt(d[yv]):.1f}" for i, yv in enumerate(YS) if d.get(yv))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linejoin="round"/>')
    v = d[YS[-1]]; g.append(f'<circle cx="{X1}" cy="{yt(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yt(v)+dy:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v)}</text>')
svg = '<svg viewBox="0 0 1060 272" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
num = {"cury_0_6": G["cury"][0]["pct"], "vivaz_0_6": G["vivaz"][0]["pct"], "cury_6_12": G["cury"][1]["pct"], "vivaz_6_12": G["vivaz"][1]["pct"], "vivaz_12_24": G["vivaz"][2]["pct"], "cury_12_24": G["cury"][2]["pct"],
       "vso_cury": CU[QV[-1]], "vso_vivaz": VZ[QV[-1]], "vso_vivaz_4T22": VZ["4T22"], "vso_cury_med": sum(CU[q] for q in QV[-4:]) / 4, "vso_vivaz_med": sum(VZ[q] for q in QV[-4:]) / 4, "ticket_cury": ct["2025"], "ticket_vivaz": vt["2025"], "n_cury": sum(r["n"] for r in G["cury"]), "n_vivaz": sum(r["n"] for r in G["vivaz"])}
json.dump({"svg": svg, "num": num}, io.open(os.path.join(here, "_cury_vivaz_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: round(v, 1) for k, v in num.items()})
