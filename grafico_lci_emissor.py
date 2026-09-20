# -*- coding: utf-8 -*-
"""LCI por emissor, série semestral jun/15-jun/26 (BCB IF.data, relatório Passivo, conglomerados prudenciais).
Saída: lci_emissor.html (SVG inline). Linhas independentes por emissor (sem empilhar), R$ bi, escala linear."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
D = json.load(io.open(os.path.join(here, "_lci_emissor_semestral.json"), encoding="utf-8"))["serie"]
MS = sorted(D)
EM = [("Caixa", "#b3123f", 2.8, ""), ("Bradesco", "#2f5fa8", 2.2, ""), ("Itaú", "#a07a12", 2.2, ""), ("Santander", "#2b2a26", 2.0, ""),
      ("Banco do Brasil", "#6b8f3a", 1.8, ""), ("Inter", "#c06a2c", 1.6, ""), ("Outros", "#8a8378", 1.8, "5 4")]
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
W, H = 1060, 470
X0, X1, Y0, Y1 = 62, 900, 70, 400
YMAX = 300
def x(i): return X0 + (X1 - X0) * i / (len(MS) - 1)
def y(v): return Y1 - (Y1 - Y0) * v / YMAX
g = []
for t in range(0, YMAX + 1, 50):
    g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="#ddd8cf"/><text x="{X0-8}" y="{y(t)+4:.1f}" text-anchor="end" class="ax">{fmt(t)}</text>')
for i, m in enumerate(MS):
    if m.endswith("-12"): g.append(f'<text x="{x(i):.1f}" y="{Y1+18}" text-anchor="middle" class="ax">dez/{m[2:4]}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#bfb8ab"/>')
# marcadores (mês do evento aproximado ao semestre)
EV = [("2022-06", "ago/22 · Selic a 13,75%", 1), ("2022-12", "jan/23 · nova gestão da Caixa; fev/23 MCMV relançado", 2), ("2023-12", "fev/24 · Res. 5.119: prazo 12 m, lastro restrito", 3), ("2024-06", "ago/24 · Res. 5.168: prazo 9 m", 4), ("2025-06", "mai/25 · Res. 5.215: prazo 6 m, teto = lastro", 5)]
for m, lab, n in EV:
    xx = x(MS.index(m)) + (X1 - X0) / (len(MS) - 1) * 0.33
    g.append(f'<line x1="{xx:.1f}" y1="{Y0-12}" x2="{xx:.1f}" y2="{Y1}" stroke="#8a8378" stroke-dasharray="2 4" opacity=".7"/><circle cx="{xx:.1f}" cy="{Y0-22}" r="9" fill="#2b2a26"/><text x="{xx:.1f}" y="{Y0-18.5}" text-anchor="middle" class="bd">{n}</text>')
def poly(k, col, w, dash):
    pts = " ".join(f"{x(i):.1f},{y(D[m][k]/1000):.1f}" for i, m in enumerate(MS))
    return f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round" stroke-linecap="round"/>'
# rótulos de fim de linha, empurrados para não encavalar
ends = sorted(((D[MS[-1]][k] / 1000, k, col) for k, col, _, _ in EM), reverse=True)
ys = []
for v, k, col in ends:
    yy = y(v)
    for prev in ys:
        if abs(yy - prev) < 14: yy = prev + 14
    ys.append(yy)
    g.append(f'<text x="{X1+8}" y="{yy+4:.1f}" class="lb" fill="{col}">{k} {fmt(v)}</text>')
for k, col, w, dash in EM:
    g.append(poly(k, col, w, dash)); g.append(f'<circle cx="{x(len(MS)-1):.1f}" cy="{y(D[MS[-1]][k]/1000):.1f}" r="3" fill="{col}"/>')
# rótulos de pontos-chave da Caixa
for m, dy, anc in (("2015-12", -10, "middle"), ("2021-12", 16, "middle"), ("2023-12", -10, "middle")):
    i = MS.index(m); g.append(f'<text x="{x(i):.1f}" y="{y(D[m]["Caixa"]/1000)+dy:.1f}" text-anchor="{anc}" class="lb" fill="#b3123f">{fmt(D[m]["Caixa"]/1000)}</text>')
tot = D[MS[-1]]["Total"] / 1000
g.append(f'<text x="{X0}" y="22" class="tit">Estoque de LCI por emissor (R$ bi, semestral)</text>')
g.append(f'<text x="{X0}" y="38" class="sub">BCB IF.data, relatório Passivo, conglomerados prudenciais; total do sistema R$ {fmt(tot)} bi em jun/26 (B3: R$ 540 bi em mai/26)</text>')
svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">' + "".join(g) + "</svg>"
# tabela: dez de cada ano + jun/26
cols = [m for m in MS if m.endswith("-12")] + [MS[-1]]
th = "".join(f"<th>{('jun' if c.endswith('-06') else 'dez')}/{c[2:4]}</th>" for c in cols)
tb = "".join(f"<tr><td>{k}</td>" + "".join(f"<td class='n'>{fmt(D[c][k]/1000)}</td>" for c in cols) + "</tr>" for k, *_ in EM) + "<tr class='t'><td>Total</td>" + "".join(f"<td class='n'>{fmt(D[c]['Total']/1000)}</td>" for c in cols) + "</tr>"
c22 = D["2022-06"]["Caixa"] / 1000; c26 = D[MS[-1]]["Caixa"] / 1000; t22 = D["2022-06"]["Total"] / 1000
html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>LCI por emissor</title>
<style>
body{{margin:0;background:#f7f5f0;color:#2b2a26;font-family:"Inter",system-ui,Segoe UI,Arial,sans-serif;padding:28px 32px}}
.wrap{{max-width:1080px;margin:0 auto}} h1{{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:30px;margin:0 0 4px;letter-spacing:-.01em}}
p.k{{color:#8a8378;font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px}}
svg{{width:100%;height:auto;display:block}} .ax{{font-size:11px;fill:#8a8378}} .lb{{font-size:11.5px;font-weight:600}} .bd{{font-size:10px;font-weight:700;fill:#fff}}
.tit{{font-size:15px;font-weight:700;fill:#2b2a26;font-family:"Fraunces",Georgia,serif}} .sub{{font-size:11px;fill:#8a8378}}
ol{{columns:2;column-gap:28px;font-size:12.5px;line-height:1.4;padding-left:20px;margin:10px 0 18px}} ol li{{break-inside:avoid;margin-bottom:4px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}} th,td{{padding:5px 8px;border-bottom:1px solid #e3ded4;text-align:left}} th{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#8a8378;text-align:right}} th:first-child{{text-align:left}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}} tr.t td{{font-weight:700;border-top:2px solid #bfb8ab}}
.out{{margin-top:14px;padding:10px 14px;border-left:5px solid #2e7d32;background:rgba(46,125,50,.08);border-radius:10px;font-size:14px}}
.fn{{font-size:11px;color:#8a8378;margin-top:12px;line-height:1.4}}
</style></head><body><div class="wrap">
<p class="k">Cyrela · anexo · funding</p><h1>LCI por emissor: a Caixa é metade do estoque, e a virada foi no 2S22.</h1>
{svg}
<ol>{"".join(f"<li>{lab}</li>" for _, lab, _ in EV)}</ol>
<table><thead><tr><th>R$ bi</th>{th}</tr></thead><tbody>{tb}</tbody></table>
<div class="out"><b>O que fica:</b> a Caixa tinha R$ 111 bi de LCI em 2015, deixou vencer até R$ 22 bi em 2021 enquanto a poupança entrava, e religou a máquina quando a poupança virou saída: R$ {fmt(c22)} bi em jun/22 para R$ {fmt(c26)} bi em jun/26, {fmt(100 * (c26 - c22) / (tot - t22))}% de todo o crescimento do sistema no período. Nenhuma norma mudou o lastro em 2022-23; o que mudou foi o incentivo (Selic a 13,75%, poupança saindo, MCMV relançado). As normas de 2024-25 apertaram prazo e lastro, e mesmo assim o estoque seguiu crescendo.</div>
<p class="fn">Fontes: BCB, IF.data (API Olinda), relatório 3 "Passivo", tipo 1 (conglomerados prudenciais e instituições independentes), coluna "Letras de Crédito Imobiliário (c1)", posições de jun e dez de 2015 a jun/26 (_lci_emissor_semestral.json); "Outros" = total do sistema menos os seis emissores nomeados. Normas: Res. CMN 5.119 (1/2/24), 5.168 (22/8/24), 5.215 (22/5/25). B3: estoque de LCI R$ 540 bi em mai/26 (Bora Investir).</p>
</div></body></html>"""
io.open(os.path.join(here, "lci_emissor.html"), "w", encoding="utf-8").write(html)
print("ok", {k: round(D[MS[-1]][k] / 1000) for k, *_ in EM})
