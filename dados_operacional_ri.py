# -*- coding: utf-8 -*-
"""Planilha de dados operacionais do RI (fontes/planilha_dados_operacionais.xlsx): landbank, estoque, estoque pronto
e vendas, por trimestre (só colunas 'nTaa'; as colunas anuais são ignoradas). Valores em R$ mil na planilha -> R$ mi aqui.
Saída: _operacional_ri.json = {"tris": [...], "landbank": {"vgv100_total", "vgv100_regiao": {...}, "vgvcbr_total", "n_terrenos", "pct_permuta"},
"estoque": {"vgv100_seg": {...}, "vgv100_total", "vgvcbr_total", "un_total"}, "pronto": {"vgv100_total", "vgv100_seg": {...}, "un_total"},
"vendas": {"vgv100_seg": {...}, "vgv100_total", "vgvcbr_total"}}. Estoque e vendas: dados a partir de 2019 são pro forma (ex-Cury e Plano&Plano), como avisa a planilha."""
import io, json, os, re
import openpyxl
here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_dados_operacionais.xlsx"), read_only=True, data_only=True)
def block(ws_name, header_row, labels, scale=1e-3):
    ws = wb[ws_name]; rows = list(ws.iter_rows(values_only=True))
    hdr = rows[header_row - 1]; cols = [(i, h) for i, h in enumerate(hdr) if isinstance(h, str) and re.fullmatch(r"\dT\d\d", h)]
    out = {}
    for r in rows[header_row:header_row + 40]:
        if r[0] is None: break
        lab = str(r[0]).strip()
        if lab in labels:
            out[labels[lab]] = {h: (round(r[i] * scale, 3) if isinstance(r[i], (int, float)) else None) for i, h in cols}
    return [h for _, h in cols], out
SEG = {"Alto": "alto", "Médio": "medio", "Vivaz Prime": "prime", "MCMV 2 e 3": "mcmv23", "MCMV 1": "mcmv1", "Total": "total"}
REG = {"São Paulo": "sp", "São Paulo - Interior": "sp_int", "Rio de Janeiro": "rj", "Minas Gerais": "mg", "Espírito Santo": "es", "Norte": "norte", "Centro Oeste": "co", "Sul": "sul", "Nordeste": "ne", "Total": "total"}
tris, lb100 = block("Terrenos", 4, REG)
_, lbcbr = block("Terrenos", 17, {"Total": "total"})
_, lbn = block("Terrenos", 30, {"Total": "total"}, scale=1)
_, lbp = block("Terrenos", 43, {"Total": "total"}, scale=1)
_, est_seg = block("Estoque", 17, SEG)
_, est_cbr = block("Estoque", 39, {"Total": "total"})
_, est_un = block("Estoque", 48, {"Total": "total"}, scale=1)
_, pr_seg = block("Estoque Pronto", 18, SEG)
_, pr_un = block("Estoque Pronto", 49, {"Total": "total"}, scale=1)
_, v_seg = block("Vendas", 30, SEG)
_, v_cbr = block("Vendas", 39, {"Total": "total"})
out = {"_meta": {"fonte": "Cyrela RI, planilha de dados operacionais (Terrenos, Estoque, Estoque Pronto, Vendas); R$ mi; estoque e vendas pro forma ex-Cury e Plano&Plano a partir de 2019 (aviso da própria planilha)"},
       "tris": tris,
       "landbank": {"vgv100_regiao": lb100, "vgv100_total": lb100["total"], "vgvcbr_total": lbcbr["total"], "n_terrenos": lbn["total"], "pct_permuta": lbp["total"]},
       "estoque": {"vgv100_seg": est_seg, "vgv100_total": est_seg["total"], "vgvcbr_total": est_cbr["total"], "un_total": est_un["total"]},
       "pronto": {"vgv100_seg": pr_seg, "vgv100_total": pr_seg["total"], "un_total": pr_un["total"]},
       "vendas": {"vgv100_seg": v_seg, "vgv100_total": v_seg["total"], "vgvcbr_total": v_cbr["total"]}}
json.dump(out, io.open(os.path.join(here, "_operacional_ri.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("tris", tris[0], tris[-1], len(tris))
for k in ("landbank", "estoque", "pronto", "vendas"):
    print(k, {kk: (vv["2T26"] if isinstance(vv, dict) and "2T26" in vv else "…") for kk, vv in out[k].items() if not kk.endswith("_seg") and not kk.endswith("_regiao")})
print("estoque seg 2T26", {k: v["2T26"] for k, v in est_seg.items()}); print("vendas seg 2T26", {k: v["2T26"] for k, v in v_seg.items()})
