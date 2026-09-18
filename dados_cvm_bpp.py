# -*- coding: utf-8 -*-
"""Extrai do BPP estruturado da CVM (ITR tri + DFP 4T, 2020-2026) as linhas que a
planilha do RI agrega: terrenos a pagar (CP/LP), adiantamentos de clientes (CP/LP)
e dividendos a pagar (CP). Match por descricao (codigos mudam entre anos).
Saida: _cvm_bpp.json {tri: {t_cp,t_lp,a_cp,a_lp,div}} em R$ mi."""
import csv
import glob
import io
import json
import os
import re
import zipfile

here = os.path.dirname(os.path.abspath(__file__))
pasta = os.path.join(here, "fontes", "cvm_itr")
RE_TER = re.compile(r"Aquisi[çc][ãa]o de Im[óo]veis|Credores por Im", re.I)
RE_ADI = re.compile(r"Adiantamentos? [ap][e]? ?Clientes|Adiantamentos? de Clientes", re.I)
RE_DIV = re.compile(r"Dividendo", re.I)

out = {}
for z in sorted(glob.glob(os.path.join(pasta, "*.zip"))):
    tipo = "itr" if "itr" in os.path.basename(z) else "dfp"
    ano = os.path.basename(z)[4:8]
    with zipfile.ZipFile(z) as zf:
        nome = f"{tipo}_cia_aberta_BPP_con_{ano}.csv"
        if nome not in zf.namelist():
            print("SEM", nome)
            continue
        with zf.open(nome) as fh:
            for r in csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";"):
                if "CYRELA BRAZIL" not in r["DENOM_CIA"] or r["ORDEM_EXERC"] != "ÚLTIMO":
                    continue
                dt = r["DT_REFER"]
                if tipo == "dfp" and not dt.endswith("12-31"):
                    continue
                a, m = int(dt[:4]), int(dt[5:7])
                tri = f"{(m - 1) // 3 + 1}T{a % 100:02d}"
                cd, ds = r["CD_CONTA"], r["DS_CONTA"]
                v = float(r["VL_CONTA"]) / 1000
                d = out.setdefault(tri, {"t_cp": 0, "t_lp": 0, "a_cp": 0, "a_lp": 0, "div": 0})
                lado = "cp" if cd.startswith("2.01") else "lp"
                if cd.count(".") >= 3:   # so folhas/subcontas, evita duplicar com pais
                    if RE_TER.search(ds):
                        d[f"t_{lado}"] += v
                    elif RE_ADI.search(ds):
                        d[f"a_{lado}"] += v
                    elif RE_DIV.search(ds) and lado == "cp":
                        d["div"] += v

out = {k: {kk: round(vv, 1) for kk, vv in v.items()} for k, v in sorted(out.items())}
io.open(os.path.join(here, "_cvm_bpp.json"), "w", encoding="utf-8").write(json.dumps(out))
for tri, d in out.items():
    print(tri, d)
print("n tris:", len(out))
