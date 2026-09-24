# -*- coding: utf-8 -*-
"""Valuation (pedido de 24/09/26): lucro líquido projetado 2027-31 linha a linha a partir do lucro bruto do modelo de caixa
(_caixa_proj_frag.json: SG&A, financeiro, outras, equivalência, IR corrente e diferido, minoritários em % da receita no nível 2023-LTM,
conferido no LTM), fluxo de caixa ao acionista = geração de caixa operacional projetada (já inclui financeiro, dividendos de JVs,
investimentos e minoritários), VPL a Ke e g do usuário (17% e 4%, memória), valor terminal sobre 2031, menos dívida líquida de 2T26.
Seis combinações: três cenários de lançamento × permuta ou terreno em caixa; mais Vivaz +30 pp. Saída: _valuation_frag.json."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0):
    v = v if abs(v) >= 0.5 * 10 ** (-d) else 0.0
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2, GR = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)", "#2e7d32"
PJ = J("_caixa_proj_frag.json")["proj"]; E = J("_econ_trimestral.json"); B = J("_balanco_cvm.json"); MK = J("_cury_valor_frag.json")["num"]["mkt"]; C = J("_caixa_reconc_frag.json")
ORD = lambda q: (int(q[2:]), int(q[0])); Q = sorted([q for q in E if "T" in q and E[q].get("rec")], key=ORD)
def s(k, qs): return sum((E[q].get(k) or 0) for q in qs)
H = [f"{i}T{y}" for y in ("23", "24", "25") for i in range(1, 5)] + Q[-2:]   # 2023-LTM (1T23-2T26)
REC = s("rec", H); PR = {"sga": -(s("vendas", H) + s("adm", H)) / REC, "outras": (s("outras_rec", H) - s("outras_desp", H)) / REC, "fin": s("fin", H) / REC, "equiv": s("equiv", H) / REC, "ir_corr": -s("ir_corr", H) / REC, "ir_dif": -s("ir_dif", H) / REC, "minor": -s("minor_ll", H) / REC}
L4 = Q[-4:]; LTM = {"rec": s("rec", L4), "lb": s("rec", L4) - s("cpv", L4), "sga": -(s("vendas", L4) + s("adm", L4)), "outras": s("outras_rec", L4) - s("outras_desp", L4), "fin": s("fin", L4), "equiv": s("equiv", L4), "ir_corr": -s("ir_corr", L4), "ir_dif": -s("ir_dif", L4), "minor": -s("minor_ll", L4), "ll": s("ll", L4)}
KE, G, NSH, PX = MK["ke"] / 100, MK["g"] / 100, MK["acoes_cyre"] / 1e6, MK["CYRE3"]
b = B["2T26"]; DL = sum(b.get(k) or 0 for k in ("emp_cp", "deb_cp", "cri_cp", "emp_lp", "deb_lp", "cri_lp")) - sum(b.get(k) or 0 for k in ("caixa", "aplic_cp_vjr", "aplic_cp_vjora", "aplic_cp_ca", "aplic_lp_vjr", "aplic_lp_vjora", "aplic_lp_ca"))
PL = b["pl_consolidado"]; YS = [2027, 2028, 2029, 2030, 2031]
def dre(key):
    out = {}
    for y in YS:
        p = PJ[key][str(y)]; rec = p["receita"]; r = {"rec": rec, "lb": p["lucro_bruto"]}
        for k in ("sga", "outras", "fin", "equiv", "ir_corr", "ir_dif", "minor"): r[k] = PR[k] * rec
        r["ll"] = r["lb"] + sum(r[k] for k in ("sga", "outras", "fin", "equiv", "ir_corr", "ir_dif", "minor")); r["caixa"] = p["caixa"]; out[y] = r
    return out
SC = [("ltm", "+5% s/ LTM"), ("2025", "+5% s/ 2025"), ("lstar", "lançar o que vende (L*)"), ("ltm+30", "LTM, Vivaz +30 pp")]
VAL = {}
for key, lab in SC:
    d = dre(key); pv = sum(d[y]["caixa"] / (1 + KE) ** (i + 1) for i, y in enumerate(YS)); tv = d[2031]["caixa"] * (1 + G) / (KE - G); pvtv = tv / (1 + KE) ** 5
    eq = pv + pvtv - DL; VAL[key] = {"lab": lab, "dre": d, "pv": pv, "tv": tv, "pvtv": pvtv, "dl": DL, "eq": eq, "ps": eq / NSH, "vs_px": eq / NSH / PX - 1, "pe27": PX * NSH / d[2027]["ll"], "pe29": PX * NSH / d[2029]["ll"], "pb": PX * NSH / PL}
BASE = VAL["ltm"]; D = BASE["dre"]
# ---- svg: painel 1 DRE projetada (base) barras LB e LL; painel 2 VPL por ação por cenário × preço
g = []
X0, X1, Y0, Y1 = 44, 400, 40, 161; ymx = 6000; xg = (X1 - X0) / (len(YS) + 1); yv = lambda v: Y1 - (Y1 - Y0) * v / ymx   # 25/09/26: 44/176 -> 40/161 (svg 205 -> 190) sem clipar os rótulos de 2 linhas do eixo x
g.append(f'<text x="{X0}" y="17" class="gtit">Lucro bruto e lucro líquido projetados, R$ mi</text><text x="{X0}" y="32" class="gsub">+5% s/ LTM; linhas abaixo do lucro bruto em % da receita (2023-LTM)</text>')
for tv_ in (0, 2000, 4000, 6000): g.append(f'<line x1="{X0}" y1="{yv(tv_):.1f}" x2="{X1}" y2="{yv(tv_):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{yv(tv_)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(tv_)}</text>')
cols = [("LTM", LTM["lb"], LTM["ll"])] + [(str(y), D[y]["lb"], D[y]["ll"]) for y in YS]
for i, (lab, lb, ll) in enumerate(cols):
    x = X0 + xg * i + xg * 0.1; w = xg * 0.38
    g.append(f'<rect x="{x:.1f}" y="{yv(lb):.1f}" width="{w:.1f}" height="{Y1-yv(lb):.1f}" fill="{S3}" fill-opacity="{.5 if lab == "LTM" else .9}"/><text x="{x+w/2:.1f}" y="{yv(lb)-4:.1f}" text-anchor="middle" class="axq" fill="{I2}" style="font-size:9px">{fmt(lb)}</text>')
    g.append(f'<rect x="{x+w+2:.1f}" y="{yv(ll):.1f}" width="{w:.1f}" height="{Y1-yv(ll):.1f}" fill="{S1}" fill-opacity="{.5 if lab == "LTM" else .9}"/><text x="{x+w*1.5+2:.1f}" y="{yv(ll)-4:.1f}" text-anchor="middle" class="axq" fill="{I2}" style="font-size:9px">{fmt(ll)}</text>')
    g.append(f'<text x="{x+w+1:.1f}" y="{Y1+13}" text-anchor="middle" class="axq" opacity=".8">{lab}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/><text x="{X0}" y="{Y1+26}" class="axq" opacity=".8">dourado: lucro bruto · vinho: lucro líquido</text>')
# painel 2
ox = 440; bx0, bx1 = ox + 44, 1060 - 20; items = [(k, VAL[k]) for k, _ in SC]; nb = len(items); gb = (bx1 - bx0) / nb; vmx = 60; yb = lambda v: Y1 - (Y1 - Y0) * v / vmx
g.append(f'<text x="{bx0}" y="17" class="gtit">VPL por ação por cenário, R$</text><text x="{bx0}" y="32" class="gsub">fluxo 2027-31 + perpetuidade (g {fmt(100*G)}%), Ke {fmt(100*KE)}%, menos dívida líquida; tracejado = preço</text>')
for tv_ in (0, 20, 40, 60): g.append(f'<line x1="{bx0}" y1="{yb(tv_):.1f}" x2="{bx1}" y2="{yb(tv_):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{bx0-5}" y="{yb(tv_)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tv_}</text>')
SH = {"ltm": "+5% s/ LTM", "2025": "+5% s/ 2025", "lstar": "lançar o que vende", "ltm+30": "LTM, Vivaz +30 pp"}
for i, (k, v) in enumerate(items):
    x = bx0 + gb * i + gb * 0.15; w = gb * 0.7; col = S3
    yt = yb(max(v["ps"], 0)); inside = (yt - 13) < (yb(PX) + 2)   # 25/09/26: rótulo colidia com o tracejado do preço -> dentro da barra, em branco, quando encostaria na linha
    g.append(f'<rect x="{x:.1f}" y="{yt:.1f}" width="{w:.1f}" height="{abs(yt - yb(0)):.1f}" fill="{col}"/>' + (f'<text x="{x+w/2:.1f}" y="{yt+12:.1f}" text-anchor="middle" class="fw-s2" style="fill:#fff;font-weight:700;font-size:11px">{fmt(v["ps"], 1)}</text>' if inside else f'<text x="{x+w/2:.1f}" y="{yt-4:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(v["ps"], 1)}</text>'))
    g.append(f'<text x="{x+w/2:.1f}" y="{Y1+13}" text-anchor="middle" class="axq" opacity=".8" style="font-size:9px">{SH[k]}</text>')
g.append(f'<line x1="{bx0}" y1="{yb(PX):.1f}" x2="{bx1}" y2="{yb(PX):.1f}" stroke="{I2}" stroke-dasharray="4 3"/><text x="{bx0+3}" y="{yb(PX)-4:.1f}" class="fw-s2" fill="{I2}">preço {fmt(PX, 2)}</text>')
g.append(f'<line x1="{bx0}" y1="{Y1}" x2="{bx1}" y2="{Y1}" stroke="var(--baseline)"/>')
svg = '<svg viewBox="0 0 1060 190" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela 1: DRE projetada (base) + caixa; tabela 2: VPL por cenário
PAD = "padding:0 8px"
def c(v, d=0, s_=""): return f'<td style="text-align:right;{PAD}">{fmt(v, d)}{s_}</td>'
LAB = [("rec", "receita líquida", None), ("lb", "lucro bruto (modelo de caixa)", None), ("sga", "despesas comerciais e administrativas", "sga"), ("outras", "outras receitas/despesas", "outras"), ("fin", "resultado financeiro", "fin"), ("equiv", "equivalência patrimonial (Cury, Lavvi, P&P)", "equiv"), ("ir_corr", "IR/CS corrente", "ir_corr"), ("ir_dif", "IR/CS diferido", "ir_dif"), ("minor", "minoritários", "minor"), ("ll", "= lucro líquido", None), ("caixa", "geração de caixa operacional (modelo)", None)]
rows = []
for k, lab, pk in LAB:
    prem = f"{fmt(100 * PR[pk], 1)}% da receita" if pk else ("modelo de lançamentos" if k in ("rec", "lb") else "")
    rows.append(f'<tr{" style=\"font-weight:700\"" if k in ("lb", "ll", "caixa") else ""}><td style="text-align:left;{PAD}">{lab}</td><td style="text-align:right;{PAD};color:var(--muted)">{prem}</td>{c(LTM[k] if k != "caixa" else C["num"]["cia"])}' + "".join(c(D[y][k]) for y in YS) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD}">lucro por ação, R$</td><td></td>{c(LTM["ll"] / NSH, 2)}' + "".join(c(D[y]["ll"] / NSH, 2) for y in YS) + '</tr>')
rows.append(f'<tr><td style="text-align:left;{PAD}">P/L ao preço de {fmt(PX, 2)}</td><td></td>{c(PX * NSH / LTM["ll"], 1, "x")}' + "".join(c(PX * NSH / D[y]["ll"], 1, "x") for y in YS) + '</tr>')
table = ('<table class="tl compact" style="margin-top:0;width:100%;font-size:9px"><thead><tr><th style="text-align:left;' + PAD + '">R$ mi · cenário +5% s/ LTM, permuta</th><th style="text-align:right;' + PAD + '">premissa</th><th style="text-align:right;' + PAD + '">LTM 2T26</th>' + "".join(f'<th style="text-align:right;{PAD}">{y}E</th>' for y in YS) + '</tr></thead><tbody>' + "".join(rows) + '</tbody></table>')
rows2 = []
for k, lab in SC:
    v = VAL[k]; rows2.append(f'<tr><td style="text-align:left;{PAD}">{lab}</td>' + "".join(c(v["dre"][y]["caixa"]) for y in YS) + c(v["pv"]) + c(v["pvtv"]) + c(-v["dl"]) + c(v["eq"]) + f'<td style="text-align:right;{PAD};font-weight:700">{fmt(v["ps"], 1)}</td>' + c(100 * v["vs_px"], 0, "%") + '</tr>')
table2 = ('<table class="tl compact" style="margin-top:2px;width:100%;font-size:9px"><thead><tr><th style="text-align:left;' + PAD + '">fluxo ao acionista, R$ mi</th>' + "".join(f'<th style="text-align:right;{PAD}">{y}E</th>' for y in YS) + f'<th style="text-align:right;{PAD}">VP 27-31</th><th style="text-align:right;{PAD}">VP perpet.</th><th style="text-align:right;{PAD}">− dív. líq.</th><th style="text-align:right;{PAD}">equity</th><th style="text-align:right;{PAD}">R$/ação</th><th style="text-align:right;{PAD}">vs preço</th></tr></thead><tbody>' + "".join(rows2) + '</tbody></table>')
num = {"ke": 100 * KE, "g": 100 * G, "px": PX, "nsh": NSH, "dl": DL, "pl": PL, "mc": PX * NSH, "pb": PX * NSH / PL, "ll_ltm": LTM["ll"], "pe_ltm": PX * NSH / LTM["ll"], "pr": {k: 100 * v for k, v in PR.items()},
       "ll27": D[2027]["ll"], "ll29": D[2029]["ll"], "ll31": D[2031]["ll"], "lpa27": D[2027]["ll"] / NSH, "lpa29": D[2029]["ll"] / NSH, "pe27": BASE["pe27"], "pe29": BASE["pe29"], "ll_lb_27": 100 * D[2027]["ll"] / D[2027]["lb"], "conv_ll_27_31": 100 * sum(D[y]["caixa"] for y in YS) / sum(D[y]["ll"] for y in YS)}
def ps_at(key, ke, g=G):
    d = VAL[key]["dre"]; pv = sum(d[y]["caixa"] / (1 + ke) ** (i + 1) for i, y in enumerate(YS)); tv = d[2031]["caixa"] * (1 + g) / (ke - g); return (pv + tv / (1 + ke) ** 5 - DL) / NSH
num["sens"] = {f"{key}@{int(100*ke)}": ps_at(key, ke) for key in ("ltm", "lstar") for ke in (0.13, 0.15, 0.17, 0.19)}
KES = [0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.20]; GS = [0.02, 0.03, 0.04, 0.05, 0.06]
grid = {ke: {g_: ps_at("ltm", ke, g_) for g_ in GS} for ke in KES}
table3 = ('<table class="tl compact" style="margin-top:4px;width:100%;font-size:9px"><thead><tr><th style="text-align:left;' + PAD + '">R$/ação, +5% s/ LTM: Ke ↓ · g →</th>' + "".join(f'<th style="text-align:right;{PAD}">{fmt(100*g_)}%</th>' for g_ in GS) + '</tr></thead><tbody>'
          + "".join(f'<tr><td style="text-align:left;{PAD}{";font-weight:700" if abs(ke - KE) < 1e-9 else ""}">Ke {fmt(100*ke)}%</td>' + "".join(f'<td style="text-align:right;{PAD}{";font-weight:700;color:var(--s3)" if abs(ke - KE) < 1e-9 and abs(g_ - G) < 1e-9 else ""}">{fmt(grid[ke][g_], 1)}</td>' for g_ in GS) + '</tr>' for ke in KES) + '</tbody></table>')
num["sens_grid"] = {f"{int(100*ke)}|{int(100*g_)}": v for ke, d in grid.items() for g_, v in d.items()}
num["sens_g"] = {f"ltm@g{int(100*g)}": ps_at("ltm", KE, g) for g in (0.02, 0.04, 0.06)}
for k, _ in SC:
    kk = k.replace("|caixa", "_tc").replace("+", "p"); num[f"ps_{kk}"] = VAL[k]["ps"]; num[f"vs_{kk}"] = 100 * VAL[k]["vs_px"]; num[f"eq_{kk}"] = VAL[k]["eq"]; num[f"pvtv_{kk}"] = VAL[k]["pvtv"]; num[f"pv_{kk}"] = VAL[k]["pv"]
json.dump({"svg": svg, "table": table, "table2": table2, "table3": table3, "num": num, "val": {k: {kk: (vv if not isinstance(vv, dict) else {str(y): r for y, r in vv.items()}) for kk, vv in v.items()} for k, v in VAL.items()}}, io.open(os.path.join(here, "_valuation_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items() if k != "pr"}); print("premissas %:", {k: round(v, 1) for k, v in num["pr"].items()})
