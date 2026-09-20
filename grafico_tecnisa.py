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
    if m < "2017-09": return 45111
    if m < "2018-01": return 31365      # 9,47% em 30/09/17 (ITR 3T17): ~13,7 mi vendidas no 3T17
    if m < "2018-12": return 26199      # 7,91% em 31/12/17 (DFP 2017): ~5,2 mi vendidas no 4T17
    if m < "2019-01": return 25440      # 25.439.958 em 31/12/18 (~0,8 mi vendidas em 2018)
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
 ("2017-05", "2", "abr-mai/17 · segunda capitalização (R$ 150 mi a R$ 2,60): Cyrela põe mais R$ 20,4 mi (28/04) e mantém 13,6%"),
 ("2017-07", "3", "jul/17 · Tecnisa emite R$ 70 mi em debêntures a 140% do CDI (5ª emissão, garantia real, vence jul/21); nas notas da Cyrela o CRI sênior da Tecnisa a 140% do CDI é pequeno: R$ 5,2 mi (dez/18) → R$ 0,9 mi (dez/20) → zero (dez/21)"),
 ("2017-08", "4", "2S17 · Cyrela vende ~18,9 mi ações a mercado (13,7 mi no 3T17, 5,2 mi no 4T17; 13,6% → 7,9%; TCSA3 entre R$ 1,97 e 2,38); entradas nos releases 3T17 e 4T17; mais ~0,8 mi em 2018"),
 ("2019-01", "5", "jan/19 · vende 0,6 mi ações e cai a 7,49%: o acordo de acionistas se extingue"),
 ("2019-07", "6", "jul/19 · follow-on de 405 mi ações a R$ 1,10 (R$ 445 mi); a Cyrela não subscreve (posição cai a 24,0 mi ações) e é diluída a 3,3-3,4%"),
 ("2020-03", "7", "1T20 · Cyrela vende ~13,8 mi ações por R$ 28 mi (início de jan/20, antes da queda); sobra 10,2 mi (R$ 7,5 mi a R$ 0,74)"),
 ("2020-06", "8", "mai/20 · grupamento 10:1 (AGE 05/05/20): 73,6 mi ações"),
 ("2021-07", "9", "jul/21 · 5ª emissão liquidada no vencimento (DFP 2021 da Tecnisa); o CRI some das notas da Cyrela em dez/21: mesma taxa e prazo sugerem, sem confirmar, que era lastro da debênture"),
 ("2025-09", "10", "3T25 · Cyrela desiste da compra dos terrenos do Jardim das Perdizes (comunicado ao mercado; call 3T25)"),
 ("2026-06", "11", "fev-jun/26 · BTG compra 26,09% da Windsor (sociedade do Jardim das Perdizes) por R$ 260,9 mi; a Tecnisa fica com 26,41% (fatos relevantes de 23/02 a 01/06/26); a Cyrela cai a 5.155 ações no 1T26 (R$ 4 mil)"),
 ("2026-09", "12", "set/26 · novo grupamento 10:1 proposto (fato relevante 28/08/26, AGE 21/09)"),
]

W, H = 1060, 585
X0, X1 = 62, 900
PA = (100, 300)     # painel A: valor de mercado (linear, R$ mi)
PB = (372, 522)     # painel B: posição da Cyrela (linear, R$ mi)
def x(i): return X0 + (X1 - X0) * i / (len(MS) - 1)
def ya(v): return PA[1] - (PA[1] - PA[0]) * v / 1500
def yb(v): return PB[1] - (PB[1] - PB[0]) * v / 150
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
g = []
for t_ in (0, 500, 1000, 1500):
    g.append(f'<line x1="{X0}" y1="{ya(t_):.1f}" x2="{X1}" y2="{ya(t_):.1f}" stroke="#ddd8cf"/><text x="{X0-8}" y="{ya(t_)+4:.1f}" text-anchor="end" class="ax">{fmt(t_)}</text>')
for t_ in (0, 50, 100, 150):
    g.append(f'<line x1="{X0}" y1="{yb(t_):.1f}" x2="{X1}" y2="{yb(t_):.1f}" stroke="#ddd8cf"/><text x="{X0-8}" y="{yb(t_)+4:.1f}" text-anchor="end" class="ax">{fmt(t_)}</text>')
for i, m in enumerate(MS):
    if m.endswith("-01"):
        g.append(f'<text x="{x(i):.1f}" y="{PA[1]+16}" text-anchor="middle" class="ax">{m[:4]}</text><text x="{x(i):.1f}" y="{PB[1]+16}" text-anchor="middle" class="ax">{m[:4]}</text>')
g.append(f'<line x1="{X0}" y1="{PA[1]}" x2="{X1}" y2="{PA[1]}" stroke="#bfb8ab"/><line x1="{X0}" y1="{PB[1]}" x2="{X1}" y2="{PB[1]}" stroke="#bfb8ab"/>')
# eventos: linha tracejada atravessa os dois painéis; badge em duas alturas para não encavalar
for k, (m, lab, _) in enumerate(EV):
    i = MS.index(m); xx = x(i); cy = PA[0] - 22 - (20 if k % 2 else 0)
    g.append(f'<line x1="{xx:.1f}" y1="{cy+9}" x2="{xx:.1f}" y2="{PB[1]}" stroke="#8a8378" stroke-dasharray="2 4" opacity=".7"/>')
    g.append(f'<circle cx="{xx:.1f}" cy="{cy}" r="9" fill="#2b2a26"/><text x="{xx:.1f}" y="{cy+3.5}" text-anchor="middle" class="bd">{lab}</text>')
def poly(d, yf, col, w):
    pts = " ".join(f"{x(MS.index(m)):.1f},{yf(v):.1f}" for m, v in sorted(d.items()))
    return f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'
g.append(poly(mcap, ya, "#2f5fa8", 2.4)); g.append(poly(pos, yb, "#b3123f", 2.2))
# rótulos de fim de linha e pontos-chave
lm = MS[-1]; g.append(f'<circle cx="{x(len(MS)-1):.1f}" cy="{ya(mcap[lm]):.1f}" r="3.5" fill="#2f5fa8"/><text x="{X1+7}" y="{ya(mcap[lm])+4:.1f}" class="lb" fill="#2f5fa8">R$ {fmt(mcap[lm])} mi (set/26)</text>')
pm = max(pos); g.append(f'<circle cx="{x(MS.index(pm)):.1f}" cy="{yb(pos[pm]):.1f}" r="3.5" fill="#b3123f"/><text x="{X1+7}" y="{yb(pos[pm])+4:.1f}" class="lb" fill="#b3123f">R$ {fmt(pos[pm], 1)} mi (dez/25)</text><text x="{X1+7}" y="{yb(pos[pm])+18:.1f}" class="lb" fill="#b3123f">R$ 4 mil em jun/26</text>')
g.append(f'<text x="{x(MS.index("2019-12")):.1f}" y="{ya(mcap["2019-12"])-9:.1f}" text-anchor="middle" class="lb" fill="#2f5fa8">pico R$ {fmt(mcap["2019-12"])} mi (dez/19)</text>')
g.append(f'<text x="{x(MS.index("2016-10"))-8:.1f}" y="{ya(mcap["2016-10"])+16:.1f}" text-anchor="end" class="lb" fill="#2f5fa8">R$ {fmt(mcap["2016-10"])} mi</text>')
pk = max(pos, key=pos.get); g.append(f'<text x="{x(MS.index(pk)):.1f}" y="{yb(pos[pk])-9:.1f}" text-anchor="middle" class="lb" fill="#b3123f">pico R$ {fmt(pos[pk])} mi ({pk[5:]}/{pk[2:4]})</text>')
g.append(f'<text x="{x(MS.index("2018-12"))+6:.1f}" y="{yb(pos["2018-12"])-8:.1f}" class="lb" fill="#b3123f">R$ {fmt(pos["2018-12"])} mi</text>')
g.append(f'<text x="{x(MS.index("2020-03"))+6:.1f}" y="{yb(pos["2020-03"])+14:.1f}" class="lb" fill="#b3123f">R$ {fmt(pos["2020-03"], 1)} mi</text>')
g.append(f'<text x="{X0}" y="22" class="tit">Tecnisa: valor de mercado (R$ mi)</text>')
g.append(f'<text x="{X0}" y="38" class="sub">fechamento mensal TCSA3 (B3) × ações em circulação; eventos numerados na lista abaixo</text>')
g.append(f'<text x="{X0}" y="{PB[0]-22}" class="tit">O que a posição da Cyrela valia (R$ mi)</text>')
g.append(f'<text x="{X0}" y="{PB[0]-8}" class="sub">ações detidas segundo as notas dos ITR/DFP da Cyrela × cotação do mês; para em dez/25 (R$ 0,8 mi)</text>')
svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(g) + "</svg>"

# tabela: entradas e saídas da Cyrela
ROWS = [
 ("out/16", "subscrição", "37,25 mi", "R$ 2,00", "−74,5", "fixado na oferta"),
 ("mai/17", "subscrição", "7,86 mi", "R$ 2,60", "−20,4", "fixado na oferta"),
 ("2S17", "venda a mercado", "18,9 mi", "R$ 2,0-2,4", "≈ +41 a 45", "preço não divulgado; ITR 3T17 (9,47%) e DFP 2017 (7,91%); fechamentos mensais jul-dez/17"),
 ("2018", "venda a mercado", "0,76 mi", "R$ 1,0-2,0", "≈ +1", "26,2 → 25,4 mi ações"),
 ("jan/19", "venda a mercado", "0,60 mi", "R$ 1,58", "≈ +1", "fechamento diário B3 de 11/01/19"),
 ("2019", "venda a mercado", "0,87 mi", "≈ R$ 1,5", "≈ +1", "24,84 → 23,97 mi ações"),
 ("1T20", "venda a mercado", "13,79 mi", "≈ R$ 2,0", "+28", "release 1T20; início de jan/20, antes da queda"),
 ("4T23-1T24", "venda a mercado", "0,32 mi (pós-grup.)", "R$ 3-4", "≈ +1", "1,018 → 0,703 mi ações"),
 ("1T26", "venda a mercado", "0,70 mi (pós-grup.)", "≈ R$ 1,2", "≈ +1", "0,703 mi → 5.155 ações"),
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
<p class="k">Cyrela · anexo · Tecnisa</p><h1>Tecnisa: R$ 95 mi de equity, ~R$ 75 mi de volta, e o que sobrou.</h1>
{svg}
<ol>{"".join(f"<li>{t}</li>" for _, _, t in EV)}</ol>
<table><thead><tr><th>quando</th><th>o quê</th><th>ações</th><th>preço</th><th>R$ mi</th><th>base</th></tr></thead><tbody>{tb}</tbody></table>
<div class="out"><b>O que fica:</b> R$ 94,9 mi aplicados em 2016-17; ~R$ 75 mi de volta entre 2017 e 2026, dos quais R$ 41-45 mi ainda no 2S17 (preço não divulgado). Perda nominal de R$ 16-21 mi no equity, sem dividendo (prejuízos acumulados de R$ 1,2 bi na Tecnisa em 2021); a CDI, a perda econômica passa de R$ 70 mi. O CRI sênior da Tecnisa nas notas da Cyrela era pequeno (R$ 5,2 mi em dez/18) e zerou em 2021. Depois de 2019 a Cyrela virou espectadora: não subscreveu o follow-on, foi diluída a 3,3% e saiu aos poucos até 5.155 ações no 1T26.</div>
<p class="fn">Fontes: B3 COTAHIST (fechamento do último pregão de cada mês, sem ajuste; o grupamento aparece como salto em jun/20); Tecnisa: FR 2026 item 1.1 (capitalizações de 13/10/16, 24/05/17 e 17/07/19; grupamento de 05/05/20), fato relevante de 28/08/26 (73.619.230 ações), DFP 2021 nota 10 (5ª emissão de debêntures: R$ 70 mi, 140% do CDI, garantia real, 15/07/17-15/07/21, liquidada no prazo), fatos relevantes do Jardim das Perdizes (23/02, 25/02, 30/04 e 01/06/26); Cyrela: FR 2026 item 1.1, releases 3T16-2T20, notas de investimentos ao valor justo dos ITR/DFP 2018-2T26 (ações detidas e cotação), notas de títulos e valores mobiliários das DFP 2018-21 (CRI sênior da Tecnisa a 140% do CDI: R$ 5,2 mi, R$ 2,2 mi, R$ 0,9 mi, zero; a linha de CRI de 2017, R$ 32,5 mi a 8,25% a.a., não identifica emissor); ITR 3T17 e DFP 2017 (participação de 9,47% e 7,91%). Ações em circulação antes de out/16 derivadas (273,5 mi − 100 mi). Posição da Cyrela entre datas de nota: degrau na data do evento conhecido.</p>
</div></body></html>"""
io.open(os.path.join(here, "tecnisa_mcap.html"), "w", encoding="utf-8").write(html)
# --- versão compacta para o slide do deck enxuto (viewBox 1060×312, dois painéis mais baixos, mesmos dados e eventos)
# 19/09/26: altura 400 → 312 para o slide caber em ~740px. Subtítulo de cada painel na linha do título (à direita, ancorado em X1),
# badges em duas alturas (17 de distância) logo abaixo, eixo a 11px numa classe própria (.axt: <style> de svg inline é global,
# não sobrescrever .axq), rótulos "R$ 676 mi" acima/esquerda do ponto (antes cruzava a linha) e "R$ 7,5 mi" acima da linha à direita da queda.
HC = 312; PA = (70, 180); PB = (226, 290)
def ya(v): return PA[1] - (PA[1] - PA[0]) * v / 1500
def yb(v): return PB[1] - (PB[1] - PB[0]) * v / 150
g = []
for t_ in (0, 500, 1000, 1500): g.append(f'<line x1="{X0}" y1="{ya(t_):.1f}" x2="{X1}" y2="{ya(t_):.1f}" stroke="var(--grid)"/><text x="{X0-8}" y="{ya(t_)+4:.1f}" text-anchor="end" class="axt">{fmt(t_)}</text>')
for t_ in (0, 50, 100, 150): g.append(f'<line x1="{X0}" y1="{yb(t_):.1f}" x2="{X1}" y2="{yb(t_):.1f}" stroke="var(--grid)"/><text x="{X0-8}" y="{yb(t_)+4:.1f}" text-anchor="end" class="axt">{fmt(t_)}</text>')
for i, m in enumerate(MS):
    if m.endswith("-01"): g.append(f'<text x="{x(i):.1f}" y="{PA[1]+14}" text-anchor="middle" class="axt">{m[:4]}</text><text x="{x(i):.1f}" y="{PB[1]+14}" text-anchor="middle" class="axt">{m[:4]}</text>')
g.append(f'<line x1="{X0}" y1="{PA[1]}" x2="{X1}" y2="{PA[1]}" stroke="var(--muted)" opacity=".5"/><line x1="{X0}" y1="{PB[1]}" x2="{X1}" y2="{PB[1]}" stroke="var(--muted)" opacity=".5"/>')
# 19/09/26: o marcador 4 (2S17) foi de out/17 para ago/17 e ficou a 6 un. do 3 (jul/17) e a 18 do 2 (mai/17): com dois níveis a 17 un. os círculos (r=8) ficavam a 2 un.;
# agora dois níveis a 20 un. (50/30) e o 4 num terceiro nível abaixo (70, encostado na grade de 1.500, longe da linha que ali passa em ~600): folgas 2-3 = 7, 2-4 = 24, 3-4 = 5
_TIER = {3: -1}   # índice do evento → deslocamento de nível (negativo = para baixo)
for k, (m, lab, _) in enumerate(EV):
    i = MS.index(m); xx = x(i); cy = PA[0] - 20 - 20 * _TIER.get(k, k % 2)
    g.append(f'<line x1="{xx:.1f}" y1="{cy+8}" x2="{xx:.1f}" y2="{PB[1]}" stroke="var(--muted)" stroke-dasharray="2 4" opacity=".7"/>')
    g.append(f'<circle cx="{xx:.1f}" cy="{cy}" r="8" fill="var(--ink)"/><text x="{xx:.1f}" y="{cy+3.2}" text-anchor="middle" style="font-size:9.5px;font-weight:700;fill:#fff">{lab}</text>')
g.append(poly(mcap, ya, "var(--s2)", 2.4)); g.append(poly(pos, yb, "var(--s1)", 2.2))
g.append(f'<circle cx="{x(len(MS)-1):.1f}" cy="{ya(mcap[lm]):.1f}" r="3.5" fill="var(--s2)"/><text x="{X1+7}" y="{ya(mcap[lm])+4:.1f}" class="lbl" fill="var(--s2)">R$ {fmt(mcap[lm])} mi (set/26)</text>')
g.append(f'<circle cx="{x(MS.index(pm)):.1f}" cy="{yb(pos[pm]):.1f}" r="3.5" fill="var(--s1)"/><text x="{X1+7}" y="{yb(pos[pm])-5:.1f}" class="lbl" fill="var(--s1)">R$ {fmt(pos[pm], 1)} mi (dez/25)</text><text x="{X1+7}" y="{yb(pos[pm])+10:.1f}" class="lbl" fill="var(--s1)">R$ 4 mil em jun/26</text>')
g.append(f'<text x="{x(MS.index("2019-12")):.1f}" y="{ya(mcap["2019-12"])-7:.1f}" text-anchor="middle" class="lbl" fill="var(--s2)">pico R$ {fmt(mcap["2019-12"])} mi (dez/19)</text>')
g.append(f'<text x="{x(MS.index("2016-10"))-6:.1f}" y="{ya(mcap["2016-10"])-6:.1f}" text-anchor="end" class="lbl" fill="var(--s2)">R$ {fmt(mcap["2016-10"])} mi</text>')
g.append(f'<text x="{x(MS.index(pk)):.1f}" y="{yb(pos[pk])-7:.1f}" text-anchor="middle" class="lbl" fill="var(--s1)">pico R$ {fmt(pos[pk])} mi ({pk[5:]}/{pk[2:4]})</text>')
g.append(f'<text x="{x(MS.index("2018-12"))+6:.1f}" y="{yb(pos["2018-12"])-6:.1f}" class="lbl" fill="var(--s1)">R$ {fmt(pos["2018-12"])} mi</text>')
g.append(f'<text x="{x(MS.index("2020-03"))+8:.1f}" y="{yb(pos["2020-03"])-9:.1f}" class="lbl" fill="var(--s1)">R$ {fmt(pos["2020-03"], 1)} mi</text>')
g.append(f'<text x="{X0}" y="16" class="gtit" style="font-size:16px">Tecnisa: valor de mercado (R$ mi)</text><text x="{X1}" y="16" text-anchor="end" class="gsub">fechamento mensal TCSA3 (B3) × ações em circulação; eventos numerados abaixo</text>')
g.append(f'<text x="{X0}" y="{PB[0]-12}" class="gtit" style="font-size:16px">O que a posição da Cyrela valia (R$ mi)</text><text x="{X1}" y="{PB[0]-12}" text-anchor="end" class="gsub">ações detidas nas notas dos ITR/DFP × cotação do mês; para em dez/25 (R$ 0,8 mi)</text>')
svg_c = f'<svg viewBox="0 0 {W} {HC}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block"><style>.lbl{{font-size:11px;font-weight:600}}.axt{{font-size:11px;fill:var(--muted)}}</style>' + "".join(g) + "</svg>"
json.dump({"svg": svg_c, "ev": [t for _, _, t in EV], "rows": ROWS, "mcap_fim": round(mcap[lm]), "pos_pico": round(pos[pk]), "pico_m": pk},
          io.open(os.path.join(here, "_tecnisa_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: round(v) for k, v in mcap.items() if k in ("2015-01", "2016-10", "2019-12", "2020-06", "2025-12", "2026-09")}, {k: round(v, 1) for k, v in pos.items() if k in ("2016-10", "2017-06", "2018-12", "2019-12", "2020-03", "2020-06", "2025-12")})
