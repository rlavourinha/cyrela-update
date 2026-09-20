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
# ---- valor
mc_cury = MKT["CURY3"] * MKT["acoes_cury"] / 1e9; pl_ctrl = D[u]["pl_ctrl"] / 1e6; pl_tot = D[u]["pl_total"] / 1e6
pb_cury = mc_cury / pl_ctrl; gord = lambda roe: (roe - MKT["g"]) / (MKT["ke"] - MKT["g"])
pb_cury_g = gord(cu["roe"]); pb_viv = gord(V["roe_est"]); val_viv = pb_viv * V["pl"]
mc_cyre = MKT["CYRE3"] * MKT["acoes_cyre"] / 1e9; stake = MKT["cyrela_em_cury"] / 100 * mc_cury
# ---- svg: painel 1 retornos (Cury ROE, Cury op, Vivaz op); painel 2 estrutura da Cury (% do PL)
g = []; X0, X1, Y0, Y1 = 46, 420, 46, 200; n = len(QC); x = lambda i: X0 + (X1 - X0) * i / (n - 1); y = lambda v: Y1 - (Y1 - Y0) * v / 100
g.append(f'<text x="{X0}" y="17" class="gtit">Retorno LTM: Cury × Vivaz, %</text><text x="{X0}" y="32" class="gsub">Cury: ROE (lucro ÷ PL) e retorno operacional (antes de juros e IR); Vivaz: operacional, ITR</text>')
for t in (0, 25, 50, 75, 100): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
for i, q in enumerate(QC):
    if q.startswith("4T"): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">20{q[2:]}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
ser = [([C[q]["ret_op"] for q in QC], GR, 2.4, "5 3", "Cury operacional"), ([C[q]["roe"] for q in QC], GR, 2.6, "", "Cury ROE"), ([R["mcmv"].get(q) for q in QC], S1, 2.6, "", "Vivaz operacional")]
ends = []
for vals, col, w, dash, lab in ser:
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>'); ends.append([y(vals[-1]), col, f"{lab} {fmt(vals[-1])}%"])
ends.sort(key=lambda e: e[0])
for k in range(1, len(ends)):
    if ends[k][0] - ends[k - 1][0] < 13: ends[k][0] = ends[k - 1][0] + 13
for yy, col, lab in ends: g.append(f'<text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab}</text>')
X0, X1 = 600, 960; x = lambda i: X0 + (X1 - X0) * i / (n - 1); y2 = lambda v: Y1 - (Y1 - Y0) * (v + 60) / 220
g.append(f'<text x="{X0}" y="17" class="gtit">Alavancagem da Cury: quem financia o ativo, % do PL</text><text x="{X0}" y="32" class="gsub">terreno a prazo (credores por imóveis), adiantamento de clientes e dívida líquida (negativo = caixa)</text>')
for t in (-50, 0, 50, 100, 150): g.append(f'<line x1="{X0}" y1="{y2(t):.1f}" x2="{X1}" y2="{y2(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y2(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
for i, q in enumerate(QC):
    if q.startswith("4T"): g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">20{q[2:]}</text>')
g.append(f'<line x1="{X0}" y1="{y2(0):.1f}" x2="{X1}" y2="{y2(0):.1f}" stroke="var(--baseline)"/>')
ser2 = [([C[q]["cred_pl"] for q in QC], S3, 2.6, "", "terreno a prazo"), ([C[q]["adiant_pl"] for q in QC], S2, 2.2, "", "adiant. de clientes"), ([C[q]["dl_pl"] for q in QC], S1, 2.4, "", "dívida líquida")]
ends = []
for vals, col, w, dash, lab in ser2:
    pts = " ".join(f"{x(i):.1f},{y2(v):.1f}" for i, v in enumerate(vals)); g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>'); ends.append([y2(vals[-1]), col, f"{lab} {fmt(vals[-1])}%"])
ends.sort(key=lambda e: e[0])
for k in range(1, len(ends)):
    if ends[k][0] - ends[k - 1][0] < 13: ends[k][0] = ends[k - 1][0] + 13
for yy, col, lab in ends: g.append(f'<text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab}</text>')
svg = '<svg viewBox="0 0 1100 226" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabelas: DuPont e valor
rows = [("margem operacional (lucro operacional ÷ receita, LTM)", f"{fmt(cu['mg_op'])}%", f"{fmt(V['mg_op'])}%"), ("giro (receita LTM ÷ ativo)", f"{fmt(cu['giro'], 2)}x", f"{fmt(V['giro'], 2)}x"), ("ativo ÷ PL", f"{fmt(cu['at_pl'], 1)}x", f"{fmt(V['at_pl'], 1)}x"),
        ("retorno operacional s/ capital, LTM", f"{fmt(cu['ret_op'])}%", f"{fmt(V['ret_op'])}%"), ("dívida líquida ÷ PL", f"{fmt(cu['dl_pl'])}% (caixa)", "n.d. (segmento)"), ("terreno a prazo + adiantamentos ÷ PL", f"{fmt(cu['cred_pl'] + cu['adiant_pl'])}%", "n.d. (segmento)")]
t1 = '<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">DuPont, 2T26</th><th style="text-align:right;color:#2e7d32">Cury</th><th style="text-align:right;color:var(--s1)">Vivaz</th></tr></thead><tbody>' + "".join(f'<tr{" class=\"total\"" if "retorno" in a else ""}><td>{a}</td><td style="text-align:right">{b}</td><td style="text-align:right">{c}</td></tr>' for a, b, c in rows) + "</tbody></table>"
rows2 = [("preço e ações", f"R$ {fmt(MKT['CURY3'], 2)} × {fmt(MKT['acoes_cury'] / 1e6)} mi", "—"), ("valor de mercado", f"R$ {fmt(mc_cury, 1)} bi", f"R$ {fmt(val_viv, 1)} bi (implícito)"), ("PL (controladora)", f"R$ {fmt(pl_ctrl, 2)} bi", f"R$ {fmt(V['pl'], 2)} bi (segmento)"),
         ("ROE", f"{fmt(cu['roe'])}%", f"~{fmt(V['roe_est'])}% (op. {fmt(V['ret_op'])}% × {fmt(fator_ll, 2)})"), ("P/B de mercado", f"{fmt(pb_cury, 1)}x", "—"), (f"P/B por Gordon, Ke {fmt(MKT['ke'])}% e g {fmt(MKT['g'])}%", f"{fmt(pb_cury_g, 1)}x", f"{fmt(pb_viv, 1)}x"),
         ("Cyrela: valor de mercado", f"R$ {fmt(mc_cyre, 1)} bi (CYRE3 R$ {fmt(MKT['CYRE3'], 2)})", f"Vivaz = {fmt(100 * val_viv / mc_cyre)}% do valor com {fmt(100 * V['pl'] / (S[su]['cyrela']['pl'] + S[su]['living']['pl'] + S[su]['mcmv']['pl'] + S[su]['demais']['pl']) * 1000)}% do PL dos segmentos"), ("15,08% da Cury na mão da Cyrela", f"R$ {fmt(stake, 2)} bi", "—")]
t2 = '<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">valor</th><th style="text-align:right;color:#2e7d32">Cury</th><th style="text-align:right;color:var(--s1)">Vivaz</th></tr></thead><tbody>' + "".join(f'<tr{" class=\"total\"" if "Gordon" in a or "valor de mercado" == a else ""}><td>{a}</td><td style="text-align:right">{b}</td><td style="text-align:right">{c}</td></tr>' for a, b, c in rows2) + "</tbody></table>"
num = {"mc_cury": mc_cury, "pb_cury": pb_cury, "pb_cury_g": pb_cury_g, "roe_cury": cu["roe"], "ret_cury": cu["ret_op"], "dl_pl": cu["dl_pl"], "cred_pl": cu["cred_pl"], "adiant_pl": cu["adiant_pl"], "at_pl": cu["at_pl"], "at_pl_v": V["at_pl"], "mg_c": cu["mg_op"], "mg_v": V["mg_op"], "giro_c": cu["giro"], "giro_v": V["giro"],
       "roe_viv": V["roe_est"], "pb_viv": pb_viv, "val_viv": val_viv, "mc_cyre": mc_cyre, "stake": stake, "pl_viv": V["pl"], "fator_ll": fator_ll, "mkt": MKT, "u": u}
json.dump({"svg": svg, "t1": t1, "t2": t2, "num": num}, io.open(os.path.join(here, "_cury_valor_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in num.items() if k != "mkt"})
