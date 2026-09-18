# -*- coding: utf-8 -*-
"""Tabela 'Resultado Financeiro' dos releases 4T08-2T26 (fontes/release_XTYY.pdf).
As tabelas sao objetos Excel com espacamento entre letras: pdftotext e o
extract_words do pdfplumber quebram tokens e pulam colunas. Aqui a leitura e por
CARACTERES: linha = mesmo 'top'; rotulo = caracteres a esquerda do primeiro
numero, sem espacos; numeros = agrupamentos de caracteres separados por gap > 6pt.
Primeiro numero da linha (menor x) = trimestre corrente.
Saida: _resfin_release.json {tri: {'unit': 'MM'|'mil', 'rows': [[rotulo, valores...]], 'map': {chave: valor R$ mi}}}."""
import glob, io, json, os, re, sys, unicodedata
from multiprocessing import Pool
import pdfplumber

here = os.path.dirname(os.path.abspath(__file__))

def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower().replace(" ", "")

KEYS = [  # '^.?' tolera a perda do primeiro caractere na extracao
    ("desp_total",  r"^.?otaldedespesasfinanceiras|^.?espesasfinanceiras$"),
    ("juros_sfh",   r"^.?uros(do)?sfh"),
    ("juros_emp",   r"^.?uros(de)?(emprestimos|financiamentos)(nacionais|nac)"),
    ("juros_cap",   r"^.?uroscapitalizados"),
    ("subtotal",    r"^.?ubtotal"),
    ("var_mon_fin", r"^.?ariacoesmonetariassobrefinanciamentos"),
    ("desp_banc",   r"^.?espesasbancarias"),
    ("desp_outras", r"^.?utrasdespesasfinanceiras"),
    ("rec_total",   r"^.?otaldereceitasfinanceiras|^.?eceitasfinanceiras$"),
    ("rend_aplic",  r"^.?endimentos?deaplica"),
    ("rec_cr",      r"^.?eceitasfinanceirassobrecontasareceber"),
    ("var_mon_rec", r"^.?ariacoesmonetarias$"),
    ("rend_parc",   r"^.?endimentos?definanciamentos?(de|a)parceiros"),
    ("rec_outras",  r"^.?utrasreceitasfinanceiras"),
    ("resultado",   r"^.?esultadofinanceiro$"),
]
NUM = re.compile(r"^\(?-?\d{1,3}(?:\.\d{3})*(?:,\d+)?\)?$")

def tok_lines(page):
    chars = [c for c in page.chars if c["text"].strip()]
    chars.sort(key=lambda c: (c["top"], c["x0"]))
    lines, cur, cy = [], [], None
    for c in chars:
        if cy is None or abs(c["top"] - cy) <= 2.5: cur.append(c); cy = c["top"] if cy is None else cy
        else: lines.append(cur); cur = [c]; cy = c["top"]
    if cur: lines.append(cur)
    out = []
    for l in lines:
        l.sort(key=lambda c: c["x0"])
        # rotulo: ate o primeiro caractere numerico/parentese apos x>120 precedido de gap > 6
        lab, rest, i = [], [], 0
        while i < len(l):
            c = l[i]
            gap = c["x0"] - l[i-1]["x1"] if i else 0
            if lab and re.match(r"[\d(\-]", c["text"]) and gap > 6 and c["x0"] > 120:
                break
            lab.append(c["text"]); i += 1
        rest = l[i:]
        toks, t = [], []
        for j, c in enumerate(rest):
            gap = c["x0"] - rest[j-1]["x1"] if j else 0
            if t and gap > 6: toks.append("".join(t)); t = []
            t.append(c["text"])
        if t: toks.append("".join(t))
        out.append((norm("".join(lab)), "".join(lab), [x.replace(" ", "") for x in toks]))
    return out

def num(tok):
    tok = tok.strip()
    if tok in ("-", "–"): return 0.0
    neg = tok.startswith("(") or tok.startswith("-")
    core = tok.strip("()").lstrip("-").replace(".", "").replace(",", ".")
    try: v = float(core)
    except ValueError: return None
    return -v if neg else v

def parse(pdf_path):
    q = os.path.basename(pdf_path)[8:12]
    try:
        pdf = pdfplumber.open(pdf_path)
        for i, p in enumerate(pdf.pages):
            t = norm(p.extract_text() or "")
            if not re.search(r"uros(do)?sfh", t) or not re.search(r"endimentos?deaplica", t):
                continue
            L = tok_lines(p)
            # regiao: da 1a linha 'despesasfinanceiras' ate 'resultadofinanceiro' depois de 'receitas'
            start = next((k for k, (n, _, _) in enumerate(L) if re.match(r"^.?espesasfinanceiras|^.?otaldedespesas", n)), None)
            if start is None: continue
            rows, seen_rec, end = [], False, None
            for k in range(start, len(L)):
                n, raw, toks = L[k]
                if re.match(r"^.?eceitasfinanceiras|^.?otaldereceitas", n): seen_rec = True
                rows.append([raw.strip(), toks])
                if seen_rec and re.match(r"^.?esultadofinanceiro", n): end = k; break
            unit = "MM"
            m = {}
            for raw, toks in rows:
                n = norm(raw)
                vals = [num(x) for x in toks if NUM.match(x) and "%" not in x]
                vals = [v for v in vals if v is not None]
                if not vals: continue
                for key, rx in KEYS:
                    if key not in m and re.search(rx, n): m[key] = vals[0]; break
            if max(abs(m.get("desp_total") or 0), abs(m.get("rec_total") or 0)) > 2000:
                unit = "mil"; m = {k: round(v / 1000, 3) for k, v in m.items()}
            return q, {"page": i + 1, "unit": unit, "rows": rows, "map": m}
        return q, None
    except Exception as e:
        return q, {"erro": str(e)[:120]}

ORD = lambda q: (int(q[2:]), int(q[0]))
if __name__ == "__main__":
    files = sorted(glob.glob(os.path.join(here, "fontes", "release_[1-4]T[0-9][0-9].pdf")))
    files = [f for f in files if ORD(os.path.basename(f)[8:12]) >= (8, 4)]
    if sys.argv[1:]: files = [f for f in files if os.path.basename(f)[8:12] in sys.argv[1:]]
    out = {}
    jpath = os.path.join(here, "_resfin_release.json")
    if sys.argv[1:] and os.path.exists(jpath):  # reprocessamento parcial: mantem o resto
        out = json.load(io.open(jpath, encoding="utf-8"))
    with Pool(4) as pool:
        for q, r in pool.imap_unordered(parse, files):
            out[q] = r
    for q in sorted(out, key=ORD):
        r = out[q]
        if not r: print(f"  {q}: tabela nao encontrada", flush=True); continue
        if "erro" in r: print(f"  {q}: erro {r['erro']}", flush=True); continue
        m = r["map"]
        sd = sum(m.get(k, 0) for k in ("juros_sfh", "juros_emp", "juros_cap", "var_mon_fin", "desp_banc", "desp_outras"))
        sr = sum(m.get(k, 0) for k in ("rend_aplic", "rec_cr", "var_mon_rec", "rend_parc", "rec_outras"))
        print(f"  {q} p{r['page']} {r['unit']:3s} D={m.get('desp_total')} (soma {sd:.1f}) sfh={m.get('juros_sfh')} emp={m.get('juros_emp')} cap={m.get('juros_cap')} vm={m.get('var_mon_fin')} banc={m.get('desp_banc')} out={m.get('desp_outras')} | R={m.get('rec_total')} (soma {sr:.1f}) aplic={m.get('rend_aplic')} cr={m.get('rec_cr')} vm={m.get('var_mon_rec')} parc={m.get('rend_parc')} out={m.get('rec_outras')} | res={m.get('resultado')}", flush=True)
    json.dump(out, io.open(os.path.join(here, "_resfin_release.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("fim", len([1 for v in out.values() if v and "map" in v]), "de", len(out), flush=True)
