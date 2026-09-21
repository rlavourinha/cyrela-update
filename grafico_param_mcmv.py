# -*- coding: utf-8 -*-
"""Slide 'Os parâmetros do MCMV': quatro gráficos de degraus regenerados com a série alongada para antes do MCMV
(programas do FGTS 1998-2009, Res. CCFGTS 289/1998, 460/2004 e alterações), a partir de
fontes/verificacao/ccfgts_pre2009/parametros_fgts_1998_2009.json (marcos com data_vigencia, norma, teto_imovel_rmsp, juros_min,
juros_max, renda_limite_financiamento, renda_limite_desconto, desconto_max). Marcos 2009-2026 = os do deck (Leis 11.977/09 e 12.424/11,
Res. CCFGTS, portarias MCid). Saída: _param_mcmv_frag.json {svgs: [teto, juro, renda, desconto]}."""
import io, json, os, re
here = os.path.dirname(os.path.abspath(__file__))
PJ = os.path.join(here, "fontes", "verificacao", "ccfgts_pre2009", "parametros_fgts_1998_2009.json")
PRE = json.load(io.open(PJ, encoding="utf-8")) if os.path.exists(PJ) else []
if isinstance(PRE, dict): PRE = PRE.get("marcos") or PRE.get("serie") or []
def dec(d):   # "2004-12-14" → 2004.95; aceita "2000 (Res. 337...)" (ano só → meio do ano) e "2005-01-01 (efeitos...)"
    m_ = re.match(r"(\d{4})(?:-(\d{2}))?", d.strip()); y = int(m_.group(1)); m = int(m_.group(2)) if m_.group(2) else 6
    return y + (m - 0.5) / 12
def pre(key):
    out = []
    for r in sorted(PRE, key=lambda r: r["data_vigencia"]):
        v = r.get(key)
        if isinstance(v, (int, float)) and dec(r["data_vigencia"]) < 2009.2: out.append((dec(r["data_vigencia"]), float(v)))
    return out
# ---- marcos 2009-2026 (os que estavam no deck)
TETO = [(a, v / 1000) for a, v in pre("teto_imovel_rmsp")] + [(2009.3, 130), (2011.1, 170), (2012.8, 190), (2016.2, 225), (2017.0, 240), (2021.6, 264), (2025.8, 275)]
TETO_F3 = [t for t in TETO if t[0] < 2023] + [(2023.3, 350), (2026.1, 400)]; TETO_F4 = [(2025.1, 500), (2026.1, 600)]; TETO_BANDA = [(2017.0, 300), (2020.5, 300)]
JMIN = pre("juros_min_mutuario") + [(2009.3, 6.0), (2016.2, 7.0)]
JMAX = pre("juros_max_mutuario") + [(2011.0, 8.16), (2021.7, 7.66), (2022.8, 8.16)]
J_F4 = [(2025.1, 10.0)]; J_BANDA = [(2017.0, 9.16), (2020.5, 9.16)]
R_F1 = [(2009.2, 1395), (2011.5, 1600), (2016.1, 1800), (2020.7, 2000), (2023.5, 2640), (2024.6, 2850), (2026.3, 3200)]
R_F2 = pre("renda_limite_desconto") + [(2009.2, 2790), (2011.5, 3100), (2016.1, 3600), (2017.1, 4000), (2023.5, 4400), (2024.6, 4700), (2026.3, 5000)]   # pré-2009: renda máxima com desconto/juro de 6% do FGTS = a faixa subsidiada, que o MCMV rebatiza de F1-F2
R_F3 = pre("renda_limite_financiamento") + [(2009.2, 4650), (2011.5, 5000), (2016.1, 6500), (2017.1, 9000), (2020.7, 7000), (2023.5, 8000), (2025.3, 8600), (2026.3, 9600)]
R_F4 = [(2025.4, 12000), (2026.3, 13000)]
R_DESC = []   # 20/09/26: a renda com desconto pré-2009 passou a ser o trecho inicial da F2 (mesma série, sem linha à parte)
DESC = pre("desconto_max") + [(2009.2, 23000), (2011.5, 25000), (2016.1, 45000), (2017.1, 47500), (2023.5, 55000)]
DESC_F2 = [(2009.2, 23000), (2011.5, 25000), (2016.1, 27500), (2017.1, 29000), (2023.5, 55000)]; DESC_N = [(2025.9, 65000)]
A0 = min([a for a, _ in TETO + JMIN + JMAX + R_F3 + DESC] + [2009.0]); A0 = float(int(A0)); A1 = 2026.7
X0, X1 = 70.0, 772.0   # margem direita para os rótulos de fim de série (ficam à direita do ponto final, sem a linha por cima)
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def chart(H, y0, yb, vmax, vmin, grid, gfmt, title, sub, series, notes, leaders, foot=None):
    def xy(a, v): return (X0 + (X1 - X0) * (a - A0) / (A1 - A0), y0 - (y0 - yb) * (v - vmin) / (vmax - vmin))
    def steps(s):
        pts = []
        for i, (a, v) in enumerate(s):
            if i > 0: pts.append(xy(a, s[i - 1][1]))
            pts.append(xy(a, v))
        pts.append(xy(A1, s[-1][1])); return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    g = [f'<text x="70" y="24" class="gtit">{title}</text><text x="830" y="24" class="gsub" style="font-size:10px" text-anchor="end">{sub}</text>']
    for gv in grid: g.append(f'<line x1="70" y1="{xy(A0, gv)[1]:.1f}" x2="{X1}" y2="{xy(A0, gv)[1]:.1f}" stroke="var(--grid)" opacity=".5"/><text x="64" y="{xy(A0, gv)[1]+4:.1f}" class="axq" text-anchor="end" opacity=".8">{gfmt(gv)}</text>')
    yrs = [a for a in range(int(A0), 2027) if (a - int(A0)) % (4 if A1 - A0 > 22 else 2) == 0]
    for a in yrs: g.append(f'<text x="{xy(a, vmin)[0]:.1f}" y="{y0+17}" class="axq" text-anchor="middle" opacity=".7">{a}</text>')
    g.append(f'<line x1="70" y1="{y0}" x2="{X1}" y2="{y0}" stroke="var(--baseline)"/>')
    # marco do MCMV
    xm = xy(2009.25, vmin)[0]; g.append(f'<line x1="{xm:.1f}" y1="{yb-6}" x2="{xm:.1f}" y2="{y0}" stroke="var(--muted)" stroke-dasharray="3 4" opacity=".7"/><text x="{xm+4:.1f}" y="{yb+2}" class="fw-s2" fill="var(--muted)">MCMV (abr/09)</text>')
    for s, col, w, dash, ends in series:
        if not s: continue
        if ends: g.append(f'<polyline points="{" ".join(f"{xy(a, v)[0]:.1f},{xy(a, v)[1]:.1f}" for a, v in s)}" fill="none" stroke="{col}" stroke-width="{w}"{dash}/>')
        else: g.append(f'<polyline points="{steps(s)}" fill="none" stroke="{col}" stroke-width="{w}"{dash} stroke-linejoin="round"/>')
    for a, v, txt, col, dy, anc in notes:
        x, y = xy(a, v); g.append(f'<text x="{x:.1f}" y="{y+dy:.1f}" class="fw-t2" style="font-size:13px" paint-order="stroke" stroke="var(--page)" stroke-width="4" stroke-linejoin="round" fill="{col}" text-anchor="{anc}">{txt}</text>')
    for v, txt, col, ty in leaders:
        x, y = xy(A1, v); g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{col}" stroke="var(--page)" stroke-width="2"/><line x1="{x:.1f}" y1="{y:.1f}" x2="{X1+8}" y2="{ty:.1f}" stroke="{col}" stroke-width="1" opacity=".55"/><text x="{X1+11}" y="{ty+4:.1f}" class="fw-t2" style="font-size:13px" fill="{col}" text-anchor="start">{txt}</text>')
    if foot and FOOT: g.append(f'<text x="450" y="{H-8}" class="fw-s2" text-anchor="middle">{foot}</text>')
    return f'<svg viewBox="0 0 900 {H}">' + "".join(g) + "</svg>"
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
FOOT = False   # 20/09/26: rodapés de texto removidos (agente de formatação: ilegíveis a ~6px; "mais imagem, menos texto")
n_pre = f"{int(A0)}-2026" if A0 < 2009 else "2009-2026"
svg_teto = chart(280, 250, 40, 640, 0, (150, 300, 450, 600), lambda v: fmt(v), f"O teto do imóvel — {2026 - int(A0)} anos de degraus", "R$ mil · RMSP, topo da tabela · CCFGTS",
    [(TETO_F3, S3, 2.6, "", False), (TETO, S2, 2.6, "", False), (TETO_F4, S1, 2.6, "", False), (TETO_BANDA, S1, 1.6, ' stroke-dasharray="3 4" opacity=".7"', True)],   # F3 por baixo: até 2023 o teto era um só (F3 = F1-2), a linha dourada só aparece quando separa
    [(2020.4, 300, "banda estendida 2017–20 · renda 9 mil · proto-F4 (Res. 836/17)", I2, -10, "end"), (2007.4, 130, "FGTS pré-MCMV: 62 → 130 mil", S2, -8, "end")],
    [(275, "F1–2 · 275", S2, 250 - (250 - 40) * 275 / 640 + 20), (400, "F3 · 400", S3, 250 - (250 - 40) * 400 / 640 + 16), (600, "F4 · 600", S1, 250 - (250 - 40) * 600 / 640 + 16)])
svg_juro = chart(240, 210, 40, 10.8, 3.2, (4, 6, 8, 10), lambda v: f"{v}%", "O juro do programa — quase imóvel", "% a.a. + TR · topo da faixa · não-cotista · Sudeste",
    [(JMIN, S2, 2.6, "", False), (JMAX, S3, 2.6, "", False), (J_F4, S1, 2.6, "", False), (J_BANDA, S1, 1.6, ' stroke-dasharray="3 4" opacity=".7"', True)],
    [(2015.0, 9.0, "8,16% desde 2011 — só piscou no corte de 0,5 p.p. de 2021–22", I2, 0, "middle"), (1999.2, 5.0, "pré-MCMV: 8% único (1998); 6 / 8,16 / 10,16% por renda (2002-07)", I2, 0, "start")],
    [(7.0, "F2 · até 7,0%", S2, 210 - (210 - 40) * (7.0 - 3.2) / 7.6 + 30), (8.16, "F3 · 8,16%", S3, 210 - (210 - 40) * (8.16 - 3.2) / 7.6 + 14), (10.0, "F4 · ~10%", S1, 210 - (210 - 40) * (10 - 3.2) / 7.6 - 10)])
svg_renda = chart(259, 218, 40, 14000, 0, (4000, 8000, 12000), lambda v: f"{v // 1000} mil", "Até onde vai cada faixa — o limite de renda", "R$/mês nominais · fim de cada faixa · pré-2009: FGTS",
    [(R_F1, MU, 2.4, ' stroke-dasharray="3 4"', False), (R_F2, S2, 2.4, ' stroke-dasharray="6 4"', False), (R_F3, S3, 2.4, "", False), (R_F4, S1, 2.4, "", False), (R_DESC, I2, 1.8, ' stroke-dasharray="2 3"', True)],
    [(2019.5, 9000, "2017: F3 vai a 9 mil (proto-F4); 2020: o CVA corta a 7 mil", S3, -24, "end"), (2003.5, 4500, "FGTS: teto 1.560 → 4.900; tracejado = renda com desconto (vira F2)", S3, -14, "middle")],
    [(13000, "F4 · 13,0 mil", S1, 218 - (218 - 40) * 13000 / 14000 - 14), (9600, "F3 · 9,6 mil", S3, 218 - (218 - 40) * 9600 / 14000 + 2), (5000, "F2 · 5,0 mil", S2, 218 - (218 - 40) * 5000 / 14000 + 2), (3200, "F1 · 3,2 mil", MU, 218 - (218 - 40) * 3200 / 14000 + 22)],
    "em salários mínimos o programa encolheu: o topo da F3 era 10 SM em 2009 — hoje são ~5,9 SM (salário mínimo de 2026). A F4 recompra o terreno perdido")
svg_desc = chart(259, 218, 40, 70000, 0, (20000, 40000, 60000), lambda v: f"{v // 1000} mil", "O desconto do FGTS — quanto o programa paga da entrada", "R$ mil · máximo por família · SP/RJ/DF",
    [(DESC_F2, S2, 2.4, ' stroke-dasharray="6 4"', False), (DESC, S2, 2.4, "", False), (DESC_N, S3, 2.4, ' stroke-dasharray="2 3"', False)],
    [(2016.1, 45000, "2016: nasce a F1,5 — subsídio dobra para quem ganha até 2.350", S2, -16, "end"), (2008.6, 14000, "2005→07: 2,8 → 14 mil", S2, -16, "end")],
    [(65000, "Norte · 65 mil", S3, 218 - (218 - 40) * 65000 / 70000 - 8), (55000, "F1 e F2 · 55 mil", S2, 218 - (218 - 40) * 55000 / 70000 + 16)],
    "o desconto abate a entrada e enquadra o LTV: 55 mil sobre um imóvel de 275 mil é 20% do preço — pago pelo cotista do FGTS, remunerado a TR+3%")
json.dump({"svgs": [svg_teto, svg_juro, svg_renda, svg_desc], "A0": A0, "n_pre": len(PRE)}, io.open(os.path.join(here, "_param_mcmv_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok A0 =", A0, "| marcos pré-2009:", len(PRE), "| teto:", TETO[:4], "| jmax:", JMAX[:3], "| renda F3:", R_F3[:3], "| desc:", DESC[:3])
