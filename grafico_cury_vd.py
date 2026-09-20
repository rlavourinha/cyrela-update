# -*- coding: utf-8 -*-
"""Cury: a VSO tem venda direta dentro. Carteira gerencial (pró-soluto e venda direta, releases, 4T22-2T26), fatia estimada de venda
direta nas vendas e VSO ajustada (tira a venda direta do trimestre e devolve ao estoque a carteira de venda direta em obra), contra a
VSO reportada e a da Vivaz. Método da fatia: carteira de venda direta ≈ vendas diretas dos últimos 8 trimestres × (1 − PAGO) →
fluxo médio por trimestre = carteira ÷ (8 × (1 − PAGO)); fatia = fluxo ÷ vendas médias dos 8 trimestres. PAGO = 30% (sensibilidade na nota).
Saída: _cury_vd_frag.json {svg, table, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2, GR = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)", "#2e7d32"
ORD = lambda q: (int(q[2:]), int(q[0]))
CA = J("_cury_carteira.json")["serie"]; C = J("_cury_hist.json"); O = J("_operacional_ri.json"); L = J("_lancamentos_ri.json"); Q = O["tris"]
VL = {q: v / 1e6 for q, v in C["VENDAS E DISTRATOS · Vendas Líquidas"].items() if "T" in q}; LC = {q: v / 1e6 for q, v in C["LANÇAMENTOS · VGV (em R$ mil)"].items() if "T" in q}
EC = {q: v / 1e6 for q, v in C["ESTOQUE A VALOR DE MERCADO · VGV (em R$ mil)"].items() if "T" in q}; VSO = {q: 100 * v for q, v in C["VENDAS E DISTRATOS · VSO Líquido"].items() if "T" in q}
PAGO = 0.30; NQ = 8   # call 2T26 (Mesquita): na tabela direta o cliente paga 60% do preço durante a obra → média de ~30% pago ao longo da carteira
qs = [q for q in Q if q in CA and ORD(q) >= (23, 1)]
VD = {q: CA[q]["venda_direta"] / 1000 for q in CA}; PS = {q: CA[q]["pro_soluto"] / 1000 for q in CA}; TOT = {q: CA[q]["carteira_total"] / 1000 for q in CA}
def d_share(q):
    i = Q.index(q); vs = [VL[x] for x in Q[i - NQ + 1:i + 1] if x in VL]; return (VD[q] / (NQ * (1 - PAGO))) / (sum(vs) / len(vs))
D = {q: d_share(q) for q in qs}
VSOX = {}
for q in qs:
    q0 = Q[Q.index(q) - 1]
    if q0 in VD and q0 in EC: VSOX[q] = 100 * VL[q] * (1 - D[q]) / (EC[q0] + VD[q0] + LC[q])
# Vivaz: vendas do trimestre ÷ (estoque no fim do trimestre anterior + lançamentos), VGV 100%
mk = ("mcmv23", "mcmv1"); ss = lambda d, q: sum((d.get(k, {}).get(q) or 0) for k in mk)
VZ = {}
for q in qs:
    i = Q.index(q); v = ss(O["vendas"]["vgv100_seg"], q); l = sum((L[k].get(q) or 0) for k in ("vgv_mcmv23", "vgv_mcmv1")) / 1000; e0 = ss(O["estoque"]["vgv100_seg"], Q[i - 1]); VZ[q] = 100 * v / (e0 + l) if e0 + l else None
# ---- svg: três painéis
g = []; Y0, Y1 = 46, 226
def panel(X0, X1, title, sub, ymax, ticks, tf, series, xs):
    n = len(xs); x = lambda i: X0 + (X1 - X0) * i / (n - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for t in ticks: g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    for i, q in enumerate(xs):
        if q.startswith("4T"): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">20{q[2:]}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>'); ends = []
    for vals, col, w, dash, lab, lf in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>')
        last = [v for v in vals if v is not None][-1]; ends.append([y(last), col, f"{lab} {lf(last)}"])
    ends.sort(key=lambda e: e[0])
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 13: ends[k][0] = ends[k - 1][0] + 13
    for yy, col, lab in ends: g.append(f'<text x="{X1+5:.1f}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab}</text>')
xs = [q for q in Q if q in VD and ORD(q) >= (22, 4)]
panel(44, 255, "Carteira Cury, R$ bi", "recebível fora dos bancos, releases (gerencial)", 4, (0, 1, 2, 3, 4), lambda t: fmt(t, 1),
      [([TOT[q] for q in xs], "#2b2a26", 2.6, "", "total", lambda v: fmt(v, 1)), ([VD[q] for q in xs], S1, 2.6, "", "venda direta", lambda v: fmt(v, 1)), ([PS[q] for q in xs], S3, 2.4, "", "pró-soluto", lambda v: fmt(v, 1))], xs)
panel(410, 620, "Venda direta, % das vendas (est.)", "carteira ÷ (8 tri × 70%) ÷ vendas médias", 30, (0, 10, 20, 30), lambda t: f"{t}%",
      [([100 * D[q] for q in qs], S1, 2.6, "", "venda direta", lambda v: fmt(v) + "%")], qs)
panel(760, 955, "VSO do trimestre, %", "Cury reportada e ex-venda direta (est.); Vivaz", 60, (0, 20, 40, 60), lambda t: f"{t}%",
      [([VSO[q] for q in qs], S3, 2.6, "", "Cury", lambda v: fmt(v) + "%"), ([VSOX.get(q) for q in qs], S3, 2.2, "5 3", "Cury ex-direta", lambda v: fmt(v) + "%"), ([VZ[q] for q in qs], S1, 2.4, "", "Vivaz", lambda v: fmt(v) + "%")], qs)
svg = '<svg viewBox="0 0 1100 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela
cols = [q for q in qs if q.startswith(("2T", "4T"))]
def row(lab, f, cls="", pct=False, d=1):
    return f'<tr class="{cls}"><td>{lab}</td>' + "".join(f'<td style="text-align:right">{("—" if f(q) is None else (fmt(f(q), d) + ("%" if pct else "")))}</td>' for q in cols) + "</tr>"
table = ('<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">R$ bi</th>' + "".join(f'<th style="text-align:right">{q}</th>' for q in cols) + '</tr></thead><tbody>'
         + row("vendas líquidas do trimestre", lambda q: VL[q]) + row("carteira de venda direta", lambda q: VD[q], cls="total") + row("carteira de pró-soluto", lambda q: PS[q]) + row("venda direta, % das vendas (est.)", lambda q: 100 * D[q], pct=True, d=0)
         + row("VSO reportada (líquida)", lambda q: VSO[q], pct=True, d=0, cls="total") + row("VSO ex-venda direta (est.)", lambda q: VSOX.get(q), pct=True, d=0, cls="total") + row("VSO Vivaz, mesma base", lambda q: VZ[q], pct=True, d=0) + "</tbody></table>")
u = qs[-1]; m4 = lambda d: sum(d[q] for q in qs[-4:]) / 4
num = {"u": u, "vd": VD[u], "vd0": VD[xs[0]], "ps": PS[u], "tot": TOT[u], "d": 100 * D[u], "d0": 100 * D[qs[0]], "vso": VSO[u], "vsox": VSOX[u], "vz": VZ[u], "vso_m4": m4(VSO), "vsox_m4": m4(VSOX), "vz_m4": m4(VZ), "pago": PAGO, "nq": NQ, "x0": xs[0]}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_cury_vd_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()}); print({q: (round(VSO[q]), round(VSOX.get(q, 0)), round(VZ[q]), round(100 * D[q])) for q in qs})
