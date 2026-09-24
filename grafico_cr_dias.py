# -*- coding: utf-8 -*-
"""Recebível: dias de contas a receber e contas a receber ÷ PL, Cyrela × Cury, e quanto caixa sai se a Cyrela convergir para o patamar
da Cury (pedido de 23/09/26). Cyrela: contas a receber líquido (CP + LP) e receita trimestral da planilha de DFs do RI (Economatica,
desde 2010), PL consolidado do balanço CVM; nota de contas a receber dos ITR (concluídos × em construção, _notas_itr.json, 2020+);
receita por segmento (_segmentos.json, acumulado no ano → trimestre por diferença). Cury: planilha Fundamentos do RI (balanço: contas
a receber CP + LP, PL total; DRE: receita), R$ mil → R$ mi. Dias = contas a receber ÷ receita 12 meses × 365.
Saída: _cr_dias_frag.json {svg, table, num}."""
import io, json, os, datetime, openpyxl
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
ORD = lambda q: (int(q[2:]), int(q[0]))
# ---- Cyrela
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"), read_only=True, data_only=True)
ws = wb.worksheets[0]; rows = list(ws.iter_rows(values_only=True)); hdr = rows[3]
E = {}
for i, c in enumerate(hdr):
    if hasattr(c, "year") and c.year >= 2010:
        q = f"{(c.month - 1) // 3 + 1}T{str(c.year)[2:]}"; E[q] = {n: (rows[r][i] / 1000 if isinstance(rows[r][i], (int, float)) else None) for r, n in {13: "cr_cp", 23: "cr_lp", 70: "rec"}.items()}
B = J("_balanco_cvm.json"); N = J("_notas_itr.json"); SEG = J("_segmentos.json")
QC = sorted([q for q in E if E[q]["rec"] and E[q]["cr_cp"] is not None and q in B], key=ORD)
def rec12(d, qs, i): return sum(d[qs[j]]["rec"] for j in range(i - 3, i + 1)) if i >= 3 else None
CY = {}
for i, q in enumerate(QC):
    r12 = rec12(E, QC, i)
    if not r12: continue
    cr = E[q]["cr_cp"] + E[q]["cr_lp"]; pl = B[q].get("pl_consolidado")
    CY[q] = {"cr": cr, "rec12": r12, "dias": 365 * cr / r12, "cr_pl": 100 * cr / pl if pl else None, "pl": pl}
# nota do ITR: concluídos × em construção (líquido de AVP no total; a abertura é bruta)
NT = {q: N[q]["cr"] for q in N if "cr" in N[q] and N[q]["cr"].get("concluidos") is not None}
# receita por segmento: acumulado no ano → trimestre
def seg_q(q, k):
    y = q[2:]; n = int(q[0]); cur = SEG.get(q, {}).get(k, {}).get("rec")
    if cur is None: return None
    if n == 1: return cur
    prev = SEG.get(f"{n-1}T{y}", {}).get(k, {}).get("rec"); return cur - prev if prev is not None else None
def seg_tot(q): return sum(v for k in SEG.get(q, {}) for v in [seg_q(q, k)] if v is not None)
L4 = QC[-4:]; mcmv12 = sum(seg_q(q, "mcmv") or 0 for q in L4); tot12 = sum(seg_tot(q) for q in L4); sh_mcmv = mcmv12 / tot12
# ---- Cury (planilha Fundamentos, R$ mil)
wbc = openpyxl.load_workbook(os.path.join(here, "fontes", "verificacao", "cury_planilha_fundamentos.xlsx"), read_only=True, data_only=True)
def bs(sheet, pat, nth=0):
    ws = wbc[sheet]; rows = list(ws.iter_rows(values_only=True, max_row=60)); hdr = rows[3]; hits = [r for r in rows if r[1] and str(r[1]).upper().startswith(pat)]; r = hits[nth]
    return {f"{(h.month - 1) // 3 + 1}T{h.year % 100:02d}": r[i] / 1000 for i, h in enumerate(hdr) if isinstance(h, (datetime.datetime, datetime.date)) and isinstance(r[i], (int, float))}
ccp = bs("Balanço Patrimonial Ativo", "CONTAS A RECEBER", 0); clp = bs("Balanço Patrimonial Ativo", "CONTAS A RECEBER", 1); cpl = bs("Balanço Patrimonial Passivo", "PATRIMÔNIO LÍQUIDO TOTAL")
CD = J("_cury_dre.json")["serie"]; QU = sorted([q for q in CD if q in ccp and CD[q].get("rec")], key=ORD)
CU = {}
for i, q in enumerate(QU):
    if i < 3: continue
    r12 = sum(CD[QU[j]]["rec"] for j in range(i - 3, i + 1)) / 1000; cr = ccp[q] + clp[q]; pl = cpl.get(q)
    CU[q] = {"cr": cr, "rec12": r12, "dias": 365 * cr / r12, "cr_pl": 100 * cr / pl if pl else None, "pl": pl}
u = QC[-1]; cy, cu = CY[u], CU[u]
PE = J("_cvm_cr_pares.json")   # pares puros de MAP (CVM, dados_cvm_cr_pares.py): Lavvi e Trisul
D_LV = {q: v["dias"] for q, v in PE["lavvi"].items() if v["dias"]}; D_TR = {q: v["dias"] for q, v in PE["trisul"].items() if v["dias"]}
# ---- cenários de liberação de caixa (LTM 2T26)
# (a) Cyrela inteira no patamar de dias da Cury; (b) mix: MCMV com dias da Cury, MAP com os dias implícitos; MCMV sobe de sh_mcmv para 30% e 40% da receita
cr_at_cury = cy["rec12"] * cu["dias"] / 365; lib_a = cy["cr"] - cr_at_cury
cr_mcmv = sh_mcmv * cy["rec12"] * cu["dias"] / 365; dias_map = 365 * (cy["cr"] - cr_mcmv) / ((1 - sh_mcmv) * cy["rec12"])
def mix(s): return cy["rec12"] * (s * cu["dias"] + (1 - s) * dias_map) / 365
lib_30 = cy["cr"] - mix(0.30); lib_40 = cy["cr"] - mix(0.40)
# (c) recebível de concluídos (performado, nota do ITR): o que já é caixa a receber de unidade entregue
nq = sorted(NT, key=ORD)[-1]; concl = NT[nq]["concluidos"]; constr = NT[nq]["em_construcao"]
# ---- svg: três painéis
def panel(ox, w, title, sub, series, ymax, step, xs, xlab, unit="%", rm=70):   # rm: margem direita para os rótulos de fim de linha
    h = 190; X0, X1, Y0, Y1 = ox + 40, ox + w - rm, 44, h - 22   # 23/09/26: 250 → 215 → 190 (slide a 759px com o painel 3 e a tabela de caixa; alvo ≤ 720)
    x = lambda i: X0 + (X1 - X0) * i / (len(xs) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+40}" y="17" class="gtit">{title}</text><text x="{ox+40}" y="32" class="gsub">{sub}</text>']
    t = 0
    while t <= ymax + 1e-9:
        g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t)}{unit}</text>'); t += step
    for i, q in enumerate(xs):
        lb = xlab(q)
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
    ends = []
    for d, col, lab, wd, dash in series:
        pts = " ".join(f"{x(i):.1f},{y(d[q]):.1f}" for i, q in enumerate(xs) if d.get(q) is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round" stroke-linecap="round"/>')
        last = [d[q] for q in xs if d.get(q) is not None][-1]; ends.append((last, col, lab))
    ys = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = y(v)
        for pv in ys:
            if abs(yy - pv) < 15: yy = pv + 15   # 23/09/26: 15 (a 14 as caixas de 12px encostavam: Lavvi/Trisul/Cyrela)
        ys.append(yy); g.append(f'<circle cx="{X1:.1f}" cy="{y(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v)}{unit}</text>')
    return "".join(g)
# 23/09/26 (formatação): anos com 2 dígitos a cada 2 anos, como no slide 33 (a 4 dígitos "2011 2013…" encostavam no painel 2); painéis 360/330/370 para as barras
xl = lambda q: q[2:] if q.startswith("4T") and int(q[2:]) % 2 == 1 else ""
D_CY = {q: v["dias"] for q, v in CY.items()}; D_CU = {q: v["dias"] for q, v in CU.items()}
P_CY = {q: v["cr_pl"] for q, v in CY.items()}; P_CU = {q: v["cr_pl"] for q, v in CU.items()}
xs = [q for q in QC if q in CY]
g = [panel(0, 360, "Dias de recebível", "contas a receber ÷ receita 12 m × 365", [(D_CY, S1, "Cyrela", 2.6, ""), (D_CU, S3, "Cury", 2.4, ""), (D_LV, S2, "Lavvi", 1.8, "5 3"), (D_TR, MU, "Trisul", 1.8, "5 3")], 400, 100, xs, xl, "", rm=82),   # 23/09/26: rm 82 (a 70 "Cyrela 241" terminava em 357 e o "250%" do painel 2 começa em 362)
     panel(360, 330, "Contas a receber ÷ PL, %", "balanço consolidado; Cury: PL total", [(P_CY, S1, "Cyrela", 2.6, ""), (P_CU, S3, "Cury", 2.4, "")], 250, 50, xs, xl)]   # Cury acima de 100%: PL pequeno
# painel 3 (24/09/26): trajetórias de dias por cenário de mix da Vivaz nos lançamentos, e geração de caixa por cenário
# Mix de lançamentos (VGV a stake ≈ 100%: participação da Cyrela igual nos dois produtos, anexo dos releases): _mix_stake.json (dados_share_rm.py / anexo)
MX = {int(y): v["mix_stake"] for y, v in J("_mix_stake.json").items()}; MX[2018] = 0.21; MX[2019] = 0.19
W = (0.0, 0.15, 0.35, 0.35, 0.15)   # receita do ano t = lançamentos de t−1 (15%), t−2 (35%), t−3 (35%), t−4 (15%): ciclo de 39 meses (anexo de entregues) + cauda; reproduz 19% de Vivaz na receita em 2026 (observado 17,7%)
def rshare(y, m): return sum(W[k] * m.get(y - k, MX[2018]) for k in range(5))
DV = 160.0; G = 0.05; Y0P = 2026; YS_P = list(range(2026, 2032))
CXR = J("_caixa_reconc_frag.json")["num"]; cx_ante = (CXR["cia"] + CXR["cr"]) / cy["rec12"]   # caixa operacional antes do recebível, LTM: release + Δ recebível, % da receita
SCN = [("base 32%", 0.0, MU), ("+10 pp", 0.10, S3), ("+20 pp", 0.20, S2), ("+30 pp", 0.30, S1)]
PROJ = {}
for lab, dpp, col in SCN:
    m = dict(MX)
    for y in range(2027, 2033): m[y] = MX[2026] + dpp
    rows_ = {}; cr_prev = cy["cr"]
    for y in YS_P:
        rec = cy["rec12"] * (1 + G) ** (y - Y0P); s = rshare(y, m) if y > Y0P else sh_mcmv
        d = cy["dias"] if y == Y0P else s * DV + (1 - s) * dias_map; cr = cy["cr"] if y == Y0P else rec * d / 365
        rows_[y] = {"rec": rec, "share": s, "dias": d, "cr": cr, "dcr": cr - cr_prev if y > Y0P else None, "cx_ante": cx_ante * rec if y > Y0P else None, "cx": cx_ante * rec - (cr - cr_prev) if y > Y0P else None, "mix": m[y]}
        cr_prev = cr
    PROJ[lab] = rows_
ox, w = 690, 370; X0, X1, Y1, Y0 = ox + 40, ox + w - 90, 168, 44   # Y1 = h − 22 do panel(); margem 90 para "base 32% 226" não vazar
xp = lambda i: X0 + (X1 - X0) * i / (len(YS_P) - 1); yp = lambda v: Y1 - (Y1 - Y0) * (v - 150) / 150
g.append(f'<text x="{X0}" y="17" class="gtit">Dias projetados por mix da Vivaz</text><text x="{X0}" y="32" class="gsub">Vivaz a {fmt(DV)} dias, resto a {fmt(dias_map)}; mix de 2027 em diante</text>')
for tv in (150, 200, 250, 300): g.append(f'<line x1="{X0}" y1="{yp(tv):.1f}" x2="{X1}" y2="{yp(tv):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{yp(tv)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tv}</text>')
for i, y in enumerate(YS_P): g.append(f'<text x="{xp(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{y}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
ends = []
for lab, dpp, col in SCN:
    pts = " ".join(f"{xp(i):.1f},{yp(PROJ[lab][y]['dias']):.1f}" for i, y in enumerate(YS_P))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>'); ends.append((PROJ[lab][YS_P[-1]]["dias"], col, lab))
ys_ = []
for v, col, lab in sorted(ends, reverse=True):
    yy = yp(v)
    for pv in ys_:
        if abs(yy - pv) < 15: yy = pv + 15
    ys_.append(yy); g.append(f'<circle cx="{X1:.1f}" cy="{yp(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v)}</text>')
svg = '<svg viewBox="0 0 1060 190" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: fim de ano e último
cols = [q for q in xs if q.startswith("4T") and int(q[2:]) >= 13] + [u]
# 23/09/26: dias sobre a receita do trimestre × 4 (Cyrela: E[q]["rec"], R$ mi; Cury: CD[q]["rec"] / 1000), fonte normal; o indicador principal segue o de 12 m
D4_CY = {q: 365 * CY[q]["cr"] / (4 * E[q]["rec"]) for q in CY}; D4_CU = {q: 365 * CU[q]["cr"] / (4 * CD[q]["rec"] / 1000) for q in CU}
PAD = "padding:0 8px"   # 23/09/26: 2px do .compact → 1px (12 linhas) → 0 (16 linhas com os pares de baixa renda; borda de 1px separa as linhas)
def cell(v, d=0, s=""): return f'<td style="text-align:right;{PAD}">{fmt(v, d) + s if v is not None else "—"}</td>'
lines = [("Cyrela · contas a receber, R$ mi", [CY[q]["cr"] for q in cols], 0, ""), ("Cyrela · receita 12 m, R$ mi", [CY[q]["rec12"] for q in cols], 0, ""), ("Cyrela · dias", [CY[q]["dias"] for q in cols], 0, ""), ("Cyrela · dias, trimestre × 4", [D4_CY[q] for q in cols], 0, ""), ("Cyrela · recebível ÷ PL", [CY[q]["cr_pl"] for q in cols], 0, "%"),
         ("Cury · dias", [CU.get(q, {}).get("dias") for q in cols], 0, ""), ("Cury · dias, trimestre × 4", [D4_CU.get(q) for q in cols], 0, ""), ("Cury · recebível ÷ PL", [CU.get(q, {}).get("cr_pl") for q in cols], 0, "%"),
         ("Plano & Plano · dias (CVM)", [PE["pp"].get(q, {}).get("dias") for q in cols], 0, ""), ("Tenda · dias (CVM)", [PE["tenda"].get(q, {}).get("dias") for q in cols], 0, ""), ("Direcional · dias (CVM)", [PE["direcional"].get(q, {}).get("dias") for q in cols], 0, ""), ("MRV · dias (CVM)", [PE["mrv"].get(q, {}).get("dias") for q in cols], 0, ""),
         ("Lavvi · dias (CVM)", [PE["lavvi"].get(q, {}).get("dias") for q in cols], 0, ""), ("Trisul · dias (CVM)", [PE["trisul"].get(q, {}).get("dias") for q in cols], 0, ""), ("Even · dias (CVM)", [PE["even"].get(q, {}).get("dias") for q in cols], 0, "")]
bold = lambda lab: "dias" in lab and "trimestre" not in lab
table = ('<table class="tl compact" style="margin-top:0;width:100%;font-size:9.5px"><thead><tr><th style="text-align:left;' + PAD + '"></th>' + "".join(f'<th style="text-align:right;{PAD}">{"20" + q[2:] if q.startswith("4T") else q}</th>' for q in cols) + '</tr></thead><tbody>'
         + "".join(f'<tr><td style="text-align:left;white-space:nowrap;{PAD}{";font-weight:700" if bold(lab) else ""}">{lab}</td>' + "".join(cell(v, d, s) for v in vals) + '</tr>' for lab, vals, d, s in lines) + '</tbody></table>')
YT = [2027, 2028, 2029, 2030, 2031]
def c2(v, d=1): return f'<td style="text-align:right;{PAD}">{fmt(v, d)}</td>'
tr2 = []
for lab, dpp, col in SCN:
    P = PROJ[lab]; acc = sum(P[y]["cx"] for y in YT); dcr = sum(P[y]["dcr"] for y in YT)
    tr2.append(f'<tr><td style="text-align:left;white-space:nowrap;{PAD};color:{col};font-weight:700">Vivaz {lab} dos lançamentos</td>' + "".join(f'<td style="text-align:right;white-space:nowrap;{PAD}">{fmt(100 * P[y]["share"])}% · {fmt(P[y]["dias"])} d · <b>{fmt(P[y]["cx"] / 1000, 1)}</b></td>' for y in YT) + c2(dcr / 1000) + c2(acc / 1000) + '</tr>')
table2 = ('<table class="tl compact" style="margin-top:2px;width:100%;font-size:9.5px"><thead><tr><th style="text-align:left;white-space:nowrap;' + PAD + '">geração de caixa operacional, R$ bi: Vivaz na receita · dias · <b>caixa</b></th>' + "".join(f'<th style="text-align:right;{PAD}">{y}</th>' for y in YT) + f'<th style="text-align:right;{PAD}">Δ recebível 27-31</th><th style="text-align:right;{PAD}">caixa 27-31</th></tr></thead><tbody>' + "".join(tr2) + '</tbody></table>')
print("dias trimestre×4:", {q: (round(D4_CY[q]), round(D4_CU[q]) if q in D4_CU else None) for q in ("4T25", "1T26", "2T26")})
num = {"u": u, "cy_cr": cy["cr"], "cy_dias": cy["dias"], "cy_cr_pl": cy["cr_pl"], "cy_rec12": cy["rec12"], "cu_cr": cu["cr"], "cu_dias": cu["dias"], "cu_cr_pl": cu["cr_pl"], "cu_rec12": cu["rec12"], "sh_mcmv": 100 * sh_mcmv, "dias_map": dias_map,
       "lib_a": lib_a, "lib_30": lib_30, "lib_40": lib_40, "cx_ante_pct": 100 * cx_ante, "cx_ante_ltm": CXR["cia"] + CXR["cr"], "cia_ltm": CXR["cia"], "dcr_ltm": CXR["cr"], "dv": DV, "g": 100 * G, "mix26": 100 * MX[2026], "share30_base": 100 * PROJ["base 32%"][2030]["share"], "dias30_base": PROJ["base 32%"][2030]["dias"], "dias31_base": PROJ["base 32%"][2031]["dias"], "dias31_p30": PROJ["+30 pp"][2031]["dias"], "cx_base_27_31": sum(PROJ["base 32%"][y]["cx"] for y in YT) / 1000, "cx_p30_27_31": sum(PROJ["+30 pp"][y]["cx"] for y in YT) / 1000, "cx_p10_27_31": sum(PROJ["+10 pp"][y]["cx"] for y in YT) / 1000, "cx_base_27": PROJ["base 32%"][2027]["cx"] / 1000, "cx_base_31": PROJ["base 32%"][2031]["cx"] / 1000, "cx_p30_31": PROJ["+30 pp"][2031]["cx"] / 1000, "dcr_base_27_31": sum(PROJ["base 32%"][y]["dcr"] for y in YT) / 1000, "dcr_p30_27_31": sum(PROJ["+30 pp"][y]["dcr"] for y in YT) / 1000, "concl": concl, "constr": constr, "nq": nq, "cy_dias_max": max(v["dias"] for v in CY.values()), "cy_dias_max_q": max(CY, key=lambda q: CY[q]["dias"]), "cy_dias_min": min(v["dias"] for v in CY.values()), "cy_dias_min_q": min(CY, key=lambda q: CY[q]["dias"]),
       "cu_dias_min": min(v["dias"] for v in CU.values()), "cu_dias_min_q": min(CU, key=lambda q: CU[q]["dias"]), "cy_dias_4T19": CY.get("4T19", {}).get("dias"), "cu_dias_4T19": CU.get("4T19", {}).get("dias"),
       "lv_dias": D_LV[u], "tr_dias": D_TR[u], "ez_dias": PE["eztec"][u]["dias"], "ev_dias": PE["even"][u]["dias"], "md_dias": PE["mdne"][u]["dias"], "pp_dias": PE["pp"][u]["dias"], "td_dias": PE["tenda"][u]["dias"], "dr_dias": PE["direcional"][u]["dias"], "mrv_dias": PE["mrv"][u]["dias"]}
json.dump({"svg": svg, "table": table, "table2": table2, "num": num}, io.open(os.path.join(here, "_cr_dias_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()})
