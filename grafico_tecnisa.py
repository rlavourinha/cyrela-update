# -*- coding: utf-8 -*-
"""Tecnisa (TCSA3): valor de mercado mensal 2015-2026 e o valor da posição da Cyrela, com os eventos
corporativos entre as duas. Saída: tecnisa_mcap.html (SVG inline, sem dependência externa).
Fontes: B3 COTAHIST (fechamento do último pregão do mês, sem ajuste); FR 2026 da Tecnisa item 1.1 (aumentos de capital
2016/2017/2019, grupamento 10:1 de 05/05/2020); fato relevante de 28/08/2026 (73.619.230 ações; novo grupamento);
DFP 2021 da Tecnisa nota 10 (debênture 5ª emissão, 140% do CDI, R$ 70 mi, jul/17-jul/21); notas de investimentos ao
valor justo dos ITR/DFP da Cyrela (ações detidas por trimestre, 2018-2T26); releases da Cyrela 3T16-2T20."""
import io, json, math, os, shutil
here = os.path.dirname(os.path.abspath(__file__))
SRC = r"C:\Users\RLAVOU~1\AppData\Local\Temp\claude\D--rlavourinha-Pictures-OneDrive--rea-de-Trabalho-Claude\e4e1cc5f-6e04-4e22-ba8b-ce88f93cdefb\scratchpad\tcsa3_mensal.json"
DST = os.path.join(here, "_tcsa3_mensal.json")
if os.path.exists(SRC): shutil.copy(SRC, DST)
PX = json.load(io.open(DST, encoding="utf-8"))
MS = sorted(PX)

# ações da Tecnisa (mil): 37.252.984 = 13,62% em out/16 → 273.516 mil após +100.000 mil; +57.692 mil em mai/17; +405.000 mil em jul/19; grupamento 10:1 (ex jun/20)
def sh_tec(m):
    if m < "2016-10": return 173516
    if m < "2017-05": return 273516
    if m < "2019-07": return 331208
    if m < "2020-06": return 736192
    return 73619.23
# ações da Cyrela na Tecnisa (mil) — notas dos ITR/DFP da Cyrela; entre datas, degrau na data do evento conhecido
def sh_cyr(m):
    if m < "2016-10": return 0
    if m < "2017-05": return 37253
    if m < "2017-10": return 45111
    if m < "2019-01": return 25440      # 25.439.958 em 31/12/18 (vendas no 2S17)
    if m < "2019-12": return 24839      # 11/01/19: 24.839.000 (7,49%)
    if m < "2020-03": return 23971      # 31/12/19
    if m < "2020-06": return 10185      # 31/03/20, após venda de R$ 28 mi
    if m < "2023-12": return 1018.48    # pós-grupamento 10:1
    if m < "2024-03": return 758.32
    if m < "2026-03": return 702.82
    return 5.155
mcap = {m: sh_tec(m) * PX[m][1] / 1000 for m in MS}          # R$ mi
pos = {m: sh_cyr(m) * PX[m][1] / 1000 for m in MS if sh_cyr(m) > 0 and m <= "2025-12"}   # R$ mi (para em dez/25: R$ 0,8 mi; jun/26 = R$ 4 mil)

EV = [  # (mês, rótulo curto, texto)
 ("2016-10", "1", "out/16 · Cyrela subscreve 37,3 mi ações a R$ 2,00 na capitalização privada de R$ 200 mi: R$ 74,5 mi, 13,6%, acordo de acionistas com a família Nigri"),
 ("2017-05", "2", "mai/17 · segunda capitalização (R$ 150 mi a R$ 2,60): Cyrela põe mais R$ 20,4 mi e mantém 13,6%"),
 ("2017-07", "3", "jul/17 · Tecnisa emite R$ 70 mi em debêntures a 140% do CDI (5ª emissão, garantia real, vence jul/21); a Cyrela fica com ~R$ 20 mi via CRI"),
 ("2017-10", "4", "2S17 · Cyrela vende 19,7 mi ações a mercado (45,1 → 25,4 mi; TCSA3 entre R$ 2,2 e 2,4); entradas citadas nos releases 3T17 e 4T17"),
 ("2019-01", "5", "jan/19 · vende 0,6 mi ações e cai a 7,49%: o acordo de acionistas se extingue"),
 ("2019-07", "6", "jul/19 · follow-on de 405 mi ações a R$ 1,10 (R$ 445 mi); a Cyrela não acompanha e é diluída a 3,3%"),
 ("2020-03", "7", "1T20 · Cyrela vende ~13,8 mi ações por R$ 28 mi; sobra 10,2 mi (R$ 7,5 mi a R$ 0,74)"),
 ("2020-06", "8", "mai/20 · grupamento 10:1 (AGE 05/05/20): 73,6 mi ações"),
 ("2021-07", "9", "jul/21 · debênture a 140% do CDI liquidada no vencimento (DFP 2021 da Tecnisa)"),
 ("2025-09", "10", "3T25 · compra do terreno Jardim das Perdizes pela Cyrela cancelada (call 3T25)"),
 ("2026-06", "11", "fev-jun/26 · BTG compra 26,09% do Jardim das Perdizes por R$ 260,9 mi (fatos relevantes 23/02, 25/02, 30/04 e 01/06/26); Cyrela zera a posição no 1S26"),
 ("2026-09", "12", "set/26 · novo grupamento 10:1 proposto (fato relevante 28/08/26, AGE 21/09)"),
]

W, H = 1060, 400
X0, X1, Y0, Y1 = 62, 900, 100, 345
LMIN, LMAX = math.log10(0.5), math.log10(3000)
def x(i): return X0 + (X1 - X0) * i / (len(MS) - 1)
def y(v): return Y1 - (Y1 - Y0) * (math.log10(v) - LMIN) / (LMAX - LMIN)
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
g = []
for t in (1, 10, 100, 1000):
    g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="#ddd8cf"/><text x="{X0-8}" y="{y(t)+4:.1f}" text-anchor="end" class="ax">{fmt(t)}</text>')
for i, m in enumerate(MS):
    if m.endswith("-01"): g.append(f'<text x="{x(i):.1f}" y="{Y1+18}" text-anchor="middle" class="ax">{m[:4]}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#bfb8ab"/>')
# eventos
for k, (m, lab, _) in enumerate(EV):
    i = MS.index(m); xx = x(i); cy = Y0 - 22 - (20 if k % 2 else 0)   # badges em duas alturas para não encavalar
    g.append(f'<line x1="{xx:.1f}" y1="{cy+9}" x2="{xx:.1f}" y2="{Y1}" stroke="#8a8378" stroke-dasharray="2 4" opacity=".7"/>')
    g.append(f'<circle cx="{xx:.1f}" cy="{cy}" r="9" fill="#2b2a26"/><text x="{xx:.1f}" y="{cy+3.5}" text-anchor="middle" class="bd">{lab}</text>')
def poly(d, col, w, dash=""):
    pts = " ".join(f"{x(MS.index(m)):.1f},{y(v):.1f}" for m, v in sorted(d.items()))
    return f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{" stroke-dasharray=" + chr(34) + dash + chr(34) if dash else ""}/>'
g.append(poly(mcap, "#2f5fa8", 2.4)); g.append(poly(pos, "#b3123f", 2.2))
# rótulos de fim de linha
lm = MS[-1]; g.append(f'<circle cx="{x(len(MS)-1):.1f}" cy="{y(mcap[lm]):.1f}" r="3.5" fill="#2f5fa8"/><text x="{X1+7}" y="{y(mcap[lm])+4:.1f}" class="lb" fill="#2f5fa8">valor de mercado</text><text x="{X1+7}" y="{y(mcap[lm])+18:.1f}" class="lb" fill="#2f5fa8">R$ {fmt(mcap[lm])} mi (set/26)</text>')
pm = max(pos); g.append(f'<circle cx="{x(MS.index(pm)):.1f}" cy="{y(pos[pm]):.1f}" r="3.5" fill="#b3123f"/><text x="{x(MS.index(pm))+8:.1f}" y="{y(pos[pm])+4:.1f}" class="lb" fill="#b3123f">posição da Cyrela</text><text x="{x(MS.index(pm))+8:.1f}" y="{y(pos[pm])+18:.1f}" class="lb" fill="#b3123f">R$ {fmt(pos[pm], 1)} mi (dez/25) → R$ 4 mil (jun/26)</text>')
# rótulos de pontos-chave
for m, txt, dy in (("2016-10", f"R$ {fmt(mcap['2016-10'])} mi", -10), ("2019-12", f"pico R$ {fmt(mcap['2019-12'])} mi", -10), ("2017-06", f"R$ {fmt(pos['2017-06'])} mi", -10), ("2020-03", f"R$ {fmt(pos['2020-03'], 1)} mi", 14)):
    d = mcap if "mcap" in txt or txt.startswith("pico") or m == "2016-10" else pos
    g.append(f'<text x="{x(MS.index(m)):.1f}" y="{y(d[m])+dy:.1f}" text-anchor="middle" class="lb" fill="{"#2f5fa8" if d is mcap else "#b3123f"}">{txt}</text>')
g.append(f'<text x="{X0}" y="22" class="tit">Tecnisa: valor de mercado e o que a posição da Cyrela valia (R$ mi, escala log)</text>')
g.append(f'<text x="{X0}" y="38" class="sub">fechamento mensal TCSA3 (B3) × ações em circulação; posição da Cyrela pelas notas dos ITR (ações detidas × cotação)</text>')
svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(g) + "</svg>"

# tabela: entradas e saídas da Cyrela
ROWS = [
 ("out/16", "subscrição", "37,25 mi", "R$ 2,00", "−74,5", "fixado na oferta"),
 ("mai/17", "subscrição", "7,86 mi", "R$ 2,60", "−20,4", "fixado na oferta"),
 ("2S17", "venda a mercado", "19,67 mi", "R$ 2,2-2,4", "≈ +45", "preço não divulgado; cotações de set-dez/17"),
 ("jan/19", "venda a mercado", "0,60 mi", "R$ 1,58", "≈ +1", "fechamento de 11/01/19"),
 ("2019", "venda a mercado", "0,87 mi", "≈ R$ 1,5", "≈ +1", "24,84 → 23,97 mi ações"),
 ("1T20", "venda a mercado", "13,79 mi", "≈ R$ 2,0", "+28", "release 1T20"),
 ("4T23-1T24", "venda a mercado", "0,32 mi (pós-grup.)", "R$ 3-4", "≈ +1", "1,018 → 0,703 mi ações"),
 ("1S26", "venda a mercado", "0,70 mi (pós-grup.)", "≈ R$ 1,2", "≈ +1", "0,703 mi → 5.155 ações"),
]
tb = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td class='n'>{e}</td><td class='o'>{f}</td></tr>" for a, b, c, d, e, f in ROWS)
html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Tecnisa × Cyrela</title>
<style>
body{{margin:0;background:#f7f5f0;color:#2b2a26;font-family:"Inter",system-ui,Segoe UI,Arial,sans-serif;padding:28px 32px}}
.wrap{{max-width:1080px;margin:0 auto}} h1{{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:30px;margin:0 0 4px;letter-spacing:-.01em}}
p.k{{color:#8a8378;font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px}}
svg{{width:100%;height:auto;display:block}} .ax{{font-size:11px;fill:#8a8378}} .lb{{font-size:11.5px;font-weight:600}} .bd{{font-size:10px;font-weight:700;fill:#fff}}
.tit{{font-size:15px;font-weight:700;fill:#2b2a26;font-family:"Fraunces",Georgia,serif}} .sub{{font-size:11px;fill:#8a8378}}
ol{{columns:2;column-gap:28px;font-size:12.5px;line-height:1.4;padding-left:20px;margin:10px 0 18px}} ol li{{break-inside:avoid;margin-bottom:4px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}} th,td{{padding:5px 8px;border-bottom:1px solid #e3ded4;text-align:left}} th{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#8a8378}}
td.n{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600}} td.o{{color:#8a8378}}
.out{{margin-top:14px;padding:10px 14px;border-left:5px solid #2e7d32;background:rgba(46,125,50,.08);border-radius:10px;font-size:14px}}
.fn{{font-size:11px;color:#8a8378;margin-top:12px;line-height:1.4}}
</style></head><body><div class="wrap">
<p class="k">Cyrela · anexo · Tecnisa</p><h1>Tecnisa: R$ 95 mi de equity, R$ 20 mi de dívida, e o que sobrou.</h1>
{svg}
<ol>{"".join(f"<li>{t}</li>" for _, _, t in EV)}</ol>
<table><thead><tr><th>quando</th><th>o quê</th><th>ações</th><th>preço</th><th>R$ mi</th><th>base</th></tr></thead><tbody>{tb}</tbody></table>
<div class="out"><b>O que fica:</b> R$ 94,9 mi aplicados em 2016-17; ~R$ 77 mi de volta entre 2017 e 2026, dos quais ~R$ 45 mi ainda em 2017 (o preço dessas vendas não foi divulgado). Perda nominal da ordem de R$ 15-20 mi no equity, sem dividendo no caminho; o CRI de ~R$ 20 mi rendeu 140% do CDI e foi pago em jul/21. Depois de 2019 a Cyrela virou espectadora: não acompanhou o follow-on, foi diluída a 3,3% e saiu aos poucos até zerar no 1S26.</div>
<p class="fn">Fontes: B3 COTAHIST (fechamento do último pregão de cada mês, sem ajuste; o grupamento aparece como salto em jun/20); Tecnisa: FR 2026 item 1.1 (capitalizações de 13/10/16, 24/05/17 e 17/07/19; grupamento de 05/05/20), fato relevante de 28/08/26 (73.619.230 ações), DFP 2021 nota 10 (5ª emissão de debêntures: R$ 70 mi, 140% do CDI, garantia real, 15/07/17-15/07/21, liquidada no prazo), fatos relevantes do Jardim das Perdizes (23/02, 25/02, 30/04 e 01/06/26); Cyrela: FR 2026 item 1.1, releases 3T16-2T20, notas de investimentos ao valor justo dos ITR/DFP 2018-2T26 (ações detidas e cotação), notas de aplicações financeiras 2017-21 (CRI sênior da Tecnisa a 140% do CDI: R$ 20,5 mi em 2017, R$ 22,3 mi em 2018). Ações em circulação antes de out/16 derivadas (273,5 mi − 100 mi). Posição da Cyrela entre datas de nota: degrau na data do evento conhecido.</p>
</div></body></html>"""
io.open(os.path.join(here, "tecnisa_mcap.html"), "w", encoding="utf-8").write(html)
print("ok", {k: round(v) for k, v in mcap.items() if k in ("2015-01", "2016-10", "2019-12", "2020-06", "2025-12", "2026-09")}, {k: round(v, 1) for k, v in pos.items() if k in ("2016-10", "2017-06", "2018-12", "2019-12", "2020-03", "2020-06", "2025-12")})
