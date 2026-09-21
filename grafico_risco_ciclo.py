# -*- coding: utf-8 -*-
"""Risco de ciclo no MAP (médio e alto padrão): quanto capital o estoque atual pede se a velocidade de venda não melhorar.
Base: estoque MAP em 2T26 (_operacional_ri.json: alto + médio + prime, VGV 100%, em obra e pronto), cronograma do custo a incorrer das
unidades em estoque (release 2T26: 12/24/36/+36 meses, consolidado), estoque a custo (_estoque_custo.json), VSO trimestral do estoque
(_vso_modelo.json 'est' = vendas de estoque ÷ estoque inicial, todos os segmentos).
Modelo (3 anos, só o estoque de hoje, sem lançamentos novos, parte consolidada = %CBR do estoque):
 - vendas do estoque no ano = VSO anual × estoque não vendido no início do ano; VSO anual = 1 − (1 − VSO_tri)^4;
 - caixa na obra: 30% do VGV vendido entra durante a obra; 70% entra na entrega (repasse), só para o que estiver vendido até lá;
 - entregas do estoque em obra: 30% / 40% / 30% nos anos 1-3 (cronograma do custo a incorrer: 46% em 12m, 36% em 24m, 18% depois);
 - custo a incorrer do estoque MAP = cronograma × participação do MAP no estoque em obra (VGV); custo do pronto = 67% do VGV (margem bruta ~33%).
Cenários de VSO: atual (média 4 tri), 2016 (média do ano, o fundo do ciclo) e 2019-21 (melhora). Saída: _risco_ciclo_frag.json {svg, table, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
O = J("_operacional_ri.json"); Q = O["tris"]; V = J("_vso_modelo.json"); EC = J("_estoque_custo.json")
MAP = ("alto", "medio", "prime"); seg = lambda d, q: sum((d.get(k, {}).get(q) or 0) for k in MAP)
u = Q[-1]; CBR = O["estoque"]["vgvcbr_total"][u] / O["estoque"]["vgv100_total"][u]
E_MAP = seg(O["estoque"]["vgv100_seg"], u); P_MAP = seg(O["pronto"]["vgv100_seg"], u); OB_MAP = E_MAP - P_MAP
E_TOT = O["estoque"]["vgv100_total"][u]; P_TOT = O["pronto"]["vgv100_total"][u]; SH_OB = OB_MAP / (E_TOT - P_TOT)
CUSTO = [1599, 1253, 537 + 121]            # release 2T26: custo a incorrer das unidades em estoque, 12m / 24m / 36m e depois (R$ mi, consolidado)
C_MAP = [c * SH_OB for c in CUSTO]
ENT = [0.30, 0.40, 0.30]; PAGO_OBRA = 0.30; CUSTO_VGV = 0.67
vq = dict(zip(V["q"], V["est"]))
def med(qs): return sum(vq[q] for q in qs) / len(qs)
CEN = {"VSO atual": med(Q[-4:]), "VSO de 2016": med(["1T16", "2T16", "3T16", "4T16"]), "VSO de 2019-21": med([q for q in V["q"] if q.endswith(("19", "20", "21"))])}
ob0 = OB_MAP * CBR; pr0 = P_MAP * CBR      # parte consolidada, R$ mi
def run(vq_):
    va = 1 - (1 - vq_ / 100) ** 4; unsold_ob = ob0; sold_cum = 0.0; pronto = pr0; rows = []; cum = 0.0
    for t in range(3):
        sold_ob = unsold_ob * va; unsold_ob -= sold_ob; sold_cum += sold_ob
        sold_pr = pronto * va; pronto -= sold_pr
        entreg = ob0 * ENT[t]; sh_sold = sold_cum / ob0            # fatia do estoque em obra já vendida na hora da entrega
        chaves = entreg * sh_sold * (1 - PAGO_OBRA); novo_pronto = entreg * (1 - sh_sold); pronto += novo_pronto
        caixa = -C_MAP[t] + PAGO_OBRA * sold_ob + chaves + sold_pr; cum += caixa
        rows.append({"ano": t + 1, "custo": C_MAP[t], "vend_ob": sold_ob, "obra_in": PAGO_OBRA * sold_ob, "chaves": chaves, "vend_pr": sold_pr, "caixa": caixa, "cum": cum, "novo_pronto": novo_pronto, "pronto_fim": pronto, "unsold_ob": unsold_ob})
    return va, rows
RES = {k: run(v) for k, v in CEN.items()}
# ---- svg: evolução do estoque MAP (em obra × pronto) + cronograma do custo a incorrer
g = []; Y0, Y1 = 46, 226
qs = [q for q in Q if q in O["pronto"]["vgv100_seg"]["alto"] and int(q[2:]) >= 13]
EOB = [(seg(O["estoque"]["vgv100_seg"], q) - seg(O["pronto"]["vgv100_seg"], q)) / 1000 for q in qs]; EPR = [seg(O["pronto"]["vgv100_seg"], q) / 1000 for q in qs]
X0, X1 = 44, 640; n = len(qs); x = lambda i: X0 + (X1 - X0) * i / (n - 1); ymax = 14; y = lambda v: Y1 - (Y1 - Y0) * v / ymax
g.append(f'<text x="{X0}" y="17" class="gtit">Estoque do MAP, R$ bi a valor de mercado (100%)</text><text x="{X0}" y="32" class="gsub">em obra (vinho) e pronto (cinza); alto + médio + Prime</text>')
for t in (0, 4, 8, 12): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}</text>')
for i, q in enumerate(qs):
    if q.startswith("1T") and int(q[2:]) % 2 == 0: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">20{q[2:]}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
for vals, col, w in ((EOB, S1, 2.6), (EPR, MU, 2.2)):
    g.append(f'<polyline points="{" ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"/>')
g.append(f'<text x="{X1+5}" y="{y(EOB[-1])+4:.1f}" class="fw-t2" fill="{S1}">em obra {fmt(EOB[-1], 1)}</text><text x="{X1+5}" y="{y(EPR[-1])+4:.1f}" class="fw-t2" fill="{I2}">pronto {fmt(EPR[-1], 1)}</text>')
i16 = qs.index("4T16"); g.append(f'<text x="{x(i16):.1f}" y="{y(EOB[i16])-22:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">2016: {fmt(EOB[i16] + EPR[i16], 1)} bi, VSO {fmt(CEN["VSO de 2016"], 0)}%/tri</text>')
X0b, X1b = 800, 1060; yb = lambda v: Y1 - (Y1 - Y0) * v / 2000
g.append(f'<text x="{X0b}" y="17" class="gtit">Obra a pagar do estoque, R$ mi</text><text x="{X0b}" y="32" class="gsub">custo a incorrer, release 2T26; dourado = MAP ({fmt(100 * SH_OB, 0)}%)</text>')
for t in (0, 500, 1000, 1500, 2000): g.append(f'<line x1="{X0b}" y1="{yb(t):.1f}" x2="{X1b}" y2="{yb(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0b-6}" y="{yb(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t)}</text>')
labs = ("12 meses", "24 meses", "36 m e depois"); bw = (X1b - X0b) / 3 * 0.55
for i, c in enumerate(CUSTO):
    xc = X0b + (X1b - X0b) * (i + 0.5) / 3
    g.append(f'<rect x="{xc-bw/2:.1f}" y="{yb(c):.1f}" width="{bw:.1f}" height="{Y1-yb(c):.1f}" fill="{MU}" fill-opacity=".45"/><rect x="{xc-bw/2:.1f}" y="{yb(C_MAP[i]):.1f}" width="{bw:.1f}" height="{Y1-yb(C_MAP[i]):.1f}" fill="{S3}" fill-opacity=".9"/>')
    g.append(f'<text x="{xc:.1f}" y="{yb(c)-5:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(c)}</text><text x="{xc:.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{labs[i]}</text>')
g.append(f'<line x1="{X0b}" y1="{Y1}" x2="{X1b}" y2="{Y1}" stroke="var(--baseline)"/>')
svg = '<svg viewBox="0 0 1100 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: três cenários × três anos
hdr = "".join(f'<th style="text-align:right">{k}<br><span style="font-weight:400">{fmt(v, 1)}%/tri = {fmt(100 * RES[k][0], 0)}%/ano</span></th>' for k, v in CEN.items())
def row(lab, key, cls="", sign=1, d=0, ano=None):
    cells = ""
    for k in CEN:
        r = RES[k][1]; v = (r[ano - 1][key] if ano else sum(x[key] for x in r)) * sign; cells += f'<td style="text-align:right">{fmt(v, d)}</td>'
    return f'<tr class="{cls}"><td>{lab}</td>{cells}</tr>'
table = ('<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">Estoque MAP de hoje, parte Cyrela, R$ mi · 3 anos</th>' + hdr + '</tr></thead><tbody>'
         + row("custo a incorrer do estoque (obra a pagar)", "custo", sign=-1)
         + row("caixa na obra: 30% do vendido do estoque em obra", "obra_in") + row("caixa nas chaves: 70% do vendido, na entrega", "chaves") + row("venda do estoque pronto", "vend_pr")
         + row("caixa líquido acumulado do estoque", "cum", cls="total", ano=3)
         + row("entregue sem vender, vira pronto (VGV)", "novo_pronto") + row("estoque pronto ao fim do ano 3 (VGV)", "pronto_fim", cls="total", ano=3)
         + row("ainda em obra e sem vender ao fim do ano 3 (VGV)", "unsold_ob", ano=3) + '</tbody></table>')
k0 = "VSO atual"; r0 = RES[k0][1]; k1 = "VSO de 2016"; r1 = RES[k1][1]
num = {"u": u, "cbr": CBR, "e_map": E_MAP, "p_map": P_MAP, "ob_map": OB_MAP, "sh_ob": SH_OB, "custo_tot": sum(CUSTO), "custo_map": sum(C_MAP), "vso_atual": CEN[k0], "vso_2016": CEN[k1], "va_atual": RES[k0][0], "va_2016": RES[k1][0],
       "pronto_fim_atual": r0[-1]["pronto_fim"], "pronto_fim_2016": r1[-1]["pronto_fim"], "pronto_fim_custo_atual": r0[-1]["pronto_fim"] * CUSTO_VGV, "pronto_fim_custo_2016": r1[-1]["pronto_fim"] * CUSTO_VGV,
       "cum_atual": r0[-1]["cum"], "cum_2016": r1[-1]["cum"], "novo_pronto_atual": sum(x["novo_pronto"] for x in r0), "novo_pronto_2016": sum(x["novo_pronto"] for x in r1), "pr0": pr0, "ob0": ob0,
       "custo_investido": EC[u]["construcao"] + EC[u]["concluidos"], "custo_vgv": CUSTO_VGV, "pago_obra": PAGO_OBRA}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_risco_ciclo_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in num.items()})
for k in CEN: print(k, round(CEN[k], 1), [{kk: round(vv) for kk, vv in r.items()} for r in RES[k][1]])
