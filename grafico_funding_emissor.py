# -*- coding: utf-8 -*-
"""Funding imobiliário por banco, trimestral 2015-2026 (BCB IF.data): poupança, LCI e carteira habitacional PF.
Pergunta: a LCI veio para refinanciar o estoque de crédito que a poupança deixou de bancar?
Saída: funding_emissor.html (SVG inline, pequenos múltiplos, linhas independentes, R$ bi)."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(here, "_funding_emissor_trimestral.json"), encoding="utf-8"))["serie"]
HB = json.load(io.open(os.path.join(here, "_funding_emissor_hab_trimestral.json"), encoding="utf-8"))["serie"]
MS = sorted(m for m in D if m in HB and HB[m]["Sistema"]["hab_pf"] > 0)
for m in MS:   # carteira habitacional = PF (relatório 11, grupo Habitação) + PJ plano empresário (relatório 13, grupo Habitacional)
    for b in D[m]:
        D[m][b]["hab_pf"] = HB[m][b]["hab_pf"]; D[m][b]["hab_pj"] = HB[m][b]["hab_pj"]; D[m][b]["hab"] = D[m][b]["hab_pf"] + D[m][b]["hab_pj"]
BK = ["Caixa", "Bradesco", "Itaú", "Santander", "Banco do Brasil", "Sistema"]
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def panel(bank, ox, oy, w, h, ymax):
    X0, X1, Y0, Y1 = ox + 46, ox + w - 8, oy + 34, oy + h - 22
    def x(i): return X0 + (X1 - X0) * i / (len(MS) - 1)
    def y(v): return Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+46}" y="{oy+14}" class="pt">{bank}</text>']
    step = ymax / 4
    for k in range(5):
        t = k * step; g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="#ddd8cf"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="ax">{fmt(t)}</text>')
    for i, m in enumerate(MS):
        if m.endswith("-12") and int(m[:4]) % 2 == 1: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="ax">{m[2:4]}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#bfb8ab"/>')
    i22 = MS.index("2022-06"); g.append(f'<line x1="{x(i22):.1f}" y1="{Y0-4}" x2="{x(i22):.1f}" y2="{Y1}" stroke="#8a8378" stroke-dasharray="2 4" opacity=".7"/>')
    ser = [("hab_pf", "#2b2a26", 2.2, "carteira habitacional PF"), ("hab_pj", "#a07a12", 2.0, "carteira PJ (plano empresário)"), ("poup", "#2f5fa8", 2.2, "poupança"), ("lci", "#b3123f", 2.6, "LCI")]
    if bank == "Caixa": ser.append(("repasses", "#2e7d32", 2.2, "repasses (FGTS)"))
    for key, col, wd, lab in ser:
        pts = " ".join(f"{x(i):.1f},{y(D[m][bank][key]/1000):.1f}" for i, m in enumerate(MS))
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}" stroke-linejoin="round" stroke-linecap="round"/>')
    ends = sorted(((D[MS[-1]][bank][k] / 1000, k, col) for k, col, _, _ in ser), reverse=True); ys = []
    for v, k, col in ends:
        yy = y(v)
        for p in ys:
            if abs(yy - p) < 11: yy = p + 11
        ys.append(yy); g.append(f'<text x="{X1-2}" y="{yy-5:.1f}" text-anchor="end" class="lb" fill="{col}">{fmt(v)}</text>')
    return "".join(g)
W = 1060; PW, PH = 353, 200
YM = {"Caixa": 1000, "Bradesco": 250, "Itaú": 250, "Santander": 125, "Banco do Brasil": 250, "Sistema": 1250}
g = []
for n, b in enumerate(BK):
    g.append(panel(b, (n % 3) * PW, 40 + (n // 3) * PH, PW, PH, YM[b]))
g.append('<text x="46" y="18" class="tit">Poupança, LCI, repasses e carteira habitacional PF e PJ por banco (R$ bi, trimestral)</text>')
g.append(f'<text x="46" y="32" class="sub">BCB IF.data, prudenciais; tracejado = jun/22; escalas próprias; poupança inclui rural. <tspan fill="#2b2a26" font-weight="700">■</tspan> hab. PF  <tspan fill="#a07a12" font-weight="700">■</tspan> hab. PJ (plano empresário)  <tspan fill="#2f5fa8" font-weight="700">■</tspan> poupança  <tspan fill="#b3123f" font-weight="700">■</tspan> LCI  <tspan fill="#2e7d32" font-weight="700">■</tspan> repasses (Caixa = FGTS)</text>')
svg = f'<svg viewBox="0 0 {W} {40 + 2 * PH + 6}" xmlns="http://www.w3.org/2000/svg">' + "".join(g) + "</svg>"
# tabela: variação jun/22 → jun/26 e dez/15 → jun/22
def dlt(b, a, z, k): return (D[z][b][k] - D[a][b][k]) / 1000
rows = []
for b in BK:
    r1 = (dlt(b, "2015-12", "2022-06", "hab"), dlt(b, "2015-12", "2022-06", "poup"), dlt(b, "2015-12", "2022-06", "lci"))
    r2 = (dlt(b, "2022-06", MS[-1], "hab"), dlt(b, "2022-06", MS[-1], "poup"), dlt(b, "2022-06", MS[-1], "lci"))
    rows.append((b, r1, r2))
tb = "".join(f"<tr><td>{b}</td>" + "".join(f"<td class='n'>{fmt(v, 0)}</td>" for v in r1) + "".join(f"<td class='n b'>{fmt(v, 0)}</td>" for v in r2) + f"<td class='n b'>{fmt(100 * r2[2] / r2[0]) if r2[0] else '-'}%</td></tr>" for b, r1, r2 in rows)
cx = [r for r in rows if r[0] == "Caixa"][0]; sx = [r for r in rows if r[0] == "Sistema"][0]
html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Funding por banco</title>
<style>
body{{margin:0;background:#f7f5f0;color:#2b2a26;font-family:"Inter",system-ui,Segoe UI,Arial,sans-serif;padding:28px 32px}}
.wrap{{max-width:1080px;margin:0 auto}} h1{{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:30px;margin:0 0 4px;letter-spacing:-.01em}}
p.k{{color:#8a8378;font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px}}
svg{{width:100%;height:auto;display:block}} .ax{{font-size:10px;fill:#8a8378}} .lb{{font-size:11px;font-weight:600}} .pt{{font-size:13px;font-weight:700;fill:#2b2a26;font-family:"Fraunces",Georgia,serif}}
.tit{{font-size:15px;font-weight:700;fill:#2b2a26;font-family:"Fraunces",Georgia,serif}} .sub{{font-size:11px;fill:#8a8378}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;margin-top:14px}} th,td{{padding:5px 8px;border-bottom:1px solid #e3ded4;text-align:left}} th{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#8a8378;text-align:right}} th:first-child{{text-align:left}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}} td.b{{font-weight:600}} th.g{{border-left:2px solid #bfb8ab}} td.g{{border-left:2px solid #bfb8ab}}
.out{{margin-top:14px;padding:10px 14px;border-left:5px solid #2e7d32;background:rgba(46,125,50,.08);border-radius:10px;font-size:14px}}
.fn{{font-size:11px;color:#8a8378;margin-top:12px;line-height:1.4}}
</style></head><body><div class="wrap">
<p class="k">Cyrela · anexo · funding</p><h1>A LCI veio refinanciar o estoque? Poupança, LCI e carteira habitacional (PF + PJ), banco a banco.</h1>
{svg}
<table><thead><tr><th>Δ R$ bi</th><th>hab. PF+PJ dez/15→jun/22</th><th>poupança</th><th>LCI</th><th class="g">hab. PF+PJ jun/22→jun/26</th><th>poupança</th><th>LCI</th><th>LCI ÷ Δhab.</th></tr></thead><tbody>{tb}</tbody></table>
<div class="out"><b>O que fica:</b> em 2015-22 a poupança financiou sozinha o crescimento da carteira (sistema: carteira +R$ {fmt(sx[1][0])} bi, poupança +R$ {fmt(sx[1][1])} bi, LCI {fmt(sx[1][2])}). Em jun/22-jun/26 a carteira cresceu R$ {fmt(sx[2][0])} bi com poupança parada (+{fmt(sx[2][1])}) e a LCI entrou com R$ {fmt(sx[2][2])} bi, {fmt(100 * sx[2][2] / sx[2][0])}% do crescimento. Nos privados a resposta à pergunta é sim em parte: Itaú, Bradesco e Santander perderam R$ 13, 13 e 10 bi de poupança e repuseram com LCI (+60, +33 e +20), ou seja, a LCI cobriu a saída da poupança do estoque antigo e financiou o crédito novo. Na Caixa a poupança não caiu (+R$ {fmt(cx[2][1])} bi); a carteira cresceu R$ {fmt(cx[2][0])} bi e a LCI (+R$ {fmt(cx[2][2])} bi) mais o FGTS (+~R$ 240 bi) mais a poupança somam mais que isso: a Caixa captou LCI além do que o crédito habitacional pediu, e o excedente financia o resto do balanço.</div>
<p class="fn">Fontes: BCB, IF.data (API Olinda), tipo 1 (conglomerados prudenciais e instituições independentes): relatório 3 "Passivo" (Depósitos de Poupança a2, inclui poupança rural; Letras de Crédito Imobiliário c1) relatório 3 coluna (d) "Obrigações por Empréstimos e Repasses" (na Caixa, essencialmente os repasses do FGTS), relatório 11 "Carteira de crédito ativa PF por modalidade" (Habitação, Total) e relatório 13 "Carteira PJ por modalidade" (Habitacional, Total: plano empresário). Trimestral mar/15 a jun/26 (_funding_emissor_trimestral.json e _funding_emissor_pj_trimestral.json, R$ mi). A carteira habitacional da Caixa inclui os financiamentos com recursos do FGTS. Até dez/24 os relatórios de carteira existem só para conglomerados financeiros (tipo 2) e a partir de mar/25 só para prudenciais (tipo 1): há um degrau em dez/24 (Itaú R$ 180 bi contra R$ 119 bi em set/24 e R$ 131 bi em mar/25) que é de consolidação, não de crédito.</p>
</div></body></html>"""
io.open(os.path.join(here, "funding_emissor.html"), "w", encoding="utf-8").write(html)
print("ok", MS[0], MS[-1], {b: (round(D[MS[-1]][b]["hab"] / 1000), round(D[MS[-1]][b]["poup"] / 1000), round(D[MS[-1]][b]["lci"] / 1000)) for b in BK})
