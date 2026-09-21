# -*- coding: utf-8 -*-
"""Releases de resultados de Lavvi e Plano & Plano via CVM (dados abertos IPE: ipe_cia_aberta_AAAA.zip → csv com link de download).
Filtra documentos de 'Comunicado ao Mercado'/'Dados Econômico-Financeiros'/'Press-release' cujo assunto cite resultado/release e baixa os
PDFs de 3T25 a 2T26 para fontes/verificacao/. Depois extrai (pypdf) linhas com 'não recorrente', 'ROE', 'lucro líquido' para o ROE ajustado.
Saída: _ipe_lavvi_pp.json {empresa: [{data, tipo, assunto, arquivo}]}"""
import io, os, re, csv, json, zipfile, requests
from pypdf import PdfReader
here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "fontes", "cvm"); V = os.path.join(here, "fontes", "verificacao"); os.makedirs(D, exist_ok=True)
H = {"User-Agent": "Mozilla/5.0"}
EMP = {"lavvi": r"LAVVI", "pp": r"PLANO\s*&\s*PLANO|PLANO E PLANO"}
out = {k: [] for k in EMP}
for ano in (2025, 2026):
    p = os.path.join(D, f"ipe_cia_aberta_{ano}.zip")
    if not os.path.exists(p) or os.path.getsize(p) < 1e5:
        r = requests.get(f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{ano}.zip", headers=H, timeout=600); open(p, "wb").write(r.content)
    z = zipfile.ZipFile(p); name = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(name) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            emp = next((k for k, rx in EMP.items() if re.search(rx, r["Nome_Companhia"], re.I)), None)
            if not emp: continue
            ass = (r.get("Assunto") or ""); cat = r.get("Categoria") or ""; tipo = r.get("Tipo") or ""
            if re.search(r"release|resultado|desempenho|earnings", ass + " " + tipo + " " + cat, re.I) and not re.search(r"ata|aviso|calend|convoca|fato relevante", ass, re.I):
                out[emp].append({"data": r.get("Data_Entrega"), "ref": r.get("Data_Referencia"), "cat": cat, "tipo": tipo, "assunto": ass[:120], "link": r.get("Link_Download")})
for emp in out:
    out[emp].sort(key=lambda x: x["data"] or ""); print("==", emp, len(out[emp]))
    for d in out[emp]: print("  ", d["data"], "|", d["cat"][:28], "|", d["tipo"][:28], "|", d["assunto"][:90])
json.dump(out, io.open(os.path.join(here, "_ipe_lavvi_pp.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# baixa os que parecem release de resultado trimestral (últimos 4 por empresa) e extrai linhas-chave
for emp in out:
    docs = [d for d in out[emp] if re.search(r"release|resultado|desempenho", d["assunto"] + d["tipo"], re.I)][-5:]
    for d in docs:
        fn = os.path.join(V, f"{emp}_ipe_{d['data'][:10]}.pdf")
        if not os.path.exists(fn):
            try:
                r = requests.get(d["link"], headers=H, timeout=300); open(fn, "wb").write(r.content)
            except Exception as e: print("ERR", d["link"], e); continue
        try: rd = PdfReader(fn)
        except Exception as e: print("PDF ERR", fn, e); continue
        print("####", emp, d["data"], d["assunto"][:80], "|", len(rd.pages), "pags")
        for i, pg in enumerate(rd.pages[:40]):
            t = pg.extract_text() or ""
            for l in t.splitlines():
                if re.search(r"n[ãa]o recorrente|ROE|retorno sobre|lucro l[íi]quido (ajustado|de R\$|foi|atingiu|totalizou)|extraordin", l, re.I): print(f"  p{i+1}: {l.strip()[:200]}")
print("fim")
