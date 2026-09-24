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
    h = 250; X0, X1, Y0, Y1 = ox + 40, ox + w - rm, 44, h - 22
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
# painel 3: barras dos cenários (margens de 28/20 e barras de 40: passo de ~70 entre rótulos, "concluídos"/"MCMV 30%" sem encostar)
ox, w = 690, 370; X0, XR, Y1, Y0 = ox + 28, ox + w - 20, 228, 60
bars = [("hoje", cy["cr"], MU), ("concluídos", concl, S2), ("MCMV 30%", lib_30, S3), ("MCMV 40%", lib_40, S3), ("dias Cury", lib_a, S1)]
ymx = 8000; yb = lambda v: Y1 - (Y1 - Y0) * v / ymx; bw = 40; gap = (XR - X0 - 5 * bw) / 4
g.append(f'<text x="{X0}" y="17" class="gtit">Caixa que sai do recebível, R$ bi</text><text x="{X0}" y="32" class="gsub">LTM 2T26; cenários sobre os dias da Cury ({fmt(cu["dias"])})</text>')
for t in (0, 2000, 4000, 6000, 8000): g.append(f'<line x1="{X0}" y1="{yb(t):.1f}" x2="{XR}" y2="{yb(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{yb(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t/1000)}</text>')
for i, (lab, v, col) in enumerate(bars):
    x0 = X0 + i * (bw + gap); g.append(f'<rect x="{x0:.1f}" y="{yb(v):.1f}" width="{bw}" height="{Y1-yb(v):.1f}" rx="2" fill="{col}" opacity="{.9 if i else .5}"/><text x="{x0+bw/2:.1f}" y="{yb(v)-5:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(v/1000, 1)}</text>')
    g.append(f'<text x="{x0+bw/2:.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".8">{lab}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{XR}" y2="{Y1}" stroke="var(--baseline)"/>')
svg = '<svg viewBox="0 0 1060 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: fim de ano e último
cols = [q for q in xs if q.startswith("4T") and int(q[2:]) >= 13] + [u]
# 23/09/26: dias sobre a receita do trimestre × 4 (Cyrela: E[q]["rec"], R$ mi; Cury: CD[q]["rec"] / 1000), fonte normal; o indicador principal segue o de 12 m
D4_CY = {q: 365 * CY[q]["cr"] / (4 * E[q]["rec"]) for q in CY}; D4_CU = {q: 365 * CU[q]["cr"] / (4 * CD[q]["rec"] / 1000) for q in CU}
PAD = "padding:1px 8px"   # 23/09/26: 1px (era 2px do .compact) para as 12 linhas caberem no slide (≤ 700px)
def cell(v, d=0, s=""): return f'<td style="text-align:right;{PAD}">{fmt(v, d) + s if v is not None else "—"}</td>'
lines = [("Cyrela · contas a receber, R$ mi", [CY[q]["cr"] for q in cols], 0, ""), ("Cyrela · receita 12 m, R$ mi", [CY[q]["rec12"] for q in cols], 0, ""), ("Cyrela · dias", [CY[q]["dias"] for q in cols], 0, ""), ("Cyrela · dias, trimestre × 4", [D4_CY[q] for q in cols], 0, ""), ("Cyrela · recebível ÷ PL", [CY[q]["cr_pl"] for q in cols], 0, "%"),
         ("Cury · dias", [CU.get(q, {}).get("dias") for q in cols], 0, ""), ("Cury · dias, trimestre × 4", [D4_CU.get(q) for q in cols], 0, ""), ("Cury · recebível ÷ PL", [CU.get(q, {}).get("cr_pl") for q in cols], 0, "%"),
         ("Plano & Plano · dias (CVM)", [PE["pp"].get(q, {}).get("dias") for q in cols], 0, ""), ("Tenda · dias (CVM)", [PE["tenda"].get(q, {}).get("dias") for q in cols], 0, ""), ("Direcional · dias (CVM)", [PE["direcional"].get(q, {}).get("dias") for q in cols], 0, ""), ("MRV · dias (CVM)", [PE["mrv"].get(q, {}).get("dias") for q in cols], 0, ""),
         ("Lavvi · dias (CVM)", [PE["lavvi"].get(q, {}).get("dias") for q in cols], 0, ""), ("Trisul · dias (CVM)", [PE["trisul"].get(q, {}).get("dias") for q in cols], 0, ""), ("Even · dias (CVM)", [PE["even"].get(q, {}).get("dias") for q in cols], 0, "")]
bold = lambda lab: "dias" in lab and "trimestre" not in lab
table = ('<table class="tl compact" style="margin-top:3px;width:100%;font-size:9.5px"><thead><tr><th style="text-align:left;' + PAD + '"></th>' + "".join(f'<th style="text-align:right;{PAD}">{"20" + q[2:] if q.startswith("4T") else q}</th>' for q in cols) + '</tr></thead><tbody>'
         + "".join(f'<tr><td style="text-align:left;white-space:nowrap;{PAD}{";font-weight:700" if bold(lab) else ""}">{lab}</td>' + "".join(cell(v, d, s) for v in vals) + '</tr>' for lab, vals, d, s in lines) + '</tbody></table>')
print("dias trimestre×4:", {q: (round(D4_CY[q]), round(D4_CU[q]) if q in D4_CU else None) for q in ("4T25", "1T26", "2T26")})
num = {"u": u, "cy_cr": cy["cr"], "cy_dias": cy["dias"], "cy_cr_pl": cy["cr_pl"], "cy_rec12": cy["rec12"], "cu_cr": cu["cr"], "cu_dias": cu["dias"], "cu_cr_pl": cu["cr_pl"], "cu_rec12": cu["rec12"], "sh_mcmv": 100 * sh_mcmv, "dias_map": dias_map,
       "lib_a": lib_a, "lib_30": lib_30, "lib_40": lib_40, "concl": concl, "constr": constr, "nq": nq, "cy_dias_max": max(v["dias"] for v in CY.values()), "cy_dias_max_q": max(CY, key=lambda q: CY[q]["dias"]), "cy_dias_min": min(v["dias"] for v in CY.values()), "cy_dias_min_q": min(CY, key=lambda q: CY[q]["dias"]),
       "cu_dias_min": min(v["dias"] for v in CU.values()), "cu_dias_min_q": min(CU, key=lambda q: CU[q]["dias"]), "cy_dias_4T19": CY.get("4T19", {}).get("dias"), "cu_dias_4T19": CU.get("4T19", {}).get("dias"),
       "lv_dias": D_LV[u], "tr_dias": D_TR[u], "ez_dias": PE["eztec"][u]["dias"], "ev_dias": PE["even"][u]["dias"], "md_dias": PE["mdne"][u]["dias"], "pp_dias": PE["pp"][u]["dias"], "td_dias": PE["tenda"][u]["dias"], "dr_dias": PE["direcional"][u]["dias"], "mrv_dias": PE["mrv"][u]["dias"]}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_cr_dias_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()})
