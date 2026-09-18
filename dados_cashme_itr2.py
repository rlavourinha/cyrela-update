# -*- coding: utf-8 -*-
"""Passo 2 da serie CashMe: nos PDFs dos ITR/DFP (scratchpad/itrdocs/<tri>_0.pdf, baixados por
dados_cashme_itr.py; os que faltam sao rebaixados aqui), localiza as paginas com 'Cashme Solu'
via pdftotext (rapido, separador \\f por pagina) e reconstroi as LINHAS pela posicao dos glifos
(page_rows de dados_divida.py) so nessas paginas. O -layout do pdftotext sangra colunas de
linhas vizinhas; a reconstrucao por glifo nao. Guarda, por documento, cada linha 'Cashme' com
as 8 linhas anteriores (cabecalho da tabela) em _cashme_itr_rows.json. Copia os PDFs para
fontes/itr/ para nao depender do scratchpad."""
import base64, csv, io, json, os, re, shutil, subprocess, sys, urllib.request, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdfplumber
from dados_divida import page_rows
here = os.path.dirname(os.path.abspath(__file__))
tmp = sys.argv[1]
docs = os.path.join(tmp, "itrdocs"); os.makedirs(docs, exist_ok=True)
keep = os.path.join(here, "fontes", "itr"); os.makedirs(keep, exist_ok=True)
BASE_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
ALVO = {}
for a in range(2020, 2027):
    for t, mes in ((1, "03-31"), (2, "06-30"), (3, "09-30"), (4, "12-31")): ALVO[f"{t}T{a%100:02d}"] = f"{a}-{mes}"
cand = {k: [] for k in ALVO}
for ano in range(2020, 2027):
    for tipo in ("itr", "dfp"):
        cam = os.path.join(tmp, f"{tipo}_cia_aberta_{ano}.zip")
        if not os.path.exists(cam): continue
        with zipfile.ZipFile(cam) as zf:
            nome = f"{tipo}_cia_aberta_{ano}.csv"
            if nome not in zf.namelist(): continue
            with zf.open(nome) as fh: linhas = list(csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";"))
        for r in linhas:
            if "CYRELA BRAZIL" not in r.get("DENOM_CIA", ""): continue
            for tri, alvo in ALVO.items():
                if r.get("DT_REFER", "")[:10] == alvo: cand[tri].append((int(r.get("VERSAO", 1)), r["LINK_DOC"]))
for tri in cand: cand[tri] = [u for _, u in sorted(cand[tri], key=lambda x: -x[0])]
def baixa_pdf(tri, url, pdf):
    zpath = pdf + ".zip"
    for tent in range(3):
        try:
            subprocess.run(["curl", "-sL", "--retry", "2", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "-o", zpath, url.replace("http://", "https://")], check=True, capture_output=True, timeout=900)
            partes = []
            with zipfile.ZipFile(zpath) as zf:
                xmls = sorted((n for n in zf.namelist() if n.lower().endswith(".xml")), key=lambda n: -zf.getinfo(n).file_size)
                bruto = zf.read(xmls[0]).decode("utf-8", "ignore") if xmls else ""
                for b in re.findall(r">([A-Za-z0-9+/=]{5000,})<", bruto):
                    try: d = base64.b64decode(b)
                    except Exception: continue
                    if d.startswith(b"%PDF"): partes.append(d)
                if not partes: partes = [zf.read(n) for n in zf.namelist() if n.lower().endswith(".pdf")]
            os.remove(zpath)
            if partes:
                partes.sort(key=len, reverse=True); io.open(pdf, "wb").write(partes[0]); return True
        except Exception as e:
            print(f"  {tri} tentativa {tent}: {str(e)[:70]}", flush=True)
            if os.path.exists(zpath): os.remove(zpath)
    return False
ORD = lambda q: (int(q[2:]), int(q[0]))
RE = re.compile(r"cash\s?me\s+solu", re.I)
out = json.load(io.open(os.path.join(here, "_cashme_itr_rows.json"), encoding="utf-8")) if os.path.exists(os.path.join(here, "_cashme_itr_rows.json")) else {}
for tri in sorted(ALVO, key=ORD):
    if tri in out: continue
    pdf = os.path.join(docs, f"{tri}_0.pdf")
    if not os.path.exists(pdf):
        ok = False
        for url in cand.get(tri, [])[:2]:
            if baixa_pdf(tri, url, pdf): ok = True; break
        if not ok: print(f"  {tri}: sem PDF", flush=True); continue
    shutil.copy(pdf, os.path.join(keep, f"{tri}.pdf"))
    txt = subprocess.run(["pdftotext", "-enc", "UTF-8", pdf, "-"], capture_output=True).stdout.decode("utf-8", "ignore")
    pags = [i for i, p in enumerate(txt.split("\f")) if RE.search(p)]
    res = []
    with pdfplumber.open(pdf) as doc:
        for i in pags:
            if i >= len(doc.pages): continue
            rows = page_rows(doc.pages[i])
            for k, r in enumerate(rows):
                if RE.search(r):
                    res.append({"pag": i + 1, "cab": [x.strip()[:160] for x in rows[max(0, k - 8):k]], "linha": r.strip()[:260]})
    out[tri] = res
    print(f"  {tri}: {len(pags)} paginas, {len(res)} linhas", flush=True)
    json.dump(out, io.open(os.path.join(here, "_cashme_itr_rows.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fim", flush=True)
