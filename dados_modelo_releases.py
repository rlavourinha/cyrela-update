# -*- coding: utf-8 -*-
"""Extrai dos releases (1T23-2T26) os itens que faltam no CYREMod_2T26:
juros apropriados no custo (r11), REF liquida/custo (r257/258), contas a receber
em construcao/construidas (r247/248) e custos orcados vendidas/estoque (r234/235).
Valor = primeiro numero apos o rotulo (trimestre corrente). Saida: _modelo_releases.json."""
import glob
import io
import json
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
NUM = re.compile(r"\(?\s*(\d{1,3}(?:\.\d{3})*(?:,\d+)?)\s*\)?")


def num_apos(texto, rotulo, janela=250):
    i = texto.find(rotulo)
    if i < 0:
        return None
    trecho = texto[i + len(rotulo):i + len(rotulo) + janela]
    m = NUM.search(trecho)
    if not m:
        return None
    v = float(m.group(1).replace(".", "").replace(",", "."))
    ate = trecho[:m.start()]
    if "(" in m.group(0) or "(" in ate[-3:]:
        v = -v
    return v


CAMPOS = {
    "juros": ["Juros Apropriados no Custo"],
    "ref_liq": ["Receita Líquida a Apropriar", "Receita Liquida a Apropriar"],
    "ref_custo": ["Custo Orçado das Unidades Vendidas a Apropriar",
                  "Custo Orçado das Unidades Vendidas a  Apropriar"],
    "car_constr": ["Unidades em construção", "Unidades em construcão"],
    "car_prontas": ["Unidades construídas", "Unidades construidas"],
    "custo_vendidas": ["referente a unidades vendidas", "referentes a unidades vendidas"],
    "custo_estoque": ["referente a unidades em estoque", "referentes a unidades em estoque"],
}

out = {}
for f in sorted(glob.glob(os.path.join(here, "fontes", "release_*.txt"))):
    tri = os.path.basename(f)[8:12]
    s = io.open(f, encoding="utf-8", errors="ignore").read()
    d = {}
    for k, rots in CAMPOS.items():
        v = None
        for r in rots:
            v = num_apos(s, r)
            if v is not None:
                break
        d[k] = v
    out[tri] = d

io.open(os.path.join(here, "_modelo_releases.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False, indent=1))
for tri, d in out.items():
    faltas = [k for k, v in d.items() if v is None]
    print(tri, {k: v for k, v in d.items() if v is not None}, "| FALTAM:", faltas or "-")
