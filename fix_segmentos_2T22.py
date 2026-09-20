# -*- coding: utf-8 -*-
"""Correção pontual de _segmentos_full.json e recálculo de _roe_seg_serie.json (20/09/26).
O parser (dados_segmentos_full.py) copiou o balanço do alto padrão para a Vivaz no 2T22 (a tabela da nota sai embaralhada no texto
do ITR). Leitura manual da nota (ITR 2T22, "Demonstrações consolidadas dos segmentos operacionais", 06/2022): CVA ativo 1.218.258,
passivo 471.210, PL 747.048; Demais ativo 72.346, passivo 232.070, PL (159.724). Depois recalcula a série de retorno operacional
sobre o capital: lucro operacional LTM (fluxos acumulados no ano, diferenciados por trimestre) ÷ PL médio de 5 pontas.
Rode depois de dados_segmentos_full.py."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
S = json.load(io.open(os.path.join(here, "_segmentos_full.json"), encoding="utf-8")); R = json.load(io.open(os.path.join(here, "_roe_seg_serie.json"), encoding="utf-8"))
S["2T22"]["mcmv"].update({"ativo": 1218.3, "passivo": 471.2, "pl": 747.0}); S["2T22"]["demais"].update({"ativo": 72.3, "passivo": 232.1, "pl": -159.7})
json.dump(S, io.open(os.path.join(here, "_segmentos_full.json"), "w", encoding="utf-8"))
ordq = lambda q: (int(q[2:]), int(q[0])); qs = sorted(S, key=ordq)
def flow(k, q):
    t = int(q[0]); return S[q][k]["lop"] if t == 1 else S[q][k]["lop"] - S[f"{t - 1}T{q[2:]}"][k]["lop"]
def ret(k, q):
    i = qs.index(q)
    if i < 4: return None
    lop = sum(flow(k, x) for x in qs[i - 3:i + 1]); pl = sum(S[x][k]["pl"] for x in qs[i - 4:i + 1]) / 5
    return round(100 * lop / pl, 1) if pl else None
for k in ("cyrela", "living", "mcmv"):
    for q in qs:
        v = ret(k, q)
        if v is not None and q in R[k]: R[k][q] = v
json.dump(R, io.open(os.path.join(here, "_roe_seg_serie.json"), "w", encoding="utf-8"))
print("ok", {k: R[k][qs[-1]] for k in ("cyrela", "living", "mcmv")})
