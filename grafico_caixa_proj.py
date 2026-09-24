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
# ---- lançamentos (VGV 100%, RI) → receita e obra (24/09/26, três cenários do usuário)
LR = J("_lancamentos_ri.json")
def lan(y): return sum(LR["vgv_total"].get(f"{i}T{str(y)[2:]}") or 0 for i in range(1, 5)) / 1000
LY = {y: lan(y) for y in range(2013, 2026)}; LY[2026] = sum(LR["vgv_total"].get(q) or 0 for q in ("3T25", "4T25", "1T26", "2T26")) / 1000   # 2026 = LTM 2T26
WL = (0.0, 0.15, 0.35, 0.35, 0.15)   # receita do ano t ← lançamentos t−1..t−4 (ciclo de 39 meses)
def lagL(y, L): return sum(WL[k] * L.get(y - k, LY[2013]) for k in range(5))
FREC = rec0 / lagL(2026, LY)   # LTM: receita ÷ regra de defasagem = ~0,81 (vendas de 2025-26 mais lentas); 2020-25 a razão foi ~1,0
# estoque de obra a custo ÷ média de 3 anos de lançamentos: 0,25-0,30 em 2021-26 (nota de estoque dos ITR × RI); Δ estoque de obra = −β × Δ média
ml = io.open(os.path.join(here, "_modelo_dump.tsv"), encoding="utf-8").read().split(chr(10)); mh = ml[0].split(chr(9))[2].split(","); MR = {}
for l in ml[1:]:
    pp_ = l.split(chr(9))
    if len(pp_) >= 3: MR[int(pp_[0])] = dict(zip(mh, [None if x == "null" else float(x) for x in pp_[2].split(",")]))
def est(q): return MR[205][q] + MR[206][q]   # R$ mi, mesma unidade dos lançamentos
def avg3(y, L): return sum(L.get(y - k, LY[2013]) for k in range(3)) / 3
BETA = est("2T26") / avg3(2026, LY)   # razão atual (0,25; 2023-25: 0,25-0,30), ancorada no estoque real de 2T26 para a Δ começar de zero
G = 0.05; YS = list(range(2027, 2032))
def path(kind):
    L = dict(LY)
    if kind == "ltm":   # +5% a partir do LTM 2T26
        for y in range(2027, 2033): L[y] = L[2026] * (1 + G) ** (y - 2026)
    elif kind == "2025":   # +5% a partir de 2025 (2026 = LTM já observado; 2027 = 2025 × 1,05²)
        for y in range(2027, 2033): L[y] = LY[2025] * (1 + G) ** (y - 2025)
    elif kind == "corte":   # −30% em 2027 (entre o −15% do Itaú BBA para 2026 e o −50% de 2015-16), 2028 estável, depois +5%
        L[2027] = L[2026] * 0.70; L[2028] = L[2027]
        for y in range(2029, 2033): L[y] = L[y - 1] * (1 + G)
    return L
SC = {"ltm": ("+5% sobre o LTM", "ltm"), "2025": ("+5% sobre 2025", "2025"), "corte": ("−30% em 2027, depois +5%", "corte")}
LP = {k: path(v[1]) for k, v in SC.items()}
# ---- recebível: mix de lançamentos → receita com defasagem 15/35/35/15; Vivaz a 160 dias, resto nos dias implícitos (mix base 32%)
MX = {int(y): v["mix_stake"] for y, v in MXJ.items()}; MX[2018] = 0.21; MX[2019] = 0.19
W = (0.0, 0.15, 0.35, 0.35, 0.15); DV = 160.0
def rshare(y, m): return sum(W[k] * m.get(y - k, MX[2018]) for k in range(5))
def cr_path(rec_by_y, dpp=0.0):
    m = dict(MX)
    for y in range(2027, 2033): m[y] = MX[2026] + dpp
    out = {}; prev = N["cy_cr"]
    for y in YS:
        rec = rec_by_y[y]; s = rshare(y, m); d = s * DV + (1 - s) * N["dias_map"]; cr = rec * d / 365
        out[y] = {"rec": rec, "dias": d, "cr": cr, "d_cr": -(cr - prev), "share": s}; prev = cr
    return out
ORDER = ["lucro_bruto", "d_cr", "d_est_ex", "terrenos", "d_adiant", "sga", "impostos", "fin", "fin_cx", "outras_dre", "div_jv", "invest", "minor"]
LABEL = {"lucro_bruto": "lucro bruto", "d_cr": "Δ contas a receber", "d_est_ex": "Δ estoque de obra", "terrenos": "terrenos (Δ custo − Δ a pagar)", "d_adiant": "Δ adiantamentos", "sga": "despesas comerciais e adm.", "impostos": "IR/CS corrente", "fin": "resultado financeiro (DRE)",
         "fin_cx": "ajuste caixa do financeiro", "outras_dre": "outras receitas/despesas", "div_jv": "dividendos de JVs", "invest": "investimentos (JVs, SPEs, imobilizado)", "minor": "minoritários"}
SHORT = {"lucro_bruto": "lucro bruto", "d_cr": "recebível", "d_est_ex": "obra", "terrenos": "terrenos", "d_adiant": "adiant.", "sga": "SG&amp;A", "impostos": "IR", "fin": "fin. DRE", "fin_cx": "fin. caixa", "outras_dre": "outras", "div_jv": "div. JVs", "invest": "invest.", "minor": "minor."}
LAND, CASH = 0.18, 0.50   # terreno do alto padrão ~18% do VGV (slide de premissas do MAP); regime "caixa": metade paga no ano do lançamento; 2013 (compra em caixa) a linha foi −12% dos lançamentos, 2019-22 (permuta/prazo) −1% a −2%
# cronograma de terrenos a pagar (nota do ITR 2T26, R$ mi): circulante 1.208 (até jun/27), 650 (12-24 m), 591 (24-36), 647 (36-48), 73 (48-60), 18 além; metade de cada balde cai em cada ano-calendário
SCHED = {2027: 0.5 * 1207.658 + 0.5 * 649.862, 2028: 0.5 * 649.862 + 0.5 * 591.17, 2029: 0.5 * 591.17 + 0.5 * 646.569, 2030: 0.5 * 646.569 + 0.5 * 73.305, 2031: 0.5 * 73.305 + 18.376}
def NL(y, L, dpp): return LAND * (1 - (MX[2026] + dpp)) * L[y + 1] if y + 1 in L and y >= 2027 else 0.0   # terreno comprado em t para os lançamentos de t+1 (landbank de um ano)
def project(sk, dpp=0.0, land="permuta"):
    L = LP[sk]; RECY = {y: FREC * lagL(y, L) for y in YS}; CRP = cr_path(RECY, dpp); R = {}; e_prev = est("2T26")
    for y in YS:
        rec = RECY[y]; r = {"receita": rec, "lanc": L[y]}
        e_now = BETA * avg3(y, L)
        for k in ORDER:
            if k == "d_cr": r[k] = CRP[y]["d_cr"]
            elif k == "d_est_ex": r[k] = -(e_now - e_prev)
            elif k == "terrenos": r[k] = 0.0 if land == "permuta" else LAND * (1 - CRP[y]["share"]) * rec - (SCHED.get(y, 0.0) + CASH * NL(y, L, dpp) + (1 - CASH) * NL(y - 2, L, dpp))   # em caixa: (+) terreno no CPV (18% da receita MAP) (−) parcelas da nota do ITR sem reposição a prazo, (−) terreno dos lançamentos de t+1 metade à vista, metade em dois anos
            else: r[k] = PR[k] * rec
        r["caixa"] = sum(r[k] for k in ORDER); r["dias"] = CRP[y]["dias"]; r["estoque"] = e_now; R[y] = r; e_prev = e_now
    return R
PJ = {k: project(k) for k in SC}; PJ["ltm+30"] = project("ltm", 0.30)
for k in list(SC): PJ[k + "|caixa"] = project(k, 0.0, "caixa")
PJ["ltm+30|caixa"] = project("ltm", 0.30, "caixa")
# ---- svg: painel 1 lançamentos por cenário; painel 2 caixa operacional por cenário; painel 3 ponte 2029 (cenário LTM)
g = []
COL = {"ltm": S1, "2025": S3, "corte": S2, "ltm+30": S1}
def lines_panel(ox, w, title, sub, series, ymin, ymax, step, unit="", rm=96, lm=44, tl=None):   # 24/09/26: Y0 a 50 (o "3.000" do eixo encostava no subtítulo); lm parametrizado
    X0, X1, Y0, Y1 = ox + lm, ox + w - rm, 46, 172   # 25/09/26: 50/183 → 46/172 (viewBox 208 → 193; o slide passou de 720 com as linhas de terreno em caixa)
    xs_ = ["LTM"] + [str(y) for y in YS]; x = lambda i: X0 + (X1 - X0) * i / (len(xs_) - 1); yv = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
    tx = ox + (lm if tl is None else tl); gg = [f'<text x="{tx}" y="17" class="gtit">{title}</text><text x="{tx}" y="32" class="gsub">{sub}</text>']
    tv = ymin
    while tv <= ymax + 1e-9:
        gg.append(f'<line x1="{X0}" y1="{yv(tv):.1f}" x2="{X1}" y2="{yv(tv):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{yv(tv)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(tv)}</text>'); tv += step
    for i, lb in enumerate(xs_): gg.append(f'<text x="{x(i):.1f}" y="{Y1+13}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    gg.append(f'<line x1="{X0}" y1="{yv(max(ymin, 0)):.1f}" x2="{X1}" y2="{yv(max(ymin, 0)):.1f}" stroke="var(--baseline)"/>')
    ends = []
    for vals, col, dash, lab in series:
        pts = " ".join(f"{x(i):.1f},{yv(v):.1f}" for i, v in enumerate(vals) if v is not None)
        gg.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>'); ends.append((vals[-1], col, lab))
    ys_ = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = yv(v)
        for pv in ys_:
            if abs(yy - pv) < 13: yy = pv + 13
        ys_.append(yy); gg.append(f'<circle cx="{X1:.1f}" cy="{yv(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}" style="font-size:11px">{lab} {fmt(v, 1) if abs(v) < 100 else fmt(v)}</text>')
    return "".join(gg)
LAB_S = {"ltm": "+5% s/ LTM", "2025": "+5% s/ 2025", "corte": "corte −30%", "ltm+30": "LTM, Vivaz +30 pp"}
LAB_TC = {"ltm": "LTM, terr. caixa", "corte": "corte, terr. caixa"}   # 25/09/26: rótulos curtos das tracejadas (os longos invadiam o painel 3)
# 24/09/26: painel 1 (3 linhas) a 280 de largura e painel 2 com margem para os rótulos de fim de linha (que invadiam o eixo do vizinho); painel 3 a 410
g.append(lines_panel(0, 280, "Lançamentos, R$ bi (VGV 100%)", "LTM 2T26 = R$ " + fmt(LY[2026] / 1000, 1) + " bi; 2025 = " + fmt(LY[2025] / 1000, 1),
    [([LY[2026] / 1000] + [LP[k][y] / 1000 for y in YS], COL[k], "", LAB_S[k]) for k in ("2025", "ltm", "corte")], 0, 25, 5, rm=98, lm=30, tl=12))
g.append(lines_panel(280, 370, "Caixa operacional, R$ mi por ano", "sólido: permuta; tracejado: metade do terreno MAP em caixa",
    [([P[LTM]["cia_oper"]] + [PJ[k][y]["caixa"] for y in YS], COL[k], "", LAB_S[k]) for k in ("2025", "ltm", "corte")] + [([P[LTM]["cia_oper"]] + [PJ[k + "|caixa"][y]["caixa"] for y in YS], COL[k], "5 3", LAB_TC[k]) for k in ("ltm", "corte")], -500, 3000, 500, rm=152))
# ponte 2029, cenário LTM: valores dos negativos abaixo da barra, rótulos do eixo em duas alturas (14 colunas em 27 px cada)
ox = 650; R29 = PJ["ltm"][2029]; items = [(k, R29[k]) for k in ORDER if abs(R29[k]) > 1]
bx0, bx1, by0, by1 = ox + 22, 1060 - 6, 46, 172; tot = R29["lucro_bruto"]; scale = (by1 - by0) / (max(tot, 1) * 1.15)
g.append(f'<text x="{bx0}" y="17" class="gtit">Ponte de 2029, +5% s/ LTM, R$ mi</text><text x="{bx0}" y="32" class="gsub">receita R$ {fmt(R29["receita"]/1000, 1)} bi; do lucro bruto ao caixa</text>')
n = len(items) + 1; bw = (bx1 - bx0) / n * 0.72; step = (bx1 - bx0) / n; run = 0.0
def yb(v): return by1 - v * scale
def xlab(i, k): return f'<text x="{bx0 + i * step + bw/2:.1f}" y="{by1 + (10 if i % 2 == 0 else 18)}" text-anchor="middle" class="axq" opacity=".8" style="font-size:8.5px">{k}</text>'
for i, (k, v) in enumerate(items):
    top, bot = (run + v, run) if v >= 0 else (run, run + v); xx = bx0 + i * step
    col = S3 if k == "lucro_bruto" else (GR if v > 0 else S1); ty = yb(top) - 3.5 if v >= 0 else yb(bot) + 9.5
    g.append(f'<rect x="{xx:.1f}" y="{yb(top):.1f}" width="{bw:.1f}" height="{max(yb(bot)-yb(top),1):.1f}" rx="2" fill="{col}" opacity=".85"/><text x="{xx+bw/2:.1f}" y="{ty:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}" style="font-size:8.5px">{fmt(v)}</text>')
    g.append(xlab(i, SHORT[k])); run += v
xx = bx0 + len(items) * step; g.append(f'<rect x="{xx:.1f}" y="{yb(run):.1f}" width="{bw:.1f}" height="{max(by1-yb(run),1):.1f}" rx="2" fill="{I2}" opacity=".9"/><text x="{xx+bw/2:.1f}" y="{yb(run)-3.5:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}" style="font-size:8.5px">{fmt(run)}</text>' + xlab(len(items), "caixa"))
g.append(f'<line x1="{bx0}" y1="{by1}" x2="{bx1}" y2="{by1}" stroke="var(--baseline)"/>')
svg = '<svg viewBox="0 0 1060 193" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: cenário LTM linha a linha (LTM, 2027, 2029, 2031) + caixa dos outros cenários
PAD = "padding:0 8px;font-size:9px"   # 25/09/26: 22 linhas; 9px na célula (o .compact fixa 10px no td, o font-size da <table> não vale)
def c(v, d=0, s=""): return f'<td style="text-align:right;{PAD}">{fmt(v, d)}{s}</td>'
YT = (2027, 2029, 2031); rows = []
rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">lançamentos, R$ mi (VGV 100%)</td><td style="text-align:right;{PAD};color:var(--muted)">+5% s/ LTM</td>{c(LY[2026])}' + "".join(c(PJ["ltm"][y]["lanc"]) for y in YT) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">receita, R$ mi</td><td style="text-align:right;{PAD};color:var(--muted)">{fmt(100 * FREC, 0)}% × lançamentos t−1..t−4 (15/35/35/15)</td>{c(rec0)}' + "".join(c(PJ["ltm"][y]["receita"]) for y in YT) + '</tr>')
for k in ORDER:
    prem = {"d_cr": "dias: Vivaz 160, resto " + fmt(N["dias_map"]) + ", mix 32%", "d_est_ex": f"estoque = {fmt(100 * BETA, 0)}% da média 3a de lançamentos", "terrenos": "permuta = 0; em caixa = CPV − parcelas da nota − terreno de t+1 (½ à vista)"}.get(k, f"{fmt(100 * PR.get(k, 0), 1)}% da receita")
    rows.append(f'<tr><td style="text-align:left;{PAD}">{LABEL[k]}</td><td style="text-align:right;{PAD};color:var(--muted)">{prem}</td>{c(P[LTM][k])}' + "".join(c(PJ["ltm"][y][k]) for y in YT) + '</tr>')
rows.append(f'<tr style="font-weight:700"><td style="text-align:left;{PAD}">= caixa operacional, +5% s/ LTM</td><td></td>{c(P[LTM]["cia_oper"])}' + "".join(c(PJ["ltm"][y]["caixa"]) for y in YT) + '</tr>')
for k, lab in (("2025", "caixa · +5% sobre 2025"), ("corte", "caixa · corte de 30% em 2027, depois +5%"), ("ltm+30", "caixa · +5% s/ LTM com Vivaz +30 pp")):
    rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">{lab}</td><td style="text-align:right;{PAD};color:var(--muted)">lanç. 2027 R$ {fmt(PJ[k][2027]["lanc"] / 1000, 1)} bi; receita 2029 R$ {fmt(PJ[k][2029]["receita"] / 1000, 1)} bi</td><td></td>' + "".join(c(PJ[k][y]["caixa"]) for y in YT) + '</tr>')
for k, lab in (("ltm", "caixa · +5% s/ LTM, terreno em caixa"), ("2025", "caixa · +5% s/ 2025, terreno em caixa"), ("corte", "caixa · corte de 30%, terreno em caixa")):
    rows.append(f'<tr><td style="text-align:left;{PAD};color:var(--muted)">{lab}</td><td style="text-align:right;{PAD};color:var(--muted)">terrenos 2027 R$ {fmt(PJ[k + "|caixa"][2027]["terrenos"] / 1000, 1)} bi</td><td></td>' + "".join(c(PJ[k + "|caixa"][y]["caixa"]) for y in YT) + '</tr>')
table = ('<table class="tl compact" style="margin-top:0;width:100%;font-size:9px"><thead><tr><th style="text-align:left;' + PAD + '">R$ mi</th><th style="text-align:right;' + PAD + '">premissa</th><th style="text-align:right;' + PAD + '">LTM 2T26</th>'
         + "".join(f'<th style="text-align:right;{PAD}">{y}E</th>' for y in YT) + '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>')
num = {"ltm_cia": P[LTM]["cia_oper"], "ltm_terr": P[LTM]["terrenos"], "ltm_obra": P[LTM]["d_est_ex"], "ltm_cr": P[LTM]["d_cr"], "mg": 100 * PR["lucro_bruto"], "sga": 100 * PR["sga"], "g": 100 * G, "frec": 100 * FREC, "beta": 100 * BETA,
       "lanc_ltm": LY[2026], "lanc_25": LY[2025], "dias_map": N["dias_map"], "rec_ltm_27_base": rec0, "cia_23_25": [P[y]["cia_oper"] for y in ("2023", "2024", "2025")], "rec_27": PJ["ltm"][2027]["receita"], "rec_29": PJ["ltm"][2029]["receita"]}
for k in PJ:
    kk = k.replace("+", "p").replace("|caixa", "_tc"); num[f"cx_{kk}_27"] = PJ[k][2027]["caixa"]; num[f"cx_{kk}_29"] = PJ[k][2029]["caixa"]; num[f"cx_{kk}_31"] = PJ[k][2031]["caixa"]; num[f"soma_{kk}"] = sum(PJ[k][y]["caixa"] for y in YS); num[f"lanc_{kk}_27"] = PJ[k][2027]["lanc"]; num[f"rec_{kk}_29"] = PJ[k][2029]["receita"]; num[f"obra_{kk}_27"] = PJ[k][2027]["d_est_ex"]; num[f"cr_{kk}_27"] = PJ[k][2027]["d_cr"]
json.dump({"svg": svg, "table": table, "num": num, "proj": {k: {str(y): v for y, v in d.items()} for k, d in PJ.items()}}, io.open(os.path.join(here, "_caixa_proj_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()})
