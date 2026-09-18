# -*- coding: utf-8 -*-
"""Serie historica de governanca da Cyrela via CVM dados abertos (dataset FRE).

Baixa fre_cia_aberta_AAAA.zip (2010-2026), extrai apenas os CSVs de posicao acionaria,
distribuicao de capital e remuneracao total por orgao, filtra Cyrela
(CNPJ 73.178.600/0001-18) e grava _governanca_cvm.json. Zips vao para o scratchpad
e sao apagados apos o uso.
"""
import csv
import io
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

CNPJ = "73.178.600/0001-18"
BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/"
here = os.path.dirname(os.path.abspath(__file__))
tmp = tempfile.gettempdir()

alvos = ("posicao_acionaria", "distribuicao_capital", "remuneracao_total_orgao", "maxima")
out = {a: [] for a in alvos}
membros_vistos = set()

for ano in range(2010, 2027):
    zpath = os.path.join(tmp, f"fre_{ano}.zip")
    try:
        if not os.path.exists(zpath):
            urllib.request.urlretrieve(f"{BASE}fre_cia_aberta_{ano}.zip", zpath)
        z = zipfile.ZipFile(zpath)
    except Exception as e:
        print(f"{ano}: FALHOU ({e})")
        continue
    nomes = z.namelist()
    for alvo in alvos:
        m = [n for n in nomes if alvo in n.lower()]
        if not m:
            if ano == 2010:
                print(f"{ano}: sem CSV p/ {alvo}; membros: {[n for n in nomes][:8]}")
            continue
        for nome in m:
            membros_vistos.add(nome.split("_20")[0])
            with z.open(nome) as f:
                txt = io.TextIOWrapper(f, encoding="latin-1")
                rd = csv.DictReader(txt, delimiter=";")
                for row in rd:
                    cnpj = row.get("CNPJ_Companhia") or row.get("CNPJ_CIA") or ""
                    if cnpj.strip() == CNPJ:
                        row["_ano_fre"] = ano
                        row["_arquivo"] = nome
                        out[alvo].append(row)
    z.close()
    os.remove(zpath)
    print(f"{ano}: ok | acum: " + " ".join(f"{a}={len(out[a])}" for a in alvos))

io.open(os.path.join(here, "_governanca_cvm.json"), "w", encoding="utf-8").write(
    json.dumps(out, ensure_ascii=False))
print("gravado _governanca_cvm.json")
print("tipos de arquivo vistos:", sorted(membros_vistos))
