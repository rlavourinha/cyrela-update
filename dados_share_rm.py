# -*- coding: utf-8 -*-
"""Share de Cury e Vivaz no MCMV por região metropolitana (pedido de 23/09/26).
Numeradores: Vivaz = anexo 'Lançamentos' dos releases da Cyrela (release_4T17..4T25 e 2T26: empreendimento, trimestre, região, VGV,
unidades, produto, % CBR; unidades 100%; produto MCMV/CVA 2 e 3 e MCMV 1); Cury = unidades lançadas da planilha do RI (100%) e contagem
de empreendimentos por região nos releases/prévias (frase 'foram lançados N empreendimentos, sendo X em SP e Y no RJ', 4T22+).
Denominadores: MCid, unidades financiadas MCMV (FGTS/FS) por município e mês (_mcmv_sprj_metro.json: RMSP 39 mun., RMRJ 22 mun.,
capitais, estados) e Brasil (_mcmv_mensal.json). Saída: _share_rm.json + tabela impressa."""
import io, json, os, re, glob, collections
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
L = J("_lancamentos_ri.json"); CH = J("_cury_hist.json"); M = J("_mcmv_sprj_metro.json"); MM = J("_mcmv_mensal.json")["mensal"]
QRX = re.compile(r"^[1-4]T\d\d$"); NUM = re.compile(r"^-?[\d.]+(,\d+)?$")
REG = {"SP", "RJ", "CO", "MG", "NE", "ES", "SUL", "RS", "PR", "SC", "BA", "CE", "PE", "DF", "GO", "N", "S", "SPINT", "SP INT"}
def num(s): return float(s.replace(".", "").replace(",", ".")) if s else None
def rows_of(path, year):
    """linhas do anexo de lançamentos: [n, nome, tri, mês, região, vgv, área, un, produto, %cbr]"""
    out = []; started = False
    for ln in io.open(path, encoding="utf-8", errors="replace"):
        t = ln.strip()
        if not started:
            if re.match(r"^\s*Empreendimento\s+Trimestre", ln): started = True
            continue
        if re.match(r"^\s*Empreendimentos Entregues", ln) or "Entregues" in t[:60]: break
        toks = t.split()
        if len(toks) < 6 or not toks[0].isdigit(): continue
        qi = next((i for i, x in enumerate(toks) if QRX.match(x)), None)
        if qi is None or qi < 2: continue
        name = " ".join(toks[1:qi]); tri = toks[qi]; mes = toks[qi + 1].replace(" ", ""); j = qi + 2
        # mês pode vir quebrado ('m ar-18')
        if not re.search(r"-\d\d$", mes) and j < len(toks) and re.search(r"-\d\d$", toks[j]): mes += toks[j]; j += 1
        reg = toks[j]; j += 1
        if j < len(toks) and toks[j] == "INT": reg += " INT"; j += 1
        rest = toks[j:]
        if not rest or not rest[-1].endswith("%"): continue
        cbr = num(rest[-1][:-1]); rest = rest[:-1]
        nums = []
        while rest and NUM.match(rest[0]): nums.append(rest.pop(0))
        prod = " ".join(rest)
        vgv = area = un = None
        if year <= 2022:
            if len(nums) == 3: vgv, area, un = nums
            elif len(nums) == 2: area, un = nums
            elif len(nums) == 1: un = nums[0]
        elif year <= 2025:
            if len(nums) == 2: vgv, un = nums
            elif len(nums) == 1: un = nums[0]
        else:
            if len(nums) == 2: vgv, un = nums
            elif len(nums) == 1: vgv = nums[0]
        out.append({"n": int(toks[0]), "nome": name, "tri": tri, "mes": mes, "reg": reg, "vgv": num(vgv) if vgv else None, "area": num(area) if area else None, "un": num(un) if un else None, "prod": prod, "cbr": cbr})
    return out
ANX = {}
PDFA = J("_anexo_lanc_cyrela.json") if os.path.exists(os.path.join(here, "_anexo_lanc_cyrela.json")) else {}   # 2017-22: tabela lida do PDF (dados_anexo_lanc.py); o txt tem VGV e produto deslocados
for y in range(2017, 2026): ANX[y] = PDFA[str(y)] if str(y) in PDFA else rows_of(os.path.join(here, "fontes", f"release_4T{str(y)[2:]}.txt"), y)
ANX[2026] = rows_of(os.path.join(here, "fontes", "release_2T26.txt"), 2026)
# correção pontual: no PDF do 4T22 o produto do 'Vivaz Prime Vila Nova Cachoeirinha' (428 un., out/22) sai como 'CVA 2 e 3'; a planilha do RI
# tem 428 un. de Vivaz Prime (médio) no 4T22 e 250 de MCMV, então a linha é Prime. Com isso 1T22-3T22 batem com o RI trimestre a trimestre.
for r in ANX[2022]:
    if "Cachoeirinha" in r["nome"] and r["tri"] == "4T22": r["prod"] = "Médio (Vivaz Prime; corrigido)"
# 2026 sem coluna de unidades: estima pelo ticket MCMV do trimestre (planilha do RI: VGV ÷ unidades)
tk = {q: L["vgv_mcmv23"][q] / L["un_mcmv23"][q] for q in L["un_mcmv23"] if L["un_mcmv23"].get(q) and L["vgv_mcmv23"].get(q)}   # R$ mil por unidade (VGV da planilha em R$ mil)
for r in ANX[2026]:
    if r["un"] is None and r["vgv"] and "MCMV" in r["prod"]: r["un"] = 1000 * r["vgv"] / tk[r["tri"]]; r["un_est"] = True   # VGV do anexo em R$ mi
def is_mcmv(r): return bool(re.search(r"MCMV|CVA", r["prod"]))
def regkey(r): return {"SP": "sp", "RJ": "rj"}.get(r["reg"], "outros")
VZ = {}
for y, rs in ANX.items():
    d = {"sp": 0.0, "rj": 0.0, "outros": 0.0, "n": 0, "n_semun": 0, "jv": []}
    for r in rs:
        if not is_mcmv(r): continue
        d["n"] += 1
        if r["un"] is None: d["n_semun"] += 1; continue
        d[regkey(r)] += r["un"]
        if r["cbr"] is not None and r["cbr"] <= 50: d["jv"].append(f'{r["nome"]} ({r["reg"]}, {r["cbr"]:.0f}%, {r["un"]:.0f} un.)')
    d["total"] = d["sp"] + d["rj"] + d["outros"]
    d["ri"] = sum((L["un_mcmv23"].get(q) or 0) + (L["un_mcmv1"].get(q) or 0) for q in L["un_mcmv23"] if q.endswith(str(y)[2:]))
    VZ[str(y)] = d
# Cury: contagem por região (releases e prévias) e unidades totais (planilha)
CUN = next(v for k, v in CH.items() if k.endswith("Número de unidades") and "LANÇ" in k.upper())
CNT = {}
for f in glob.glob(os.path.join(here, "fontes", "verificacao", "cury_*.txt")):
    t = re.sub(r"\s+", " ", io.open(f, encoding="utf-8", errors="replace").read())
    q = re.search(r"([1-4]T\d\d)", os.path.basename(f)); q = q.group(1) if q else None
    m = re.search(r"foram lançados (\d+) empreendimentos?, sendo (\d+) (?:localizados )?em SP e (\d+) no RJ", t)
    if m and q: CNT[q] = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    elif q == "4T25" and "release" in f:   # 4T25: o texto do trimestre e o do ano vêm entrelaçados ("5 empreendimentos, sendo Em 2025, foram lançados 37 ... 25 4 localizados em SP e 1 no RJ ... 12 no RJ")
        m = re.search(r"foram lançados 5 empreendimentos, sendo Em 2025, foram lançados 37 empreendimentos, sendo 25 4 localizados em SP e 1 no RJ", t)
        if m: CNT["4T25"] = (5, 4, 1); CNT["2025"] = (37, 25, 12)
# denominadores por ano e LTM
def den(f):
    t = {"est": 0, "rmsp": 0, "rmrj": 0, "cap": 0, "rm": 0, "fin_rmsp": 0.0, "fin_rmrj": 0.0, "sub_rmsp": 0.0, "sub_rmrj": 0.0, "fin_est": 0.0, "sub_est": 0.0}
    for k, v in M.items():
        if f(k):
            for c in t: t[c] += v.get(c, 0)
    t["br"] = sum(v["un"] for k, v in MM.items() if f(k)); t["fin_br"] = 1000 * sum(v["fin_bi"] for k, v in MM.items() if f(k)); t["sub_br"] = 1000 * sum(v["sub_bi"] for k, v in MM.items() if f(k)); return t
OUT = {"vivaz": VZ, "cury_cnt": CNT, "den": {}}
for y in range(2017, 2027):
    f = (lambda k, y=y: k[:4] == str(y)) if y < 2026 else (lambda k: "2026-01" <= k <= "2026-06")
    OUT["den"][str(y)] = den(f)
OUT["den"]["LTM 2T26"] = den(lambda k: "2025-07" <= k <= "2026-06")
# --- índice por região metropolitana
# JVs fora da Vivaz: Plano & Plano ('Plano &', 'by Plano e Plano') e Cury (marca 'Dez', ex.: 'Dez Ipiranga' na apresentação 3T20 da Cury; nos anexos
# de 2017-19 aparecem 'Dez ...' a 25-50% CBR). 'Meu Mundo Estação Mooca' (50%, 2020-21) fica: a planilha do RI inclui (2020 bate exato).
def is_pp(r): return bool(re.search(r"Plano ?&|Plano e Plano|^Dez\b", r["nome"]))
def viv_rows(pred, key="un"):
    d = {"sp": 0.0, "rj": 0.0, "outros": 0.0, "pp": 0.0}
    for y, rs in ANX.items():
        for r in rs:
            if not is_mcmv(r) or r.get(key) is None or not pred(y, r): continue
            if is_pp(r): d["pp"] += r[key]
            else: d[regkey(r)] += r[key]
    d["total"] = d["sp"] + d["rj"] + d["outros"]; return d
# Geoimóvel (Mercado Completo, cidade de São Paulo): unidades lançadas por grupo incorporador e data de lançamento → Cury e Vivaz na capital
import openpyxl, datetime
_ws = openpyxl.load_workbook(os.path.join(here, "fontes", "geoimovel", "mercado_completo_geoimovel.xlsx"), read_only=True, data_only=True)["plan"]
_rows = list(_ws.iter_rows(values_only=True)); _H = {h: i for i, h in enumerate(_rows[0])}
GEO = {"cury": collections.Counter(), "vivaz": collections.Counter()}
for _r in _rows[1:]:
    _d = _r[_H["Data Lançamento"]]
    if not isinstance(_d, datetime.datetime): continue
    _g = str(_r[_H["Grupo Incorporador Apelido"]] or "").upper(); _q = f"{(_d.month - 1) // 3 + 1}T{str(_d.year)[2:]}"
    if _g.startswith("CURY"): GEO["cury"][_q] += _r[_H["Unidades"]] or 0
    if "VIVAZ" in _g: GEO["vivaz"][_q] += _r[_H["Unidades"]] or 0
def geo(k, qs): return sum(GEO[k].get(q, 0) for q in qs)
def cury_reg(qs):
    """unidades da Cury por região: total da planilha × fatia da contagem de empreendimentos (estimativa; a Cury não abre unidades por praça)"""
    tot = sum(CUN.get(q, 0) for q in qs); c = [CNT[q] for q in qs if q in CNT]
    if not c or len(c) < len(qs): return {"total": tot, "sp": None, "rj": None, "n": sum(x[0] for x in c), "nsp": sum(x[1] for x in c), "nrj": sum(x[2] for x in c)}
    n, nsp, nrj = (sum(x[i] for x in c) for i in range(3))
    return {"total": tot, "sp": tot * nsp / n, "rj": tot * nrj / n, "n": n, "nsp": nsp, "nrj": nrj}
IDX = {}
def block(qs, pred, denk):
    c = cury_reg(qs); c["geo_sp"] = geo("cury", qs); c["rj_teto"] = c["total"] - c["geo_sp"]   # teto do RJ = total − capital paulista (Geoimóvel); sobra RMSP fora da capital
    v = viv_rows(pred); v["geo_sp"] = geo("vivaz", qs)
    return {"vivaz": v, "vivaz_vgv": viv_rows(pred, "vgv"), "cury": c, "den": OUT["den"][denk]}
for y in range(2017, 2027):
    qs = [f"{i}T{str(y)[2:]}" for i in range(1, 5 if y < 2026 else 3)]
    IDX[str(y)] = block(qs, lambda yy, r, y=y: yy == y, str(y))
IDX["LTM 2T26"] = block(["3T25", "4T25", "1T26", "2T26"], lambda yy, r: (yy == 2025 and r["tri"] in ("3T25", "4T25")) or yy == 2026, "LTM 2T26")
OUT["idx"] = IDX
json.dump(OUT, io.open(os.path.join(here, "_share_rm.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pc = lambda a, b: f"{100 * a / b:5.1f}%" if a is not None and b else "   — "
print("\nÍNDICE POR REGIÃO METROPOLITANA (lançadas 100% ÷ financiadas MCMV/FGTS no ano; Cury SP/RJ = estimativa pela contagem de empreendimentos)")
print(f"{'período':9}|{'Vivaz SP':>9}{'RJ':>7}{'outros':>7}{'P&P':>7}|{'peso RJ':>8}|{'RMSP':>7}{'RMRJ':>7}{'Brasil':>7}|| {'Cury':>7}{'SP est':>8}{'RJ est':>8}|{'peso RJ':>8}|{'RMSP':>7}{'RMRJ':>7}{'Brasil':>7}| proj SP/RJ")
for k, d in IDX.items():
    v, c, t = d["vivaz"], d["cury"], d["den"]
    print(f"{k:9}|{v['sp']:9,.0f}{v['rj']:7,.0f}{v['outros']:7,.0f}{v['pp']:7,.0f}|{pc(v['rj'], v['sp'] + v['rj']):>8}|{pc(v['sp'], t['rmsp']):>7}{pc(v['rj'], t['rmrj']):>7}{pc(v['total'], t['br']):>7}|| {c['total']:7,.0f}{(f'{c['sp']:8,.0f}' if c['sp'] is not None else '       —')}{(f'{c['rj']:8,.0f}' if c['rj'] is not None else '       —')}|{pc(c['rj'], c['total']):>8}|{pc(c['sp'], t['rmsp']):>7}{pc(c['rj'], t['rmrj']):>7}{pc(c['total'], t['br']):>7}| {c['nsp']}/{c['nrj']} de {c['n']}")
print("\nCRUZAMENTO GEOIMÓVEL (cidade de São Paulo, unidades lançadas por grupo): Cury capital ÷ total RI; RJ teto = total − capital; Vivaz capital ÷ SP do anexo")
print(f"{'período':9}|{'Cury tot':>9}{'SP cap':>8}{'% cap':>7}{'RJ teto':>8}{'RJ cont':>8}|{'teto/RMRJ':>10}{'cont/RMRJ':>10}|| {'Vivaz SP':>9}{'SP cap':>8}{'% cap':>7}")
for k, d in IDX.items():
    v, c, t = d["vivaz"], d["cury"], d["den"]
    print(f"{k:9}|{c['total']:9,.0f}{c['geo_sp']:8,.0f}{pc(c['geo_sp'], c['total']):>7}{c['rj_teto']:8,.0f}{(f'{c['rj']:8,.0f}' if c['rj'] is not None else '       —')}|{pc(c['rj_teto'], t['rmrj']):>10}{pc(c['rj'], t['rmrj']):>10}|| {v['sp']:9,.0f}{v['geo_sp']:8,.0f}{pc(v['geo_sp'], v['sp']):>7}")
print("\nVERSÃO EM VALOR: Vivaz VGV lançado (R$ mi, anexo, 100%) ÷ (valor financiado + subsídio MCMV/FGTS, R$ mi, MCid); ticket = VGV ÷ unidades (R$ mil)")
print(f"{'período':9}|{'VGV SP':>8}{'VGV RJ':>8}{'outros':>8}|{'peso RJ':>8}|{'tkt SP':>7}{'tkt RJ':>7}|{'fin+sub RMSP':>13}{'RMRJ':>9}|{'sh RMSP':>8}{'sh RMRJ':>8}{'Brasil':>8}")
for k, d in IDX.items():
    g, v, t = d["vivaz_vgv"], d["vivaz"], d["den"]
    print(f"{k:9}|{g['sp']:8,.0f}{g['rj']:8,.0f}{g['outros']:8,.0f}|{pc(g['rj'], g['sp'] + g['rj']):>8}|{(1000 * g['sp'] / v['sp'] if v['sp'] else 0):7,.0f}{(1000 * g['rj'] / v['rj'] if v['rj'] else 0):7,.0f}|{t['fin_rmsp'] + t['sub_rmsp']:13,.0f}{t['fin_rmrj'] + t['sub_rmrj']:9,.0f}|{pc(g['sp'], t['fin_rmsp'] + t['sub_rmsp']):>8}{pc(g['rj'], t['fin_rmrj'] + t['sub_rmrj']):>8}{pc(g['total'], t['fin_br'] + t['sub_br']):>8}")
print("Vivaz (anexos Cyrela, un. 100%, MCMV/CVA):")
print(f"{'ano':6}|{'SP':>7}|{'RJ':>7}|{'outros':>7}|{'total':>7}|{'RI ex-Cury/P&P':>15}|{'proj':>5}|{'s/un':>5}| JV ≤50%")
for y, d in VZ.items(): print(f"{y:6}|{d['sp']:7,.0f}|{d['rj']:7,.0f}|{d['outros']:7,.0f}|{d['total']:7,.0f}|{d['ri']:15,.0f}|{d['n']:5}|{d['n_semun']:5}| {'; '.join(d['jv'])[:150]}")
print("\nCury, empreendimentos por região (releases):", dict(sorted(CNT.items(), key=lambda kv: (kv[0][2:], kv[0][0]))))
print("\nDenominadores MCid (un. financiadas):"); print(f"{'per':9}|{'Brasil':>9}|{'estados':>9}|{'RMSP':>8}|{'RMRJ':>7}|{'capitais':>9}")
for y, t in OUT["den"].items(): print(f"{y:9}|{t['br']:9,}|{t['est']:9,}|{t['rmsp']:8,}|{t['rmrj']:7,}|{t['cap']:9,}")
