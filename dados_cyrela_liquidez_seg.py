# -*- coding: utf-8 -*-
"""Liquidez da PROPRIA Cyrela por segmento (planilha de dados operacionais do RI).

Estoque a valor de mercado %CBR por segmento (aba Estoque) x vendas VGV %CBR (com
permuta) por segmento (aba Vendas) — as linhas com permuta cobrem 1T06-2T26 (20 anos);
as ex-permuta so existem desde 1T23, por isso nao sao usadas. Segmentos: Alto, Medio, MCMV
(Vivaz Prime + MCMV 2 e 3 + MCMV 1). Metricas: meses de estoque = estoque /
(vendas 4T moveis / 12); VSO 12m = vendas 4T / (vendas 4T + estoque).
Saida: _cyrela_liquidez_seg.json {tri, seg:{alto,medio,mcmv}:{mest, vso}}.
"""
import io
import json
import os

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_dados_operacionais.xlsx"),
                            read_only=True)


def bloco(aba, linhas):
    ws = wb[aba]
    grid = list(ws.iter_rows(min_row=1, max_row=170, values_only=True))
    hdr = next(r for r in grid[:6] if any(isinstance(c, str) and len(str(c)) == 4 and str(c)[1] == "T"
                                          for c in r if c))
    qcols = [j for j, c in enumerate(hdr) if isinstance(c, str) and len(c) == 4 and c[1] == "T"]
    tris = [hdr[j] for j in qcols]
    out = {}
    for nome, i in linhas.items():
        out[nome] = [grid[i - 1][j] if isinstance(grid[i - 1][j], (int, float)) else None for j in qcols]
    return tris, out


tris_e, est = bloco("Estoque", {"alto": 40, "medio": 41, "vp": 42, "m23": 43, "m1": 44})
tris_v, ven = bloco("Vendas", {"alto": 40, "medio": 41, "vp": 42, "m23": 43, "m1": 44})
assert tris_e == tris_v, (tris_e[:3], tris_v[:3])
wb.close()


def soma(*series):
    return [sum(x or 0 for x in vals) for vals in zip(*series)]


seg_est = {"alto": est["alto"], "medio": est["medio"], "mcmv": soma(est["vp"], est["m23"], est["m1"])}
seg_ven = {"alto": ven["alto"], "medio": ven["medio"], "mcmv": soma(ven["vp"], ven["m23"], ven["m1"])}

out = {"tri": tris_e[3:], "seg": {}}
for sgm in ("alto", "medio", "mcmv"):
    mest, vso = [], []
    for i in range(3, len(tris_e)):
        v4 = seg_ven[sgm][i - 3:i + 1]
        e = seg_est[sgm][i]
        if e and all(v is not None for v in v4) and sum(v4) > 0:
            v12 = sum(v4)
            mest.append(round(e / (v12 / 12), 1))
            vso.append(round(100 * v12 / (v12 + e), 1))
        else:
            mest.append(None)
            vso.append(None)
    out["seg"][sgm] = {"mest": mest, "vso": vso}
    ok = [(out["tri"][k], mest[k], vso[k]) for k in range(len(mest)) if mest[k]]
    print(f"{sgm:5s}: {len(ok)} tri | {ok[0][0]}: {ok[0][1]}m/{ok[0][2]}% ... {ok[-1][0]}: {ok[-1][1]}m/{ok[-1][2]}%")
    for t, m, v in ok[-6:]:
        print(f"   {t}: {m} meses | VSO12m {v}%")

io.open(os.path.join(here, "_cyrela_liquidez_seg.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))
