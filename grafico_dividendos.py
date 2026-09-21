# -*- coding: utf-8 -*-
"""Dividendos da Cyrela: quanto foi pago, de onde saiu o caixa e o payout ajustado (2017-2T26).
 - Proventos: B3, proventos por ação com data ex (_cotacao_cyre3.json) × ações ex-tesouraria (_cvm_acoes.json / DFs), R$ mi, por ano da data ex.
 - Lucro atribuível: _dupont.json (ll_ltm em dezembro = ano; jun/26 = 12 meses).
 - Caixa de venda de participações: linha '(+) Aquisição/Venda de participação societária' da tabela de geração de caixa dos releases
   (_ger_caixa_release_clean.json 'part'; sinal invertido: entrada positiva). Caixa operacional = linha 'Geração/consumo de caixa
   operacional' (exclui participações; a companhia já exclui recompra).
 - Ganho contábil com participações: 2020 R$ 1.335 mi (marcação dos IPOs Cury/P&P/Lavvi + secundária, ledger _one_offs.json), 2022 R$ 139 mi
   (alienação de ações da Cury, release 3T22), 2024 ~R$ 135 mi (60 no 2T24 + ~75 no 3T24, ledger, estimado), 2025 R$ 240 mi (Cury, 3T25).
Saída: _dividendos_frag.json {svg, table, num}."""
import io, json, os, collections
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
C = J("_cotacao_cyre3.json"); ACV = J("_cvm_acoes.json"); DU = J("_dupont.json")["dados"]; G = J("_ger_caixa_release_clean.json")
SHY = {2011: 410668, 2012: 412106, 2013: 407260, 2014: 395417, 2015: 379000, 2016: 384400, 2017: 384400, 2018: 384400, 2019: 384400}
def sh(d):
    y = int(d[:4]); q = f"{(int(d[5:7]) - 1) // 3 + 1}T{d[2:4]}"; return ACV.get(q) or SHY.get(y, 384400) / 1000
DIV = collections.defaultdict(float); DIV12 = 0.0
for d, v, k in C["divs"]:
    if d >= "2017": DIV[d[:4]] += v * sh(d)
    if "2025-07-01" <= d <= "2026-06-30": DIV12 += v * sh(d)
ANOS = [str(a) for a in range(2017, 2026)]
LL = {a: DU[f"{a}-12"]["ll_ltm"] for a in ANOS}; LL12 = DU["2026-06"]["ll_ltm"]
PART = collections.defaultdict(float); OPER = collections.defaultdict(float)
for q, v in G["part"].items(): PART["20" + q[2:]] += -v
for q, v in G["oper"].items(): OPER["20" + q[2:]] += v
L4 = ("3T25", "4T25", "1T26", "2T26"); PART12 = sum(-G["part"].get(q, 0) for q in L4); OPER12 = sum(G["oper"].get(q, 0) for q in L4)
GAN = {"2020": 1335.0, "2022": 139.0, "2024": 135.0, "2025": 240.0}; GAN12 = 240.0
cols = ANOS + ["12m"]
def col(a, D, v12): return v12 if a == "12m" else D.get(a, 0.0)
def pay(a):
    d, l = col(a, DIV, DIV12), (LL12 if a == "12m" else LL[a]); return 100 * d / l if l > 0 else None
def pay_exg(a):
    d, l = col(a, DIV, DIV12), (LL12 if a == "12m" else LL[a]) - col(a, GAN, GAN12); return 100 * d / l if l > 0 else None
def pay_liq(a):
    d, l = col(a, DIV, DIV12) - col(a, PART, PART12), (LL12 if a == "12m" else LL[a]); return 100 * d / l if l > 0 else None
# ---- svg: (1) proventos × lucro por ano; (2) de onde saiu o caixa 2020-25; (3) payout: três leituras
g = []; Y0, Y1 = 46, 226
def axis(X0, X1, title, sub, ymin, ymax, ticks, tf):
    y = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
    g.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for t in ticks: g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    g.append(f'<line x1="{X0}" y1="{y(0):.1f}" x2="{X1}" y2="{y(0):.1f}" stroke="var(--baseline)"/>'); return y
def bars(X0, X1, keys, series, y, lab):
    n = len(keys); gw = (X1 - X0) / n; k = len(series); bw = gw * 0.8 / k
    for j, key in enumerate(keys):
        for i, (vals, colr, op) in enumerate(series):
            v = vals(key); x = X0 + gw * j + gw * 0.1 + i * bw
            if v is None: continue
            g.append(f'<rect x="{x:.1f}" y="{min(y(v), y(0)):.1f}" width="{bw-1:.1f}" height="{abs(y(v)-y(0)):.1f}" fill="{colr}" fill-opacity="{op}"/>')
        g.append(f'<text x="{X0 + gw * (j + 0.5):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lab(key)}</text>')
y = axis(44, 380, "Proventos e lucro por ano, R$ bi", "vinho: proventos (data ex); cinza: lucro atribuível; 12m = até jun/26", -0.2, 2.2, (0, 1, 2), lambda t: fmt(t))
bars(44, 380, cols, [(lambda a: col(a, DIV, DIV12) / 1000, S1, .9), (lambda a: (LL12 if a == "12m" else LL[a]) / 1000, MU, .6)], y, lambda a: a[2:] if a != "12m" else "12m")
y = axis(450, 740, "De onde saiu o caixa, R$ bi", "proventos (vinho), venda de participações (dourado), caixa operacional (azul)", -0.5, 1.5, (-0.5, 0, 0.5, 1, 1.5), lambda t: fmt(t, 1))
c2 = [a for a in cols if a == "12m" or a >= "2020"]
bars(450, 740, c2, [(lambda a: col(a, DIV, DIV12) / 1000, S1, .9), (lambda a: col(a, PART, PART12) / 1000, S3, .9), (lambda a: col(a, OPER, OPER12) / 1000, S2, .8)], y, lambda a: a[2:] if a != "12m" else "12m")
y = axis(830, 1030, "Payout, três leituras, %", "reportado; sem ganho com participações; líquido do caixa das sócias", 0, 100, (0, 25, 50, 75, 100), lambda t: f"{t:g}%")
c3 = [a for a in cols if a == "12m" or a >= "2019"]; n3 = len(c3); x3 = lambda i: 830 + 200 * i / (n3 - 1)
for f_, colr, dash, lab in ((pay, S1, "", "reportado"), (pay_exg, S3, "5 3", "sem ganhos"), (pay_liq, S2, "2 3", "líq. participações")):
    pts = [(x3(i), y(min(f_(a), 100))) for i, a in enumerate(c3) if f_(a) is not None]
    g.append(f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in pts)}" fill="none" stroke="{colr}" stroke-width="2.4"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round"/>')
    g.append(f'<text x="{pts[-1][0]+5:.1f}" y="{pts[-1][1]+4:.1f}" class="fw-t2" fill="{colr}">{lab} {fmt(f_(c3[-1]))}%</text>')
for i, a in enumerate(c3): g.append(f'<text x="{x3(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{a[2:] if a != "12m" else "12m"}</text>')
svg = '<svg viewBox="0 0 1150 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela
def cell(v, d=0, pct=False): return "—" if v is None else fmt(v, d) + ("%" if pct else "")
tc = ANOS[2:] + ["12m"]
def row(lab, f, cls="", pct=False, d=0):
    return f'<tr class="{cls}"><td>{lab}</td>' + "".join(f'<td style="text-align:right">{cell(f(a), d, pct)}</td>' for a in tc) + "</tr>"
table = ('<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">R$ mi</th>' + "".join(f'<th style="text-align:right">{a if a != "12m" else "12m 2T26"}</th>' for a in tc) + '</tr></thead><tbody>'
         + row("proventos declarados (data ex)", lambda a: col(a, DIV, DIV12), cls="total") + row("lucro líquido atribuível", lambda a: LL12 if a == "12m" else LL[a])
         + row("caixa de venda de participações (Cury, P&P, Lavvi)", lambda a: col(a, PART, PART12)) + row("ganho contábil com participações", lambda a: col(a, GAN, GAN12) or None)
         + row("caixa operacional (ex-participações e recompra)", lambda a: (OPER12 if a == "12m" else OPER.get(a)) if (a == "12m" or a >= "2020") else None)
         + row("payout sobre o lucro", pay, pct=True, cls="total") + row("payout sem os ganhos com participações", pay_exg, pct=True) + row("payout líquido do caixa das participações", pay_liq, pct=True) + "</tbody></table>")
tot = lambda D, ks: sum(D.get(a, 0) for a in ks); K = [a for a in ANOS if a >= "2019"]
num = {"div_tot": tot(DIV, K), "ll_tot": sum(LL[a] for a in K), "part_tot": tot(PART, K), "gan_tot": tot(GAN, K), "oper_tot": tot(OPER, K), "pay_tot": 100 * tot(DIV, K) / sum(LL[a] for a in K),
       "pay_exg_tot": 100 * tot(DIV, K) / (sum(LL[a] for a in K) - tot(GAN, K)), "pay_liq_tot": 100 * (tot(DIV, K) - tot(PART, K)) / sum(LL[a] for a in K), "div12": DIV12, "ll12": LL12, "pay12": pay("12m"), "pay12_exg": pay_exg("12m"),
       "div_2025": DIV["2025"], "pay_2025": pay("2025"), "pay_2025_exg": pay_exg("2025"), "pay_2025_liq": pay_liq("2025"), "preco": C["stats"]["preco_fim"], "preco_dt": C["stats"]["fim"]}
ps12 = sum(v / (1.18958333333 if d < "2026-01-02" else 1) for d, v, k in C["divs"] if d > C["stats"]["fim"][:4] + "-" + C["stats"]["fim"][5:] .replace(C["stats"]["fim"][5:], "") and False)
num["dy12"] = 100 * (2.72992121 / 1.18958333333) / C["stats"]["preco_fim"]   # único provento com data ex nos 12 meses até set/26: R$ 2,73/ação em 10/12/25, ajustado pela bonificação de jan/26
num["part_share"] = 100 * num["part_tot"] / num["div_tot"]; num["oper_share"] = 100 * num["oper_tot"] / tot(DIV, [a for a in K if a >= "2020"])
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_dividendos_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()})
