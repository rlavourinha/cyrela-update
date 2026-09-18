# -*- coding: utf-8 -*-
"""Microdados do ITBI da Prefeitura de SP (fontes/mercado/itbi/itbi_AAAA.xlsx, uma aba por mês de pagamento,
2019-2026): fração das compras pagas com crédito, por faixa de preço e por ano.
Filtros: natureza '1.Compra e venda', proporção transmitida 100%, uso residencial (IPTU 10 = residência
horizontal, 20 = apartamento), valor de transação > R$ 50 mil. 'Novo' = SQL 'Ativo Territorial' (prédio ainda
não individualizado no cadastro: unidade em obra/entrega = repasse do mercado primário); 'demais' = SQL predial.
Saída: _itbi_sp.json {ano: {faixa: {n, n_fin, val, val_fin, ltv_med (financiado ÷ valor, só financiados),
tipo: {SFH:n, ...}}}, 'novo'/'predial' idem}."""
import io, json, os, glob, collections, datetime
import openpyxl
here = os.path.dirname(os.path.abspath(__file__))
FAIXAS = [(0, 350e3, "até 350 mil"), (350e3, 700e3, "350-700 mil"), (700e3, 1.5e6, "700 mil-1,5 mi"), (1.5e6, 3e6, "1,5-3 mi"), (3e6, 6e6, "3-6 mi"), (6e6, 1e12, "acima de 6 mi")]
def faixa(v):
    for a, b, n in FAIXAS:
        if a <= v < b: return n
def f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
def novo():
    return {"n": 0, "n_fin": 0, "val": 0.0, "val_fin": 0.0, "ltv_sum": 0.0, "tipo": collections.Counter()}
AGG = collections.defaultdict(lambda: collections.defaultdict(novo))   # (ano, grupo) -> faixa -> agg
tot = collections.Counter()
for fp in sorted(glob.glob(os.path.join(here, "fontes", "mercado", "itbi", "itbi_*.xlsx"))):
    wb = openpyxl.load_workbook(fp, read_only=True)
    for ws in wb.worksheets:
        if not ws.title[:3].isupper() or "-" not in ws.title: continue
        for r in ws.iter_rows(min_row=1, values_only=True):
            if not r or r[0] is None or str(r[0]).startswith("N°"): continue
            nat = str(r[7] or "");
            if not nat.startswith("1."): continue
            prop = f(r[11]); val = f(r[8]); fin = f(r[15]) or 0.0; uso = f(r[23]); dt = r[9]
            if prop is None or abs(prop - 100) > 0.01 or not val or val < 50e3: continue
            if uso not in (10.0, 20.0): continue
            ano = dt.year if isinstance(dt, datetime.datetime) else int(ws.title[-4:])
            if ano < 2018: continue
            situ = str(r[18] or ""); grupo = "novo" if situ.startswith("Ativo Territorial") else "predial"
            tipo = str(r[14] or "").strip()
            fx = faixa(val)
            for g in (grupo, "todos"):
                a = AGG[(ano, g)][fx]; a["n"] += 1; a["val"] += val
                if fin > 0:
                    a["n_fin"] += 1; a["val_fin"] += min(fin, val); a["ltv_sum"] += min(fin, val) / val
                    a["tipo"][tipo[:2] if tipo else "s/ tipo"] += 1
            tot[ano] += 1
    print(os.path.basename(fp), dict(tot), flush=True)
out = {}
for (ano, g), d in AGG.items():
    for fx, a in d.items():
        out.setdefault(str(ano), {}).setdefault(g, {})[fx] = {"n": a["n"], "n_fin": a["n_fin"], "pct_fin": round(100 * a["n_fin"] / a["n"], 1) if a["n"] else None,
            "val_bi": round(a["val"] / 1e9, 3), "val_fin_bi": round(a["val_fin"] / 1e9, 3), "pct_val_fin": round(100 * a["val_fin"] / a["val"], 1) if a["val"] else None,
            "ltv_med_fin": round(100 * a["ltv_sum"] / a["n_fin"], 1) if a["n_fin"] else None, "tipo": dict(a["tipo"])}
out["_meta"] = {"fonte": "Prefeitura de SP, Secretaria da Fazenda, Guias de ITBI pagas (dados abertos, p=31501), arquivos anuais 2019-2026 (2026 até jul)",
                "filtros": "compra e venda, proporção 100%, uso IPTU 10/20 (residencial), valor > 50 mil; ano = data da transação", "faixas": [n for _, _, n in FAIXAS],
                "novo": "SQL 'Ativo Territorial' = prédio ainda não individualizado (mercado primário, repasse na entrega)"}
json.dump(out, io.open(os.path.join(here, "_itbi_sp.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fim", flush=True)
