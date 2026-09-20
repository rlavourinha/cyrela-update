# -*- coding: utf-8 -*-
"""MAP × Vivaz por dentro (2T26, LTM): lançamentos (100%, %Cyrela, consolidado, minoritários consolidados), vendas, estoque a valor
de mercado (em construção e pronto), e a alocação do balanço por segmento: contas a receber (resíduo do ativo do segmento), estoque a
custo (obra em andamento, concluídos, terrenos) e capital empregado (PL do segmento). Fontes: lista de empreendimentos e planilha
operacional do RI, nota de segmentos e nota de estoques dos ITR (_cbr_lanc, _operacional_ri, _segmentos_full, _estoque_custo, _balanco_cvm).
Saída: _map_vivaz_frag.json {table, svg, num}."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
def fmt(v, d=1): return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
O, S, EC, B, RSG = J("_operacional_ri.json"), J("_segmentos_full.json"), J("_estoque_custo.json"), J("_balanco_cvm.json"), J("_roe_seg_serie.json"); CB = J("_cbr_lanc.json")["trimestral"]
q = "2T26"; L4 = ("3T25", "4T25", "1T26", "2T26"); MAPS, VIVS = ("alto", "medio", "prime"), ("mcmv23", "mcmv1")
seg = lambda k, ss, x=q: sum((O[k]["vgv100_seg"][s].get(x) or 0) for s in ss) / 1000
R = {}
for n, g, ss in (("MAP", "MAP", MAPS), ("Vivaz", "MCMV", VIVS)):
    v = sum(CB[x][g]["vgv"] for x in L4) / 1000; vc = sum(CB[x][g]["vgv_cbr"] for x in L4) / 1000; vk = sum(CB[x][g]["vgv"] * CB[x][g]["consol"] / 100 for x in L4) / 1000
    R[n] = {"lanc": v, "lanc_cbr": vc, "lanc_cons": vk, "lanc_min": vk - vc, "vend": sum(seg("vendas", ss, x) for x in L4), "est": seg("estoque", ss), "pronto": seg("pronto", ss)}
    R[n]["obra"] = R[n]["est"] - R[n]["pronto"]
# --- balanço consolidado (R$ bi) e alocação por segmento
cr = (B[q]["cr_cp_clientes"] + B[q]["cr_lp_clientes"]) / 1000; ec = {k: EC[q][k] / 1000 for k in ("construcao", "concluidos", "terrenos", "adiant_terrenos")}
adi = (B[q]["adiant_cp"] + B[q]["adiant_lp"]) / 1000
SG = {"MAP": {k: (S[q]["cyrela"][k] + S[q]["living"][k]) / 1000 for k in ("ativo", "passivo", "pl")}, "Vivaz": {k: S[q]["mcmv"][k] / 1000 for k in ("ativo", "passivo", "pl")}}
w_obra = {n: R[n]["obra"] / (R["MAP"]["obra"] + R["Vivaz"]["obra"]) for n in R}; w_pronto = {n: R[n]["pronto"] / (R["MAP"]["pronto"] + R["Vivaz"]["pronto"]) for n in R}
_land = {"MAP": R["MAP"]["lanc"] * 0.18, "Vivaz": R["Vivaz"]["lanc"] * 0.10}; w_land = {n: _land[n] / sum(_land.values()) for n in R}   # terreno pesa 18% do VGV no MAP e 10% no MCMV (premissas do deck)
for n in R:
    R[n]["c_obra"] = ec["construcao"] * w_obra[n]; R[n]["c_pronto"] = ec["concluidos"] * w_pronto[n]; R[n]["c_terr"] = (ec["terrenos"] + ec["adiant_terrenos"]) * w_land[n]
    R[n]["adi"] = adi * (SG[n]["ativo"] / (SG["MAP"]["ativo"] + SG["Vivaz"]["ativo"]))
    R[n]["cr_res"] = SG[n]["ativo"] - R[n]["c_obra"] - R[n]["c_pronto"] - R[n]["c_terr"] - R[n]["adi"]
_kcr = cr / (R["MAP"]["cr_res"] + R["Vivaz"]["cr_res"])   # escala o resíduo para o contas a receber consolidado
for n in R: R[n]["cr"] = R[n]["cr_res"] * _kcr; R[n].update(SG[n]); R[n]["ret"] = None
R["MAP"]["ret"] = None; R["Vivaz"]["ret"] = RSG["mcmv"][q]
# --- tabela
def row(lab, key, d=1, pct=False, cls="", f=None):
    cells = ""
    for n in ("MAP", "Vivaz"):
        v = f(R[n]) if f else R[n].get(key)
        cells += f'<td style="text-align:right">{("—" if v is None else (fmt(v, d) + ("%" if pct else "")))}</td>'
    return f'<tr class="{cls}"><td>{lab}</td>{cells}</tr>'
rows = [row("lançamentos 12m, VGV 100%", "lanc", cls="total"), row("   parte Cyrela (%CBR)", None, f=lambda r: 100 * r["lanc_cbr"] / r["lanc"], d=0, pct=True), row("   consolidado (% do VGV)", None, f=lambda r: 100 * r["lanc_cons"] / r["lanc"], d=0, pct=True),
        row("   minoritários dentro do consolidado, R$ bi", "lanc_min"), row("vendas 12m, VGV 100%", "vend", cls="total"), row("estoque a valor de mercado, 100%", "est", cls="total"), row("   em construção", "obra"), row("   pronto", "pronto"),
        row("   pronto, % do estoque", None, f=lambda r: 100 * r["pronto"] / r["est"], d=0, pct=True), row("contas a receber (est., resíduo do ativo)", "cr", cls="total"), row("estoque a custo: obra em andamento (est.)", "c_obra"), row("estoque a custo: concluídos (est.)", "c_pronto"), row("terrenos e adiantamentos (est.)", "c_terr"),
        row("ativo do segmento (ITR)", "ativo", cls="total"), row("passivo do segmento", "passivo"), row("capital empregado = PL do segmento", "pl", cls="total")]
table = ('<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">2T26, R$ bi</th><th style="text-align:right;color:var(--s3)">médio e alto padrão</th><th style="text-align:right;color:var(--s1)">Vivaz (MCMV)</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")
# --- svg: barras lado a lado, composição do ativo e capital por segmento
g = []; X0, Y0, Y1 = 50, 40, 214; W = 420; ymax = 8
cats = [("contas a receber", "cr"), ("obra em andamento", "c_obra"), ("pronto (custo)", "c_pronto"), ("terrenos", "c_terr"), ("passivo", "passivo"), ("PL (capital)", "pl")]
y = lambda v: Y1 - (Y1 - Y0) * v / ymax; slot = W / len(cats); bw = slot * 0.36
g.append(f'<text x="{X0}" y="17" class="gtit">Onde está o ativo de cada segmento, R$ bi</text><text x="{X0}" y="32" class="gsub">2T26; recebível e estoque a custo alocados (est.); passivo e PL do ITR</text>')
for t in (0, 2, 4, 6, 8): g.append(f'<line x1="{X0}" y1="{y(t):.1f}" x2="{X0+W}" y2="{y(t):.1f}" stroke="var(--grid)" opacity=".55"/><text x="{X0-6}" y="{y(t)+3.5:.1f}" text-anchor="end" class="axq" opacity=".85">{t}</text>')
for i, (lab, key) in enumerate(cats):
    for k, (n, col) in enumerate((("MAP", "var(--s3)"), ("Vivaz", "var(--s1)"))):
        v = R[n][key]; x = X0 + i * slot + slot / 2 - bw + k * bw
        g.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bw - 2:.1f}" height="{Y1 - y(v):.1f}" rx="2" fill="{col}" fill-opacity=".85"/><text x="{x + bw / 2 - 1:.1f}" y="{y(v) - 4:.1f}" text-anchor="middle" class="axq" style="font-size:9px" fill="{col}">{fmt(v, 1)}</text>')
    for j, w in enumerate(lab.split(" ")): g.append(f'<text x="{X0 + i * slot + slot / 2:.1f}" y="{Y1 + 13 + 10 * j}" text-anchor="middle" class="axq" style="font-size:9px" opacity=".8">{w}</text>')
g.append(f'<line x1="{X0}" y1="{Y1}" x2="{X0+W}" y2="{Y1}" stroke="var(--baseline)"/><rect x="{X0+W-150}" y="{Y0-2}" width="9" height="9" fill="var(--s3)"/><text x="{X0+W-138}" y="{Y0+6}" class="axq">médio e alto</text><rect x="{X0+W-70}" y="{Y0-2}" width="9" height="9" fill="var(--s1)"/><text x="{X0+W-58}" y="{Y0+6}" class="axq">Vivaz</text>')
svg = f'<svg viewBox="0 0 {X0+W+10} 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">' + "".join(g) + "</svg>"
num = {n: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in R[n].items()} for n in R}; num["cr_total"] = cr; num["k_cr"] = _kcr
json.dump({"table": table, "svg": svg, "num": num}, io.open(os.path.join(here, "_map_vivaz_frag.json"), "w", encoding="utf-8"), ensure_ascii=False)
for n in R: print(n, {k: round(v, 2) for k, v in R[n].items() if isinstance(v, float)})
print("CR consolidado", round(cr, 2), "fator", round(_kcr, 2))
