# -*- coding: utf-8 -*-
"""Cury × Vivaz (slide 33): tabela de safras da Geoimóvel (SP capital, % vendido por semestre de lançamento, na mesma idade),
VSO trimestral (RI de cada uma) e ticket médio lançado por ano (RI). Saída: _cury_vivaz_frag.json {table, svg, num}.
20/09/26: o painel 'curva por faixa de idade' virou tabela por safra a pedido (a curva era foto de mai/26 e lia-se como série no tempo)."""
import io, json, os, datetime, collections, openpyxl
here = os.path.dirname(os.path.abspath(__file__))
G = json.load(io.open(os.path.join(here, "_geoimovel.json"), encoding="utf-8"))["curvas"]
O = json.load(io.open(os.path.join(here, "_operacional_ri.json"), encoding="utf-8")); L = json.load(io.open(os.path.join(here, "_lancamentos_ri.json"), encoding="utf-8"))
C = json.load(io.open(os.path.join(here, "_cury_hist.json"), encoding="utf-8"))
ORD = lambda q: (int(q[2:]), int(q[0])); Q = O["tris"]
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
# --- safras Geoimóvel: % vendido em mai/26 por semestre de lançamento, Vivaz × Cury × econômico ex-ambas (SP capital, residencial vertical)
ws = openpyxl.load_workbook(os.path.join(here, "fontes", "geoimovel", "mercado_completo_geoimovel.xlsx"), read_only=True, data_only=True)["plan"]
rows = list(ws.iter_rows(values_only=True)); H = {h: i for i, h in enumerate(rows[0])}
gi, dl, U, V, RG, PAD = H["Grupo Incorporador Apelido"], H["Data Lançamento"], H["Unidades"], H["Unidades Vendidas"], H["RGI"], H["Padrão"]
REF = datetime.datetime(2026, 5, 1)
def coh(filt):
    agg = collections.defaultdict(lambda: [set(), 0, 0])
    for r in rows[1:]:
        if not filt(r) or not isinstance(r[dl], datetime.datetime) or r[dl] < datetime.datetime(2022, 7, 1): continue
        k = f"{r[dl].year}-{1 if r[dl].month <= 6 else 2}"; a = agg[k]; a[0].add(r[RG]); a[1] += r[U] or 0; a[2] += r[V] or 0
    return {k: (len(a[0]), a[1], a[2]) for k, a in agg.items()}
isv = lambda r: r[gi] and "VIVAZ" in str(r[gi]).upper(); isc = lambda r: r[gi] and str(r[gi]).upper().startswith("CURY")
CO = {"Vivaz": coh(isv), "Cury": coh(isc), "econ": coh(lambda r: str(r[PAD]).lower().startswith("econ") and not (isv(r) or isc(r)))}
SAF = sorted(set(CO["Vivaz"]) | set(CO["Cury"]))
def age(k):
    y, s = int(k[:4]), int(k[-1]); m = 3 if s == 1 else 9; return (REF.year - y) * 12 + REF.month - m
def pct(d, k): return 100 * d[k][2] / d[k][1] if k in d and d[k][1] else None
cell = lambda v, cls="": f'<td style="text-align:right{cls}">{fmt(v) + "%" if v is not None else "—"}</td>'
tr = []
for k in SAF:
    lab = f"{k[-1]}S{k[2:4]}"; pv, pc, pe = pct(CO["Vivaz"], k), pct(CO["Cury"], k), pct(CO["econ"], k)
    tr.append(f'<tr><td style="white-space:nowrap">{lab}</td><td style="text-align:right">{age(k)}</td>{cell(pc, ";color:var(--s3);font-weight:700")}{cell(pv, ";color:var(--s1);font-weight:700")}{cell(pe)}</tr>')
table = ('<table class="tl compact" style="margin-top:0;width:100%"><thead><tr><th style="text-align:left">safra</th><th style="text-align:right">idade, meses</th><th style="text-align:right">Cury</th><th style="text-align:right">Vivaz</th><th style="text-align:right">econ. SP</th></tr></thead><tbody>'
         + "".join(tr) + '</tbody></table>')
# --- VSO trimestral. Cury: VSO líquida do trimestre (RI). Vivaz (MCMV 2 e 3 + Faixa 1): vendas do trimestre ÷ (estoque a valor de mercado no fim do trimestre anterior + lançamentos do trimestre), VGV 100%, bruta
mk = ["mcmv23", "mcmv1"]; lk = ["vgv_mcmv23", "vgv_mcmv1"]
def ss(d, q): return sum((d.get(k, {}).get(q) or 0) for k in mk)
VZ = {}
for i, q in enumerate(Q):
    if i < 1 or ORD(q) < (19, 2): continue   # 1T19 = primeiro trimestre pro forma ex-Cury; o estoque de 4T18 ainda inclui a Cury (VSO de 9% é artefato)
    v = ss(O["vendas"]["vgv100_seg"], q); l = sum((L[k].get(q) or 0) for k in lk) / 1000; e0 = ss(O["estoque"]["vgv100_seg"], Q[i - 1])
    VZ[q] = 100 * v / (e0 + l) if e0 + l else None
CU = {q: 100 * v for q, v in C["VENDAS E DISTRATOS · VSO Líquido"].items() if "T" in q and ORD(q) >= (19, 2)}
QV = [q for q in Q if q in VZ]
# --- ticket médio lançado por ano (R$ mil por unidade)
ct = {y: v for y, v in C["LANÇAMENTOS · Preço médio por unidade (em R$ mil)"].items() if "T" not in y}
vt = {}
for y in range(2017, 2026):
    yy = str(y)[2:]; v = sum(L["vgv_mcmv23"].get(f"{k}T{yy}") or 0 for k in range(1, 5)); u = sum(L["un_mcmv23"].get(f"{k}T{yy}") or 0 for k in range(1, 5)); vt[str(y)] = v / u if u else None
YS = [str(y) for y in range(2017, 2026)]
# --- svg: dois painéis (VSO trimestral, ticket)
g = []; Y0, Y1 = 46, 232
X0, X1 = 44, 330; xq = lambda i: X0 + (X1 - X0) * i / (len(QV) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / 60
g.append(f'<text x="{X0}" y="17" class="gtit">VSO do trimestre, %</text><text x="{X0}" y="32" class="gsub">Cury: RI, líquida; Vivaz: vendas ÷ (estoque inicial + lançamentos)</text>')
for t in (0, 20, 40, 60): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
for i, q in enumerate(QV):
    if q.startswith("4T"): g.append(f'<text x="{xq(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">20{q[2:]}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
for d, col, lab in ((CU, S3, "Cury"), (VZ, S1, "Vivaz")):
    pts = " ".join(f"{xq(i):.1f},{y(d[q]):.1f}" for i, q in enumerate(QV) if d.get(q) is not None)
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linejoin="round"/>')
    v = d[QV[-1]]; g.append(f'<circle cx="{X1}" cy="{y(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{y(v)+4:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v)}%</text>')
X0, X1 = 440, 640; xy_ = lambda i: X0 + (X1 - X0) * i / (len(YS) - 1); yt = lambda v: Y1 - (Y1 - Y0) * v / 400
g.append(f'<text x="{X0}" y="17" class="gtit">Ticket médio lançado, R$ mil</text><text x="{X0}" y="32" class="gsub">VGV lançado ÷ unidades, por ano (RI)</text>')
for t in (0, 100, 200, 300, 400): g.append(f'<line x1="{X0}" y1="{yt(t):.1f}" x2="{X1}" y2="{yt(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{yt(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}</text>')
for i, yv in enumerate(YS):
    if int(yv) % 2 == 1: g.append(f'<text x="{xy_(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{yv}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
for d, col, lab, dy in ((ct, S3, "Cury", -4), (vt, S1, "Vivaz", 8)):
    pts = " ".join(f"{xy_(i):.1f},{yt(d[yv]):.1f}" for i, yv in enumerate(YS) if d.get(yv))
    g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.6" stroke-linejoin="round"/>')
    v = d[YS[-1]]; g.append(f'<circle cx="{X1}" cy="{yt(v):.1f}" r="3" fill="{col}"/><text x="{X1+6}" y="{yt(v)+dy:.1f}" class="fw-t2" fill="{col}">{lab} {fmt(v)}</text>')
svg = '<svg viewBox="0 0 720 252" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
k8 = "2025-2"   # safra mais recente com idade fechada (8 meses em mai/26)
num = {"cury_0_6": G["cury"][0]["pct"], "vivaz_0_6": G["vivaz"][0]["pct"], "saf8": "2S25", "idade8": age(k8), "cury8": pct(CO["Cury"], k8), "vivaz8": pct(CO["Vivaz"], k8), "econ8": pct(CO["econ"], k8),
       "vso_cury": CU[QV[-1]], "vso_vivaz": VZ[QV[-1]], "vso_vivaz_4T22": VZ["4T22"], "vso_cury_med": sum(CU[q] for q in QV[-4:]) / 4, "vso_vivaz_med": sum(VZ[q] for q in QV[-4:]) / 4,
       "ticket_cury": ct["2025"], "ticket_vivaz": vt["2025"], "n_cury": sum(v[0] for v in CO["Cury"].values()), "n_vivaz": sum(v[0] for v in CO["Vivaz"].values()), "un_vivaz_2s25": CO["Vivaz"][k8][1], "un_cury_2s25": CO["Cury"][k8][1]}
json.dump({"table": table, "svg": svg, "num": num}, io.open(os.path.join(here, "_cury_vivaz_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items()})
