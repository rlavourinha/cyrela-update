# -*- coding: utf-8 -*-
"""Extrai a aba 'Resultados Operacionais' da planilha Fundamentos do RI da Cury (fontes/verificacao/cury_planilha_fundamentos.xlsx)
para _cury_hist.json, alinhando cada valor ao cabeçalho da própria coluna (anos 2017-2025 e trimestres 1T17-2T26).
Motivo (23/09/26): a extração anterior estava deslocada um trimestre para a frente (o valor de 1T26 aparecia como 2T26; o 2T26
real, 6.549 unidades lançadas na prévia operacional, não existia). Chave = 'SEÇÃO · rótulo'; seção = última linha sem dados.
Confere com a prévia operacional 2T26 (6.549 un., 1T26 8.001, 2T25 6.588) antes de gravar."""
import io, json, os
import openpyxl
here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "verificacao", "cury_planilha_fundamentos.xlsx"), read_only=True, data_only=True)
ws = next(w for w in wb.worksheets if w.title.strip() == "Resultados Operacionais")
rows = list(ws.iter_rows(values_only=True))
hdr = None; out = {}; sec = None
for r in rows:
    lab = r[1]
    if lab is None: continue
    lab = str(lab).strip()
    data = list(r[4:])
    if all(v is None for v in data): sec = lab; continue   # linha de seção (LANÇAMENTOS, VENDAS E DISTRATOS, ...), antes do cabeçalho inclusive
    if hdr is None and any(str(v) == "2017" for v in data) and any("T" in str(v) for v in data if v is not None):
        hdr = [str(v).strip() if v is not None else None for v in data]   # linha de cabeçalho (anos + trimestres)
    if hdr is None: continue
    d = {}
    for h, v in zip(hdr, data):
        if h is None or v is None or (isinstance(v, str) and not v.strip()): continue
        if isinstance(v, str):
            try: v = float(v.replace(".", "").replace(",", "."))
            except ValueError: continue
        d[h] = v
    if d: out[f"{sec} · {lab}"] = d
out["_meta"] = {"fonte": "Cury RI, Planilha Fundamentos (ri.cury.net/informacoes-aos-investidores/planilha-interativa, baixada 19/09/2026), aba Resultados Operacionais; valores alinhados ao cabeçalho de cada coluna (dados_cury_hist.py, 23/09/26)",
                "colunas": [h for h in hdr if h]}
un = out["LANÇAMENTOS · Número de unidades"]
assert (un["2T26"], un["1T26"], un["2T25"]) == (6549, 8001, 6588), un   # prévia operacional 2T26
assert sum(un[q] for q in ("1T25", "2T25", "3T25", "4T25")) == un["2025"], un
p = os.path.join(here, "_cury_hist.json")
old = json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}
json.dump(out, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(out) - 1} séries; colunas {hdr[0]}..{[h for h in hdr if h][-1]}")
if old:
    ORD = lambda q: (int(q[2:]), int(q[0]))
    qs = sorted([q for q in un if "T" in q], key=ORD); nxt = {q: qs[i + 1] for i, q in enumerate(qs[:-1])}
    miss = [k for k in old if k != "_meta" and k not in out]; new = [k for k in out if k != "_meta" and k not in old]
    print("chaves só no antigo:", miss); print("chaves só no novo:", new)
    shift = same = diff = 0
    for k, d in out.items():
        if k == "_meta" or k not in old: continue
        for q, v in d.items():
            if "T" not in q or q not in nxt: continue
            o = old[k].get(nxt[q])
            if o is None: continue
            if abs(o - v) < 1e-6: shift += 1
            elif abs((old[k].get(q) or 0) - v) < 1e-6: same += 1
            else: diff += 1
    print(f"trimestres: {shift} valores iguais ao antigo deslocado (+1T), {same} iguais sem deslocamento, {diff} diferentes")
