# -*- coding: utf-8 -*-
"""Serie da CashMe (entidade) pelos ITR/DFP da CVM: linhas 'Cashme Solucoes Financeiras'
da nota de investimentos (PL, resultado) e linhas 'CashMe' das notas de despesas.
Baixa os documentos estruturados (zip ENET -> PDF embutido no XML) como em
dados_receita_bruta_itr.py, extrai com pdftotext -layout e guarda TODAS as linhas
candidatas por documento em _cashme_itr_raw.json (interpretacao das colunas e manual,
porque o layout da nota muda de ano para ano)."""
import base64, csv, io, json, os, re, subprocess, sys, urllib.request, zipfile
here = os.path.dirname(os.path.abspath(__file__))
tmp = sys.argv[1] if len(sys.argv) > 1 else here
docs = os.path.join(tmp, "itrdocs"); os.makedirs(docs, exist_ok=True)
BASE_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
def baixa(tipo, ano):
    nome = f"{tipo}_cia_aberta_{ano}.zip"; cam = os.path.join(tmp, nome)
    if not os.path.exists(cam):
        url = f"{BASE_CVM}/{tipo.upper()}/DADOS/{nome}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try: io.open(cam, "wb").write(urllib.request.urlopen(req, timeout=600).read())
        except Exception as e: print(f"  ! {nome}: {e}", flush=True); return None
    return cam
ALVO = {}
for a in range(2020, 2027):
    for t, mes in ((1, "03-31"), (2, "06-30"), (3, "09-30"), (4, "12-31")):
        ALVO[f"{t}T{a%100:02d}"] = f"{a}-{mes}"
cand = {k: [] for k in ALVO}
for ano in range(2020, 2027):
    for tipo in ("itr", "dfp"):
        cam = baixa(tipo, ano)
        if not cam: continue
        with zipfile.ZipFile(cam) as zf:
            nome = f"{tipo}_cia_aberta_{ano}.csv"
            if nome not in zf.namelist(): continue
            with zf.open(nome) as fh: linhas = list(csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";"))
        for r in linhas:
            if "CYRELA BRAZIL" not in r.get("DENOM_CIA", ""): continue
            dt = r.get("DT_REFER", "")[:10]
            for tri, alvo in ALVO.items():
                if dt == alvo: cand[tri].append((int(r.get("VERSAO", 1)), r["LINK_DOC"]))
for tri in cand: cand[tri] = [u for _, u in sorted(cand[tri], key=lambda x: -x[0])]
def obtem_txt(tri, i, url):
    pdf = os.path.join(docs, f"{tri}_{i}.pdf"); txt = pdf.replace(".pdf", ".lay.txt")
    if os.path.exists(txt): return txt
    zpath = pdf.replace(".pdf", ".zip")
    subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "-o", zpath, url.replace("http://", "https://")], check=True, capture_output=True, timeout=900)
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
ORD = lambda q: (int(q[2:]), int(q[0]))
RE = re.compile(r"cash\s?me", re.I)
out = {}
for tri in sorted(ALVO, key=ORD):
    if not cand.get(tri): print(f"  {tri}: sem candidato", flush=True); continue
    for i, url in enumerate(cand[tri][:2]):
        try: txt = obtem_txt(tri, i, url)
        except Exception as e: print(f"  {tri} cand{i}: erro {str(e)[:80]}", flush=True); continue
        if not txt: continue
        s = io.open(txt, encoding="utf-8", errors="ignore").read()
        L = s.splitlines(); hits = []
        for k, ln in enumerate(L):
            if RE.search(ln) and re.search(r"\d", ln):
                hits.append({"n": k, "l": re.sub(r"\s{2,}", " | ", ln.strip())[:260]})
        out[tri] = {"doc": os.path.basename(txt), "n_linhas": len(L), "hits": hits}
        print(f"  {tri}: {os.path.basename(txt)} | {len(hits)} linhas com CashMe+numero", flush=True)
        break
json.dump(out, io.open(os.path.join(here, "_cashme_itr_raw.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fim", flush=True)
