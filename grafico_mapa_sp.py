# -*- coding: utf-8 -*-
"""Mapa de São Paulo capital: onde Cury e Vivaz lançaram, por período (unidades por distrito, Geoimóvel), sobre a malha de
distritos da Prefeitura (GeoSampa WFS, EPSG:31983, fontes/geo/geosampa_wfs.geojson). Três mapas (2019-21, 2022-24, 2025-26) com
bolhas por distrito (área ∝ unidades lançadas), Cury dourado e Vivaz vermelho; tabela de exposição por região (5 regiões da
Prefeitura). Saída: _mapa_sp_frag.json {svg, table, num}."""
import io, json, os, math, unicodedata, datetime, collections, openpyxl
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
norm = lambda s: unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper().strip()
S1, S3, MU, I2 = "var(--s1)", "var(--s3)", "var(--muted)", "var(--ink-2)"
# ---- malha
J = json.load(io.open(os.path.join(here, "fontes", "geo", "geosampa_wfs.geojson"), encoding="utf-8"))
def rdp(pts, tol):
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]; dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-9
    dm, im = -1, 0
    for i in range(1, len(pts) - 1):
        x, y = pts[i]; d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
        if d > dm: dm, im = d, i
    if dm > tol: return rdp(pts[:im + 1], tol)[:-1] + rdp(pts[im:], tol)
    return [pts[0], pts[-1]]
def simp(ring, tol):   # anel fechado: RDP em duas metades (com primeiro == último a distância perpendicular degenera e o anel colapsa)
    r = ring[:-1] if ring[0] == ring[-1] else ring[:]; m = len(r) // 2
    a = rdp(r[:m + 1], tol); b = rdp(r[m:] + [r[0]], tol); return a[:-1] + b
def centroid(ring):
    A = Cx = Cy = 0.0
    for i in range(len(ring) - 1):
        (x0, y0), (x1, y1) = ring[i], ring[i + 1]; c = x0 * y1 - x1 * y0; A += c; Cx += (x0 + x1) * c; Cy += (y0 + y1) * c
    A *= 0.5; return (Cx / (6 * A), Cy / (6 * A)) if A else ring[0]
DIST = {}
for f in J["features"]:
    p = f["properties"]; g = f["geometry"]; polys = g["coordinates"] if g["type"] == "Polygon" else [q for mp in g["coordinates"] for q in mp]
    rings = [simp([tuple(pt) for pt in r], 60.0) for r in polys]; big = max(polys, key=len)
    DIST[norm(p["nm_distrito_municipal"])] = {"nome": p["nm_distrito_municipal"], "reg": p["nm_regiao_05"], "rings": rings, "c": centroid([tuple(pt) for pt in big])}
# ---- lançamentos Geoimóvel
ws = openpyxl.load_workbook(os.path.join(here, "fontes", "geoimovel", "mercado_completo_geoimovel.xlsx"), read_only=True, data_only=True)["plan"]
rows = list(ws.iter_rows(values_only=True)); H = {h: i for i, h in enumerate(rows[0])}
gi, dl, U, D, RG = H["Grupo Incorporador Apelido"], H["Data Lançamento"], H["Unidades"], H["Distrito"], H["RGI"]
PER = [("2019-21", 2019, 2021), ("2022-24", 2022, 2024), ("2025-26", 2025, 2026)]
CO = {"Cury": lambda r: r[gi] and str(r[gi]).upper().startswith("CURY"), "Vivaz": lambda r: r[gi] and "VIVAZ" in str(r[gi]).upper()}
un = {c: {p[0]: collections.Counter() for p in PER} for c in CO}; nemp = {c: {p[0]: set() for p in PER} for c in CO}
for r in rows[1:]:
    if not isinstance(r[dl], datetime.datetime): continue
    for c, f in CO.items():
        if not f(r): continue
        for p, a, b in PER:
            if a <= r[dl].year <= b: un[c][p][norm(r[D])] += r[U] or 0; nemp[c][p].add(r[RG])
# ---- projeção: recorte na área com lançamentos (+ margem), 3 mapas lado a lado
used = {d for c in un for p in un[c] for d in un[c][p]}
xs = [DIST[d]["c"][0] for d in used]; ys = [DIST[d]["c"][1] for d in used]
X0, X1, Y0, Y1 = min(xs) - 5000, max(xs) + 5000, min(ys) - 4500, max(ys) + 4500
MW = 330; sc = MW / (X1 - X0); MH = (Y1 - Y0) * sc; GAP = 35; TOP = 40
def prj(x, y, ox): return (ox + (x - X0) * sc, TOP + (Y1 - y) * sc)
# malha definida uma vez (coordenadas do 1º mapa) e reusada com <use>
defs = []
for d, v in DIST.items():
    path = " ".join("M" + " L".join(f"{prj(x, y, 0)[0]:.1f},{prj(x, y, 0)[1]:.1f}" for x, y in ring) + " Z" for ring in v["rings"])
    defs.append(f'<path d="{path}"/>')
REGC = {"Centro": "rgba(0,0,0,.10)", "Oeste": "rgba(43,92,138,.10)", "Sul": "rgba(200,150,30,.10)", "Leste": "rgba(179,38,30,.07)", "Norte": "rgba(46,125,50,.09)"}
defs_reg = "".join(f'<g fill="{REGC[reg]}">' + "".join(f'<path d="{" ".join("M" + " L".join(f"{prj(x, y, 0)[0]:.1f},{prj(x, y, 0)[1]:.1f}" for x, y in ring) + " Z" for ring in v["rings"])}"/>' for d, v in DIST.items() if v["reg"] == reg) + "</g>" for reg in REGC)
g = [f'<defs><clipPath id="mapclip"><rect x="0" y="{TOP}" width="{MW}" height="{MH:.1f}"/></clipPath><g id="malha" fill="none" stroke="var(--baseline)" stroke-width=".5" opacity=".55">' + "".join(defs) + f'</g><g id="regioes">{defs_reg}</g></defs>']
RMAX = 17; UMAX = max(un[c][p][d] for c in un for p in un[c] for d in un[c][p])
rad = lambda u: RMAX * math.sqrt(u / UMAX)
# rótulos de regiões (posição = centroide médio dos distritos da região), só no 1º mapa
regc = collections.defaultdict(list)
for d, v in DIST.items(): regc[v["reg"]].append(v["c"])
LAB = {norm(x): x for x in ("Lapa", "Jaguaré", "Santo Amaro", "Barra Funda", "Penha", "Freguesia do Ó", "Jaraguá", "Cambuci", "Mooca", "Ermelino Matarazzo", "Morumbi", "Sacomã", "Butantã", "Mandaqui", "Rio Pequeno", "São Lucas", "Jabaquara")}
tot = {}
for k, (p, a, b) in enumerate(PER):
    ox = k * (MW + GAP); g.append(f'<g transform="translate({ox},0)"><g clip-path="url(#mapclip)"><use href="#regioes"/><use href="#malha"/></g></g>')
    g.append(f'<text x="{ox + MW / 2:.1f}" y="{TOP - 16}" class="gtit" text-anchor="middle">{p}</text>')
    tc, tv = sum(un["Cury"][p].values()), sum(un["Vivaz"][p].values()); tot[p] = (tc, tv, len(nemp["Cury"][p]), len(nemp["Vivaz"][p]))
    g.append(f'<text x="{ox + MW / 2:.1f}" y="{TOP - 3}" class="gsub" text-anchor="middle">Cury {fmt(tc / 1000, 1)} mil un. em {len(nemp["Cury"][p])} lanç. · Vivaz {fmt(tv / 1000, 1)} mil em {len(nemp["Vivaz"][p])}</text>')
    if k == 0:
        for reg, cs in regc.items():
            cx = sum(c[0] for c in cs) / len(cs); cy = sum(c[1] for c in cs) / len(cs); x, y = prj(cx, cy, ox)
            if TOP < y < TOP + MH: g.append(f'<text x="{x:.1f}" y="{y:.1f}" class="axq" text-anchor="middle" opacity=".35" style="font-size:9.5px;letter-spacing:.08em">{reg.upper()}</text>')
    labs = []
    for c, col, dx in (("Vivaz", S1, 1), ("Cury", S3, -1)):
        for d, u in sorted(un[c][p].items(), key=lambda kv: -kv[1]):
            x, y = prj(*DIST[d]["c"], ox); r = rad(u)
            g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{col}" fill-opacity=".55" stroke="{col}" stroke-width="1"/>')
            if d in LAB and u >= 1100: labs.append((x, y, r, LAB[d], col))
    seen = set()
    for x, y, r, n, col in labs:
        if n in seen: continue
        seen.add(n); g.append(f'<text x="{x + r + 4:.1f}" y="{y + 3.5:.1f}" class="axq" style="font-size:9px" fill="{I2}" paint-order="stroke" stroke="var(--page)" stroke-width="3.5" stroke-linejoin="round">{n}</text>')
# legenda
ly = TOP + MH + 14; g.append(f'<circle cx="8" cy="{ly - 4}" r="5" fill="{S3}" fill-opacity=".55" stroke="{S3}"/><text x="17" y="{ly}" class="axq">Cury</text><circle cx="58" cy="{ly - 4}" r="5" fill="{S1}" fill-opacity=".55" stroke="{S1}"/><text x="67" y="{ly}" class="axq">Vivaz</text><text x="110" y="{ly}" class="axq" opacity=".8">área da bolha ∝ unidades lançadas no distrito no período; fundo = regiões da Prefeitura (Centro, Oeste, Sul, Leste, Norte)</text>')
W = 3 * MW + 2 * GAP; Hh = ly + 6
svg = f'<svg viewBox="0 0 {W:.0f} {Hh:.0f}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
# ---- tabela: share de unidades por região
REGS = ["Centro", "Oeste", "Sul", "Leste", "Norte"]
def share(c, p):
    t = sum(un[c][p].values()); s = collections.Counter()
    for d, u in un[c][p].items(): s[DIST[d]["reg"]] += u
    return {r: (100 * s[r] / t if t else 0) for r in REGS}
th = "".join(f'<th style="text-align:right">{r}</th>' for r in REGS)
tr = []
for c, col in (("Cury", "var(--s3)"), ("Vivaz", "var(--s1)")):
    for p, _, _ in PER:
        s = share(c, p); cells = "".join(f'<td style="text-align:right{";font-weight:700" if s[r] == max(s.values()) else ""}">{fmt(s[r])}%</td>' for r in REGS)
        tr.append(f'<tr><td style="color:{col};font-weight:700">{c} {p}</td>{cells}<td style="text-align:right">{fmt(tot[p][0 if c == "Cury" else 1] / 1000, 1)} mil</td></tr>')
table = f'<table class="tl compact" style="margin-top:0;width:100%"><thead><tr><th style="text-align:left">unidades lançadas, % por região</th>{th}<th style="text-align:right">total</th></tr></thead><tbody>{"".join(tr)}</tbody></table>'
num = {"tot": tot, "share": {c: {p: share(c, p) for p, _, _ in PER} for c in CO}, "umax": UMAX, "svg_kb": round(len(svg) / 1024)}
json.dump({"svg": svg, "table": table, "num": num}, io.open(os.path.join(here, "_mapa_sp_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok svg", num["svg_kb"], "KB | umax", UMAX, "| mapa", round(MW), "x", round(MH)); print(json.dumps(num["share"], ensure_ascii=False, indent=0)[:900]); print(tot)
