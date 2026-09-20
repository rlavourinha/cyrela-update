# -*- coding: utf-8 -*-
"""Fragmento do slide 'bancos' do deck enxuto: LCI por emissor (semestral, IF.data) e o funding da Caixa (trimestral).
Saída: _bancos_frag.json {svg}. Estilo do deck (var(--s1) etc.), viewBox 1060×300, dois painéis."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
L = json.load(io.open(os.path.join(here, "_lci_emissor_semestral.json"), encoding="utf-8"))["serie"]; MS = sorted(L)
F = json.load(io.open(os.path.join(here, "_funding_emissor_trimestral.json"), encoding="utf-8"))["serie"]
H = json.load(io.open(os.path.join(here, "_funding_emissor_hab_trimestral.json"), encoding="utf-8"))["serie"]
MQ = sorted(m for m in F if m in H and H[m]["Sistema"]["hab_pf"] > 0)
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def panel(ox, w, title, sub, xs, series, ymax, xlab, lab_d=0):
    X0, X1, Y0, Y1 = ox + 44, ox + w - 96, 46, 272
    x = lambda i: X0 + (X1 - X0) * i / (len(xs) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+44}" y="17" class="gtit">{title}</text><text x="{ox+44}" y="32" class="gsub">{sub}</text>']
    for k in range(5):
        tv = ymax * k / 4; g.append(f'<line x1="{X0}" y1="{y(tv):.1f}" x2="{X1}" y2="{y(tv):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(tv)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(tv)}</text>')
    for i, m in enumerate(xs):
        lb = xlab(m)
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
    i22 = next(i for i, m in enumerate(xs) if m >= "2022-06"); g.append(f'<line x1="{x(i22):.1f}" y1="{Y0-4}" x2="{x(i22):.1f}" y2="{Y1}" stroke="var(--muted)" stroke-dasharray="2 4" opacity=".7"/><text x="{x(i22)+4:.1f}" y="{Y0+4}" class="fw-s2" fill="var(--muted)">jun/22</text>')
    ends = []
    for vals, col, wd, dash, lab in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append((vals[-1], col, lab))
    ys = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = y(v)
        for pv in ys:
            if abs(yy - pv) < 13: yy = pv + 13
        ys.append(yy); g.append(f'<circle cx="{X1:.1f}" cy="{y(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v, lab_d)}</text>')
    return "".join(g)
EM = [("Caixa", "var(--s1)", 2.8, ""), ("Bradesco", "var(--s2)", 2.0, ""), ("Itaú", "var(--s3)", 2.0, ""), ("Santander", "var(--ink)", 1.8, ""), ("Banco do Brasil", "var(--ink-2)", 1.6, "5 3"), ("Outros", "var(--muted)", 1.6, "5 3")]
p1 = panel(0, 530, "LCI por emissor, R$ bi (semestral)", "BCB IF.data, conglomerados prudenciais; Outros = sistema menos os cinco", MS, [([L[m][k] / 1000 for m in MS], c, w, d, k.replace("Banco do Brasil", "BB")) for k, c, w, d in EM], 300, lambda m: "dez/" + m[2:4] if m.endswith("-12") and int(m[:4]) % 2 == 1 else "")
cx = lambda k: [F[m]["Caixa"][k] / 1000 for m in MQ]
hab = [(H[m]["Caixa"]["hab_pf"] + H[m]["Caixa"]["hab_pj"]) / 1000 for m in MQ]
p2 = panel(530, 530, "Caixa: como o crédito habitacional é financiado, R$ bi", "BCB IF.data; carteira habitacional PF + PJ (inclui FGTS); repasses = FGTS", MQ,
           [(hab, "var(--ink)", 2.4, "", "carteira"), (cx("repasses"), "var(--s3)", 2.2, "", "FGTS"), (cx("poup"), "var(--s2)", 2.2, "", "poupança"), (cx("lci"), "var(--s1)", 2.8, "", "LCI")], 1000, lambda m: "20" + m[2:4] if m.endswith("-12") and int(m[:4]) % 2 == 1 else "")
svg = '<svg viewBox="0 0 1060 300" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + p1 + p2 + "</svg>"
num = {"caixa_lci": L[MS[-1]]["Caixa"] / 1000, "tot_lci": L[MS[-1]]["Total"] / 1000, "caixa_jun22": L["2022-06"]["Caixa"] / 1000, "tot_jun22": L["2022-06"]["Total"] / 1000, "caixa_2015": L["2015-12"]["Caixa"] / 1000, "caixa_2021": L["2021-12"]["Caixa"] / 1000, "ult": MS[-1]}
json.dump({"svg": svg, "num": num}, io.open(os.path.join(here, "_bancos_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", num)
