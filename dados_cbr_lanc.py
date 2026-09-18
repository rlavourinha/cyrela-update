# -*- coding: utf-8 -*-
"""%CBR dos lancamentos por segmento, 2005-2026, da planilha do RI
(fontes/planilha_lancamentos.xlsx: projeto a projeto, VGV 100% com permuta, segmento,
%CBR, contabilizacao). %CBR ponderado por VGV. Saida: _cbr_lanc.json"""
import io, json, os, openpyxl, collections
here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_lancamentos.xlsx"), read_only=True, data_only=True)
ws = wb.worksheets[0]; rows = list(ws.iter_rows(min_row=4, values_only=True))
L = []
for r in rows:
    if not r or len(r) < 11 or not isinstance(r[6], (int, float)) or not isinstance(r[4], str): continue
    L.append({"nome": r[2], "tri": r[4].strip(), "ano": r[4].strip()[-2:], "vgv": float(r[6]), "un": r[7], "seg": (r[8] or "").strip(), "cbr": r[9], "cont": r[10]})
print("projetos:", len(L), "| segmentos:", collections.Counter(x["seg"] for x in L).most_common())
def grupo(seg):
    s = seg.lower()
    if "mcmv" in s or "cva" in s or "econ" in s or "faixa" in s: return "MCMV"  # CVA = Casa Verde e Amarela (2021-22); Vivaz Prime fica no MAP (perímetro Living + Vivaz Prime)
    if s in ("", "lote", "loteamento", "comercial", "corporativo", "salas comerciais", "hotel"): return "outro"
    return "MAP"
for x in L: x["g"] = grupo(x["seg"])
def agg(sel):
    v = sum(x["vgv"] for x in sel); c = sum(x["vgv"] * x["cbr"] for x in sel if isinstance(x["cbr"], (int, float)))
    vc = sum(x["vgv"] for x in sel if isinstance(x["cbr"], (int, float)))
    return {"vgv": round(v, 1), "cbr": round(c / vc * 100, 1) if vc else None, "n": len(sel),
            "vgv_cbr": round(c, 1), "consol": round(sum(x["vgv"] for x in sel if str(x["cont"]).lower().startswith("consol")) / v * 100, 1) if v else None}
anos = sorted(set(f"20{x['ano']}" for x in L))
out = {"anual": {}, "trimestral": {}}
for a in anos:
    s = [x for x in L if f"20{x['ano']}" == a]
    out["anual"][a] = {g: agg([x for x in s if x["g"] == g]) for g in ("MCMV", "MAP")} | {"total": agg(s)}
tris = sorted(set(x["tri"] for x in L), key=lambda t: (int(t[2:]), int(t[0])))
for t in tris:
    s = [x for x in L if x["tri"] == t]
    out["trimestral"][t] = {g: agg([x for x in s if x["g"] == g]) for g in ("MCMV", "MAP")} | {"total": agg(s)}
out["_meta"] = {"fonte": "RI Cyrela, planilha_lancamentos.xlsx (Lista Empreendimentos, 1T05-2T26), VGV 100% com permuta", "grupo_MCMV": "segmentos com MCMV/Vivaz/econômico no nome", "nota": "%CBR ponderado por VGV; consol = % do VGV contabilizado por consolidação"}
json.dump(out, io.open(os.path.join(here, "_cbr_lanc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ano | MCMV vgv / %CBR / n / %consol | MAP vgv / %CBR | total %CBR")
for a in anos:
    d = out["anual"][a]; m, p, t = d["MCMV"], d["MAP"], d["total"]
    print(f"{a} | {m['vgv']:7.0f} {m['cbr']} n={m['n']:2d} consol={m['consol']} | {p['vgv']:7.0f} {p['cbr']} | {t['cbr']}")
