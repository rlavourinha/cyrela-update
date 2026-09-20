# -*- coding: utf-8 -*-
"""Caixa: imóveis retomados no balanço. Série semestral extraída das demonstrações contábeis BrGaap (dados_caixa_bndu.py →
_caixa_bndu_linhas.txt, transcrita aqui com a página de origem):
 - 'Ativos não financeiros mantidos para venda – recebidos' (bruto, nota de outros ativos), dez/20 a jun/26; antes, a nota 'Outros valores
   e bens' trazia 'Bens não de uso próprio' e a linha 'Imóveis adjudicados/arrematados' (dez/19 e jun/20), com abrangência diferente.
 - Provisão para desvalorização dos bens não de uso / impairment AMV (saldo).
 - Despesa 'Imóveis adjudicados/arrematados' em outras despesas (semestral; anual = soma).
Saída: _caixa_bndu_frag.json {svg, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
REC = {"12/20": 6145.4, "06/21": 5206.8, "12/21": 3953.5, "06/22": 3303.8, "12/22": 3433.8, "06/23": 4136.9, "12/23": 4676.2, "06/24": 5625.1, "12/24": 6180.9, "06/25": 6319.4, "12/25": 6401.0, "06/26": 5977.1}   # R$ mi, bruto
ADJ_OLD = {"12/19": 6808.7, "06/20": 5683.5, "12/20": 3936.5}   # 'Imóveis adjudicados/arrematados' dentro de bens não de uso (nota antiga)
PROV = {"12/19": 1156.6, "06/20": 1027.9, "12/20": 815.2, "06/21": 767.6, "12/21": 589.1, "06/22": 481.1, "12/22": 417.5, "06/23": 448.6, "12/23": 449.5, "06/24": 495.8, "12/24": 252.1, "06/25": 188.5, "12/25": 150.9, "06/26": 310.6}
DESP = {"1S22": 64.7, "2S22": 208.3, "1S23": 423.2, "2S23": 505.2, "1S24": 670.2, "2S24": 721.6, "1S25": 627.9, "2S25": 710.3, "1S26": 671.9}   # outras despesas, R$ mi
ks = ["12/19", "06/20"] + list(REC)
g = []; Y0, Y1 = 40, 118; W = 1100
def frame(X0, X1, title, sub, ymax, ticks, tf, n):
    x = lambda i: X0 + (X1 - X0) * i / (n - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g.append(f'<text x="{X0}" y="14" class="gtit">{title}</text><text x="{X0}" y="28" class="gsub">{sub}</text>')
    for t in ticks: g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>'); return x, y
# painel 1: estoque de imóveis retomados
x, y = frame(44, 480, "Caixa: imóveis retomados no balanço, R$ bi", "ativos não financeiros mantidos para venda, recebidos (bruto); pontilhado = nota antiga, só adjudicados", 10, (0, 5, 10), lambda t: fmt(t), len(ks))
for i, k in enumerate(ks):
    if k.startswith("12"): g.append(f'<text x="{x(i):.1f}" y="{Y1+13}" text-anchor="middle" class="axq" opacity=".75">20{k[3:]}</text>')
pts = " ".join(f"{x(ks.index(k)):.1f},{y(v/1000):.1f}" for k, v in ADJ_OLD.items()); g.append(f'<polyline points="{pts}" fill="none" stroke="{S1}" stroke-width="2" stroke-dasharray="3 3" opacity=".8"/>')
pts = " ".join(f"{x(ks.index(k)):.1f},{y(v/1000):.1f}" for k, v in REC.items()); g.append(f'<polyline points="{pts}" fill="none" stroke="{S1}" stroke-width="2.6" stroke-linejoin="round"/>')
pts = " ".join(f"{x(ks.index(k)):.1f},{y(v/1000):.1f}" for k, v in PROV.items()); g.append(f'<polyline points="{pts}" fill="none" stroke="{MU}" stroke-width="1.8" stroke-linejoin="round"/>')
lo = min(REC, key=REC.get)
g.append(f'<text x="{x(ks.index(lo)):.1f}" y="{y(REC[lo]/1000)+14:.1f}" text-anchor="middle" class="fw-s2" fill="{S1}">{fmt(REC[lo]/1000, 1)}</text>')
g.append(f'<text x="{x(len(ks)-1)+5:.1f}" y="{y(REC["06/26"]/1000)+4:.1f}" class="fw-t2" fill="{S1}">{fmt(REC["06/26"]/1000, 1)}</text><text x="{x(len(ks)-1)+5:.1f}" y="{y(PROV["06/26"]/1000)+4:.1f}" class="fw-s2" fill="{I2}">provisão {fmt(PROV["06/26"]/1000, 1)}</text>')
g.append(f'<text x="{x(0):.1f}" y="{y(ADJ_OLD["12/19"]/1000)-6:.1f}" class="fw-s2" fill="{S1}">{fmt(ADJ_OLD["12/19"]/1000, 1)}</text>')
# painel 2: despesa com imóveis adjudicados/arrematados por semestre
dk = list(DESP); X0, X1 = 600, 1060; n = len(dk); xb = lambda i: X0 + (X1 - X0) * (i + 0.5) / n; ymax = 800; yb = lambda v: Y1 - (Y1 - Y0) * v / ymax
g.append(f'<text x="{X0}" y="14" class="gtit">Despesa com imóveis adjudicados, R$ mi por semestre</text><text x="{X0}" y="28" class="gsub">outras despesas operacionais; diferença entre a dívida e a avaliação do imóvel retomado</text>')
for t in (0, 400, 800): g.append(f'<line x1="{X0}" y1="{yb(t):.1f}" x2="{X1}" y2="{yb(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{yb(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t)}</text>')
bw = (X1 - X0) / n * 0.6
for i, k in enumerate(dk):
    g.append(f'<rect x="{xb(i)-bw/2:.1f}" y="{yb(DESP[k]):.1f}" width="{bw:.1f}" height="{Y1-yb(DESP[k]):.1f}" fill="{S3}" fill-opacity=".85"/><text x="{xb(i):.1f}" y="{Y1+13}" text-anchor="middle" class="axq" opacity=".75">{k}</text>')
    if k in ("1S22", "1S26"): g.append(f'<text x="{xb(i):.1f}" y="{yb(DESP[k])-4:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(DESP[k])}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
svg = f'<svg viewBox="0 0 {W} 136" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
num = {"rec_now": REC["06/26"], "rec_min": REC[lo], "rec_min_k": lo, "rec_1220": REC["12/20"], "adj_1219": ADJ_OLD["12/19"], "prov_now": PROV["06/26"], "desp_2025": DESP["1S25"] + DESP["2S25"], "desp_2022": DESP["1S22"] + DESP["2S22"], "desp_1s26": DESP["1S26"]}
json.dump({"svg": svg, "num": num}, io.open(os.path.join(here, "_caixa_bndu_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", num)
