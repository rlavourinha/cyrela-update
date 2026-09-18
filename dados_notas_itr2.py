# -*- coding: utf-8 -*-
"""Notas dos ITR/DFP consolidados (fontes/itr/<tri>.pdf, 1T20-2T26) lidas por POSICAO DOS
GLIFOS (pdfplumber): linhas reconstruidas por y, tokens por x, e a coluna 'consolidado corrente'
identificada pela posicao do cabecalho 'Consolidado' (ou, sem cabecalho, pela contagem de
colunas). Substitui dados_notas_itr.py (pdftotext -layout quebrava linhas das tabelas).
Tabelas: contas a receber, adiantamentos de clientes, cronograma de contas a pagar por terrenos,
provisoes para riscos (provavel e possivel), provisao para garantia de obra.
Saida: _notas_itr.json (R$ mi) com flags _ok / _derivado. Cache de paginas em fontes/itr/<tri>.rows.json."""
import io, json, os, re, sys, unicodedata
import pdfplumber
here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "fontes", "itr")
TRIS = [f"{t}T{a:02d}" for a in range(20, 27) for t in (1, 2, 3, 4)][:26]
def norm(s): return re.sub(r"\s+", " ", "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()).strip()
NUM = re.compile(r"^\(?-?\d{1,3}(?:\.\d{3})+\)?$|^\(?-?\d{1,4}\)?$|^-$")
def page_tokens(page, ytol=1.5, gap=1.2):
    chars = [c for c in page.chars if c["text"].strip()]
    chars.sort(key=lambda c: (round(c["top"], 1), c["x0"]))
    rows, cur, top = [], [], None
    for c in chars:
        if top is None or abs(c["top"] - top) <= ytol: cur.append(c); top = c["top"] if top is None else top
        else: rows.append(cur); cur, top = [c], c["top"]
    if cur: rows.append(cur)
    out = []
    for cs in rows:
        cs = sorted(cs, key=lambda c: c["x0"]); toks = []; t = [cs[0]]
        for c in cs[1:]:
            if c["x0"] - t[-1]["x1"] > gap: toks.append(t); t = [c]
            else: t.append(c)
        toks.append(t)
        tk = [{"x0": round(t[0]["x0"], 1), "x1": round(t[-1]["x1"], 1), "text": "".join(c["text"] for c in t)} for t in toks]
        # une tokens numericos fragmentados: '1' + '.353' (gap grande dentro do numero)
        merged = []
        for k in tk:
            if merged and re.fullmatch(r"\(?-?\d{1,3}", merged[-1]["text"]) and re.fullmatch(r"(\.\d{3})+\)?", k["text"]) and k["x0"] - merged[-1]["x1"] < 8:
                merged[-1] = {"x0": merged[-1]["x0"], "x1": k["x1"], "text": merged[-1]["text"] + k["text"]}
            else: merged.append(k)
        out.append({"top": round(cs[0]["top"], 1), "text": " ".join(k["text"] for k in merged), "tk": merged})
    return out
def val(text):
    t = text.strip()
    if t == "-": return 0.0
    neg = t.startswith("("); v = float(t.strip("()").replace(".", "")); return -v if neg else v
def numtoks(row): return [k for k in row["tk"] if NUM.match(k["text"]) and not re.fullmatch(r"\d{1,2}/20\d\d|20\d\d|\d{1,2}", k["text"].strip("()"))]
class Table:
    """rows: lista de linhas da pagina; a coluna alvo e a 1a coluna sob 'Consolidado' (ou por contagem)."""
    def __init__(self, rows, i_start, i_end):
        self.rows = rows[i_start:i_end]
        hdr = [k for r in rows[max(0, i_start - 8):i_end] for k in r["tk"] if norm(k["text"]).startswith("consolidado")]
        self.cons_x0 = min(k["x0"] for k in hdr) if hdr else None
        # anchors: bordas direitas dos numeros nas linhas com >= 2 numeros
        xs = sorted(k["x1"] for r in self.rows for k in numtoks(r) if len(numtoks(r)) >= 2)
        cols = []
        for x in xs:
            if cols and x - cols[-1][-1] <= 14: cols[-1].append(x)
            else: cols.append([x])
        self.cols = [sum(c) / len(c) for c in cols if len(c) >= 2] or [sum(c) / len(c) for c in cols]
        if self.cons_x0 is not None:
            under = [c for c in self.cols if c >= self.cons_x0 - 6]
            self.target = under[0] if under else (self.cols[-2] if len(self.cols) >= 2 else (self.cols[0] if self.cols else None))
        else:
            self.target = (self.cols[2] if len(self.cols) >= 4 else (self.cols[0] if len(self.cols) in (1, 2) else (self.cols[-2] if self.cols else None)))
    def get(self, row):
        nt = numtoks(row)
        if not nt or self.target is None: return None
        k = min(nt, key=lambda k: abs(k["x1"] - self.target))
        return val(k["text"]) if abs(k["x1"] - self.target) <= 22 else None
    def find(self, pat):
        for r in self.rows:
            if re.search(pat, norm(r["text"])): return r
        return None
    def value(self, pat):
        r = self.find(pat); return self.get(r) if r else None
def load_rows(q):
    cache = os.path.join(D, f"{q}.rows.json")
    if os.path.exists(cache): return json.load(io.open(cache, encoding="utf-8"))
    pages = []
    with pdfplumber.open(os.path.join(D, f"{q}.pdf")) as pdf:
        for pg in pdf.pages:
            rows = page_tokens(pg); pages.append({"rows": rows, "norm": norm(" ".join(r["text"] for r in rows))})
    json.dump(pages, io.open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return pages
def find_page(pages, *pats):
    for i, p in enumerate(pages):
        if all(re.search(pt, p["norm"]) for pt in pats): return i
    return None
def near(v, lst, tol=2.0): return any(abs(v - x) <= tol for x in lst)
def idx(rows, pat, start=0):
    for i in range(start, len(rows)):
        if re.search(pat, norm(rows[i]["text"])): return i
    return None
def parse_cr(pages):
    ip = find_page(pages, r"contas a receber de vendas apropriad", r"provisao para distrato")
    if ip is None: return None
    rows = pages[ip]["rows"]; i0 = idx(rows, r"empreendimentos concluidos"); i1 = idx(rows, r"nao circulante", i0 or 0)
    if i0 is None or i1 is None: return {"_erro": "linhas nao achadas"}
    T = Table(rows, max(0, i0 - 2), i1 + 1)
    g = lambda pat: T.value(pat)
    out = {"concluidos": g(r"^empreendimentos concluidos"), "receita_apropriada": g(r"^receita apropriada"), "parcelas_recebidas": g(r"^parcelas recebidas"), "avp": g(r"ajuste a valor presente"),
           "em_construcao": g(r"^empreendimentos em construcao"), "cr_vendas_apropriadas": g(r"contas a receber de vendas apropriad"), "pdd": g(r"provisao para risco de credito|provisao para creditos"), "prov_distrato": g(r"provisao para distrato"),
           "servicos": g(r"prestacao de servico"), "total": g(r"^total do contas a receber|^total"), "circulante": g(r"^circulante"), "nao_circulante": g(r"^nao circulante")}
    # em construcao pode vir como subtotal (linha sem rotulo) -> deriva pela identidade se faltar
    if out["em_construcao"] in (None, 0) and None not in (out["receita_apropriada"], out["parcelas_recebidas"], out["avp"]):
        out["em_construcao"] = out["receita_apropriada"] + out["parcelas_recebidas"] + out["avp"]
    chk1 = None not in (out["concluidos"], out["em_construcao"], out["cr_vendas_apropriadas"]) and abs(out["concluidos"] + out["em_construcao"] - out["cr_vendas_apropriadas"]) <= 3
    chk2 = None not in (out["cr_vendas_apropriadas"], out["pdd"], out["prov_distrato"], out["total"]) and abs(out["cr_vendas_apropriadas"] + out["pdd"] + out["prov_distrato"] + (out["servicos"] or 0) - out["total"]) <= 3
    chk3 = None not in (out["total"], out["circulante"], out["nao_circulante"]) and abs(out["circulante"] + out["nao_circulante"] - out["total"]) <= 3
    out["_ok"] = bool(chk1 and (chk2 or chk3)); out["_chk"] = [chk1, chk2, chk3]
    return out
def parse_adiant(pages):
    ip = find_page(pages, r"valores por permuta com terrenos", r"total de adiantamento")
    if ip is None: return None
    rows = pages[ip]["rows"]; i0 = idx(rows, r"adiantamentos de clientes|por recebimento da venda"); i1 = idx(rows, r"nao circulante", i0 or 0)
    if i0 is None or i1 is None: return {"_erro": "linhas nao achadas"}
    T = Table(rows, i0, i1 + 1); g = lambda pat: T.value(pat)
    out = {"antecipacoes": g(r"demais antecipacoes"), "receitas_apropriadas_acum": g(r"^receitas apropriadas"), "receitas_recebidas_acum": g(r"^receitas recebidas"), "permuta_fisica": g(r"valores por permuta"), "total": g(r"total de adiantamento"), "circulante": g(r"^circulante"), "nao_circulante": g(r"^nao circulante")}
    if None not in (out["receitas_apropriadas_acum"], out["receitas_recebidas_acum"]): out["saldo_unidades_vendidas"] = out["receitas_apropriadas_acum"] + out["receitas_recebidas_acum"]
    chk = None not in (out.get("saldo_unidades_vendidas"), out["antecipacoes"], out["permuta_fisica"], out["total"]) and abs((out["antecipacoes"] or 0) + out["saldo_unidades_vendidas"] + out["permuta_fisica"] - out["total"]) <= 3
    chk2 = None not in (out["total"], out["circulante"], out["nao_circulante"]) and abs(out["circulante"] + out["nao_circulante"] - out["total"]) <= 3
    out["_ok"] = bool(chk or (chk2 and out["permuta_fisica"] is not None)); return out
def parse_terrenos(pages):
    ip = None
    for i, p in enumerate(pages):
        if re.search(r"contas a pagar por aquisicao de imoveis", p["norm"]) and re.search(r"cronograma de vencimentos", p["norm"]) and re.search(r"\d meses", p["norm"]): ip = i; break
    if ip is None: return None
    rows = pages[ip]["rows"]; i0 = idx(rows, r"cronograma de vencimentos"); ia = idx(rows, r"^(12|24|36|48|60) meses|^ate 12 meses", i0 or 0)
    if ia is None: return {"_erro": "sem cronograma"}
    i1 = idx(rows, r"^total", ia) or idx(rows, r"^nao circulante", ia) or min(ia + 10, len(rows) - 1)
    T = Table(rows, ia - 1, i1 + 1); out = {}
    for r in T.rows:
        t = norm(r["text"]); m = re.match(r"^(?:ate )?(12|24|36|48|60) meses", t)
        if m: out[f"m{m.group(1)}"] = T.get(r)
        elif re.match(r"^(acima de|>) ?(48|60)", t): out["m_alem"] = T.get(r)
        elif re.match(r"^total", t): out["total"] = T.get(r)
        elif re.match(r"^circulante", t): out["circulante"] = T.get(r)
        elif re.match(r"^nao circulante", t): out["nao_circulante"] = T.get(r)
    bk = [k for k in out if k.startswith("m") and out[k] is not None]
    if bk:
        out["soma_baldes"] = sum(out[k] for k in bk)
        nc = out.get("nao_circulante"); tot = out.get("total"); ci = out.get("circulante")
        tol = max(3, 0.001 * abs(out["soma_baldes"])); out["_ok"] = (nc is not None and abs(out["soma_baldes"] - nc) <= tol) or (tot is not None and abs(out["soma_baldes"] - tot) <= tol) or (tot is not None and ci is not None and abs(out["soma_baldes"] + ci - tot) <= tol)
    return out
def parse_prov(pages):
    out = {}
    ip = find_page(pages, r"processos civeis")
    if ip is not None:
        rows = pages[ip]["rows"]; ia = idx(rows, r"^processos civeis"); i1 = idx(rows, r"^nao circulante", ia or 0)
        if ia is not None and i1 is not None:
            T = Table(rows, ia - 1, i1 + 1); g = lambda pat: T.value(pat)
            out.update({"provavel_civeis": g(r"^processos civeis"), "provavel_tributarios": g(r"^processos tributarios"), "provavel_trabalhistas": g(r"^processos trabalhistas"), "provavel_total_nota": g(r"^total"), "circulante": g(r"^circulante"), "nao_circulante": g(r"^nao circulante")})
            soma = sum(out[k] or 0 for k in ("provavel_civeis", "provavel_tributarios", "provavel_trabalhistas")); out["provavel_total"] = soma
            tn = out["provavel_total_nota"]; ci = out["circulante"]; nc = out["nao_circulante"]
            out["_ok"] = (tn is not None and abs(tn - soma) <= 3) or (ci is not None and nc is not None and abs(ci + nc - soma) <= 3)
    # perda possivel (consolidado): pagina com 'perda possivel'; ultimo bloco civel/tributario/trabalhista (o 2o e o consolidado)
    for i, p in enumerate(pages):
        if re.search(r"perda possivel", p["norm"]) and re.search(r"assim apresentad", p["norm"]):
            rows = p["rows"]; i0 = idx(rows, r"perda possivel"); blocos = []; cur = {}
            seq = rows[i0 or 0:] + (pages[i + 1]["rows"] if i + 1 < len(pages) else [])  # a tabela pode estar na pagina seguinte
            for r in seq:
                t = norm(r["text"]); nt = numtoks(r)
                if re.match(r"^civel\b", t) and nt: cur = {"civel": val(nt[0]["text"])}
                elif re.match(r"^tributario\b", t) and nt and cur: cur["tributario"] = val(nt[0]["text"])
                elif re.match(r"^trabalhista\b", t) and nt and cur: cur["trabalhista"] = val(nt[0]["text"]); blocos.append(cur); cur = {}
            full = [b for b in blocos if len(b) == 3]
            if full:
                b = full[-1]; out["possivel_civel"] = b["civel"]; out["possivel_tributario"] = b["tributario"]; out["possivel_trabalhista"] = b["trabalhista"]; out["_possivel_blocos"] = len(full)
            break
    for i, p in enumerate(pages):
        if re.search(r"provisao para garantia de obra", p["norm"]):
            rows = p["rows"]; r = next((r for r in rows if re.search(r"provisao para garantia de obra", norm(r["text"]))), None)
            if r:
                nt = numtoks(r)
                if nt: out["garantia_obra"] = val(nt[0]["text"])
            break
    return out
out = {}
for q in TRIS:
    if not os.path.exists(os.path.join(D, f"{q}.pdf")): out[q] = {"_erro": "sem pdf"}; continue
    pages = load_rows(q)
    rec = {"cr": parse_cr(pages), "adiant": parse_adiant(pages), "terrenos": parse_terrenos(pages), "prov": parse_prov(pages)}
    for k, v in rec.items():
        if isinstance(v, dict):
            for kk, vv in list(v.items()):
                if isinstance(vv, (int, float)) and not isinstance(vv, bool) and not kk.startswith("_"): v[kk] = round(vv / 1000, 3)
    out[q] = rec
    def f(x): return "ok" if isinstance(x, dict) and x.get("_ok") else ("None" if x is None else "ERR " + str({k: v for k, v in x.items() if not k.startswith("_")})[:110])
    pv = rec["prov"] or {}
    print(q, "| cr", f(rec["cr"]), "| adiant", f(rec["adiant"]), "| terr", f(rec["terrenos"]), "| prov", f(pv), "| possivel", pv.get("possivel_civel"), pv.get("possivel_tributario"), pv.get("possivel_trabalhista"), "| gar", pv.get("garantia_obra"), flush=True)
json.dump(out, io.open(os.path.join(here, "_notas_itr.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
