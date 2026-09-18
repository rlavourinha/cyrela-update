# -*- coding: utf-8 -*-
"""Book ('Investimento') de Cury, Lavvi e Plano&Plano na nota de investimentos dos ITR/DFP
(fontes/itr/<tri>.pdf), 4T10-2T26. Leitura por indice de coluna nas linhas com >= 10 numeros
(layout: % cur, % ant, PL cur, PL ant, lucro cur, lucro ant, INVESTIMENTO cur, inv ant,
equivalencia cur, eq ant). Sanidade: investimento entre 0,5x e 4x de %xPL; guarda tambem a
equivalencia (para conferir com o modelo). Prefere a pagina 'composicao ... consolidado'.
Saida: _book_participacoes.json {tri: {cury:{inv,pl,pct,eq}, lavvi:..., pp:..., pagina}}"""
import io, json, os, re, sys
from multiprocessing import Pool
import pdfplumber
from dados_resfin_release import tok_lines, norm

here = os.path.dirname(os.path.abspath(__file__))
itr = os.path.join(here, "fontes", "itr")
NUM = re.compile(r"^\(?-?\d{1,3}(?:\.\d{3})*(?:,\d+)?\)?$|^-$")
def num(t):
    if t == "-": return 0.0
    neg = t.startswith("("); v = float(t.strip("()").replace(".", "").replace(",", ".")); return -v if neg else v
NAMES = {"cury": r"^curyconstrutora", "lavvi": r"^lavviempreendimentosimobiliarios", "pp": r"^plano&?planodesenvolvimento|^planoeplanodesenvolvimento"}

def rows_page(page):
    out = []
    for n, raw, toks in tok_lines(page):
        vals = [x for x in toks if NUM.match(x)]
        if len(vals) >= 10 and re.search(r"[a-z]{4}", n): out.append((n, [num(x) for x in vals]))
    return out

def pick(rows):
    res = {}
    for n, v in rows:
        for k, rx in NAMES.items():
            if k in res or not re.search(rx, n): continue
            pct, pl, lucro, inv, eq = v[0], v[2], v[4], v[6], v[8]
            if pct <= 0 or pct > 100: continue
            esp = pct / 100 * pl
            ok = (esp > 0 and 0.5 <= inv / esp <= 4.0) or (esp <= 0 and inv > 0)
            res[k] = {"inv": round(inv / 1000, 3), "pl": round(pl / 1000, 1), "pct": pct, "eq": round(eq / 1000, 3), "lucro": round(lucro / 1000, 1), "ok": bool(ok)}
    return res

def parse(tri):
    pdf_path = os.path.join(itr, f"{tri}.pdf")
    if not os.path.exists(pdf_path): return tri, None
    try:
        pdf = pdfplumber.open(pdf_path); cands = []
        for i, p in enumerate(pdf.pages):
            if i < 8 or i > 80: continue
            t = norm(p.extract_text() or "")
            if not any(k in t for k in ("curyconstrutora", "lavviempreendimentos", "plano&plano", "planoeplano")): continue
            r = pick(rows_page(p))
            if r: cands.append({"pagina": i + 1, "cons": ("consolidado" in t and "composicao" in t), "vals": r})
        if not cands: return tri, None
        # por investida: pagina do consolidado se tiver; senao o menor 'inv' entre candidatos ok
        out = {}; pag = {}
        for k in NAMES:
            cs = [c for c in cands if k in c["vals"]]
            if not cs: continue
            cons = [c for c in cs if c["cons"] and c["vals"][k]["ok"]]
            oks = [c for c in cs if c["vals"][k]["ok"]]
            pool_ = cons or oks or cs
            c = min(pool_, key=lambda c: c["vals"][k]["inv"]) if not cons else cons[0]
            out[k] = c["vals"][k]; pag[k] = c["pagina"]
        out["pagina"] = pag; out["cons"] = any(c["cons"] for c in cands)
        out["cands"] = [(c["pagina"], c["cons"], {k: (v["inv"], v["ok"]) for k, v in c["vals"].items()}) for c in cands]
        return tri, out
    except Exception as e:
        return tri, {"erro": str(e)[:120]}

ORD = lambda q: (int(q[2:]), int(q[0]))
if __name__ == "__main__":
    quarters = [f"4T{a:02d}" for a in range(10, 20)] + [f"{t}T{a:02d}" for a in range(20, 27) for t in (1, 2, 3, 4)]
    quarters = [q for q in quarters if ORD(q) <= (26, 2)]
    if sys.argv[1:]: quarters = [q for q in quarters if q in sys.argv[1:]]
    out = {}
    with Pool(4) as pool:
        for q, r in pool.imap_unordered(parse, quarters): out[q] = r
    for q in sorted(out, key=ORD):
        r = out[q]
        if not r: print(f"  {q}: nada", flush=True); continue
        if "erro" in r: print(f"  {q}: erro {r['erro']}", flush=True); continue
        s = " ".join(f"{k}=inv {v['inv']} ({'ok' if v['ok'] else 'X'}; {v['pct']}% x PL {v['pl']}; eq {v['eq']})" for k, v in r.items() if k in NAMES)
        print(f"  {q} p{r['pagina']} {'cons' if r['cons'] else 'outra'}: {s} | cands={r['cands']}", flush=True)
    json.dump(out, io.open(os.path.join(here, "_book_participacoes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("fim", flush=True)
