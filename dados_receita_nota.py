# -*- coding: utf-8 -*-
"""Nota 'Receita liquida' (abertura da receita bruta) dos ITR/DFP da CVM, consolidado.
Linhas: incorporacao e revenda, loteamento, locacao, provisao para distrato, PCLD,
prestacao de servicos e outras, deducoes, receita liquida.
Documentos: fontes/itr/<tri>.pdf (baixa os que faltam via LINK_DOC dos zips itr/dfp
da CVM no scratchpad). Leitura por caracteres (tok_lines de dados_resfin_release).
Coluna: consolidado do periodo corrente. Se a nota tem 8 colunas (3M/YTD x ano/anterior
x controladora/consolidado) pega o 3M; se tem 4, pega o YTD e o trimestre sai por
diferenca (feito no final). Saida: _receita_nota.json."""
import base64, csv, io, json, os, re, subprocess, sys, zipfile
from multiprocessing import Pool
import pdfplumber
from dados_resfin_release import tok_lines, norm

here = os.path.dirname(os.path.abspath(__file__))
tmp = r"C:\Users\RLAVOU~1\AppData\Local\Temp\claude\D--rlavourinha-Pictures-OneDrive--rea-de-Trabalho-Claude\e4e1cc5f-6e04-4e22-ba8b-ce88f93cdefb\scratchpad"
itr = os.path.join(here, "fontes", "itr")
ORD = lambda q: (int(q[2:]), int(q[0]))
MES = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}

def link_docs(tipo, ano):
    cam = os.path.join(tmp, f"{tipo}_cia_aberta_{ano}.zip")
    if not os.path.exists(cam): return {}
    with zipfile.ZipFile(cam) as zf:
        nome = f"{tipo}_cia_aberta_{ano}.csv"
        with zf.open(nome) as fh:
            linhas = list(csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";"))
    out = {}
    for r in linhas:
        if "CYRELA BRAZIL" not in r.get("DENOM_CIA", ""): continue
        out.setdefault(r.get("DT_REFER", "")[:10], []).append((int(r.get("VERSAO", 1)), r["LINK_DOC"]))
    return {k: [u for _, u in sorted(v, key=lambda x: -x[0])] for k, v in out.items()}

def baixa_doc(tri, url):
    pdf = os.path.join(itr, f"{tri}.pdf")
    if os.path.exists(pdf): return pdf
    zpath = os.path.join(tmp, f"{tri}_doc.zip")
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
    return pdf

KEYS = [("incorp", r"^.?ncorporacao(e|,)?(re)?venda"), ("lote", r"^.?oteamento"), ("locacao", r"^.?ocacao"),
        ("pcld", r"^.?rovisaoparadistrato-?pc|pcld|pecld"), ("distrato", r"^.?rovisaoparadistrato"),
        ("servicos", r"^.?restacaodeservicos"), ("deducoes", r"^.?educoes"), ("liquida", r"^.?eceitas?liquida")]
NUM = re.compile(r"^\(?-?\d{1,3}(?:\.\d{3})*(?:,\d+)?\)?$|^-$")
def num(t):
    if t == "-": return 0.0
    neg = t.startswith("(") or t.startswith("-"); v = float(t.strip("()").lstrip("-").replace(".", "").replace(",", "."))
    return -v if neg else v

def parse(args):
    tri, pdf_path = args
    try:
        pdf = pdfplumber.open(pdf_path)
        for i, p in enumerate(pdf.pages):
            if i < 10: continue
            t = norm(p.extract_text() or "")
            if not (re.search(r"ncorporacao(e|,)?(re)?venda", t) and re.search(r"eceitas?liquida", t) and re.search(r"educoes", t)): continue
            L = tok_lines(p); m, ncols = {}, None; seen_liq = False
            for n, raw, toks in L:
                vals = [x for x in toks if NUM.match(x)]
                if not vals: continue
                for key, rx in KEYS:
                    if key in m: continue
                    if re.search(rx, n):
                        m[key] = [num(x) for x in vals]
                        if key == "liquida": seen_liq = True
                        break
                if seen_liq: break
            if "incorp" not in m or "liquida" not in m: continue
            ncols = len(m["liquida"])
            if ncols == 3: continue  # tabela de reapresentacao (original | ajuste | reapresentado), nao e a nota do periodo
            def pick(v):
                if ncols == 8 and len(v) == 8: return v[4], "3M"
                if ncols == 4 and len(v) == 4: return v[2], "YTD"
                if ncols == 2 and len(v) == 2: return v[0], "YTD"
                # linhas com menos tokens (controladora vazia): assume os ultimos ncols//2 sao consolidado
                if len(v) >= ncols // 2:
                    cons = v[-(ncols // 2):]
                    return cons[0], ("3M" if ncols == 8 else "YTD")
                return None, "?"
            out = {"page": i + 1, "ncols": ncols, "raw": {k: v for k, v in m.items()}}
            for k, v in m.items():
                val, tipo = pick(v); out[k] = None if val is None else round(val / 1000, 3); out["tipo"] = tipo
            return tri, out
        return tri, None
    except Exception as e:
        return tri, {"erro": str(e)[:150]}

if __name__ == "__main__":
    quarters = [f"{t}T{a%100:02d}" for a in range(2010, 2027) for t in (1, 2, 3, 4)]
    quarters = [q for q in quarters if (10, 4) <= ORD(q) <= (26, 2)]
    if sys.argv[1:]: quarters = [q for q in quarters if q in sys.argv[1:]]
    # garante documentos
    links = {}
    for ano in range(2010, 2027):
        for tipo in ("itr", "dfp"): links.update(link_docs(tipo, ano))
    jobs = []
    for q in quarters:
        pdf = os.path.join(itr, f"{q}.pdf")
        if not os.path.exists(pdf):
            t, a = int(q[0]), 2000 + int(q[2:]); urls = links.get(f"{a}-{MES[t]}", [])
            got = None
            for u in urls[:2]:
                try: got = baixa_doc(q, u)
                except Exception as e: print(f"  {q}: download erro {str(e)[:80]}", flush=True)
                if got: break
            if not got: print(f"  {q}: sem documento", flush=True); continue
            print(f"  {q}: baixado", flush=True)
        jobs.append((q, pdf))
    out = {}
    jpath = os.path.join(here, "_receita_nota.json")
    if sys.argv[1:] and os.path.exists(jpath): out = json.load(io.open(jpath, encoding="utf-8"))
    with Pool(4) as pool:
        for q, r in pool.imap_unordered(parse, jobs): out[q] = r
    for q in sorted(out, key=ORD):
        r = out[q]
        if not r: print(f"  {q}: nota nao encontrada", flush=True); continue
        if "erro" in r: print(f"  {q}: erro {r['erro']}", flush=True); continue
        g = sum(r.get(k) or 0 for k in ("incorp", "lote", "locacao", "distrato", "pcld", "servicos"))
        chk = g + (r.get("deducoes") or 0) - (r.get("liquida") or 0)
        print(f"  {q} p{r['page']} {r['tipo']:3s} ncols={r['ncols']} incorp={r.get('incorp')} lote={r.get('lote')} loc={r.get('locacao')} distr={r.get('distrato')} pcld={r.get('pcld')} serv={r.get('servicos')} ded={r.get('deducoes')} liq={r.get('liquida')} | bruta={g:.1f} check={chk:.1f}", flush=True)
    json.dump(out, io.open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("fim", flush=True)
