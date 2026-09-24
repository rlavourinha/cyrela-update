# -*- coding: utf-8 -*-
"""Projeção de geração de caixa operacional 2027-2031 com as linhas da reconciliação (slide 'Do lucro bruto ao caixa'): lucro bruto,
Δ contas a receber (cenários de dias do slide de recebível), Δ estoque de obra, terrenos, SG&A, impostos, financeiro (DRE e caixa),
outras, dividendos de JVs, investimentos e minoritários (pedido de 24/09/26). Cada linha em % da receita no nível histórico escolhido;
receita cresce g ao ano a partir do LTM 2T26. Regimes de capital de giro (obra + terrenos), que são as linhas que oscilam:
(A) como 2023-LTM (obra −7,6%, terrenista financiando +10,2%); (B) neutro (0 e 0); (C) como 2019-22 (obra −6,4%, terrenos −1,8%).
Fontes: _caixa_reconc_frag.json (per: linhas por ano, R$ mi), _cr_dias_frag.json (dias, mix), _mix_stake.json. Saída: _caixa_proj_frag.json."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0):
    v = v if abs(v) >= 0.5 * 10 ** (-d) else 0.0
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2, GR = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)", "#2e7d32"
C = J("_caixa_reconc_frag.json"); P = C["per"]; N = J("_cr_dias_frag.json")["num"]; MXJ = J("_mix_stake.json")
LTM = next(k for k in P if k.startswith("LTM")); rec0 = P[LTM]["receita"]
def pct(k, ys): return sum(P[y][k] for y in ys) / sum(P[y]["receita"] for y in ys)
H1 = ["2023", "2024", "2025", LTM]; H2 = ["2019", "2021", "2022"]   # 2020 fora (IPOs das sócias)
# ---- premissas por linha (% da receita), no nível 2023-LTM salvo as de capital de giro, que variam por regime
PR = {"lucro_bruto": pct("lucro_bruto", H1), "sga": pct("sga", H1), "impostos": pct("impostos", H1), "fin": pct("fin", H1), "fin_cx": pct("fin_cx", H1), "outras_dre": pct("outras_dre", H1),
      "div_jv": pct("div_jv", H1), "invest": pct("invest", H1), "minor": pct("minor", H1), "d_adiant": pct("d_adiant", H1), "d_prov": 0.0}
REG = {"A": {"lab": "obra e terrenos como 2023-LTM", "d_est_ex": pct("d_est_ex", H1), "terrenos": pct("terrenos", H1)},
       "B": {"lab": "obra e terrenos neutros", "d_est_ex": 0.0, "terrenos": 0.0},
       "C": {"lab": "obra e terrenos como 2019-22", "d_est_ex": pct("d_est_ex", H2), "terrenos": pct("terrenos", H2)}}
# ---- recebível: mesma mecânica do slide de recebível (mix de lançamentos → receita com defasagem 15/35/35/15; Vivaz a 160 dias, resto nos dias implícitos)
MX = {int(y): v["mix_stake"] for y, v in MXJ.items()}; MX[2018] = 0.21; MX[2019] = 0.19
W = (0.0, 0.15, 0.35, 0.35, 0.15); DV = 160.0; G = 0.05; YS = list(range(2027, 2032))
def rshare(y, m): return sum(W[k] * m.get(y - k, MX[2018]) for k in range(5))
def cr_path(dpp):
    m = dict(MX)
    for y in range(2027, 2033): m[y] = MX[2026] + dpp
    out = {}; prev = N["cy_cr"]
    for y in YS:
        rec = rec0 * (1 + G) ** (y - 2026); s = rshare(y, m); d = s * DV + (1 - s) * N["dias_map"]; cr = rec * d / 365
        out[y] = {"rec": rec, "dias": d, "cr": cr, "d_cr": -(cr - prev), "share": s}; prev = cr
    return out
CRP = {"base": cr_path(0.0), "+10": cr_path(0.10), "+20": cr_path(0.20), "+30": cr_path(0.30)}
ORDER = ["lucro_bruto", "d_cr", "d_est_ex", "terrenos", "d_adiant", "sga", "impostos", "fin", "fin_cx", "outras_dre", "div_jv", "invest", "minor"]
LABEL = {"lucro_bruto": "lucro bruto", "d_cr": "Δ contas a receber", "d_est_ex": "Δ estoque de obra", "terrenos": "terrenos (Δ custo − Δ a pagar)", "d_adiant": "Δ adiantamentos", "sga": "despesas comerciais e adm.", "impostos": "IR/CS corrente", "fin": "resultado financeiro (DRE)",
         "fin_cx": "ajuste caixa do financeiro", "outras_dre": "outras receitas/despesas", "div_jv": "dividendos de JVs", "invest": "investimentos (JVs, SPEs, imobilizado)", "minor": "minoritários"}
SHORT = {"lucro_bruto": "lucro bruto", "d_cr": "recebível", "d_est_ex": "obra", "terrenos": "terrenos", "d_adiant": "adiant.", "sga": "SG&amp;A", "impostos": "IR", "fin": "fin. DRE", "fin_cx": "fin. caixa", "outras_dre": "outras", "div_jv": "div. JVs", "invest": "invest.", "minor": "minor."}
def project(reg, crk):
    R = {}
    for y in YS:
        rec = CRP[crk][y]["rec"]; r = {"receita": rec}
        for k in ORDER:
            if k == "d_cr": r[k] = CRP[crk][y]["d_cr"]
            elif k in ("d_est_ex", "terrenos"): r[k] = REG[reg][k] * rec
            else: r[k] = PR[k] * rec
        r["caixa"] = sum(r[k] for k in ORDER); R[y] = r
    return R
PJ = {(reg, crk): project(reg, crk) for reg in REG for crk in CRP}
# ---- svg: painel 1 caixa por ano e regime (mix base) + Vivaz +30 pp no regime B; painel 2 decomposição 2029 (regime B)
g = []; W1 = 520
X0, X1, Y0, Y1 = 44, W1 - 96, 44, 228; ymin, ymax = -1000, 2500
x = lambda i: X0 + (X1 - X0) * i / (len(YS) - 1 + 1); yv = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
g.append(f'<text x="{X0}" y="17" class="gtit">Caixa operacional projetado, R$ mi por ano</text><text x="{X0}" y="32" class="gsub">linhas da reconciliação em % da receita; LTM 2T26 = R$ {fmt(P[LTM]["cia_oper"])} mi (release)</text>')
for tv in range(ymin, ymax + 1, 500): g.append(f'<line x1="{X0}" y1="{yv(tv):.1f}" x2="{X1}" y2="{yv(tv):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{yv(tv)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(tv)}</text>')
g.append(f'<line x1="{X0}" y1="{yv(0):.1f}" x2="{X1}" y2="{yv(0):.1f}" stroke="var(--baseline)"/>')
xs_ = ["LTM"] + [str(y) for y in YS]
for i, lb in enumerate(xs_): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
g.append(f'<circle cx="{x(0):.1f}" cy="{yv(P[LTM]["cia_oper"]):.1f}" r="3.5" fill="{I2}"/>')
series = [("A", "base", S3, "", "A · como 2023-LTM"), ("B", "base", S1, "", "B · neutro"), ("C", "base", S2, "", "C · como 2019-22"), ("B", "+30", S1, "5 3", "B · Vivaz +30 pp")]
ends = []
for reg, crk, col, dash, lab in series:
    pts = " ".join(f"{x(i+1):.1f},{yv(PJ[(reg, crk)][y]['caixa']):.1f}" for i, y in enumerate(YS))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>'); ends.append((PJ[(reg, crk)][YS[-1]]["caixa"], col, lab))
ys_ = []
for v, col, lab in sorted(ends, reverse=True):
    yy = yv(v)
    for pv in ys_:
        if abs(yy - pv) < 14: yy = pv + 14
    ys_.append(yy); g.append(f'<circle cx="{X1:.1f}" cy="{yv(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v/1000, 1)}</text>')
# painel 2: ponte 2029, regime B, mix base
ox = W1 + 20; R29 = PJ[("B", "base")][2029]; items = [(k, R29[k]) for k in ORDER if abs(R29[k]) > 1]
bx0, bx1, by0, by1 = ox + 44, 1060 - 20, 44, 228; tot = R29["lucro_bruto"]; scale = (by1 - by0) / (max(tot, 1) * 1.15)
g.append(f'<text x="{bx0}" y="17" class="gtit">Ponte de 2029, regime neutro, R$ mi</text><text x="{bx0}" y="32" class="gsub">do lucro bruto ao caixa operacional; receita R$ {fmt(R29["receita"]/1000, 1)} bi</text>')
n = len(items) + 1; bw = (bx1 - bx0) / n * 0.72; step = (bx1 - bx0) / n; run = 0.0
def yb(v): return by1 - v * scale
for i, (k, v) in enumerate(items):
    top, bot = (run + v, run) if v >= 0 else (run, run + v); xx = bx0 + i * step
    col = S3 if k == "lucro_bruto" else (GR if v > 0 else S1)
    g.append(f'<rect x="{xx:.1f}" y="{yb(top):.1f}" width="{bw:.1f}" height="{max(yb(bot)-yb(top),1):.1f}" rx="2" fill="{col}" opacity=".85"/><text x="{xx+bw/2:.1f}" y="{yb(top)-4:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(v)}</text>')
    g.append(f'<text x="{xx+bw/2:.1f}" y="{by1+13}" text-anchor="middle" class="axq" opacity=".8" style="font-size:8.5px">{SHORT[k]}</text>'); run += v
xx = bx0 + len(items) * step; g.append(f'<rect x="{xx:.1f}" y="{yb(run):.1f}" width="{bw:.1f}" height="{max(by1-yb(run),1):.1f}" rx="2" fill="{I2}" opacity=".9"/><text x="{xx+bw/2:.1f}" y="{yb(run)-4:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(run)}</text><text x="{xx+bw/2:.1f}" y="{by1+12}" text-anchor="middle" class="axq" opacity=".8" style="font-size:8.5px">caixa</text>')
g.append(f'<line x1="{bx0}" y1="{by1}" x2="{bx1}" y2="{by1}" stroke="var(--baseline)"/>')
svg = '<svg viewBox="0 0 1060 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: linhas × (LTM, 2027, 2029, 2031 no regime B) + premissa % + caixa por regime
PAD = "padding:1px 8px"
def c(v, d=0, s=""): return f'<td style="text-align:right;{PAD}">{fmt(v, d)}{s}</td>'
rows = []
for k in ORDER:
    pr = (REG["B"][k] if k in ("d_est_ex", "terrenos") else PR.get(k)) if k != "d_cr" else None
    prem = "cenário de dias" if k == "d_cr" else f'{fmt(100 * pr, 1)}% (A {fmt(100 * REG["A"][k], 1)} / C {fmt(100 * REG["C"][k], 1)})' if k in ("d_est_ex", "terrenos") else f"{fmt(100 * pr, 1)}%"
    rows.append(f'<tr><td style="text-align:left;{PAD}">{LABEL[k]}</td><td style="text-align:right;{PAD};color:var(--muted)">{prem}</td>{c(P[LTM][k])}' + "".join(c(PJ[("B", "base")][y][k]) for y in (2027, 2029, 2031)) + '</tr>')
rows.append(f'<tr style="font-weight:700"><td style="text-align:left;{PAD}">= caixa operacional (regime B, neutro)</td><td></td>{c(P[LTM]["cia_oper"])}' + "".join(c(PJ[("B", "base")][y]["caixa"]) for y in (2027, 2029, 2031)) + '</tr>')
for reg, lab in (("A", "regime A, como 2023-LTM"), ("C", "regime C, como 2019-22")):
    rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">caixa · {lab}</td><td></td><td></td>' + "".join(c(PJ[(reg, "base")][y]["caixa"]) for y in (2027, 2029, 2031)) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">caixa · regime B com Vivaz +30 pp</td><td></td><td></td>' + "".join(c(PJ[("B", "+30")][y]["caixa"]) for y in (2027, 2029, 2031)) + '</tr>')
table = ('<table class="tl compact" style="margin-top:4px;width:100%;font-size:9.5px"><thead><tr><th style="text-align:left;' + PAD + '">R$ mi</th><th style="text-align:right;' + PAD + '">premissa, % da receita</th><th style="text-align:right;' + PAD + '">LTM 2T26</th>'
         + "".join(f'<th style="text-align:right;{PAD}">{y}E</th>' for y in (2027, 2029, 2031)) + '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>')
num = {"ltm_cia": P[LTM]["cia_oper"], "ltm_terr": P[LTM]["terrenos"], "ltm_obra": P[LTM]["d_est_ex"], "ltm_cr": P[LTM]["d_cr"], "mg": 100 * PR["lucro_bruto"], "sga": 100 * PR["sga"], "g": 100 * G,
       "A_29": PJ[("A", "base")][2029]["caixa"], "B_29": PJ[("B", "base")][2029]["caixa"], "C_29": PJ[("C", "base")][2029]["caixa"], "B30_29": PJ[("B", "+30")][2029]["caixa"], "A_31": PJ[("A", "base")][2031]["caixa"], "B_31": PJ[("B", "base")][2031]["caixa"], "C_31": PJ[("C", "base")][2031]["caixa"], "B30_31": PJ[("B", "+30")][2031]["caixa"],
       "B_27": PJ[("B", "base")][2027]["caixa"], "cr_27": PJ[("B", "base")][2027]["d_cr"], "cr_31": PJ[("B", "base")][2031]["d_cr"], "terrA": 100 * REG["A"]["terrenos"], "terrC": 100 * REG["C"]["terrenos"], "obraA": 100 * REG["A"]["d_est_ex"], "obraC": 100 * REG["C"]["d_est_ex"],
       "soma_B_27_31": sum(PJ[("B", "base")][y]["caixa"] for y in YS), "soma_A_27_31": sum(PJ[("A", "base")][y]["caixa"] for y in YS), "soma_C_27_31": sum(PJ[("C", "base")][y]["caixa"] for y in YS), "soma_B30_27_31": sum(PJ[("B", "+30")][y]["caixa"] for y in YS),
       "cia_23_25": [P[y]["cia_oper"] for y in ("2023", "2024", "2025")]}
json.dump({"svg": svg, "table": table, "num": num, "proj": {f"{r}|{k}": {str(y): v for y, v in d.items()} for (r, k), d in PJ.items()}}, io.open(os.path.join(here, "_caixa_proj_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()})
