# -*- coding: utf-8 -*-
"""Lei do Distrato (13.786/2018): dados da Cyrela para o anexo, série longa (2015-2T26).
Provisão para distratos (consolidado, R$ mi):
 - antes do CPC 47 (2015-2017): item 'distratos de clientes' dentro de 'provisões para riscos' (DFP 2015/2016/2017, nota de
   provisões): R$ 20,7 / 23,0 / 16,6 mi. O distrato só entrava no resultado quando acontecia; não há provisão do esperado.
 - CPC 47 (Ofício CVM 02/2018, 'ajustamento preditivo'): provisão para distrato deduzida do contas a receber apropriado.
   Saldo de abertura em 01/01/2018 R$ 697,1 mi (DFP 2018, nota 5); 4T18 444,3; 2019 trimestral (ITR 1T-3T19, DFP 2019);
   1T20-2T26 em _prov_distrato_mov.json (dados_notas_itr.py). Contas a receber apropriado idem (_notas_itr.json a partir de 1T20).
 - Movimento anual: adições e reversões (2018 e 2019 das DFP; 2020+ soma dos trimestres; último ponto = 12 meses até o trimestre).
A Cyrela não publica distratos em VGV (só vendas líquidas). Saída: _distrato_frag.json {svg, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
ORD = lambda q: (int(q[2:]), int(q[0]))
D = J("_prov_distrato_mov.json"); DT = D["trimestre"]; DA = D["acumulado"]
OLD = {"4T15": 20.697, "4T16": 22.996, "4T17": 16.616}                       # provisões para riscos, 'distratos de clientes'
SAL = {"4T17": 697.104, "4T18": 444.329, "1T19": 452.679, "2T19": 477.928, "3T19": 440.793, "4T19": 362.504}   # 4T17 = abertura 01/01/18
CR = {"4T17": 2663.998, "4T18": 2396.701, "1T19": 2429.207, "2T19": 2438.800, "3T19": 2396.887, "4T19": 2448.914}
N = J("_notas_itr.json")
def find(d, key):
    if isinstance(d, dict):
        if key in d and isinstance(d[key], (int, float)): return d[key]
        for v in d.values():
            r = find(v, key)
            if r is not None: return r
    return None
for q in sorted(DT, key=ORD):
    SAL[q] = DT[q]["saldo"]; v = find(N.get(q, {}), "cr_vendas_apropriadas")
    if v: CR[q] = v   # _notas_itr.json já em R$ mi
qs = ["4T15", "1T16", "2T16", "3T16", "4T16", "1T17", "2T17", "3T17", "4T17", "1T18", "2T18", "3T18", "4T18"] + [q for q in sorted(DT, key=ORD) if ORD(q) >= (19, 1)]
qs = qs[:qs.index("4T18") + 1] + ["1T19", "2T19", "3T19", "4T19"] + sorted(DT, key=ORD)
qs = sorted(set(qs), key=ORD)
PCT = {q: 100 * SAL[q] / CR[q] for q in SAL if q in CR}
ANO = {"2018": (194.701, -447.476), "2019": (208.313, -290.138)}
for y in range(2020, 2027):
    t = [q for q in DT if q.endswith(str(y)[2:])]
    if len(t) == 4: ANO[str(y)] = (sum(DT[q]["adicoes_tri"] for q in t), sum(DT[q]["reversoes_tri"] for q in t))
last4 = sorted(DT, key=ORD)[-4:]; u = last4[-1]
ANO[f"12m {u}"] = (sum(DT[q]["adicoes_tri"] for q in last4), sum(DT[q]["reversoes_tri"] for q in last4))
# ---- svg: três painéis
g = []; Y0, Y1 = 46, 226
def frame(X0, X1, title, sub, ymin, ymax, ticks, tf, n, xlab):
    x = lambda i: X0 + (X1 - X0) * i / (n - 1); y = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
    g.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for t in ticks: g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    for i in range(n):
        lb = xlab(i)
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    g.append(f'<line x1="{X0}" y1="{y(max(ymin, 0)):.1f}" x2="{X1}" y2="{y(max(ymin, 0)):.1f}" stroke="var(--baseline)"/>'); return x, y
yl = lambda i: ("20" + qs[i][2:]) if qs[i].startswith("1T") and int(qs[i][2:]) % 2 == 0 else ""
# painel 1: saldo
x, y = frame(44, 330, "Provisão para distratos, R$ mi", "saldo no fim do trimestre; CPC 47 desde 2018 (abertura: R$ 697 mi)", 0, 800, (0, 200, 400, 600, 800), lambda t: fmt(t), len(qs), yl)
i18 = qs.index("4T17"); g.append(f'<line x1="{x(i18):.1f}" y1="{Y0}" x2="{x(i18):.1f}" y2="{Y1}" stroke="{MU}" stroke-dasharray="3 3"/><text x="{x(i18)+4:.1f}" y="{Y0+10}" class="axq" fill="{I2}">CPC 47</text>')
for q, v in OLD.items(): g.append(f'<circle cx="{x(qs.index(q)):.1f}" cy="{y(v):.1f}" r="3.2" fill="{MU}"/>')
g.append(f'<text x="{x(i18)-5:.1f}" y="{y(23)-9:.1f}" text-anchor="end" class="axq" fill="{I2}">antigo: 21 · 23 · 17</text>')
g.append(f'<polyline points="{x(i18):.1f},{y(SAL["4T17"]):.1f} {x(qs.index("4T18")):.1f},{y(SAL["4T18"]):.1f}" fill="none" stroke="{S1}" stroke-width="2.2" stroke-dasharray="5 3"/>')
seq = [q for q in qs if q in SAL and ORD(q) >= (18, 4)]; pts = " ".join(f"{x(qs.index(q)):.1f},{y(SAL[q]):.1f}" for q in seq)
g.append(f'<polyline points="{pts}" fill="none" stroke="{S1}" stroke-width="2.6" stroke-linejoin="round"/>')
g.append(f'<text x="{x(i18)+5:.1f}" y="{y(SAL["4T17"])-6:.1f}" class="fw-s2" fill="{S1}">697</text><text x="{x(len(qs)-1)+5:.1f}" y="{y(SAL[u])+4:.1f}" class="fw-t2" fill="{S1}">{fmt(SAL[u])}</text>')
# painel 2: provisão ÷ contas a receber apropriado
x, y = frame(410, 700, "Provisão ÷ recebível apropriado, %", "distrato esperado ÷ contas a receber de vendas apropriado", 0, 30, (0, 10, 20, 30), lambda t: f"{t}%", len(qs), yl)
g.append(f'<line x1="{x(i18):.1f}" y1="{Y0}" x2="{x(i18):.1f}" y2="{Y1}" stroke="{MU}" stroke-dasharray="3 3"/>')
g.append(f'<polyline points="{x(i18):.1f},{y(PCT["4T17"]):.1f} {x(qs.index("4T18")):.1f},{y(PCT["4T18"]):.1f}" fill="none" stroke="{S2}" stroke-width="2.2" stroke-dasharray="5 3"/>')
seq = [q for q in qs if q in PCT and ORD(q) >= (18, 4)]; pts = " ".join(f"{x(qs.index(q)):.1f},{y(PCT[q]):.1f}" for q in seq)
g.append(f'<polyline points="{pts}" fill="none" stroke="{S2}" stroke-width="2.6" stroke-linejoin="round"/>')
g.append(f'<text x="{x(i18)+5:.1f}" y="{y(PCT["4T17"])-6:.1f}" class="fw-s2" fill="{S2}">{fmt(PCT["4T17"])}%</text><text x="{x(len(qs)-1)+5:.1f}" y="{y(PCT[seq[-1]])+4:.1f}" class="fw-t2" fill="{S2}">{fmt(PCT[seq[-1]])}%</text>')
# painel 3: adições e reversões por ano
ks = list(ANO); n3 = len(ks); X0, X1 = 790, 1075; ymax = 500; ymin = -500
x3 = lambda i: X0 + (X1 - X0) * (i + 0.5) / n3; y3 = lambda v: Y1 - (Y1 - Y0) * (v - ymin) / (ymax - ymin)
g.append(f'<text x="{X0}" y="17" class="gtit">Adições e reversões, R$ mi por ano</text><text x="{X0}" y="32" class="gsub">dourado: adições; cinza: reversões e distratos efetivados</text>')
for t in (-400, -200, 0, 200, 400): g.append(f'<line x1="{X0}" y1="{y3(t):.1f}" x2="{X1}" y2="{y3(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y3(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(t)}</text>')
bw = (X1 - X0) / n3 * 0.36
for i, k in enumerate(ks):
    a, r = ANO[k]
    g.append(f'<rect x="{x3(i)-bw:.1f}" y="{y3(a):.1f}" width="{bw-1:.1f}" height="{y3(0)-y3(a):.1f}" fill="{S3}" fill-opacity=".85"/><rect x="{x3(i):.1f}" y="{y3(0):.1f}" width="{bw-1:.1f}" height="{y3(r)-y3(0):.1f}" fill="{MU}" fill-opacity=".7"/>')
    g.append(f'<text x="{x3(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{k[:4] if k.startswith("20") else "12m"}</text>')
g.append(f'<line x1="{X0}" y1="{y3(0):.1f}" x2="{X1}" y2="{y3(0):.1f}" stroke="var(--baseline)"/>')
a, r = ANO[ks[-1]]; g.append(f'<text x="{x3(n3-1)-bw/2:.1f}" y="{y3(a)-5:.1f}" text-anchor="middle" class="fw-s2" fill="{S3}">{fmt(a)}</text><text x="{x3(n3-1)+bw/2:.1f}" y="{y3(r)+12:.1f}" text-anchor="middle" class="fw-s2" fill="{I2}">{fmt(-r)}</text>')
svg = '<svg viewBox="0 0 1100 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
num = {"cy_saldo": SAL[u], "cy_saldo_1T20": DT["1T20"]["saldo"], "cy_saldo_0118": SAL["4T17"], "cy_saldo_4T18": SAL["4T18"], "pct_0118": PCT["4T17"], "pct_4T18": PCT["4T18"], "pct_now": PCT[u], "cr_now": CR[u],
       "cy_adic_ltm": ANO[ks[-1]][0], "cy_rev_ltm": ANO[ks[-1]][1], "adic_2018": ANO["2018"][0], "rev_2018": ANO["2018"][1], "q": u, "old_2015": 20.7, "old_2016": 23.0, "old_2017": 16.6}
json.dump({"svg": svg, "num": num}, io.open(os.path.join(here, "_distrato_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()}); print({q: round(PCT[q], 1) for q in seq})
