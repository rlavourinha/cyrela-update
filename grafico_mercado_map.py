# -*- coding: utf-8 -*-
"""Mercado agregado × Cyrela: o médio e alto padrão desacelera, o MCMV segue forte.
Painéis: ABRAINC-FIPE Brasil (MAP e MCMV, lançamentos e vendas 12m, mil unidades, 2015-26); Cyrela MAP (lançamentos 12m, R$ bi, RI);
Secovi-SP capital (unidades vendidas e VGV 12m, MCMV × outros mercados, jun/24-jun/26). Saída: mercado_map.html."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
A = json.load(io.open(os.path.join(here, "_mercado_liquidez.json"), encoding="utf-8")); MA = A["meses"]
L = json.load(io.open(os.path.join(here, "_lancamentos_ri.json"), encoding="utf-8"))
ORD = lambda q: (int(q[2:]), int(q[0])); Q = sorted(L["vgv_total"], key=ORD)
def s(k): return {q: (L[k].get(q) or 0) for q in Q}
map_q = {q: s("vgv_alto")[q] + s("vgv_medio")[q] + s("vgv_prime")[q] for q in Q}; mcmv_q = {q: s("vgv_mcmv23")[q] + s("vgv_mcmv1")[q] for q in Q}
def ltm(d): return {Q[i]: sum(d[Q[j]] for j in range(i - 3, i + 1)) / 1e6 for i in range(3, len(Q))}   # R$ bi
CM, CC = ltm(map_q), ltm(mcmv_q); QL = [q for q in Q if q in CM and ORD(q) >= (15, 1)]
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
i0 = MA.index("2015-01"); MS = MA[i0:]
def panel(ox, oy, w, h, title, sub, series, ymax, xs, xlab):
    X0, X1, Y0, Y1 = ox + 44, ox + w - 10, oy + 40, oy + h - 22
    x = lambda i: X0 + (X1 - X0) * i / (len(xs) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+44}" y="{oy+14}" class="pt">{title}</text><text x="{ox+44}" y="{oy+28}" class="sub">{sub}</text>']
    for k in range(5):
        t = ymax * k / 4; g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="#ddd8cf"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="ax">{fmt(t)}</text>')
    for i, m in enumerate(xs):
        lb = xlab(m)
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="ax">{lb}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="#bfb8ab"/>')
    ends = []
    for vals, col, wd, dash, lab in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round" stroke-linecap="round"/>')
        last = [v for v in vals if v is not None][-1]; ends.append((last, col, lab))
        pk = max((v, i) for i, v in enumerate(vals) if v is not None)
        if pk[1] < len(vals) - 6: g.append(f'<text x="{x(pk[1]):.1f}" y="{y(pk[0])-6:.1f}" text-anchor="middle" class="lb" fill="{col}">{fmt(pk[0])} · {xs[pk[1]][2:4]}</text>')
    ys = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = y(v)
        for p in ys:
            if abs(yy - p) < 13: yy = p + 13
        ys.append(yy); g.append(f'<text x="{X1-2}" y="{yy-4:.1f}" text-anchor="end" class="lb" fill="{col}">{lab} {fmt(v)}</text>')
    return "".join(g)
W = 1060; PW, PH = 530, 240
xl = lambda m: m[:4] if m.endswith("-01") and int(m[:4]) % 2 == 1 else ""
g = []
g.append(panel(0, 0, PW, PH, "Brasil · médio e alto padrão (ABRAINC-FIPE, mil unidades, 12 meses)", "lançamentos e vendas líquidas de distratos", [(A["seg"]["map"]["lanc12"][i0:], "#b3123f", 2.4, "", "lanç."), (A["seg"]["map"]["vend12"][i0:], "#2f5fa8", 2.4, "", "vendas")], 80, MS, xl))
g.append(panel(PW, 0, PW, PH, "Brasil · MCMV (ABRAINC-FIPE, mil unidades, 12 meses)", "mesma base; escala própria", [(A["seg"]["mcmv"]["lanc12"][i0:], "#b3123f", 2.4, "", "lanç."), (A["seg"]["mcmv"]["vend12"][i0:], "#2f5fa8", 2.4, "", "vendas")], 200, MS, xl))
xq = lambda q: "20" + q[2:] if q.startswith("1T") and int(q[2:]) % 2 == 1 else ""
g.append(panel(0, PH, PW, PH, "Cyrela · médio e alto padrão (RI, VGV lançado 100%, R$ bi, 12 meses)", "alto padrão + médio + Vivaz Prime; MCMV à parte", [([CM[q] for q in QL], "#b3123f", 2.4, "", "MAP"), ([CC[q] for q in QL], "#a07a12", 2.0, "5 3", "MCMV")], 20, QL, xq))
# Secovi-SP: barras lado a lado, 3 pontos (jun/24, jun/25, jun/26): unidades vendidas 12m e VGV 12m, MCMV × outros mercados
SV = {"un": {"jun/24": (44.7, 44.2), "jun/25": (67.8, 45.5), "jun/26": (77.9, 36.1)}, "vgv": {"jun/24": (13.1, 43.4), "jun/25": (19.5, 42.0), "jun/26": (22.2, 37.5)}}
ox, oy = PW, PH; X0 = ox + 44
g.append(f'<text x="{X0}" y="{oy+14}" class="pt">São Paulo capital (Secovi-SP, 12 meses): MCMV × outros mercados</text><text x="{X0}" y="{oy+28}" class="sub">unidades vendidas (mil) e VGV (R$ bi, INCC de jun/26); MCMV = Faixas 1-3</text>')
for k, (key, lab, ymax) in enumerate((("un", "unidades vendidas 12m (mil)", 100), ("vgv", "VGV vendido 12m (R$ bi)", 60))):
    bx = X0 + k * 250; by0, by1 = oy + 62, oy + PH - 40
    y = lambda v: by1 - (by1 - by0) * v / ymax
    g.append(f'<text x="{bx}" y="{by0-8}" class="ax">{lab}</text><line x1="{bx}" y1="{by1}" x2="{bx+225}" y2="{by1}" stroke="#bfb8ab"/>')
    for j, (per, (mc, ot)) in enumerate(SV[key].items()):
        cx = bx + 20 + j * 75
        g.append(f'<rect x="{cx}" y="{y(mc):.1f}" width="24" height="{by1-y(mc):.1f}" rx="2" fill="#a07a12"/><rect x="{cx+28}" y="{y(ot):.1f}" width="24" height="{by1-y(ot):.1f}" rx="2" fill="#b3123f"/>')
        g.append(f'<text x="{cx+12}" y="{y(mc)-4:.1f}" text-anchor="middle" class="lb" fill="#a07a12">{fmt(mc,1)}</text><text x="{cx+40}" y="{y(ot)-4:.1f}" text-anchor="middle" class="lb" fill="#b3123f">{fmt(ot,1)}</text><text x="{cx+26}" y="{by1+14}" text-anchor="middle" class="ax">{per}</text>')
g.append(f'<text x="{X0}" y="{oy+PH-8}" class="ax"><tspan fill="#a07a12" font-weight="700">■</tspan> MCMV  <tspan fill="#b3123f" font-weight="700">■</tspan> outros mercados (médio e alto padrão, compactos, HMP)</text>')
svg = f'<svg viewBox="0 0 {W} {2*PH+8}" xmlns="http://www.w3.org/2000/svg">' + "".join(g) + "</svg>"
mapL, mapV = A["seg"]["map"]["lanc12"], A["seg"]["map"]["vend12"]; mcL, mcV = A["seg"]["mcmv"]["lanc12"], A["seg"]["mcmv"]["vend12"]
pkL = max(range(len(mapL)), key=lambda i: mapL[i] or 0); pkV = max(range(len(mapV)), key=lambda i: mapV[i] or 0)
cm_pk = max(QL, key=lambda q: CM[q])
html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>Mercado MAP × MCMV</title>
<style>
body{{margin:0;background:#f7f5f0;color:#2b2a26;font-family:"Inter",system-ui,Segoe UI,Arial,sans-serif;padding:28px 32px}}
.wrap{{max-width:1080px;margin:0 auto}} h1{{font-family:"Fraunces",Georgia,serif;font-weight:600;font-size:30px;margin:0 0 4px;letter-spacing:-.01em}}
p.k{{color:#8a8378;font-size:12px;letter-spacing:.08em;text-transform:uppercase;margin:0 0 12px}}
svg{{width:100%;height:auto;display:block}} .ax{{font-size:10px;fill:#8a8378}} .lb{{font-size:11px;font-weight:600}} .pt{{font-size:13px;font-weight:700;fill:#2b2a26;font-family:"Fraunces",Georgia,serif}} .sub{{font-size:10.5px;fill:#8a8378}}
.cards{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:14px}} .c{{background:#fff;border:1px solid #e3ded4;border-radius:10px;padding:10px 12px;font-size:12.5px;line-height:1.4}} .c b{{display:block;font-family:"Fraunces",Georgia,serif;font-size:20px;color:#b3123f;margin-bottom:4px}}
.out{{margin-top:14px;padding:10px 14px;border-left:5px solid #2e7d32;background:rgba(46,125,50,.08);border-radius:10px;font-size:14px}}
.fn{{font-size:11px;color:#8a8378;margin-top:12px;line-height:1.4}}
</style></head><body><div class="wrap">
<p class="k">Cyrela · anexo · mercado</p><h1>O médio e alto padrão desacelera no agregado; o MCMV segue forte. A Cyrela não é exceção.</h1>
{svg}
<div class="cards">
<div class="c"><b>Brasil: −{fmt(100*(1-mapL[-1]/mapL[pkL]))}% e −{fmt(100*(1-mapV[-1]/mapV[pkV]))}%</b>Lançamentos do MAP em 12 meses caíram de {fmt(mapL[pkL])} mil ({MA[pkL][5:]}/{MA[pkL][2:4]}) para {fmt(mapL[-1])} mil ({MA[-1][5:]}/{MA[-1][2:4]}); vendas de {fmt(mapV[pkV])} mil ({MA[pkV][5:]}/{MA[pkV][2:4]}) para {fmt(mapV[-1])} mil. MCMV: lançamentos {fmt(mcL[-1])} mil e vendas {fmt(mcV[-1])} mil, ambos no recorde.</div>
<div class="c"><b>São Paulo capital: −21% nas unidades, −11% no VGV</b>Vendas de 12 meses fora do MCMV caíram de 45,5 mil (jun/25) para 36,1 mil (jun/26); o VGV de R$ 42,0 bi para R$ 37,5 bi. No MCMV: +15% em unidades e +14% em VGV. Em jun/26 o MCMV foi 81% das unidades lançadas e 75% das vendidas; VSO dos outros mercados 5,7% contra 11,6% do MCMV; VSO 12 meses total de 62,5% para 53,6%.</div>
<div class="c"><b>Rio: sem série pública por segmento</b>A Ademi-RJ publica só o agregado da pesquisa Brain: 2025 com R$ 17,6 bi lançados (+37%) e R$ 14,2 bi vendidos; 1S26 com 13,3 mil unidades lançadas (+2%) e 12,9 mil vendidas, com compactos e luxo ganhando peso. O agregado do Rio não mostra desaceleração até jun/26; a abertura por padrão só existe na base paga (Brain).</div></div>
<div class="out"><b>O que fica:</b> a queda de lançamentos e vendas da Cyrela no médio e alto padrão (pico de R$ {fmt(CM[cm_pk],1)} bi em {cm_pk} para R$ {fmt(CM[QL[-1]],1)} bi no 2T26) acompanha o agregado: no Brasil o MAP vende {fmt(100*(1-mapV[-1]/mapV[pkV]))}% menos que no pico e lança {fmt(100*(1-mapL[-1]/mapL[pkL]))}% menos; em São Paulo capital as vendas fora do MCMV caíram 21% em unidades em 12 meses. O MCMV, com funding próprio, está no recorde nos dois recortes. Só o Rio não confirma, e lá não há dado público por segmento.</div>
<p class="fn">Fontes: ABRAINC-FIPE, Indicadores do Mercado Imobiliário (lançamentos, vendas líquidas de distratos, por segmento MAP e MCMV, acumulado 12 meses, abr/26; _mercado_liquidez.json); Secovi-SP, Pesquisa do Mercado Imobiliário jun/26, itens 1.2, 1.4, 2.2 e 5 (cidade de São Paulo, empresas associadas; MCMV = Faixas 1 a 3 pelos limites de abr/26); Ademi-RJ / Brain Inteligência Estratégica, comunicados de jan/26 e jul/26 (agregado da cidade do Rio); Cyrela, planilha de dados operacionais do RI (VGV lançado 100%, por segmento; 12 meses). Séries em unidades (ABRAINC, Secovi) e em VGV (Cyrela, Secovi VGV) não são comparáveis em nível, só em direção.</p>
</div></body></html>"""
io.open(os.path.join(here, "mercado_map.html"), "w", encoding="utf-8").write(html)
# --- fragmentos para dois slides do deck enxuto: um para o MAP, outro para o MCMV (viewBox 1060×250: Brasil à esquerda, Cyrela à direita; Secovi-SP em svg à parte)
def deck_panel(ox, oy, w, h, title, sub, series, ymax, xs, xlab):
    X0, X1, Y0, Y1 = ox + 44, ox + w - 96, oy + 44, oy + h - 20
    x = lambda i: X0 + (X1 - X0) * i / (len(xs) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+44}" y="{oy+16}" class="gtit">{title}</text><text x="{ox+44}" y="{oy+31}" class="gsub">{sub}</text>']
    for k in range(5):
        tv = ymax * k / 4; g.append(f'<line x1="{X0}" y1="{y(tv):.1f}" x2="{X1}" y2="{y(tv):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(tv)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(tv)}</text>')
    for i, m in enumerate(xs):
        lb = xlab(m)
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
    ends = []
    for vals, col, wd, dash, lab in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round" stroke-linecap="round"/>')
        last = [v for v in vals if v is not None][-1]; ends.append((last, col, lab))
        pk = max((v, i) for i, v in enumerate(vals) if v is not None)
        if pk[1] < len(vals) - 6: g.append(f'<text x="{x(pk[1]):.1f}" y="{y(pk[0])-6:.1f}" text-anchor="middle" class="fw-s2" fill="{col}">{fmt(pk[0], 1) if ymax <= 20 else fmt(pk[0])} · {xs[pk[1]][2:4]}</text>')
    ys = []
    for v, col, lab in sorted(ends, reverse=True):
        yy = y(v)
        for pv in ys:
            if abs(yy - pv) < 13: yy = pv + 13
        ys.append(yy); g.append(f'<circle cx="{X1:.1f}" cy="{y(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v, 1) if ymax <= 20 else fmt(v)}</text>')
    return "".join(g)
def secovi_svg(seg):
    """barras: MCMV ou outros mercados em SP capital (unidades vendidas 12m e VGV 12m), jun/24-jun/26"""
    idx = 0 if seg == "mcmv" else 1; col = "var(--s3)" if seg == "mcmv" else "var(--s1)"
    g = [f'<text x="10" y="16" class="gtit">São Paulo capital, 12 meses (Secovi-SP)</text><text x="10" y="31" class="gsub">{"MCMV (Faixas 1-3)" if seg == "mcmv" else "outros mercados: médio e alto padrão, compactos, HMP"}</text>']
    for k, (key, lab, ymax) in enumerate((("un", "unidades vendidas (mil)", 100), ("vgv", "VGV vendido (R$ bi, INCC jun/26)", 60))):
        bx = 14 + k * 230; by0, by1 = 62, 150
        y = lambda v: by1 - (by1 - by0) * v / ymax
        g.append(f'<text x="{bx}" y="{by0-8}" class="axq" opacity=".85">{lab}</text><line x1="{bx}" y1="{by1}" x2="{bx+205}" y2="{by1}" stroke="var(--baseline)"/>')
        for j, (per, vals) in enumerate(SV[key].items()):
            v = vals[idx]; cx = bx + 18 + j * 66
            g.append(f'<rect x="{cx}" y="{y(v):.1f}" width="34" height="{by1-y(v):.1f}" rx="2" fill="{col}" opacity="{1 if j == 2 else .55}"/><text x="{cx+17}" y="{y(v)-4:.1f}" text-anchor="middle" class="fw-s2" fill="{col}">{fmt(v,1)}</text><text x="{cx+17}" y="{by1+13}" text-anchor="middle" class="axq" opacity=".75">{per}</text>')
    return '<svg viewBox="0 0 470 168" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
xl2 = lambda m: m[:4] if m.endswith("-01") and int(m[:4]) % 2 == 1 else ""
xq2 = lambda q: "20" + q[2:] if q.startswith("1T") and int(q[2:]) % 2 == 1 else ""
FR = {}
for seg, ttl, ymB, cy, ymC in (("map", "médio e alto padrão", 80, CM, 20), ("mcmv", "MCMV", 200, CC, 8)):
    gg = deck_panel(0, 0, 530, 250, f"Brasil · {ttl}: mil unidades, 12 meses", "ABRAINC-FIPE; lançamentos e vendas líquidas de distratos", [(A["seg"][seg]["lanc12"][i0:], "var(--s1)", 2.6, "", "lanç."), (A["seg"][seg]["vend12"][i0:], "var(--s2)", 2.6, "", "vendas")], ymB, MS, xl2)
    gg += deck_panel(530, 0, 530, 250, f"Cyrela · {ttl}: VGV lançado, R$ bi, 12 meses", "alto padrão + médio + Vivaz Prime" if seg == "map" else "Vivaz + MCMV Faixa 1 (Cury/FAR até 2014)", [([cy[q] for q in QL], "var(--s1)", 2.6, "", "lanç.")], ymC, QL, xq2)
    FR[seg] = {"svg": '<svg viewBox="0 0 1060 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + gg + "</svg>", "secovi": secovi_svg(seg)}
FR["num"] = {"map_lanc_pico": [MA[pkL], mapL[pkL]], "map_lanc_ult": [MA[-1], mapL[-1]], "map_vend_pico": [MA[pkV], mapV[pkV]], "map_vend_ult": mapV[-1], "mcmv_lanc_ult": mcL[-1], "mcmv_vend_ult": mcV[-1],
             "mcmv_lanc_pico": [MA[max(range(len(mcL)), key=lambda i: mcL[i] or 0)], max(v for v in mcL if v)], "cy_map_pico": [cm_pk, CM[cm_pk]], "cy_map_ult": [QL[-1], CM[QL[-1]]], "cy_mcmv_ult": [QL[-1], CC[QL[-1]]], "cy_mcmv_pico": [max(QL, key=lambda q: CC[q]), max(CC[q] for q in QL)]}
json.dump(FR, io.open(os.path.join(here, "_mercado_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("frag ok", FR["num"])
print("ok", "MAP lanc pico", MA[pkL], mapL[pkL], "último", mapL[-1], "| vend pico", MA[pkV], mapV[pkV], mapV[-1], "| Cyrela MAP 12m pico", cm_pk, round(CM[cm_pk], 1), "último", round(CM[QL[-1]], 1))
