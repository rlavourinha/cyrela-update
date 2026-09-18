# -*- coding: utf-8 -*-
"""Adiantamentos de clientes - 'Valores por permuta com terrenos' (permuta fisica)
nas DFPs 2010-2019 da CVM (documento ENET -> PDF). Cada DFP traz o ano e o
comparativo do ano anterior. PDFs guardados em fontes/itr/4Tyy.pdf.
Saida: _permuta_dfp.json com todas as linhas candidatas por documento."""
import base64, csv, io, json, os, re, subprocess, sys, urllib.request, zipfile
here = os.path.dirname(os.path.abspath(__file__))
tmp = r"C:\Users\RLAVOU~1\AppData\Local\Temp\claude\D--rlavourinha-Pictures-OneDrive--rea-de-Trabalho-Claude\e4e1cc5f-6e04-4e22-ba8b-ce88f93cdefb\scratchpad"
itr = os.path.join(here, "fontes", "itr")
BASE_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
anos = [int(a) for a in sys.argv[1:]] or list(range(2010, 2020))

def baixa(tipo, ano):
    nome = f"{tipo}_cia_aberta_{ano}.zip"; cam = os.path.join(tmp, nome)
    if not os.path.exists(cam):
        url = f"{BASE_CVM}/{tipo.upper()}/DADOS/{nome}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        io.open(cam, "wb").write(urllib.request.urlopen(req, timeout=600).read())
    return cam

def link_doc(ano):
    cam = baixa("dfp", ano)
    with zipfile.ZipFile(cam) as zf:
        nome = f"dfp_cia_aberta_{ano}.csv"
        with zf.open(nome) as fh:
            linhas = list(csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";"))
    c = [(int(r.get("VERSAO", 1)), r["LINK_DOC"]) for r in linhas
         if "CYRELA BRAZIL" in r.get("DENOM_CIA", "") and r.get("DT_REFER", "")[:10] == f"{ano}-12-31"]
    c.sort(key=lambda x: -x[0])
    return [u for _, u in c]

def obtem(tri, url):
    pdf = os.path.join(itr, f"{tri}.pdf"); txt = os.path.join(itr, f"{tri}.lay.txt")
    if os.path.exists(txt): return txt
    zpath = os.path.join(tmp, f"{tri}_dfp.zip")
    subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "-o", zpath,
                    url.replace("http://", "https://")], check=True, capture_output=True, timeout=900)
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
    if not partes: return None
    partes.sort(key=len, reverse=True); io.open(pdf, "wb").write(partes[0])
    subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", pdf, txt], check=True, capture_output=True)
    return txt

RE = re.compile(r"permuta", re.I)
out = {}
for ano in anos:
    tri = f"4T{ano%100:02d}"
    try: urls = link_doc(ano)
    except Exception as e: print(f"  {tri}: csv erro {str(e)[:80]}", flush=True); continue
    if not urls: print(f"  {tri}: sem candidato", flush=True); continue
    txt = None
    for url in urls[:2]:
        try: txt = obtem(tri, url)
        except Exception as e: print(f"  {tri}: erro {str(e)[:80]}", flush=True)
        if txt: break
    if not txt: continue
    L = io.open(txt, encoding="utf-8", errors="ignore").read().splitlines()
    hits = []
    for k, ln in enumerate(L):
        if RE.search(ln):
            ctx = L[max(0, k-3):k+4]
            if any(re.search(r"\d{2,3}\.\d{3}", c) for c in ctx):
                hits.append({"n": k, "ctx": [re.sub(r"\s{2,}", " | ", c.strip())[:200] for c in ctx]})
    out[tri] = {"doc": os.path.basename(txt), "n_linhas": len(L), "hits": hits}
    print(f"  {tri}: {len(L)} linhas | {len(hits)} hits permuta", flush=True)
json.dump(out, io.open(os.path.join(here, "_permuta_dfp.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fim", flush=True)
