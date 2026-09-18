# -*- coding: utf-8 -*-
"""VSO trimestral por segmento, formula do Rafael: vendas(t) / (lancamentos(t) +
estoque(t-1)). Fonte: planilha de dados operacionais do RI (abas Lctos, Vendas,
Estoque; VGV 100% linhas 31-35, %CBR linhas 40-44; MCMV = Vivaz Prime + MCMV 2e3
+ MCMV 1). Saida: _vso_seg.json {tri, base:{seg:[...]}} nas duas bases."""
import io
import json
import os

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_dados_operacionais.xlsx"),
                            read_only=True)
# layout difere por aba: na Estoque o bloco 100% por segmento e r18-22
LIN = {"100": {"Lçtos": 31, "Vendas": 31, "Estoque": 18},
       "cbr": {"Lçtos": 40, "Vendas": 40, "Estoque": 40}}
SEGS = ("alto", "medio", "vp", "m23", "m1")


def bloco(aba, linhas):
    ws = wb[aba]
    grid = list(ws.iter_rows(min_row=1, max_row=95, values_only=True))
    hdr = next(r for r in grid[:6] if any(isinstance(c, str) and len(str(c)) == 4 and str(c)[1] == "T"
                                          for c in r if c))
    qcols = [j for j, c in enumerate(hdr) if isinstance(c, str) and len(c) == 4 and c[1] == "T"]
    tris = [hdr[j] for j in qcols]
    return tris, {n: [grid[i - 1][j] if isinstance(grid[i - 1][j], (int, float)) else None for j in qcols]
                  for n, i in linhas.items()}


def soma(*ss):
    return [sum(x or 0 for x in v) for v in zip(*ss)]


out = {}
for base, base0 in LIN.items():
    mk = lambda aba: {n: base0[aba] + k for k, n in enumerate(SEGS)}
    t1, lanc = bloco("Lçtos", mk("Lçtos"))
    t2, ven = bloco("Vendas", mk("Vendas"))
    t3, est = bloco("Estoque", mk("Estoque"))
    assert t1 == t2 == t3
    L = {"alto": lanc["alto"], "medio": lanc["medio"], "mcmv": soma(lanc["vp"], lanc["m23"], lanc["m1"])}
    V = {"alto": ven["alto"], "medio": ven["medio"], "mcmv": soma(ven["vp"], ven["m23"], ven["m1"])}
    E = {"alto": est["alto"], "medio": est["medio"], "mcmv": soma(est["vp"], est["m23"], est["m1"])}
    res = {}
    for sgm in ("alto", "medio", "mcmv"):
        serie = [None]
        for i in range(1, len(t1)):
            v, l, e0 = V[sgm][i], L[sgm][i], E[sgm][i - 1]
            if v is None or e0 is None:   # sem estoque inicial reportado nao ha oferta
                serie.append(None); continue
            of = (l or 0) + e0
            serie.append(round(100 * v / of, 1) if of > 0 else None)
        res[sgm] = serie
    out[base] = res
# pre-2013 a segmentacao retrofitada nao fecha (VSO>100%): corta em 1T13
i0 = t1.index("1T13")
for b in out:
    for sg in out[b]:
        out[b][sg] = out[b][sg][i0:]
out["tri"] = t1[i0:]
wb.close()
io.open(os.path.join(here, "_vso_seg.json"), "w", encoding="utf-8").write(json.dumps(out))

tri = out["tri"]
print("VSO trimestral = vendas / (lançamentos + estoque inicial)")
print(f"{'tri':>5} | {'— 100% —':^24} | {'— %CBR —':^24}")
print(f"{'':>5} | {'Alto':>7}{'Médio':>8}{'MCMV':>8} | {'Alto':>7}{'Médio':>8}{'MCMV':>8}")
for i in range(len(tri) - 12, len(tri)):
    f = lambda b, s: (f"{out[b][s][i]:.0f}%" if out[b][s][i] is not None else "—")
    print(f"{tri[i]:>5} | {f('100','alto'):>7}{f('100','medio'):>8}{f('100','mcmv'):>8} | "
          f"{f('cbr','alto'):>7}{f('cbr','medio'):>8}{f('cbr','mcmv'):>8}")
print()
for b in ("100", "cbr"):
    for s in ("alto", "medio", "mcmv"):
        v = [x for x in out[b][s] if x is not None]
        print(f"{b:>4} {s:5s}: n={len(v)} | média {sum(v)/len(v):5.1f}% | min {min(v):4.1f} | max {max(v):5.1f}")
