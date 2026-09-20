# -*- coding: utf-8 -*-
"""Cury × Vivaz, parte 2: alavancagem da Cury (estrutural, não financeira), retorno decomposto (DuPont) e o que a Vivaz valeria
a P/B implícito pelo retorno (Gordon: P/B = (ROE − g) ÷ (Ke − g), Ke 17% e g 4%, premissas da apresentação).
Entradas: _cury_dre.json (DRE e balanço trimestrais do RI da Cury), fontes/verificacao/cury_planilha_fundamentos.xlsx (linhas do
balanço), _segmentos_full.json e _roe_seg_serie.json (Vivaz), B3 (CURY3 e CYRE3 em 18/09/26; nº de ações). Saída: _cury_valor_frag.json."""
import io, json, os, datetime, openpyxl
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2, GR = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)", "#2e7d32"
ordq = lambda q: (int(q[2:]), int(q[0]))
MKT = {"data": "18/09/2026", "CURY3": 29.05, "CYRE3": 26.67, "acoes_cury": 308_047_594, "acoes_cyre": 453_446_450, "ke": 17.0, "g": 4.0, "cyrela_em_cury": 15.08}   # B3 COTAHIST diário e GetListedSupplementCompany; Ke e g = premissas da apresentação (slide do P/B)
# ---- Cury
D = json.load(io.open(os.path.join(here, "_cury_dre.json"), encoding="utf-8"))["serie"]; qs = sorted(D, key=ordq)
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "verificacao", "cury_planilha_fundamentos.xlsx"), read_only=True, data_only=True)
def rowmap(sheet, idx):
    ws = wb[sheet]; rows = list(ws.iter_rows(values_only=True, max_row=60)); hdr = rows[3]; res = {}
    for key, r in idx.items():
        for i, h in enumerate(hdr):
            if isinstance(h, (datetime.datetime, datetime.date)) and isinstance(rows[r - 1][i], (int, float)): res.setdefault(f"{(h.month - 1) // 3 + 1}T{h.year % 100:02d}", {})[key] = rows[r - 1][i]
    return res
BA = rowmap("Balanço Patrimonial Ativo", {"caixa": 6, "tvm": 7, "cr_c": 8, "imov_c": 9, "cr_nc": 14, "imov_nc": 15, "ativo": 23})
BP = rowmap("Balanço Patrimonial Passivo", {"emp_c": 7, "cred_c": 10, "adiant": 11, "emp_nc": 18, "cred_nc": 20, "pl_total": 28})
def ltm(k, q): i = qs.index(q); return sum(D[x][k] for x in qs[i - 3:i + 1])
def med5(k, q): i = qs.index(q); return sum(D[x][k] for x in qs[i - 4:i + 1]) / 5
QC = [q for q in qs if ordq(q) >= (19, 4) and q in BA and q in BP]
C = {}
for q in QC:
    a, p = BA[q], BP[q]; db = p["emp_c"] + p["emp_nc"]; cx = a["caixa"] + a["tvm"]
    C[q] = {"ret_op": 100 * ltm("lop", q) / med5("pl_total", q), "roe": 100 * ltm("ll_ctrl", q) / med5("pl_ctrl", q), "dl_pl": 100 * (db - cx) / p["pl_total"], "cred_pl": 100 * (p["cred_c"] + p["cred_nc"]) / p["pl_total"],
            "adiant_pl": 100 * p["adiant"] / p["pl_total"], "at_pl": a["ativo"] / p["pl_total"], "mg_op": 100 * ltm("lop", q) / ltm("rec", q), "giro": ltm("rec", q) / a["ativo"]}
u = QC[-1]; cu = C[u]
# ---- Vivaz (nota de segmentos) e retorno
S = json.load(io.open(os.path.join(here, "_segmentos_full.json"), encoding="utf-8")); R = json.load(io.open(os.path.join(here, "_roe_seg_serie.json"), encoding="utf-8"))
sq = sorted(S, key=ordq); su = sq[-1]
def sflow(k, f, q):
    t_ = int(q[0]); return S[q][k][f] if t_ == 1 else S[q][k][f] - S[f"{t_ - 1}T{q[2:]}"][k][f]
def sltm(k, f): return sum(sflow(k, f, q) for q in sq[-4:])
V = {"ret_op": R["mcmv"][su], "mg_op": 100 * sltm("mcmv", "lop") / sltm("mcmv", "rec"), "giro": sltm("mcmv", "rec") / S[su]["mcmv"]["ativo"], "at_pl": S[su]["mcmv"]["ativo"] / S[su]["mcmv"]["pl"], "pl": S[su]["mcmv"]["pl"] / 1000, "rec": sltm("mcmv", "rec") / 1000}
fator_ll = cu["roe"] / cu["ret_op"]                      # quanto do retorno operacional vira ROE líquido na Cury (juros, IR e minoritários)
V["roe_est"] = V["ret_op"] * fator_ll
# ---- vendas ÷ receita, LTM (Cury: vendas líquidas parte Cury e receita do RI; Vivaz: vendas 100% do segmento MCMV, planilha operacional, e receita do segmento na nota do ITR)
CH = json.load(io.open(os.path.join(here, "_cury_hist.json"), encoding="utf-8")); OP = json.load(io.open(os.path.join(here, "_operacional_ri.json"), encoding="utf-8"))
_vc = {q: v for q, v in CH["VENDAS E DISTRATOS · Vendas Líquidas parte Cury"].items() if "T" in q}; _lc = {q: v for q, v in CH["LANÇAMENTOS · VGV (em R$ mil) - Parte Cury"].items() if "T" in q}
def _ltm(d, q, n=4):
    ks = sorted(d, key=ordq); i = ks.index(q); return sum((d[x] or 0) for x in ks[i - n + 1:i + 1]) if i >= n - 1 else None
RC = {q: _ltm(_vc, q) / 1e3 / (ltm("rec", q) / 1e3) for q in QC if _ltm(_vc, q) and q in D}          # Cury: vendas ÷ receita
LC = {q: _ltm(_lc, q) / 1e3 / (ltm("rec", q) / 1e3) for q in QC if _ltm(_lc, q) and q in D}          # Cury: lançamentos ÷ receita
_vv = {q: sum((OP["vendas"]["vgv100_seg"][k].get(q) or 0) for k in ("mcmv23", "mcmv1")) for q in OP["tris"]}
_rv = {q: sflow("mcmv", "rec", q) for q in sq}
CBL = json.load(io.open(os.path.join(here, "_cbr_lanc.json"), encoding="utf-8"))["trimestral"]   # %consol do VGV lançado de MCMV (lista de empreendimentos do RI): a Vivaz lança muito em JV
def _okc(x): m = CBL.get(x, {}).get("MCMV"); return bool(m and m.get("vgv") and m.get("consol") is not None)
def consol(q):   # perímetro consolidado da venda de hoje ≈ %consol do lançado nos 8 trimestres anteriores, ponderado por VGV
    qs_ = [x for x in OP["tris"] if ordq(x) <= ordq(q) and _okc(x)][-8:]; den = sum(CBL[x]["MCMV"]["vgv"] for x in qs_); return sum(CBL[x]["MCMV"]["vgv"] * CBL[x]["MCMV"]["consol"] / 100 for x in qs_) / den if den else None
_vvc = {q: _vv[q] * consol(q) for q in OP["tris"] if consol(q)}
RV = {q: _ltm(_vvc, q) / _ltm(_rv, q) for q in sq if ordq(q) >= (20, 4) and _ltm(_rv, q) and _ltm(_vvc, q)}   # Vivaz: vendas consolidadas ÷ receita do segmento
RV100 = {q: _ltm(_vv, q) / _ltm(_rv, q) for q in sq if ordq(q) >= (20, 4) and _ltm(_rv, q)}; CONS_U = consol(OP["tris"][-1])
# ---- valor
mc_cury = MKT["CURY3"] * MKT["acoes_cury"] / 1e9; pl_ctrl = D[u]["pl_ctrl"] / 1e6; pl_tot = D[u]["pl_total"] / 1e6
pb_cury = mc_cury / pl_ctrl; gord = lambda roe: (roe - MKT["g"]) / (MKT["ke"] - MKT["g"])
pb_cury_g = gord(cu["roe"]); pb_viv = gord(V["roe_est"]); val_viv = pb_viv * V["pl"]
mc_cyre = MKT["CYRE3"] * MKT["acoes_cyre"] / 1e9; stake = MKT["cyrela_em_cury"] / 100 * mc_cury
def v2(g1, n, roe, pl0, g2=None):   # dois estágios: cresce g1 por n anos reinvestindo (payout = 1 − g1/ROE), depois perpetuidade a g2 com o mesmo ROE
    ke = MKT["ke"] / 100; g2 = MKT["g"] / 100 if g2 is None else g2; pl = pl0; pv = 0.0
    for k in range(1, n + 1):
        ll = roe * pl; pv += ll * (1 - g1 / roe) / (1 + ke) ** k; pl *= 1 + g1
    return pv + pl * (roe - g2) / (ke - g2) / (1 + ke) ** n
G1, N1 = 0.20, 5   # teto: lucro da Vivaz +20% a.a. por 5 anos = cenário em que ela alcança o lançado da Cury em 2 anos (curva de reconhecimento da Cury, perímetro consolidado de 74%)
val_viv_top = v2(G1, N1, V["roe_est"] / 100, V["pl"]); pb_viv_top = val_viv_top / V["pl"]
# ---- svg: painel 1 retornos; painel 2 estrutura da Cury (% do PL); painel 3 vendas ÷ receita LTM
g = []; Y0, Y1 = 46, 200
def painel(X0, X1, title, sub, ymin, ymax, ticks, tickf, series, xs):
    n = len(xs); x = lambda i: X0 + (X1 - X0) * i / (n - 1); y = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
    g.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for tv in ticks: g.append(f'<line x1="{X0}" y1="{y(tv):.1f}" x2="{X1}" y2="{y(tv):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(tv)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tickf(tv)}</text>')
    for i, q in enumerate(xs):
        if q.startswith("4T"): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">20{q[2:]}</text>')
    g.append(f'<line x1="{X0}" y1="{y(0) if ymin <= 0 <= ymax else Y1:.1f}" x2="{X1}" y2="{y(0) if ymin <= 0 <= ymax else Y1:.1f}" stroke="var(--baseline)"/>')
    ends = []
    for vals, col, w, dash, lab, labf in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>')
        last = [v for v in vals if v is not None][-1]; ends.append([y(last), col, f"{lab} {labf(last)}"])
    ends.sort(key=lambda e: e[0])
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 13: ends[k][0] = ends[k - 1][0] + 13
    for yy, col, lab in ends: g.append(f'<text x="{X1+5:.1f}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab}</text>')
pct = lambda v: f"{fmt(v)}%"
painel(46, 290, "Retorno LTM: Cury × Vivaz, %", "Cury: ROE e retorno operacional; Vivaz: operacional (ITR)", 0, 100, (0, 25, 50, 75, 100), pct,
       [([C[q]["ret_op"] for q in QC], GR, 2.4, "5 3", "Cury op.", pct), ([C[q]["roe"] for q in QC], GR, 2.6, "", "Cury ROE", pct), ([R["mcmv"].get(q) for q in QC], S1, 2.6, "", "Vivaz op.", pct)], QC)
painel(430, 660, "Alavancagem da Cury, % do PL", "terreno a prazo, adiantamentos e dívida líquida (negativo = caixa)", -60, 160, (-50, 0, 50, 100, 150), pct,
       [([C[q]["cred_pl"] for q in QC], S3, 2.6, "", "terreno a prazo", pct), ([C[q]["adiant_pl"] for q in QC], S2, 2.2, "", "adiant. clientes", pct), ([C[q]["dl_pl"] for q in QC], S1, 2.4, "", "dívida líq.", pct)], QC)
QX = [q for q in QC if q in RV or q in RC]; xf = lambda v: f"{fmt(v, 1)}x"
painel(790, 1010, "Vendas ÷ receita, LTM", "vendido e não reconhecido; Vivaz: consolidado ÷ segmento", 0, 4, (0, 1, 2, 3, 4), xf,
       [([RC.get(q) for q in QX], GR, 2.6, "", "Cury", xf), ([RV.get(q) for q in QX], S1, 2.6, "", "Vivaz", xf)], QX)
svg = '<svg viewBox="0 0 1100 226" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabelas: DuPont e valor
rows = [("margem operacional (lucro operacional ÷ receita, LTM)", f"{fmt(cu['mg_op'])}%", f"{fmt(V['mg_op'])}%"), ("giro (receita LTM ÷ ativo)", f"{fmt(cu['giro'], 2)}x", f"{fmt(V['giro'], 2)}x"), ("ativo ÷ PL", f"{fmt(cu['at_pl'], 1)}x", f"{fmt(V['at_pl'], 1)}x"),
        ("retorno operacional s/ capital, LTM", f"{fmt(cu['ret_op'])}%", f"{fmt(V['ret_op'])}%"), ("dívida líquida ÷ PL", f"{fmt(cu['dl_pl'])}% (caixa)", "n.d. (segmento)"), ("terreno a prazo + adiantamentos ÷ PL", f"{fmt(cu['cred_pl'] + cu['adiant_pl'])}%", "n.d. (segmento)")]
t1 = '<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">DuPont, 2T26</th><th style="text-align:right;color:#2e7d32">Cury</th><th style="text-align:right;color:var(--s1)">Vivaz</th></tr></thead><tbody>' + "".join(f'<tr{" class=\"total\"" if "retorno" in a else ""}><td>{a}</td><td style="text-align:right">{b}</td><td style="text-align:right">{c}</td></tr>' for a, b, c in rows) + "</tbody></table>"
rows2 = [("preço × ações", f"{fmt(MKT['CURY3'], 2)} × {fmt(MKT['acoes_cury'] / 1e6)} mi", "—"), ("valor de mercado", f"R$ {fmt(mc_cury, 1)} bi", f"R$ {fmt(val_viv, 1)} a {fmt(val_viv_top, 1)} bi (implícito)"), ("PL (controladora)", f"R$ {fmt(pl_ctrl, 2)} bi", f"R$ {fmt(V['pl'], 2)} bi (segmento)"),
         ("ROE", f"{fmt(cu['roe'])}%", f"~{fmt(V['roe_est'])}% (op. {fmt(V['ret_op'])}% × {fmt(fator_ll, 2)})"), ("vendas ÷ receita, LTM", f"{fmt(RC[QC[-1]], 1)}x (em regime)", f"{fmt(RV[sq[-1]], 1)}x (crescimento contratado)"), ("P/B de mercado", f"{fmt(pb_cury, 1)}x", "—"),
         (f"piso: Gordon, Ke {fmt(MKT['ke'])}% e g {fmt(MKT['g'])}%", f"{fmt(pb_cury_g, 1)}x", f"{fmt(pb_viv, 1)}x · R$ {fmt(val_viv, 1)} bi"), (f"teto: lucro +{fmt(100 * G1)}% a.a. por {N1} anos, depois {fmt(MKT['g'])}%", "—", f"{fmt(pb_viv_top, 1)}x · R$ {fmt(val_viv_top, 1)} bi"),
         ("Cyrela: valor de mercado", f"R$ {fmt(mc_cyre, 1)} bi", f"{fmt(100 * val_viv / mc_cyre)} a {fmt(100 * val_viv_top / mc_cyre)}% do valor, 8% do PL"), ("15,08% da Cury na mão da Cyrela", f"R$ {fmt(stake, 2)} bi", "—")]
t2 = '<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">valor</th><th style="text-align:right;color:#2e7d32">Cury</th><th style="text-align:right;color:var(--s1)">Vivaz</th></tr></thead><tbody>' + "".join(f'<tr{" class=\"total\"" if "Gordon" in a or "valor de mercado" == a else ""}><td>{a}</td><td style="text-align:right">{b}</td><td style="text-align:right">{c}</td></tr>' for a, b, c in rows2) + "</tbody></table>"
num = {"mc_cury": mc_cury, "pb_cury": pb_cury, "pb_cury_g": pb_cury_g, "roe_cury": cu["roe"], "ret_cury": cu["ret_op"], "dl_pl": cu["dl_pl"], "cred_pl": cu["cred_pl"], "adiant_pl": cu["adiant_pl"], "at_pl": cu["at_pl"], "at_pl_v": V["at_pl"], "mg_c": cu["mg_op"], "mg_v": V["mg_op"], "giro_c": cu["giro"], "giro_v": V["giro"],
       "roe_viv": V["roe_est"], "pb_viv": pb_viv, "val_viv": val_viv, "pb_viv_top": pb_viv_top, "val_viv_top": val_viv_top, "g1": G1, "n1": N1, "vr_cury": RC[QC[-1]], "vr_viv": RV[sq[-1]], "vr_viv100": RV100[sq[-1]], "cons": CONS_U, "mc_cyre": mc_cyre, "stake": stake, "pl_viv": V["pl"], "fator_ll": fator_ll, "mkt": MKT, "u": u}
json.dump({"svg": svg, "t1": t1, "t2": t2, "num": num}, io.open(os.path.join(here, "_cury_valor_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in num.items() if k != "mkt"})
