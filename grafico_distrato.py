# -*- coding: utf-8 -*-
"""Lei do Distrato (13.786/2018): dados para o anexo. Cury: distratos ÷ vendas brutas (planilha Fundamentos do RI, anual 2017-25 e
trimestral 2023-2T26); Cyrela: provisão para distratos no balanço (saldo, adições e reversões por trimestre, notas dos ITR,
_prov_distrato_mov.json) e a linha 'Provisão para distrato' da DRE (releases 1T23+). Saída: _distrato_frag.json {svg, num}."""
import io, json, os, re, glob
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2, GR = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)", "#2e7d32"
ORD = lambda q: (int(q[2:]), int(q[0]))
C = J("_cury_hist.json"); D = J("_prov_distrato_mov.json")["trimestre"]
cd = C["VENDAS E DISTRATOS · Distratos / Vendas Brutas"]; cd_a = {y: 100 * v for y, v in cd.items() if "T" not in y and v is not None}; cd_q = {q: 100 * v for q, v in cd.items() if "T" in q and ORD(q) >= (23, 1)}
un_d = C["VENDAS E DISTRATOS · Unidades Distratadas"]; un_v = C["VENDAS E DISTRATOS · Unidades Vendidas Brutas"]
# Cyrela: DRE, provisão para distrato (dedução da receita bruta), por trimestre
dre = {}
for f in glob.glob(os.path.join(here, "fontes", "release_[1-4]T2[3-6].txt")):
    q = re.search(r"release_(\dT\d\d)", f).group(1); t = re.sub(r"\s+", " ", io.open(f, encoding="utf-8", errors="ignore").read())
    m = re.search(r"Provisão Para Distrato (\(?-?[\d.]+\)?) ", t)
    if m: v = m.group(1); dre[q] = -float(v.strip("()").replace(".", "")) if "(" in v else float(v.replace(".", ""))
qs = sorted(D, key=ORD); qd = sorted(dre, key=ORD)
# ---- svg: painel 1 Cury % anual; painel 2 Cyrela provisão (saldo) e DRE (despesa do tri)
g = []; Y0, Y1 = 46, 196
def axis(X0, X1, title, sub, ymin, ymax, ticks, tf, xs, xlab):
    n = len(xs); x = lambda i: X0 + (X1 - X0) * i / (n - 1); y = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
    g.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for t in ticks: g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    for i, q in enumerate(xs):
        lb = xlab(q)
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    g.append(f'<line x1="{X0}" y1="{y(0) if ymin <= 0 <= ymax else Y1:.1f}" x2="{X1}" y2="{y(0) if ymin <= 0 <= ymax else Y1:.1f}" stroke="var(--baseline)"/>'); return x, y
ys = sorted(cd_a)
x, y = axis(46, 400, "Cury: distratos ÷ vendas brutas, %", "planilha Fundamentos do RI, por ano; 2T26: 9,4% do trimestre", 0, 25, (0, 5, 10, 15, 20, 25), lambda t: f"{t}%", ys, lambda q: q if int(q) % 2 == 1 else "")
pts = " ".join(f"{x(i):.1f},{y(cd_a[q]):.1f}" for i, q in enumerate(ys)); g.append(f'<polyline points="{pts}" fill="none" stroke="{GR}" stroke-width="2.6" stroke-linejoin="round"/>')
for i, q in enumerate(ys): g.append(f'<circle cx="{x(i):.1f}" cy="{y(cd_a[q]):.1f}" r="3" fill="{GR}"/><text x="{x(i):.1f}" y="{y(cd_a[q]) - 7:.1f}" text-anchor="middle" class="axq" style="font-size:9.5px" fill="{GR}">{fmt(cd_a[q])}%</text>')
# marco da lei: dez/2018 entre 2018 e 2019
xl = x(ys.index("2018")) + (x(ys.index("2019")) - x(ys.index("2018"))) * 0.95
g.append(f'<line x1="{xl:.1f}" y1="{Y0-4}" x2="{xl:.1f}" y2="{Y1}" stroke="{S1}" stroke-dasharray="3 3" opacity=".8"/><text x="{xl+4:.1f}" y="{Y0+4}" class="fw-s2" fill="{S1}">Lei 13.786 (dez/18)</text>')
x2, y2 = axis(500, 790, "Cyrela: provisão para distratos, R$ mi", "saldo no balanço (ITR) e despesa do trimestre na DRE (releases)", -120, 600, (0, 200, 400, 600), lambda t: fmt(t), qs, lambda q: "20" + q[2:] if q.startswith("1T") else "")
pts = " ".join(f"{x2(i):.1f},{y2(D[q]['saldo']):.1f}" for i, q in enumerate(qs)); g.append(f'<polyline points="{pts}" fill="none" stroke="{S1}" stroke-width="2.6" stroke-linejoin="round"/>')
g.append(f'<text x="{x2(len(qs)-1)+5:.1f}" y="{y2(D[qs[-1]]["saldo"])+4:.1f}" class="fw-t2" fill="{S1}">saldo {fmt(D[qs[-1]]["saldo"])}</text>')
bw = (x2(1) - x2(0)) * 0.6
for i, q in enumerate(qs):
    if q in dre:
        v = dre[q]; g.append(f'<rect x="{x2(i) - bw / 2:.1f}" y="{min(y2(0), y2(v)):.1f}" width="{bw:.1f}" height="{abs(y2(v) - y2(0)):.1f}" fill="{S2}" fill-opacity=".7"/>')
g.append(f'<text x="{x2(len(qs)-1)+5:.1f}" y="{y2(dre[qd[-1]])+4:.1f}" class="fw-t2" fill="{S2}">DRE {fmt(dre[qd[-1]])}</text><text x="500" y="{Y1+28}" class="axq" opacity=".8">barras: provisão (−) ou reversão (+) do trimestre na DRE</text>')
svg = '<svg viewBox="0 0 900 232" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
num = {"cury_2017": cd_a["2017"], "cury_2019": cd_a["2019"], "cury_2025": cd_a["2025"], "cury_ult": cd_a[ys[-1]], "cury_un_2025": un_d["2025"], "cury_unv_2025": un_v["2025"], "cy_saldo": D[qs[-1]]["saldo"], "cy_saldo_1T20": D[qs[0]]["saldo"], "cy_dre_ltm": sum(dre[q] for q in qd[-4:]), "cy_adic_ltm": sum(D[q]["adicoes_tri"] for q in qs[-4:]), "cy_rev_ltm": sum(D[q]["reversoes_tri"] for q in qs[-4:]), "q": qs[-1]}
json.dump({"svg": svg, "num": num}, io.open(os.path.join(here, "_distrato_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()}); print("Cury tri:", {q: round(v, 1) for q, v in cd_q.items()}); print("DRE:", dre)
