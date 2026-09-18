# -*- coding: utf-8 -*-
"""Extrai, release a release (1T20..4T25), a tabela 'Modalidade' da secao ENDIVIDAMENTO:
financiamentos (SFH), emprestimos/divida corporativa (Cyrela e CashMe quando abertos),
juros a pagar / juros e custos, total. Linhas reconstruidas pelos glifos do PDF (como em
dados_receber_aging.py). Tambem soma os CRIs listados como 'Dividas CashMe' no detalhe
(para separar a CashMe antes de 2T24). Saida: _divida.json (R$ milhoes)."""
import io, json, os, re, sys, unicodedata
import pdfplumber
BASE = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(BASE, "fontes")
TRIS = [f"{t}T{a:02d}" for a in range(20, 26) for t in (1, 2, 3, 4)]
def strip_acc(s): return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
def norm(s): return re.sub(r"\s+", "", strip_acc(s).lower())
NUM = re.compile(r"\(?-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?\)?%?")
def nums(s):
    out = []
    for m in NUM.finditer(s):
        t = m.group(0)
        if t.endswith("%"): continue
        neg = t.startswith("(") or t.startswith("-"); raw = t.strip("()-").replace(".", "").replace(",", ".")
        try: v = float(raw)
        except ValueError: continue
        out.append(-v if neg else v)
    return out
def page_rows(page, ytol=1.2, gap=1.0):
    chars = [c for c in page.chars if c["text"].strip()]; chars.sort(key=lambda c: (round(c["top"], 1), c["x0"]))
    rows, cur, top = [], [], None
    for c in chars:
        if top is None or abs(c["top"] - top) <= ytol: cur.append(c); top = c["top"] if top is None else top
        else: rows.append(cur); cur, top = [c], c["top"]
    if cur: rows.append(cur)
    out = []
    for cs in rows:
        cs = sorted(cs, key=lambda c: c["x0"]); parts, prev = [], None
        for c in cs:
            if prev is not None and c["x0"] - prev["x1"] > gap: parts.append(" ")
            parts.append(c["text"]); prev = c
        out.append("".join(parts))
    return out
def find_pages(pdf):
    for i, pg in enumerate(pdf.pages):
        rows = page_rows(pg); ns = [norm(r) for r in rows]
        has_fin = any(n.startswith("financiamentos") and nums(r) for n, r in zip(ns, rows))
        has_sub = any(n.startswith("subtotal") for n in ns)
        has_end = any("endividamento" in n for n in ns) or any("dividabruta" in n for n in ns)
        if has_fin and has_sub and has_end: yield i
def parse(tri):
    p = os.path.join(F, f"release_{tri}.pdf")
    if not os.path.exists(p): return None
    rec = {k: None for k in ("financ", "corp", "corp_cyrela", "corp_cashme", "subtotal", "juros", "total", "cashme_detalhe")}
    with pdfplumber.open(p) as pdf:
        pages = list(find_pages(pdf))
        if not pages: return rec
        rows = []
        for i in pages[:2]: rows += page_rows(pdf.pages[i])
        # tambem a pagina seguinte (detalhe da divida corporativa / CashMe)
        for i in pages[:1]:
            if i + 1 < len(pdf.pages): rows += page_rows(pdf.pages[i + 1])
    def first_after(label_norms, skip=()):
        for r in rows:
            n = norm(r)
            if any(n.startswith(l) for l in label_norms) and not any(s in n for s in skip):
                v = nums(r[len(r) - len(r.lstrip()):])  # numeros na linha
                v = [x for x in nums(r) if abs(x) < 100000]
                if v: return v[0]
        return None
    rec["financ"] = first_after(("financiamentos-moedanacional", "financiamentos"), skip=("moedaestrangeira", "obtidos", "pagos"))
    rec["corp_cyrela"] = first_after(("dividacorporativa-cyrela",))
    rec["corp_cashme"] = first_after(("dividacorporativa-cashme",))
    rec["corp"] = first_after(("emprestimos-moedanacional", "emprestimos"), skip=("estrangeira", "obtidos", "pagos", "juros"))
    rec["subtotal"] = first_after(("subtotal",))
    rec["juros"] = first_after(("jurosecustos", "jurosapagar-moedanacional", "jurosapagar"), skip=("estrangeira",))
    rec["total"] = first_after(("total",), skip=("subtotal", "totaldivida", "totalda"))
    # detalhe CashMe: bloco 'Dividas CashMe' ... 'Subtotal'
    blk, acc = False, None
    for r in rows:
        n = norm(r)
        if n.startswith("dividascashme") or n.startswith("dividacashme"): blk = True; acc = None; continue
        if blk and n.startswith("subtotal"):
            v = [x for x in nums(r) if abs(x) < 100000]; rec["cashme_detalhe"] = v[0] if v else None; blk = False
    return rec
if __name__ == "__main__":
    out = {}
    for t in TRIS:
        r = parse(t); out[t] = r
        if r: print(t, {k: v for k, v in r.items() if v is not None})
    json.dump(out, io.open(os.path.join(BASE, "_divida.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
