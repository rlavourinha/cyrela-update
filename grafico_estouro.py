# -*- coding: utf-8 -*-
"""Estouro de obra: custo de construção +10%, em dois segmentos (MAP e MCMV) e quatro cenários, com a tabela didática de como cada
componente se mexe (por R$ 100 de VGV) e um gráfico de barras da margem. Revisão no meio da obra (50% do custo de construção incorrido).
Contabilidade PoC (CPC 47, custo incorrido): PoC = custo incorrido ÷ custo total orçado; receita acumulada = PoC × preço vendido.
Cenários: (A) orçamento original; (B) inflação de custo +10%, 100% vendido: no MAP o saldo devedor (85% do preço, já que 15% foi pago
até a revisão) é corrigido pelo INCC, que aqui é índice perfeito da inflação de custo; no MCMV o preço fica travado na assinatura com
a Caixa; (C) inflação de custo +10%, 0% vendido: a tabela é remarcada +10% (no MCMV, se o teto deixar); (D) erro de orçamento +10%
(quantidade/produtividade, não preço): o INCC não se mexe, o preço vendido não muda. Premissas do deck (slide do caixa por segmento):
MAP terreno 18% do VGV, margem 33%; MCMV terreno 10%, margem 32%. Saída: _estouro_frag.json {map, mcmv: {table, svg, num}}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=1): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
SEG = {"map": {"terreno": 18.0, "margem": 33.0, "pago": 15.0, "incc": True}, "mcmv": {"terreno": 10.0, "margem": 32.0, "pago": 100.0, "incc": False}}
def modelo(s):
    P = 100.0; ter = s["terreno"]; custo = P - s["margem"]; obra = custo - ter; obra2 = obra * 1.10; custo2 = ter + obra2
    poc0 = (ter + 0.5 * obra) / custo; poc1 = (ter + 0.5 * obra) / custo2
    pB = P * (s["pago"] / 100 + (1 - s["pago"] / 100) * 1.10) if s["incc"] else P   # INCC no saldo devedor (MAP) ou preço travado (MCMV)
    sc = {"A": dict(preco=P, ter=ter, obra=obra, custo=custo, poc0=poc0, poc1=poc0, vend=True),
          "B": dict(preco=pB, ter=ter, obra=obra2, custo=custo2, poc0=poc0, poc1=poc1, vend=True),
          "C": dict(preco=P * 1.10, ter=ter, obra=obra2, custo=custo2, poc0=poc0, poc1=poc1, vend=False),
          "D": dict(preco=P, ter=ter, obra=obra2, custo=custo2, poc0=poc0, poc1=poc1, vend=True)}
    for k, r in sc.items():
        r["lb"] = r["preco"] - r["custo"]; r["mg"] = 100 * r["lb"] / r["preco"]
        r["rec0"] = P * r["poc0"] if r["vend"] else 0.0            # receita acumulada antes da revisão (preço original × PoC original)
        r["rec1"] = r["preco"] * r["poc1"] if r["vend"] else 0.0   # depois: PoC novo × preço novo
        r["est"] = r["rec1"] - r["rec0"]
    return sc
HEAD = {"map": ["orçamento<br>original", "inflação +10%<br>100% vendido", "inflação +10%<br>0% vendido, tabela +10%", "erro +10%<br>100% vendido"],
        "mcmv": ["orçamento<br>original", "inflação +10%<br>100% vendido", "inflação +10%<br>0% vendido, teto", "erro +10%<br>100% vendido"]}   # 20/09/26: 2 linhas fixas (agente de formatação: 3-4 linhas antes); INCC no saldo / preço travado ficam na nota
def table(seg, sc):
    K = ["A", "B", "C", "D"]; h = "".join(f'<th style="text-align:right;font-weight:600;line-height:1.15">{x}</th>' for x in HEAD[seg])
    def row(lab, f, cls="", d=1, pct=False):
        cells = "".join(f'<td style="text-align:right">{f(sc[k], d, pct)}</td>' for k in K)
        return f'<tr class="{cls}"><td>{lab}</td>{cells}</tr>'
    v = lambda key: (lambda r, d, pct: fmt(r[key], d) + ("%" if pct else ""))
    dl = lambda a, b: (lambda r, d, pct: ("—" if not r["vend"] else (fmt(r[a], d) + (" → " + fmt(r[b], d) if abs(r[a] - r[b]) > 0.05 else ""))))
    rows = [row("preço de venda (VGV)", v("preco")), row("terreno", v("ter")), row("obra (custo de construção)", v("obra")), row("custo total", v("custo"), "total"),
            row("lucro bruto", v("lb"), "total"), row("margem bruta", lambda r, d, pct: fmt(r["mg"], 1) + "%", "total"),
            row("PoC antes → depois da revisão", lambda r, d, pct: "—" if not r["vend"] else (fmt(100 * r["poc0"], 1) + "%" + (" → " + fmt(100 * r["poc1"], 1) + "%" if abs(r["poc0"] - r["poc1"]) > 5e-4 else ""))),
            row("receita acumulada reconhecida", dl("rec0", "rec1")),
            row("ajuste de receita no trimestre", lambda r, d, pct: "—" if not r["vend"] else ("0" if abs(r["est"]) < 0.05 else (("+" if r["est"] > 0 else "−") + fmt(abs(r["est"]), 1))), "total")]
    return f'<table class="tl compact" style="margin-top:0;table-layout:fixed;width:100%"><colgroup><col style="width:34%"><col style="width:15%"><col style="width:17%"><col style="width:19%"><col style="width:15%"></colgroup><thead><tr><th style="text-align:left">por R$ 100 de VGV</th>{h}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
def svg(seg, sc):
    S1, S2, S3, MU = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)"; g = []
    X0, W, Y0, Y1 = 46, 300, 40, 200; ymax = 40; y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g.append(f'<text x="{X0}" y="16" class="gtit">Margem bruta por cenário, %</text>')
    for t in (0, 10, 20, 30, 40): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X0+W}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+4:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
    bars = [("A", "original", MU), ("B", "inflação · 100% vend.", S3 if seg == "map" else S1), ("C", "inflação · 0% vend.", S2), ("D", "erro de · orçamento", S1)]
    bw = 58; gap = (W - 4 * bw) / 5
    for i, (k, lab, col) in enumerate(bars):
        x = X0 + gap + i * (bw + gap); m = sc[k]["mg"]
        g.append(f'<rect x="{x:.1f}" y="{y(m):.1f}" width="{bw}" height="{Y1-y(m):.1f}" rx="3" fill="{col}"/><text x="{x+bw/2:.1f}" y="{y(m)-6:.1f}" text-anchor="middle" class="fw-t2" fill="{col}">{fmt(m, 1)}%</text>')
        for j, w in enumerate(lab.split(" · ")): g.append(f'<text x="{x+bw/2:.1f}" y="{Y1+13+11*j}" text-anchor="middle" class="axq" opacity=".8">{w}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X0+W}" y2="{Y1}" stroke="var(--baseline)"/>')
    return f'<svg viewBox="0 0 {X0+W+10} 240" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
out = {}
for seg in ("map", "mcmv"):
    sc = modelo(SEG[seg]); out[seg] = {"table": table(seg, sc), "svg": svg(seg, sc), "num": {k: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in r.items()} for k, r in sc.items()}}
    print(seg, {k: (round(r["preco"], 1), round(r["mg"], 1), round(r["est"], 1)) for k, r in sc.items()})
json.dump(out, io.open(os.path.join(here, "_estouro_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
