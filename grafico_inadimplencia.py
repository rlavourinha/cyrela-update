# -*- coding: utf-8 -*-
"""Inadimplência (> 90 dias) do crédito habitacional por origem de recurso, BCB, mensal abr/14-jun/26: PF FGTS (MCMV) × PF SFH × PF livre,
e PJ FGTS × PJ SFH. Pontos da Caixa (relatório 2T26): imobiliário total 1,26% (jun/25), 1,60% (mar/26), 1,45% (jun/26). Saída: inadimplencia_mcmv.html."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
S = json.load(io.open(os.path.join(here, "_bcb_inadimplencia_imob.json"), encoding="utf-8"))["serie"]
MS = sorted(S["pf_fgts"])
def fmt(v, d=1): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def panel(ox, w, h, title, sub, series, ymax, extra=""):
    X0, X1, Y0, Y1 = ox + 44, ox + w - 100, 46, h - 26
    x = lambda i: X0 + (X1 - X0) * i / (len(MS) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+44}" y="18" class="tit">{title}</text><text x="{ox+44}" y="33" class="sub">{sub}</text>']
    for k in range(5):
        t = ymax * k / 4; g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="#ddd8cf"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="ax">{fmt(t)}%</text>')
    for i, m in enumerate(MS):
        if m.endswith("-01") and int(m[:4]) % 2 == 1: g.append(f'<text x="{x(i):.1f}" y="{Y1+15}" text-anchor="middle" class="ax">{m[:4]}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#bfb8ab"/>')
    ends = []
    for key, col, wd, lab in series:
        pts = " ".join(f"{x(i):.1f},{y(min(S[key][m], ymax)):.1f}" for i, m in enumerate(MS) if m in S[key])
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}" stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append((S[key][MS[-1]], col, lab))
    ys = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = y(v)
        for p in ys:
            if abs(yy - p) < 13: yy = p + 13
        ys.append(yy); g.append(f'<text x="{X1+7}" y="{yy+4:.1f}" class="lb" fill="{col}">{lab} {fmt(v, 2)}%</text>')
    return "".join(g) + extra.replace("__X__", str(x)).replace("__Y__", str(y)) if False else "".join(g), x, y
W = 1060
pA, xA, yA = panel(0, 620, 330, "Pessoa física: FGTS (MCMV) × SFH (poupança) × recursos livres", "BCB, % da carteira com atraso > 90 dias; FGTS = Caixa em quase tudo", [("pf_fgts", "#b3123f", 2.6, "FGTS"), ("pf_sfh", "#2f5fa8", 2.2, "SFH"), ("pf_livre", "#a07a12", 2.0, "livre")], 4)
# pontos da Caixa (imobiliário total)
CX = [("2025-06", 1.26), ("2026-03", 1.60), ("2026-06", 1.45)]
for m, v in CX:
    i = MS.index(m); pA += f'<circle cx="{xA(i):.1f}" cy="{yA(v):.1f}" r="4" fill="none" stroke="#2b2a26" stroke-width="1.8"/>'
pA += f'<text x="{xA(MS.index("2025-06"))-6:.1f}" y="{yA(1.26)+16:.1f}" text-anchor="end" class="lb" fill="#2b2a26">○ Caixa, imobiliário total</text>'
pB, _, _ = panel(620, 440, 330, "Pessoa jurídica (produção)", "PJ FGTS × PJ SFH; PJ livre chegou a 38% em jun/21 (fora da escala)", [("pj_fgts", "#b3123f", 2.4, "FGTS"), ("pj_sfh", "#2f5fa8", 2.2, "SFH"), ("pj_livre", "#a07a12", 1.8, "livre")], 12)
svg = f'<svg viewBox="0 0 {W} 330" xmlns="http://www.w3.org/2000/svg">' + pA + pB + "</svg>"
mx = max(S["pf_fgts"].items(), key=lambda kv: kv[1]); mn = min(S["pf_fgts"].items(), key=lambda kv: kv[1])
html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Inadimplência MCMV</title>
<style>
body{{margin:0;background:#f7f5f0;color:#2b2a26;font-family:"Inter",system-ui,Segoe UI,Arial,sans-serif;padding:28px 32px}}
.wrap{{max-width:1080px;margin:0 auto}} h1{{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:30px;margin:0 0 4px;letter-spacing:-.01em}}
p.k{{color:#8a8378;font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px}}
svg{{width:100%;height:auto;display:block}} .ax{{font-size:11px;fill:#8a8378}} .lb{{font-size:11.5px;font-weight:600}} .tit{{font-size:15px;font-weight:700;fill:#2b2a26;font-family:"Fraunces",Georgia,serif}} .sub{{font-size:11px;fill:#8a8378}}
.out{{margin-top:14px;padding:10px 14px;border-left:5px solid #2e7d32;background:rgba(46,125,50,.08);border-radius:10px;font-size:14px}}
.fn{{font-size:11px;color:#8a8378;margin-top:12px;line-height:1.4}}
</style></head><body><div class="wrap">
<p class="k">Cyrela · anexo · MCMV</p><h1>Inadimplência no MCMV: o dobro do SFH, mas estável há dez anos.</h1>
{svg}
<div class="out"><b>O que fica:</b> a inadimplência do crédito com FGTS (o MCMV) oscila entre {fmt(mn[1], 2)}% ({mn[0][5:]}/{mn[0][2:4]}) e {fmt(mx[1], 2)}% ({mx[0][5:]}/{mx[0][2:4]}, pandemia) desde 2014 e está em {fmt(S["pf_fgts"][MS[-1]], 2)}% em jun/26, contra {fmt(S["pf_sfh"][MS[-1]], 2)}% no SFH: o dobro do crédito de poupança, mas sem tendência de alta. O risco da Caixa no MCMV é o mutuário de renda baixa com LTV alto, não uma safra ruim; o que sobe no balanço da Caixa é o crédito livre PJ (14%) e o agro (21%), não a habitação.</div>
<p class="fn">Fontes: BCB, Estatísticas do mercado imobiliário (API Olinda), séries credito_estoque_inadimplencia_&lt;pf|pj&gt;_&lt;fgts|sfh|livre&gt;_br, % da carteira com atraso superior a 90 dias, abr/14 a jun/26 (_bcb_inadimplencia_imob.json); Caixa, Relatório de Análise de Desempenho 2T26 (inadimplência do crédito imobiliário 1,26% em jun/25, 1,60% em mar/26, 1,45% em jun/26; Res. CMN 4.966 alongou a permanência de operações em atraso na carteira a partir de 2025). A carteira FGTS é operada quase toda pela Caixa (R$ 652 bi de repasses contra R$ 629 bi de carteira FGTS no sistema).</p>
</div></body></html>"""
io.open(os.path.join(here, "inadimplencia_mcmv.html"), "w", encoding="utf-8").write(html)
print("ok", mn, mx, S["pf_fgts"][MS[-1]], S["pf_sfh"][MS[-1]])
