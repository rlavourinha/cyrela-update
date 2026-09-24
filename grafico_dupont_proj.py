# -*- coding: utf-8 -*-
"""ROE DuPont histórico e projetado (pedido de 24/09/26). Histórico: _dupont.json (lucro atribuível 12 m, receita 12 m, ativo e PL
médios; margem × giro × alavancagem), trimestral desde 2006. Projeção 2027-31: lucro líquido e caixa do modelo (_valuation_frag.json,
por cenário de lançamento); PL dos controladores cresce pelo lucro retido, com a Cyrela distribuindo o caixa que gera (única hipótese
consistente com o VPL); ROE = lucro ÷ PL médio; giro sobre o PL (receita ÷ PL médio), porque o modelo não projeta o ativo; a alavancagem
ativo ÷ PL fica a de 2T26 (memo). Saída: _dupont_proj_frag.json {svg, table, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0):
    v = v if abs(v) >= 0.5 * 10 ** (-d) else 0.0
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
DP = J("_dupont.json")["dados"]; VL = J("_valuation_frag.json"); E = J("_econ_trimestral.json"); B = J("_balanco_cvm.json")
H = {k: v for k, v in DP.items() if k >= "2012-12"}; HK = sorted(H)
pl0 = B["2T26"]["pl_consolidado"] - (E["2T26"].get("minor") or 0); alav0 = H[HK[-1]]["alav"]
YS = [2027, 2028, 2029, 2030, 2031]
SC = [("ltm", "+5% s/ LTM", S1, ""), ("2025", "+5% s/ 2025", S3, ""), ("lstar", "lançar o que vende", S2, ""), ("ltm+30", "LTM, Vivaz +30 pp", S1, "5 3")]
PJ = {}
for k, lab, col, dash in SC:
    d = VL["val"][k]["dre"]; prev = pl0; rows = {}
    for y in YS:
        r = d[str(y)]; ret = r["ll"] - max(r["caixa"], 0); new = prev + ret; avg = (prev + new) / 2
        rows[y] = {"rec": r["rec"], "ll": r["ll"], "caixa": r["caixa"], "ret": ret, "pl": new, "pl_med": avg, "margem": 100 * r["ll"] / r["rec"], "giro_pl": r["rec"] / avg, "roe": 100 * r["ll"] / avg, "giro": r["rec"] / (avg * alav0)}
        prev = new
    PJ[k] = rows
BASE = PJ["ltm"]
# ---- svg: painel 1 ROE histórico (12 m) + projetado por cenário; painel 2 margem e giro sobre o PL, histórico + base
def q_of(k): y, m = k[:4], int(k[5:7]); return f"{m // 3}T{y[2:]}"
xs = HK + [str(y) for y in YS]; n = len(xs)
TX = [int(k[:4]) + int(k[5:7]) / 12 for k in HK] + [float(y) + 1.0 for y in YS]   # eixo x em tempo: trimestres no histórico, anos (fim) na projeção
T0, T1 = TX[0], TX[-1]
def panel(ox, w, title, sub, series, ymin, ymax, step, unit, rm):
    X0, X1, Y0, Y1 = ox + 44, ox + w - rm, 44, 176; x = lambda i: X0 + (X1 - X0) * (TX[i] - T0) / (T1 - T0); yv = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
    g = [f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>']
    t = ymin
    while t <= ymax + 1e-9:
        g.append(f'<line x1="{X0}" y1="{yv(t):.1f}" x2="{X1}" y2="{yv(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{yv(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t, 1 if step < 1 else 0)}{unit}</text>'); t += step
    for i, k in enumerate(xs):
        lb = ("20" + k[2:4]) if (len(k) == 7 and k.endswith("-12") and int(k[:4]) % 2 == 1) else (k if len(k) == 4 and int(k) % 2 == 1 else "")
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    xl = x(len(HK) - 1); g.append(f'<line x1="{xl:.1f}" y1="{Y0}" x2="{xl:.1f}" y2="{Y1}" stroke="var(--muted)" stroke-dasharray="3 3" opacity=".6"/><text x="{xl+4:.1f}" y="{Y0+10}" class="fw-s2" fill="var(--muted)">projeção →</text>')
    g.append(f'<line x1="{X0}" y1="{yv(max(ymin, 0)):.1f}" x2="{X1}" y2="{yv(max(ymin, 0)):.1f}" stroke="var(--baseline)"/>')
    ends = []
    for vals, col, dash, lab, wd in series:
        pts = " ".join(f"{x(i):.1f},{yv(max(min(v, ymax), ymin)):.1f}" for i, v in enumerate(vals) if v is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>'); ends.append(([v for v in vals if v is not None][-1], col, lab))
    ys_ = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = yv(max(min(v, ymax), ymin))
        for pv in ys_:
            if abs(yy - pv) < 13: yy = pv + 13
        ys_.append(yy); g.append(f'<circle cx="{X1:.1f}" cy="{yv(max(min(v, ymax), ymin)):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}" style="font-size:11px">{lab} {fmt(v, 1 if step < 1 else 0)}{unit}</text>')
    return "".join(g)
g = []
roe_h = [H[k]["roe"] for k in HK]
g.append(panel(0, 560, "ROE, 12 meses, %", "lucro atribuível ÷ PL médio dos controladores; projeção distribuindo o caixa gerado", [(roe_h + [None] * 5, I2, "", "histórico", 2.4)] + [(([None] * (len(HK) - 1)) + [roe_h[-1]] + [PJ[k][y]["roe"] for y in YS], col, dash, lab, 2.0) for k, lab, col, dash in SC], -10, 30, 10, "%", 150))
mg_h = [H[k]["margem"] for k in HK]; gp_h = [H[k]["rec_ltm"] / H[k]["pl_med"] for k in HK]
g.append(panel(560, 500, "Margem líquida, % · receita ÷ PL médio, x", "as duas peças do ROE; giro sobre o PL porque o modelo não projeta o ativo", [(mg_h + [None] * 5, S3, "", "margem", 2.4), (([None] * (len(HK) - 1)) + [mg_h[-1]] + [BASE[y]["margem"] for y in YS], S3, "5 3", "margem proj.", 2.0), ([100 * v for v in gp_h] + [None] * 5, S1, "", "giro ×100", 2.4), (([None] * (len(HK) - 1)) + [100 * gp_h[-1]] + [100 * BASE[y]["giro_pl"] for y in YS], S1, "5 3", "giro proj. ×100", 2.0)], -10, 130, 20, "", 130))
svg = '<svg viewBox="0 0 1060 205" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: anos (4T13..4T25), LTM, 2027-31 base; linhas DuPont; ROE dos outros cenários
PAD = "padding:0 8px"
def c(v, d=1, s_=""): return f'<td style="text-align:right;{PAD}">{fmt(v, d)}{s_}</td>'
cols = [k for k in HK if k.endswith("-12") and int(k[:4]) >= 2013] + [HK[-1]]
lab_c = lambda k: ("LTM 2T26" if k == HK[-1] else k[:4])
rows = []
rows.append(f'<tr><td style="text-align:left;{PAD}">margem líquida, %</td>' + "".join(c(H[k]["margem"]) for k in cols) + "".join(c(BASE[y]["margem"]) for y in YS) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD}">giro: receita ÷ ativo médio, x</td>' + "".join(c(H[k]["giro"], 2) for k in cols) + "".join(c(BASE[y]["giro"], 2) for y in YS) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD}">alavancagem: ativo ÷ PL médio, x</td>' + "".join(c(H[k]["alav"], 2) for k in cols) + "".join(c(alav0, 2) for y in YS) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD}">receita ÷ PL médio, x</td>' + "".join(c(H[k]["rec_ltm"] / H[k]["pl_med"], 2) for k in cols) + "".join(c(BASE[y]["giro_pl"], 2) for y in YS) + '</tr>')
rows.append(f'<tr style="font-weight:700"><td style="text-align:left;{PAD}">ROE, % (+5% s/ LTM)</td>' + "".join(c(H[k]["roe"]) for k in cols) + "".join(c(BASE[y]["roe"]) for y in YS) + '</tr>')
for k, lab, col, dash in SC[1:]:
    rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">ROE, % · {lab}</td>' + "".join('<td></td>' for _ in cols) + "".join(c(PJ[k][y]["roe"]) for y in YS) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">lucro retido (lucro − caixa), R$ mi</td>' + "".join('<td></td>' for _ in cols) + "".join(c(BASE[y]["ret"], 0) for y in YS) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">PL controladores (média; proj.: fim), R$ mi</td>' + "".join(c(H[k]["pl_med"], 0) for k in cols) + "".join(c(BASE[y]["pl"], 0) for y in YS) + '</tr>')
table = ('<table class="tl compact" style="margin-top:2px;width:100%;font-size:9px"><thead><tr><th style="text-align:left;' + PAD + '">DuPont</th>' + "".join(f'<th style="text-align:right;{PAD}">{lab_c(k)}</th>' for k in cols) + "".join(f'<th style="text-align:right;{PAD};border-left:1px solid var(--grid)">{y}E</th>' for y in YS) + '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>')
hist_max = max(H[k]["roe"] for k in cols); hist_max_k = max(cols, key=lambda k: H[k]["roe"])
num = {"roe_ltm": H[HK[-1]]["roe"], "mg_ltm": H[HK[-1]]["margem"], "giro_ltm": H[HK[-1]]["giro"], "alav_ltm": alav0, "gp_ltm": H[HK[-1]]["rec_ltm"] / H[HK[-1]]["pl_med"],
       "roe27": BASE[2027]["roe"], "roe29": BASE[2029]["roe"], "roe31": BASE[2031]["roe"], "mg27": BASE[2027]["margem"], "gp27": BASE[2027]["giro_pl"], "gp31": BASE[2031]["giro_pl"], "ret_27_31": sum(BASE[y]["ret"] for y in YS), "pl31": BASE[2031]["pl"], "pl0": pl0,
       "roe31_lstar": PJ["lstar"][2031]["roe"], "roe31_p30": PJ["ltm+30"][2031]["roe"], "roe31_2025": PJ["2025"][2031]["roe"], "roe_max": hist_max, "roe_max_ano": hist_max_k[:4], "roe_2019": H["2019-12"]["roe"], "roe_2016": H["2016-12"]["roe"], "ke": VL["num"]["ke"]}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_dupont_proj_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in num.items()})
