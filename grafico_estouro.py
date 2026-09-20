# -*- coding: utf-8 -*-
"""Estouro de obra: revisão de orçamento de +10% na construção, em dois segmentos (MAP e MCMV) e dois cenários (0% e 100% vendido),
com e sem INCC (INCC = índice perfeito da inflação de custo). Modelo por R$ 100 de VGV, revisão no meio da obra (50% do custo de
construção incorrido). Contabilidade PoC: receita reconhecida = PoC × vendas; PoC = custo incorrido ÷ custo total orçado (terreno + obra).
Premissas do deck (slide do caixa por segmento): MAP terreno 18% do VGV, margem bruta ~33%; MCMV terreno 10%, margem ~32%.
MAP: fluxo do cliente 30% na obra, 70% nas chaves; saldo devedor corrigido pelo INCC até a entrega. MCMV: preço travado na assinatura
com a Caixa; obra financiada por medição; sem INCC para o comprador. Saída: _estouro_frag.json {map, mcmv}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def fmt(v, d=1): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
SEG = {
 "map": {"nome": "médio e alto padrão", "terreno": 18.0, "margem": 33.0, "pago_na_revisao": 15.0, "incc_repassa": True, "teto": False,
         "nota_incc": "saldo devedor do contrato corrigido pelo INCC até as chaves"},
 "mcmv": {"nome": "MCMV (Vivaz)", "terreno": 10.0, "margem": 32.0, "pago_na_revisao": 100.0, "incc_repassa": False, "teto": True,
          "nota_incc": "preço travado na assinatura com a Caixa; o INCC não chega ao comprador"},
}
def modelo(s):
    P = 100.0; terreno = s["terreno"]; custo = P - s["margem"]; obra = custo - terreno
    inc = 0.5 * obra                      # incorrido na revisão
    obra2 = obra * 1.10; custo2 = terreno + obra2
    poc0 = (terreno + inc) / custo; poc1 = (terreno + inc) / custo2
    # 100% vendido, sem INCC (preço fixo)
    m_fixo = (P - custo2) / P * 100
    rev = P * (poc0 - poc1)               # receita já reconhecida que estorna (por R$ 100 de VGV vendido)
    lb_rev = rev * (1 - custo / P)        # lucro bruto estornado (receita − custo proporcional)
    # 100% vendido, com INCC perfeito (+10% no saldo devedor não pago)
    if s["incc_repassa"]:
        P2 = P * (1 + 0.10 * (1 - s["pago_na_revisao"] / 100)); m_incc = (P2 - custo2) / P2 * 100
    else:
        P2 = P; m_incc = m_fixo
    # 0% vendido: preço livre; se o mercado acompanha o INCC, remarca +10%; no MCMV o teto trava
    P3 = P * 1.10; m_remarca = (P3 - custo2) / P3 * 100
    return {"custo": custo, "obra": obra, "custo2": custo2, "poc0": poc0 * 100, "poc1": poc1 * 100, "rev": rev, "lb_rev": lb_rev, "m_base": s["margem"], "m_fixo": m_fixo, "m_incc": m_incc, "m_remarca": m_remarca, "P2": P2}
def svg(seg, r):
    s = SEG[seg]; S1, S2, S3, MU = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)"
    g = []
    # painel 1: margem bruta por cenário (barras)
    X0, W, Y0, Y1 = 60, 560, 60, 240; ymax = 40
    y = lambda v: Y1 - (Y1 - Y0) * v / ymax
    g.append(f'<text x="{X0}" y="18" class="gtit">Margem bruta do projeto (%), orçamento de obra +10%</text><text x="{X0}" y="33" class="gsub">por R$ 100 de VGV; revisão no meio da obra; {s["nota_incc"]}</text>')
    for t in (0, 10, 20, 30, 40): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X0+W}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+4:.1f}" text-anchor="end" class="axq" opacity=".85">{t}%</text>')
    bars = [("base", r["m_base"], MU, "orçamento original"),
            ("0% vendido", r["m_remarca"], S2, "0% vendido · remarca o preço +10%" + (" (se o teto deixar)" if s["teto"] else "")),
            ("100% · sem INCC", r["m_fixo"], S1, "100% vendido · preço fixo (erro de orçamento)"),
            ("100% · com INCC", r["m_incc"], S3 if s["incc_repassa"] else S1, "100% vendido · inflação de custo = INCC")]
    bw = 90; gap = (W - 4 * bw) / 5
    for i, (lab, v, col, sub) in enumerate(bars):
        x = X0 + gap + i * (bw + gap)
        g.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw}" height="{Y1-y(v):.1f}" rx="3" fill="{col}"/><text x="{x+bw/2:.1f}" y="{y(v)-6:.1f}" text-anchor="middle" class="fw-t2" fill="{col}">{fmt(v, 1)}%</text>')
        g.append(f'<text x="{x+bw/2:.1f}" y="{Y1+14}" text-anchor="middle" class="axq" opacity=".85">{lab}</text>')
        if i == 1 and s["teto"]: g.append(f'<text x="{x+bw/2:.1f}" y="{Y1+26}" text-anchor="middle" class="axq" opacity=".7">se o teto deixar</text>')
        if i == 3: g.append(f'<text x="{x+bw/2:.1f}" y="{Y1+26}" text-anchor="middle" class="axq" opacity=".7">{"saldo devedor +10%" if s["incc_repassa"] else "preço travado"}</text>')
    g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X0+W}" y2="{Y1}" stroke="var(--baseline)"/>')
    # painel 2: PoC e estorno (cartões em svg)
    x2 = 660
    g.append(f'<text x="{x2}" y="18" class="gtit">O que a revisão faz na DRE (100% vendido)</text><text x="{x2}" y="33" class="gsub">PoC = custo incorrido ÷ custo total; receita reconhecida = PoC × VGV vendido</text>')
    rows = [("PoC antes da revisão", f"{fmt(r['poc0'], 1)}%"), ("PoC depois (+10% na obra)", f"{fmt(r['poc1'], 1)}%"), ("receita estornada no trimestre", f"−{fmt(r['rev'], 1)} por R$ 100 de VGV"), ("lucro bruto estornado", f"−{fmt(r['lb_rev'], 1)} por R$ 100 de VGV"), ("custo total", f"{fmt(r['custo'], 1)} → {fmt(r['custo2'], 1)}"), ("preço com INCC nas chaves", f"100 → {fmt(r['P2'], 1)}" if s["incc_repassa"] else "100 → 100 (travado)")]
    for i, (a, b) in enumerate(rows):
        yy = 62 + i * 30
        g.append(f'<rect x="{x2}" y="{yy-18}" width="360" height="26" rx="4" fill="rgba(0,0,0,.035)"/><text x="{x2+8}" y="{yy}" class="fw-s2" fill="var(--ink-2)">{a}</text><text x="{x2+352}" y="{yy}" text-anchor="end" class="fw-t2" fill="{S1 if "estorn" in a else "var(--ink-2)"}">{b}</text>')
    return '<svg viewBox="0 0 1060 278" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
out = {}
for seg in ("map", "mcmv"):
    r = modelo(SEG[seg]); out[seg] = {"svg": svg(seg, r), "num": r}
    print(seg, {k: round(v, 1) for k, v in r.items()})
json.dump(out, io.open(os.path.join(here, "_estouro_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
