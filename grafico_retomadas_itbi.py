# -*- coding: utf-8 -*-
"""Retomadas em SP: guias de ITBI com natureza '17. Resolução da alienação fiduciária por inadimplemento' (o credor consolida a
propriedade do imóvel financiado; Lei 9.514/1997, art. 26) e '4. Arrematação em leilão' (a venda posterior). Microdados da
Prefeitura de SP (fontes/mercado/itbi/itbi_AAAA.xlsx, uma aba por mês de pagamento, 2019-2026). Série mensal pelo mês da guia
(pagamento do ITBI = registro da consolidação). Residencial = uso IPTU 10 (residência) e 20 (apartamento). Faixas pela base de
cálculo (valor venal de referência, já que na retomada não há preço de venda). Saída: _retomadas_frag.json {svg, table, num}."""
import io, json, os, glob, collections, datetime
import openpyxl
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
S1, S2, S3, MU, I2 = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)", "var(--ink-2)"
MES = {"JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12}
FX = [(0, 350e3, "até 350 mil"), (350e3, 700e3, "350-700 mil"), (700e3, 1.5e6, "700 mil-1,5 mi"), (1.5e6, 1e12, "acima de 1,5 mi")]
def fx(v):
    for a, b, n in FX:
        if a <= v < b: return n
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
cache = os.path.join(here, "_retomadas_itbi_raw.json")
if os.path.exists(cache): R = json.load(io.open(cache, encoding="utf-8"))
else:
    M = collections.defaultdict(lambda: collections.Counter()); V = collections.defaultdict(float); FXC = collections.defaultdict(collections.Counter)
    for fp in sorted(glob.glob(os.path.join(here, "fontes", "mercado", "itbi", "itbi_*.xlsx"))):
        wb = openpyxl.load_workbook(fp, read_only=True)
        for ws in wb.worksheets:
            if ws.title[:3] not in MES or "-" not in ws.title: continue
            ym = f"{ws.title[-4:]}-{MES[ws.title[:3]]:02d}"
            for r in ws.iter_rows(min_row=2, values_only=True):
                if not r or r[0] is None: continue
                n = str(r[7] or ""); uso = f(r[23]); res = uso in (10.0, 20.0); base = f(r[13]) or 0.0
                if n.startswith("17."):
                    M[ym]["ret"] += 1
                    if res: M[ym]["ret_res"] += 1; V[ym] += base; FXC[ym[:4]][fx(base)] += 1
                elif n.startswith("4."):
                    M[ym]["arr"] += 1
                    if res: M[ym]["arr_res"] += 1
                elif n.startswith("1.") and res and abs((f(r[11]) or 0) - 100) < 0.01: M[ym]["cv_res"] += 1
        print(os.path.basename(fp), flush=True)
    R = {"m": {k: dict(v) for k, v in M.items()}, "v": dict(V), "fx": {k: dict(v) for k, v in FXC.items()}}
    json.dump(R, io.open(cache, "w", encoding="utf-8"), ensure_ascii=False)
M, V, FXC = R["m"], R["v"], R["fx"]
ms = sorted(k for k in M if k >= "2019-01")
g = lambda k, c: M.get(k, {}).get(c, 0)
ret = [g(k, "ret_res") for k in ms]; arr = [g(k, "arr_res") for k in ms]; cv = [g(k, "cv_res") for k in ms]
def mm12(s): return [sum(s[i - 11:i + 1]) / 12 if i >= 11 else None for i in range(len(s))]
ret12, arr12 = mm12(ret), mm12(arr); shr = [100 * sum(ret[i - 11:i + 1]) / sum(cv[i - 11:i + 1]) if i >= 11 and sum(cv[i - 11:i + 1]) else None for i in range(len(ms))]
# ---- svg: três painéis
G = []; Y0, Y1 = 46, 226
def panel(X0, X1, title, sub, ymax, ticks, tf, series, n):
    x = lambda i: X0 + (X1 - X0) * i / (n - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    G.append(f'<text x="{X0}" y="17" class="gtit">{title}</text><text x="{X0}" y="32" class="gsub">{sub}</text>')
    for t in ticks: G.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X1}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{tf(t)}</text>')
    for i, k in enumerate(ms):
        if k.endswith("-01"): G.append(f'<text x="{x(i):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{k[:4]}</text>')
    G.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>'); ends = []
    for vals, col, w, dash, lab, lf, op in series:
        pts = " ".join(f"{x(i):.1f},{y(min(v, ymax)):.1f}" for i, v in enumerate(vals) if v is not None)
        G.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round" opacity="{op}"/>')
        if lab:
            last = [v for v in vals if v is not None][-1]; ends.append([y(last), col, f"{lab} {lf(last)}"])
    ends.sort(key=lambda e: e[0])
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 13: ends[k][0] = ends[k - 1][0] + 13
    for yy, col, lab in ends: G.append(f'<text x="{X1+5:.1f}" y="{yy+4:.1f}" class="fw-t2" fill="{col}">{lab}</text>')
n = len(ms); top = 50 * (int(max(ret + arr) / 50) + 1)
panel(44, 330, "Retomadas e leilões em SP, por mês", "unidades residenciais; linha fina = mês, grossa = média 12m", top, list(range(0, top + 1, 100)), lambda t: fmt(t),
      [(ret, S1, 1.2, "", "", None, .45), (ret12, S1, 2.6, "", "retomadas", lambda v: fmt(v), 1), (arr, S3, 1.2, "", "", None, .45), (arr12, S3, 2.6, "", "leilões", lambda v: fmt(v), 1)], n)
smax = 5 * (int(max(v for v in shr if v) / 5) + 1)
panel(410, 700, "Retomadas ÷ compras residenciais, %", "12 meses; compra e venda com 100% transmitido", smax, list(range(0, smax + 1, 1 if smax <= 5 else 2)), lambda t: f"{t}%",
      [(shr, S2, 2.6, "", "", lambda v: fmt(v, 1) + "%", 1)], n)
G.append(f'<text x="{705}" y="{Y1 - (Y1 - Y0) * shr[-1] / smax + 4:.1f}" class="fw-t2" fill="{S2}">{fmt(shr[-1], 1)}%</text>')
# painel 3: faixa de valor (base de cálculo) das retomadas, % por ano
anos = sorted(a for a in FXC if a >= "2019"); X0, X1 = 790, 1075; k4 = [n_ for _, _, n_ in FX]
G.append(f'<text x="{X0}" y="17" class="gtit">Retomadas por faixa de valor, %</text><text x="{X0}" y="32" class="gsub">R$ mil, valor venal de referência; 2026 até jul</text>')
y3 = lambda v: Y1 - (Y1 - Y0) * v / 80
for t in (0, 20, 40, 60, 80): G.append(f'<line x1="{X0}" y1="{y3(t):.1f}" x2="{X1}" y2="{y3(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y3(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
cols = [S1, S3, S2, MU]; gw = (X1 - X0) / len(anos); bw = gw / 5.2
for j, a in enumerate(anos):
    tot = sum(FXC[a].values()) or 1; x0 = X0 + gw * j + gw * 0.1
    for i, kf in enumerate(k4):
        p = 100 * FXC[a].get(kf, 0) / tot
        G.append(f'<rect x="{x0 + i * bw:.1f}" y="{y3(p):.1f}" width="{bw - 1:.1f}" height="{Y1 - y3(p):.1f}" fill="{cols[i]}" fill-opacity=".85"/>')
    G.append(f'<text x="{X0 + gw * (j + 0.5):.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".75">{a}</text>')
G.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
for i, kf in enumerate(("até 350", "350-700", "700-1.500", "> 1.500")): G.append(f'<rect x="{X0 + i * 68:.0f}" y="{Y0 - 4}" width="8" height="8" fill="{cols[i]}"/><text x="{X0 + i * 68 + 11:.0f}" y="{Y0 + 3}" class="axq" fill="{I2}">{kf}</text>')
svg = '<svg viewBox="0 0 1100 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(G) + "</svg>"
# ---- tabela anual
def yr(a, s): return sum(v for k, v in zip(ms, s) if k.startswith(a))
anos_t = sorted({k[:4] for k in ms}); rows = []
for a in anos_t:
    rr, aa, cc = yr(a, ret), yr(a, arr), yr(a, cv); vv = sum(V.get(k, 0) for k in ms if k.startswith(a))
    rows.append((a + (" até jul" if a == ms[-1][:4] else ""), rr, aa, 100 * rr / cc if cc else None, vv / rr / 1000 if rr else None, 100 * FXC.get(a, {}).get("até 350 mil", 0) / (sum(FXC.get(a, {}).values()) or 1)))
table = ('<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">SP, residencial</th>' + "".join(f'<th style="text-align:right">{r[0]}</th>' for r in rows) + '</tr></thead><tbody>'
         + '<tr class="total"><td>retomadas (resolução da alienação fiduciária)</td>' + "".join(f'<td style="text-align:right">{fmt(r[1])}</td>' for r in rows) + '</tr>'
         + '<tr><td>arrematações em leilão</td>' + "".join(f'<td style="text-align:right">{fmt(r[2])}</td>' for r in rows) + '</tr>'
         + '<tr><td>retomadas ÷ compras e vendas</td>' + "".join(f'<td style="text-align:right">{fmt(r[3], 1)}%</td>' for r in rows) + '</tr>'
         + '<tr><td>valor venal médio da unidade retomada, R$ mil</td>' + "".join(f'<td style="text-align:right">{fmt(r[4])}</td>' for r in rows) + '</tr>'
         + '<tr><td>retomadas até R$ 350 mil, % do ano</td>' + "".join(f'<td style="text-align:right">{fmt(r[5])}%</td>' for r in rows) + '</tr></tbody></table>')
num = {"u": ms[-1], "ret12": ret12[-1], "ret12_min": min(v for v in ret12 if v), "ret12_min_m": ms[ret12.index(min(v for v in ret12 if v))], "ret12_max": max(v for v in ret12 if v), "ret12_max_m": ms[ret12.index(max(v for v in ret12 if v))],
       "arr12": arr12[-1], "shr": shr[-1], "shr_min": min(v for v in shr if v), "shr_max": max(v for v in shr if v), "ano": [dict(zip(("ano", "ret", "arr", "shr", "vm", "p350"), r)) for r in rows]}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_retomadas_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok"); [print(r) for r in rows]; print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in num.items() if k != "ano"})
