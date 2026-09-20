# -*- coding: utf-8 -*-
"""Fragmento do slide 'bancos' do deck enxuto (BCB IF.data, trimestral 2015-2026):
svg A: seis painéis (Caixa, Bradesco, Itaú, Santander, BB, sistema) com carteira habitacional PF, PJ, poupança, LCI (Caixa: + FGTS);
svg B: market share no crédito habitacional ex-FGTS, PF e PJ, por banco.
Saída: _bancos_frag.json {svgA, svgB, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
F = json.load(io.open(os.path.join(here, "_funding_emissor_trimestral.json"), encoding="utf-8"))["serie"]
H = json.load(io.open(os.path.join(here, "_funding_emissor_hab_trimestral.json"), encoding="utf-8"))["serie"]
MQ = sorted(m for m in F if m in H and H[m]["Sistema"]["hab_pf"] > 0)   # carteira por modalidade: IF.data só a partir de jun/14
MF = sorted(m for m in F if all(b in F[m] for b in ("Caixa", "Bradesco", "Itaú", "Santander", "Banco do Brasil", "Sistema")))   # passivo (LCI, poupança, repasses): desde mar/00 (20/09/26, dados_ifdata_2000_2014.py)
BK = ["Caixa", "Bradesco", "Itaú", "Santander", "Banco do Brasil", "Sistema"]
COL = {"Caixa": "var(--s1)", "Bradesco": "var(--s2)", "Itaú": "var(--s3)", "Santander": "#2b2a26", "Banco do Brasil": "var(--muted)", "Outros": "var(--ink-2)"}
def fmt(v, d=0): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
def xlab(m, every=2): return "20" + m[2:4] if m.endswith("-12") and int(m[:4]) % every == 1 else ""
def panel(ox, oy, w, h, title, sub, xs, series, ymax, lab_d=0, ygrid=4, sub2=None, every=2):
    X0, X1, Y0, Y1 = ox + 40, ox + w - 72, oy + 34, oy + h - 18   # 20/09/26: X1 −2 e rótulo em X1+7 (mesma borda direita de antes): o "2025" do eixo x (31 un.) terminava em X1+5,2, em cima do rótulo em X1+5
    x = lambda i: X0 + (X1 - X0) * i / (len(xs) - 1); y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g = [f'<text x="{ox+40}" y="{oy+13}" class="gtit" style="font-size:13px">{title}</text><text x="{ox+40}" y="{oy+28}" class="gsub">{sub}</text>']   # 20/09/26: gsub +2 (bbox do título terminava em oy+16,1 e o do subtítulo começava em oy+15,6; a 28 fica 1,5 un. de folga e ainda acima da 1ª linha de grade em oy+34)
    for k in range(ygrid + 1):
        tv = ymax * k / ygrid; g.append(f'<line x1="{X0}" y1="{y(tv):.1f}" x2="{X1}" y2="{y(tv):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-5}" y="{y(tv)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{fmt(tv)}</text>')
    for i, m in enumerate(xs):
        lb = xlab(m, every)
        if lb: g.append(f'<text x="{x(i):.1f}" y="{Y1+13}" text-anchor="middle" class="axq" opacity=".75">{lb}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X1}" y2="{Y1}" stroke="var(--baseline)"/>')
    i22 = next(i for i, m in enumerate(xs) if m >= "2022-06"); g.append(f'<line x1="{x(i22):.1f}" y1="{Y0}" x2="{x(i22):.1f}" y2="{Y1}" stroke="var(--muted)" stroke-dasharray="2 4" opacity=".7"/>')
    ends = []
    for vals, col, wd, dash, lab in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals) if v is not None)
        g.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wd}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} stroke-linejoin="round" stroke-linecap="round"/>')
        ends.append((vals[-1], col, lab))
    GAP = 13   # 20/09/26: bbox de um rótulo de 10px mede 11,5 un. (12,5 com descendente, "poup."); com 11 os empilhados encostavam (poup. 121 / hab. PF 110)
    ends = sorted(ends, reverse=True); ys = []
    for v, col, lab in ends:   # 1ª passada: de cima para baixo, empurra para baixo quem encosta
        yy = y(v)
        for pv in ys:
            if abs(yy - pv) < GAP: yy = pv + GAP
        ys.append(yy)
    lim = Y1 - 5   # 2ª passada: o rótulo de baixo não desce ao eixo x (bbox = yy−8..yy+7; os anos começam em Y1+1,6) e empurra a pilha para cima
    for i in range(len(ys) - 1, -1, -1):
        ys[i] = min(ys[i], lim); lim = ys[i] - GAP
    for (v, col, lab), yy in zip(ends, ys):
        g.append(f'<text x="{X1+7}" y="{yy+3.5:.1f}" class="fw-s2" fill="{col}" style="font-weight:700">{lab} {fmt(v, lab_d)}</text>')
    return "".join(g)
# ---- svg A: seis painéis
PW, PH = 353, 220   # 20/09/26: 205 → 220 (o slide ganhou ~43px com a caixa verde em uma linha; painéis mais altos folgam os rótulos empilhados)
YM = {"Caixa": 1000, "Bradesco": 250, "Itaú": 250, "Santander": 125, "Banco do Brasil": 250, "Sistema": 1500}
gA = []
for n, b in enumerate(BK):
    hv = lambda k: [(H[m][b][k] / 1000 if m in H and b in H[m] else None) for m in MF]
    ser = [(hv("hab_pf"), "#2b2a26", 2.2, "", "hab. PF"), (hv("hab_pj"), "var(--s3)", 2.4, "5 3", "hab. PJ"),
           ([F[m][b]["poup"] / 1000 for m in MF], "var(--s2)", 2.0, "", "poup."), ([F[m][b]["lci"] / 1000 for m in MF], "var(--s1)", 2.6, "", "LCI")]
    if b == "Caixa": ser.append(([F[m][b]["repasses"] / 1000 for m in MF], "#2e7d32", 2.0, "", "FGTS"))
    sub = "R$ bi; poupança inclui rural" if b == "Banco do Brasil" else ("R$ bi; FGTS = obrigações por repasses" if b == "Caixa" else "R$ bi")
    gA.append(panel((n % 3) * PW, (n // 3) * PH, PW, PH, b if b != "Sistema" else "Sistema (todos os bancos)", sub, MF, ser, YM[b], every=4))
svgA = f'<svg viewBox="0 0 1060 {2*PH}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(gA) + "</svg>"
# ---- svg B: market share ex-FGTS (PF: Caixa menos repasses; sistema idem), PJ
def pf_ex(m, b):
    v = H[m][b]["hab_pf"]
    if b in ("Caixa", "Sistema"): v -= F[m]["Caixa"]["repasses"]
    return max(v, 0)
SH_PF = {b: [100 * pf_ex(m, b) / pf_ex(m, "Sistema") for m in MQ] for b in BK[:-1]}
SH_PF["Outros"] = [100 - sum(SH_PF[b][i] for b in BK[:-1]) for i in range(len(MQ))]
SH_PJ = {b: [100 * H[m][b]["hab_pj"] / H[m]["Sistema"]["hab_pj"] for m in MQ] for b in BK[:-1]}
SH_PJ["Outros"] = [100 - sum(SH_PJ[b][i] for b in BK[:-1]) for i in range(len(MQ))]
LB = {"Banco do Brasil": "BB"}
PHB = 340   # 20/09/26: 300 → 340 (slide 21 ficou em ~578px com a caixa verde em uma linha; h2 de duas linhas não cabe em uma nem a 34px)
gB = [panel(0, 0, 530, PHB, "Share no crédito habitacional PF ex-FGTS, %", "carteira PF do banco ÷ sistema; Caixa e sistema sem os repasses do FGTS", MQ, [(SH_PF[b], COL[b], 2.4 if b == "Caixa" else 1.8, "5 3" if b == "Outros" else "", LB.get(b, b)) for b in BK[:-1] + ["Outros"]], 60, ygrid=4),
      panel(530, 0, 530, PHB, "Share no crédito habitacional PJ (plano empresário), %", "carteira PJ habitacional do banco ÷ sistema", MQ, [(SH_PJ[b], COL[b], 2.4 if b == "Caixa" else 1.8, "5 3" if b == "Outros" else "", LB.get(b, b)) for b in BK[:-1] + ["Outros"]], 60, ygrid=4)]
svgB = f'<svg viewBox="0 0 1060 {PHB}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(gB) + "</svg>"
i22 = MQ.index("2022-06")
num = {"ult": MQ[-1], "sh_pf": {b: (round(SH_PF[b][0], 1), round(SH_PF[b][i22], 1), round(SH_PF[b][-1], 1)) for b in SH_PF}, "sh_pj": {b: (round(SH_PJ[b][0], 1), round(SH_PJ[b][i22], 1), round(SH_PJ[b][-1], 1)) for b in SH_PJ},
       "caixa_lci": F[MQ[-1]]["Caixa"]["lci"] / 1000, "tot_lci": F[MQ[-1]]["Sistema"]["lci"] / 1000, "caixa_jun22": F["2022-06"]["Caixa"]["lci"] / 1000, "tot_jun22": F["2022-06"]["Sistema"]["lci"] / 1000}
json.dump({"svgA": svgA, "svgB": svgB, "num": num}, io.open(os.path.join(here, "_bancos_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("ok", MF[0], MQ[0], MQ[-1]); print("share PF ex-FGTS (2015-03, jun/22, jun/26):", num["sh_pf"]); print("share PJ:", num["sh_pj"])
