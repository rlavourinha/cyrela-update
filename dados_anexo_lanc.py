# -*- coding: utf-8 -*-
"""Anexo 'Lançamentos' dos releases 4T17-4T22 da Cyrela lido direto do PDF (pdfplumber, palavras com posição), porque o texto extraído
(release_4TAA.txt, pdftotext) tem as colunas VGV e Produto deslocadas entre linhas. Cada palavra é atribuída à linha pelo y do
trimestre mais próximo e à coluna pelo x do cabeçalho (Empreendimento, Trimestre, Mês, Região, VGV, Área, Unidades, Produto, % CBR).
Saída: _anexo_lanc_cyrela.json {ano: [linhas]} com unidades 100%. Uso: python dados_anexo_lanc.py [anos]"""
import io, json, os, re, sys
import pdfplumber
here = os.path.dirname(os.path.abspath(__file__))
QRX = re.compile(r"^[1-4]T\d\d$")
def num(s):
    if s is None: return None
    s = str(s).strip()
    if not s or s in ("-", "–"): return None
    try: return float(s.replace(".", "").replace(",", "."))
    except ValueError: return None
COLS = ["nome", "tri", "mes", "reg", "vgv", "area", "un", "prod", "cbr"]
def header_x(words):
    """centros x das colunas a partir do cabeçalho; None se a página não tem cabeçalho"""
    want = {"Trimestre": "tri", "Mês": "mes", "Região": "reg", "VGV": "vgv", "Unidades": "un", "Produto": "prod", "CBR": "cbr"}
    hx = {}
    for w in words:
        t = w["text"].strip()
        if t in want and want[t] not in hx: hx[want[t]] = (w["x0"] + w["x1"]) / 2, w["top"]
        if t in ("Area", "Área") and "area" not in hx: hx["area"] = (w["x0"] + w["x1"]) / 2, w["top"]
    if not all(k in hx for k in ("tri", "mes", "reg", "un", "prod", "cbr")): return None
    ytop = hx["tri"][1]
    out = {k: v[0] for k, v in hx.items() if abs(v[1] - ytop) < 30}
    if "vgv" not in out and "reg" in out and "area" in out: out["vgv"] = (out["reg"] + out["area"]) / 2   # 4T19: 'VGV' e '(R$ MM)' se sobrepõem e não formam palavra
    return out, ytop
def parse_page(page, hx, xtol=1.5):
    words = page.extract_words(keep_blank_chars=False, x_tolerance=xtol)
    rows = [(w["top"] + w["bottom"]) / 2 for w in words if QRX.match(w["text"].strip())]
    rows = sorted(rows)
    if not rows: return []
    # limites de coluna: pontos médios entre centros vizinhos
    order = [k for k in ("tri", "mes", "reg", "vgv", "area", "un", "prod", "cbr") if k in hx]
    xs = [hx[k] for k in order]
    bounds = [(xs[i] + xs[i + 1]) / 2 for i in range(len(xs) - 1)]
    def col(xc):
        if xc < xs[0] - (xs[1] - xs[0]) / 2: return "nome"
        for i, b in enumerate(bounds):
            if xc < b: return order[i]
        return order[-1]
    out = [{k: [] for k in COLS} for _ in rows]
    for w in words:
        yc = (w["top"] + w["bottom"]) / 2
        i = min(range(len(rows)), key=lambda j: abs(rows[j] - yc))
        if abs(rows[i] - yc) > 6: continue
        out[i][col((w["x0"] + w["x1"]) / 2)].append((w["x0"], w["text"]))
    res = []
    for r in out:
        d = {k: " ".join(t for _, t in sorted(v)) for k, v in r.items()}
        if not QRX.match(d["tri"].strip()): continue
        nome = re.sub(r"^\d+\s+", "", d["nome"]).strip()
        res.append({"nome": nome, "tri": d["tri"].strip(), "mes": d["mes"].replace(" ", ""), "reg": d["reg"].strip(), "vgv": num(d["vgv"]), "area": num(d["area"]), "un": num(d["un"]), "prod": d["prod"].strip(), "cbr": num(d["cbr"].replace("%", ""))})
    return res
def parse_pdf(path, xtol=1.5):
    rows = []; hx = None; title = None
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        for i in range(min(20, n), n):
            p = pdf.pages[i]; words = p.extract_words(x_tolerance=xtol)
            txt = " ".join(w["text"] for w in words[:40])
            m = re.search(r"ANEXO\s+[IVX]+\s*[–-]\s*([A-ZÇÃÕÉÍÓ+ ]+)", txt)
            if hx is None:
                if "Entregues" in txt or not (m and "LANÇAMENTO" in m.group(1)): continue
                h = header_x(words)
                if not h: continue
                hx, _ = h; title = m.group(1).strip()
            else:
                if m and m.group(1).strip() != title: break
                if "Entregues" in txt: break
                h = header_x(words)
                if h: hx = h[0]
            got = parse_page(p, hx, xtol)
            if not got and hx is not None and rows: break
            rows.extend(got)
    return rows
def parse_chars(path):
    """4T20 e 4T22: a tabela vem como glifos soltos (sem palavras); agrupa caracteres em linhas (top) e em células (salto de x > 6 pt),
    e lê cada linha do fim para o começo: % CBR, produto, unidades, área, VGV; região = célula depois do trimestre (e do mês, se houver)"""
    rows = []; started = False
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        for i in range(min(20, n), n):
            p = pdf.pages[i]; txt = (p.extract_text() or "")[:200]
            m = re.search(r"ANEXO\s+[IVX]+\s*[–-]\s*([A-ZÇÃÕÉÍÓ+ ]+)", txt)
            if not started:
                if m and "LANÇAMENTO" in m.group(1): started = True
                else: continue
            elif m and "LANÇAMENTO" not in m.group(1): break
            lines = {}
            for c in p.chars:
                k = round(c["top"] / 2) * 2   # ~2 pt
                lines.setdefault(k, []).append(c)
            got = 0
            for k in sorted(lines):
                cs = sorted(lines[k], key=lambda c: c["x0"]); cells = []; cur = [cs[0]]
                for a, b in zip(cs, cs[1:]):
                    if b["x0"] - a["x1"] > 6: cells.append(cur); cur = [b]
                    else: cur.append(b)
                cells.append(cur)
                cells = ["".join(c["text"] for c in cl).strip() for cl in cells]
                cells = [c for c in cells if c]
                qi = next((j for j, c in enumerate(cells) if QRX.match(c)), None)
                if qi is None or len(cells) < qi + 5 or not cells[-1].endswith("%"): continue
                name = re.sub(r"^\d+\s*", "", " ".join(cells[1:qi] if cells[0].isdigit() else cells[:qi])); rest = cells[qi + 1:]
                if not name: continue   # linhas de cabeçalho de outro anexo que caem no mesmo bloco
                cbr = num(rest[-1][:-1]); prod = rest[-2]; un = num(rest[-3]); area = num(rest[-4]) if len(rest) >= 4 else None
                if num(prod) is not None: un, area, prod = num(prod), un, ""   # produto vazio
                mid = rest[:-4] if len(rest) >= 4 else []
                mes = next((x for x in mid if re.match(r"^[a-z]{3}-\d\d$", x)), None)
                reg = next((x for x in mid if re.fullmatch(r"[A-Za-z][A-Za-z ]{0,7}", x) and not re.match(r"^[a-z]{3}-\d\d$", x)), None)
                vgv = next((num(x) for x in reversed(mid) if num(x) is not None), None)
                rows.append({"nome": name, "tri": cells[qi], "mes": mes, "reg": reg, "vgv": vgv, "area": area, "un": un, "prod": prod, "cbr": cbr}); got += 1
            if started and not got and rows: break
    return rows
def parse_any(path):
    rows = parse_pdf(path)
    if not rows: rows = parse_chars(path)   # 4T20 e 4T22: glifos soltos no PDF
    return rows
years = [int(a) for a in sys.argv[1:]] or list(range(2017, 2023))
out_p = os.path.join(here, "_anexo_lanc_cyrela.json")
OUT = json.load(io.open(out_p, encoding="utf-8")) if os.path.exists(out_p) else {}
for y in years:
    rows = parse_any(os.path.join(here, "fontes", f"release_4T{str(y)[2:]}.pdf"))
    OUT[str(y)] = rows
    un = sum(r["un"] or 0 for r in rows)
    print(y, len(rows), "linhas;", f"{un:,.0f} un.;", "sem região:", sum(1 for r in rows if not r["reg"]), "sem un.:", sum(1 for r in rows if r["un"] is None), "| produtos:", sorted({str(r["prod"]) for r in rows}), "| regiões:", sorted({str(r["reg"]) for r in rows}))
json.dump(OUT, io.open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
