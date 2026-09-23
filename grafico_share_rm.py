# -*- coding: utf-8 -*-
"""Slide 'Share por região metropolitana' (23/09/26): Cury e Vivaz ÷ unidades financiadas MCMV/FGTS na RMSP, na RMRJ e no Brasil, e peso
do Rio nos lançamentos de cada uma. Dados de dados_share_rm.py (_share_rm.json). Saída: _share_rm_frag.json {svg, table, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(here, "_share_rm.json"), encoding="utf-8"))["idx"]
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S3 = "var(--s1)", "var(--s3)"
PER = ["2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026", "LTM 2T26"]
LAB = {"2026": "1S26", "LTM 2T26": "LTM"}
def sh(a, b): return 100 * a / b if a is not None and b else None
def row(k):
    v, c, t = D[k]["vivaz"], D[k]["cury"], D[k]["den"]
    return {"v_sp": v["sp"], "v_rj": v["rj"], "v_out": v["outros"], "v_tot": v["total"], "v_prj": sh(v["rj"], v["sp"] + v["rj"]), "v_rmsp": sh(v["sp"], t["rmsp"]), "v_rmrj": sh(v["rj"], t["rmrj"]), "v_br": sh(v["total"], t["br"]),
            "c_tot": c["total"], "c_sp": c["sp"], "c_rj": c["rj"], "c_prj": sh(c["rj"], c["total"]) if c["rj"] is not None else None, "c_rmsp": sh(c["sp"], t["rmsp"]), "c_rmrj": sh(c["rj"], t["rmrj"]), "c_br": sh(c["total"], t["br"]),
            "nsp": c["nsp"], "nrj": c["nrj"], "rmsp": t["rmsp"], "rmrj": t["rmrj"], "br": t["br"]}
R = {k: row(k) for k in PER}
# --- svg: quatro painéis lado a lado
def panel(ox, title, sub, cury, vivaz, ymax, step):
    w, h = 265, 250; X0, X1, Y0, Y1 = ox + 36, ox + w - 62, 44, h - 22
    x = lambda i: X0 + (X1 - X0) * i / (len(PER) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+36}" y="17" class="gtit">{title}</text><text x="{ox+36}" y="32" class="gsub">{sub}</text>']
    t = 0
    while t <= ymax + 1e-9:
        g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t)}%</text>'); t += step
    for i, k in enumerate(PER):
        if k in ("2019", "2021", "2023", "2025", "LTM 2T26"): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{LAB.get(k, k[2:])}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
    ends = []
    for vals, col, lab, dash in ((cury, S3, "Cury", ""), (vivaz, S1, "Vivaz", "")):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/>')
        last = [v for v in vals if v is not None][-1]; ends.append((last, col, lab))
    ys = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = y(v)
        for pv in ys:
            if abs(yy - pv) < 14: yy = pv + 14
        ys.append(yy); g.append(f'<circle cx="{X1:.1f}" cy="{y(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v)}%</text>')
    return "".join(g)
g = []
g.append(panel(0, "Share na RM de São Paulo", "lançadas ÷ financiadas MCMV, 39 mun.", [R[k]["c_rmsp"] for k in PER], [R[k]["v_rmsp"] for k in PER], 50, 10))
g.append(panel(265, "Share na RM do Rio", "lançadas ÷ financiadas MCMV, 22 mun.", [R[k]["c_rmrj"] for k in PER], [R[k]["v_rmrj"] for k in PER], 50, 10))
g.append(panel(530, "Peso do Rio nos lançamentos", "% das unidades lançadas em SP + RJ", [R[k]["c_prj"] for k in PER], [R[k]["v_prj"] for k in PER], 50, 10))
g.append(panel(795, "Share no Brasil", "lançadas ÷ financiadas MCMV, país", [R[k]["c_br"] for k in PER], [R[k]["v_br"] for k in PER], 5, 1))
svg = '<svg viewBox="0 0 1060 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# --- tabela
def c(v, d=0, pct=False, cls=""):
    if v is None: return f'<td style="text-align:right{cls}">—</td>'
    return f'<td style="text-align:right{cls}">{fmt(v, d)}{"%" if pct else ""}</td>'
tr = []
for k in ("2019", "2021", "2022", "2023", "2024", "2025", "2026", "LTM 2T26"):
    r = R[k]; lab = {"2026": "1S26"}.get(k, k)
    tr.append(f'<tr><td style="white-space:nowrap">{lab}</td>{c(r["c_tot"])}{c(r["c_sp"])}{c(r["c_rj"])}{c(r["c_prj"], 0, True)}{c(r["c_rmsp"], 1, True, ";color:var(--s3);font-weight:700")}{c(r["c_rmrj"], 1, True, ";color:var(--s3);font-weight:700")}{c(r["c_br"], 1, True)}'
              f'<td style="border-left:1px solid var(--grid)"></td>{c(r["v_tot"])}{c(r["v_sp"])}{c(r["v_rj"])}{c(r["v_prj"], 0, True)}{c(r["v_rmsp"], 1, True, ";color:var(--s1);font-weight:700")}{c(r["v_rmrj"], 1, True, ";color:var(--s1);font-weight:700")}{c(r["v_br"], 1, True)}</tr>')
th = lambda s, a="right": f'<th style="text-align:{a}">{s}</th>'
table = ('<table class="tl compact" style="margin-top:4px;width:100%;font-size:9.5px"><thead><tr><th></th><th colspan="7" style="text-align:center;color:var(--s3)">Cury (SP e RJ estimados pela contagem de projetos)</th><th></th><th colspan="7" style="text-align:center;color:var(--s1)">Vivaz (anexo de lançamentos, ex-P&amp;P)</th></tr>'
         '<tr>' + th("período", "left") + th("un.") + th("SP") + th("RJ") + th("peso RJ") + th("RMSP") + th("RMRJ") + th("Brasil") + '<th></th>' + th("un.") + th("SP") + th("RJ") + th("peso RJ") + th("RMSP") + th("RMRJ") + th("Brasil") + '</tr></thead><tbody>' + "".join(tr) + '</tbody></table>')
L, Y25 = R["LTM 2T26"], R["2025"]
num = {"c_rmsp": L["c_rmsp"], "c_rmrj": L["c_rmrj"], "c_br": L["c_br"], "v_rmsp": L["v_rmsp"], "v_rmrj": L["v_rmrj"], "v_br": L["v_br"], "c_prj": L["c_prj"], "v_prj": L["v_prj"],
       "c_rmrj_25": Y25["c_rmrj"], "c_rmrj_24": R["2024"]["c_rmrj"], "soma_rmsp_25": Y25["c_rmsp"] + Y25["v_rmsp"], "soma_rmrj_25": Y25["c_rmrj"] + Y25["v_rmrj"], "rmrj_25": Y25["rmrj"], "rmsp_25": Y25["rmsp"],
       "v_rmsp_20": R["2020"]["v_rmsp"], "v_rmsp_22": R["2022"]["v_rmsp"], "v_rmsp_25": Y25["v_rmsp"], "c_rj_25": Y25["c_rj"], "v_rj_25": Y25["v_rj"]}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_share_rm_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: round(v, 1) for k, v in num.items()})
