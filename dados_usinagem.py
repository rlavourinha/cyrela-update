# -*- coding: utf-8 -*-
"""Séries trimestrais para a decomposição da receita (lançamento × estoque × usinagem), 1T20-2T26:
- releases (fontes/release_nTaa.txt): "custos orçados e ainda não incorridos, referente a unidades em estoque" (R$ mi) e
  "referente a unidades vendidas";
- ITR (fontes/itr/nTaa.lay.txt), nota de obras em andamento: receita total de vendas, receita total apropriada,
  saldo de receita a apropriar (R$ mil -> R$ mi);
- _estoque_custo.json: imóveis a comercializar em construção (custo incorrido do estoque em obra, R$ mi).
PoC do estoque em construção = incorrido ÷ (incorrido + a incorrer). Saída: _usinagem.json {tri: {...}}."""
import io, json, os, re, glob
here = os.path.dirname(os.path.abspath(__file__))
def num(s):
    s = s.strip().replace("(", "-").replace(")", "").replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return None
def ord_(q): return (int(q[2:]), int(q[0]))
EC = json.load(io.open(os.path.join(here, "_estoque_custo.json"), encoding="utf-8"))
out = {}
for fp in sorted(glob.glob(os.path.join(here, "fontes", "release_?T2?.txt"))):
    q = os.path.basename(fp)[8:12]
    if ord_(q) < (20, 1): continue
    t = io.open(fp, encoding="utf-8", errors="ignore").read()
    d = out.setdefault(q, {})
    for key, lab in (("a_incorrer_estoque", "em estoque"), ("a_incorrer_vendidas", "vendidas")):
        # layout novo: número na linha seguinte ao rótulo; layout 2020-21: "(975)  (781)" na linha anterior ao rótulo
        m = re.search(r"Compromisso com custos or.ados e ainda n.o\s+\(([\d\.]+)\)\s+\(([\d\.]+)\)[^\n]*\n\s*incorridos, referente a unidades " + lab, t)
        if m: d[key] = num(m.group(1)); continue
        m = re.search(r"referente a unidades " + lab + r"\s*\n?\s*\(?([\d\.]+)\)?", t)
        if m: d[key] = num(m.group(1))
    m = re.search(r"Receitas? L[ií]quidas? a Apropriar \(R\$ milh[õo]es\)\s+([\d\.]+)", t)
    if m: d["ref_release"] = num(m.group(1))
    m = re.search(r"Margem a Apropriar\s+([\d]+,[\d])%", t)
    if m: d["margem_ref"] = num(m.group(1))
for fp in sorted(glob.glob(os.path.join(here, "fontes", "itr", "?T2?.lay.txt"))):
    q = os.path.basename(fp)[:4]
    if ord_(q) < (20, 1): continue
    t = io.open(fp, encoding="utf-8", errors="ignore").read()
    d = out.setdefault(q, {})
    m = re.search(r"\(\+\)\s*Receita total de vendas\s+([\d\.]+)", t)
    if m: d["rec_total_vendas"] = num(m.group(1)) / 1000
    m = re.search(r"\(-\)\s*Receita total apropriada\s+\(?([\d\.]+)\)?", t)
    if m: d["rec_total_apropriada"] = num(m.group(1)) / 1000
    # cronograma do custo a incorrer das unidades vendidas: no texto, a linha "Valores não refletidos" traz o valor de 12 meses
    # e a linha "12 meses" traz o de acima de 12 meses (rótulos deslocados pelo layout); soma = custo a apropriar
    m = re.search(r"Valores n[ãa]o refletidos nas informa[çc][õo]es financeiras\s+([\d\.]+)\s+[\d\.]+\s*\n\s*12 meses\s+([\d\.]+)", t)
    if m: d["custo_incorrer_12m"] = num(m.group(1)) / 1000; d["custo_incorrer_alem_12m"] = num(m.group(2)) / 1000
    # o saldo a apropriar do ITR sai mal alinhado no texto (2020-22); usar vendas − apropriada
    if d.get("rec_total_vendas") and d.get("rec_total_apropriada"): d["ref_itr"] = round(d["rec_total_vendas"] - d["rec_total_apropriada"], 3)
for q, d in out.items():
    ec = EC.get(q, {})
    if ec.get("construcao"): d["estoque_custo_construcao"] = ec["construcao"]
    if d.get("estoque_custo_construcao") and d.get("a_incorrer_estoque"):
        d["poc_estoque_construcao"] = round(d["estoque_custo_construcao"] / (d["estoque_custo_construcao"] + d["a_incorrer_estoque"]), 4)
    if d.get("rec_total_vendas") and d.get("rec_total_apropriada"):
        d["poc_base_vendida"] = round(d["rec_total_apropriada"] / d["rec_total_vendas"], 4)
out = {q: out[q] for q in sorted(out, key=ord_)}
out["_meta"] = {"fonte": "releases (custos orçados a incorrer de unidades em estoque e vendidas, R$ mi), ITR nota de obras em andamento (receita total de vendas/apropriada/a apropriar, R$ mi), _estoque_custo.json (imóveis a comercializar em construção, R$ mi)",
                "poc_estoque_construcao": "custo incorrido do estoque em construção ÷ (incorrido + a incorrer das unidades em estoque)",
                "poc_base_vendida": "receita total apropriada ÷ receita total de vendas das obras em andamento (nota do ITR)"}
json.dump(out, io.open(os.path.join(here, "_usinagem.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for q, d in out.items():
    if q != "_meta": print(q, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()})
