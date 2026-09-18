# -*- coding: utf-8 -*-
"""Notas explicativas dos ITR/DFP consolidados (fontes/itr/<tri>.pdf, 1T20-2T26), via
pdftotext -layout: (a) contas a receber: receita apropriada, parcelas recebidas, AVP, em
construcao, concluidos, provisao p/ risco de credito, provisao p/ distrato, total;
(b) adiantamentos de clientes: permuta fisica, antecipacoes, total; (c) contas a pagar por
aquisicao de imoveis: cronograma 24/36/48/60/+60 meses; (d) provisoes para riscos: perda
provavel (civeis/tributarios/trabalhistas) e perda possivel (consolidado); (e) provisao para
garantia de obra. O -layout desalinha rotulo e numero em varias tabelas, entao a leitura e
POSICIONAL na coluna do consolidado corrente (3o de 4 tokens, 1o de 2), resolvida pelas
identidades contabeis da tabela. Saida: _notas_itr.json (R$ mi) com flag de validacao."""
import io, json, os, re, subprocess
here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "fontes", "itr")
TRIS = [f"{t}T{a:02d}" for a in range(20, 27) for t in (1, 2, 3, 4)][:26]
TOK = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})+\)?|\(?-?\d+\)?|(?<!\S)-(?!\S)")
def tokens(line):
    out = []
    for m in TOK.finditer(line):
        t = m.group(0)
        if t == "-": out.append(0.0); continue
        neg = t.startswith("("); v = float(t.strip("()").replace(".", "")); out.append(-v if neg else v)
    return out
def cons(line, three=None):
    """valor do consolidado corrente pela posicao dos tokens (so a parte da linha depois do rotulo)."""
    m = list(re.finditer(r"[A-Za-zÀ-ÿ]", line))
    part = line[m[-1].end():] if m else line
    tk = tokens(part)
    if not m and tk and 2010 <= tk[0] <= 2039 and len(tk) > 1: tk = tk[1:]  # linha de ano
    if len(tk) == 4: return tk[2]
    if len(tk) == 2: return tk[0]
    if len(tk) == 1: return tk[0]
    if len(tk) == 3 and three is not None: return tk[three]
    return None
def near(v, lst, tol=2.0): return any(abs(v - x) <= tol for x in lst)
def section(lines, start_pat, end_pat, max_lines=60):
    for i, l in enumerate(lines):
        if re.search(start_pat, l, re.I):
            for j in range(i + 1, min(i + max_lines, len(lines))):
                if re.search(end_pat, lines[j], re.I): return lines[i:j + 1]
            return lines[i:i + max_lines]
    return None
def num_lines(sec, skip_hdr=True):
    vals = []
    for l in sec:
        if re.search(r"\b(20\d\d|0[369]/20\d\d|12/20\d\d)\b", l) and not re.search(r"\d{1,3}\.\d{3}", l): continue  # linha de datas
        v = cons(l)
        if v is not None: vals.append(v)
    return vals
def parse_cr(lines):
    sec = section(lines, r"^\s*\d+\.\s*CONTAS A RECEBER", r"N[aã]o Circulante", 80)
    if not sec: return None
    V = [v for v in num_lines(sec[1:]) if abs(v) >= 1]
    if len(V) < 6: return {"_erro": "poucos numeros", "_seq": V}
    concl = V[0]; rec = max(V); parc = min(V); X0 = rec + parc
    cands = []  # (avp, X, derivado)
    for avp in [v for v in V if v < 0 and v != parc and abs(v) >= 500]:
        X = X0 + avp
        if near(X, V): cands.append((avp, X, False))
    for X in [v for v in V if 0 < v < X0 and X0 - v < 600000 and X0 - v > 1000]:  # avp nao lido: deriva
        cands.append((X - X0, X, True))
    for avp, X, avp_der in cands:
        Y = concl + X
        if not near(Y, V): continue
        iY = next(i for i, v in enumerate(V) if abs(v - Y) <= 2)
        after = V[iY + 1:]
        negs = [v for v in after if v < 0 and abs(v) >= 500]
        servs = [v for v in after if 0 < v < 100000] + [0.0]
        tots = [v for v in after if v > 100000]
        if len(negs) >= 2:
            pdd, dist = sorted(negs[:2], key=lambda z: -z)
            for serv in servs:
                tot = Y + pdd + dist + serv
                if near(tot, V, 3):
                    return {"concluidos": concl, "receita_apropriada": rec, "parcelas_recebidas": parc, "avp": avp, "em_construcao": X, "cr_vendas_apropriadas": Y, "pdd": pdd, "prov_distrato": dist, "servicos": serv, "total": tot, "_ok": True, "_derivado": "avp" if avp_der else ""}
        if len(negs) >= 1:  # distrato nao lido: deriva do total
            pdd = negs[0]
            for tot in tots:
                for serv in servs:
                    dist = tot - Y - pdd - serv
                    if -1200000 < dist < -50000:
                        return {"concluidos": concl, "receita_apropriada": rec, "parcelas_recebidas": parc, "avp": avp, "em_construcao": X, "cr_vendas_apropriadas": Y, "pdd": pdd, "prov_distrato": dist, "servicos": serv, "total": tot, "_ok": True, "_derivado": ("avp+" if avp_der else "") + "distrato"}
    return {"_erro": "identidades nao fecharam", "_seq": V}
def parse_adiant(lines):
    i0 = next((i for i, l in enumerate(lines) if re.search(r"ADIANTAMENTOS DE CLIENTES", l) and not re.search(r"\d{1,3}\.\d{3}", l)), None)
    if i0 is None: return None
    ip = next((i for i in range(i0, min(i0 + 80, len(lines))) if re.search(r"Valores por permuta", lines[i], re.I)), None)
    if ip is None: return {"_erro": "sem linha de permuta"}
    ie = next((i for i in range(ip, min(ip + 12, len(lines))) if re.search(r"N[aã]o Circulante", lines[i], re.I)), ip + 8)
    sec = lines[i0:ie + 1]
    V = [v for v in num_lines(sec[1:]) if abs(v) >= 1]
    if len(V) < 5: return {"_erro": "poucos numeros", "_seq": V}
    d = V[0]; rec = max(V); apr = min(V); sub = rec + apr
    for p in [v for v in V if v > 0 and v not in (rec,)]:
        tot = d + sub + p
        if near(tot, V, 3) and p != d:
            return {"antecipacoes": d, "receitas_apropriadas_acum": apr, "receitas_recebidas_acum": rec, "saldo_unidades_vendidas": sub, "permuta_fisica": p, "total": tot, "_ok": True}
    return {"_erro": "identidades nao fecharam", "_seq": V}
def parse_terrenos(lines):
    i0 = next((i for i, l in enumerate(lines) if re.search(r"CONTAS A PAGAR POR AQUISI[CÇ][AÃ]O DE IM[OÓ]VEIS", l, re.I) and not re.search(r"\d{1,3}\.\d{3}", l)), None)
    if i0 is None: return None
    win = lines[i0:i0 + 60]
    im = [i for i, l in enumerate(win) if re.match(r"\s*(12|24|36|48|60)\s*meses|\s*(Acima de|>)\s*(48|60)|\s*20[2-3]\d", l, re.I)]
    if not im: return {"_erro": "sem cronograma"}
    sec = win[im[0]:im[-1] + 6]
    out = {}
    for l in sec:
        m = re.match(r"\s*(12|24|36|48|60)\s*meses", l, re.I); my = re.match(r"\s*(20[2-3]\d)", l)
        if m: out[f"m{m.group(1)}"] = cons(l)
        elif re.match(r"\s*(Acima de|>)\s*(48|60)", l, re.I): out["m_alem"] = cons(l)
        elif my and not m: out[f"a{my.group(1)}"] = cons(l)
        elif re.match(r"\s*Total\b", l): out["total"] = cons(l)
        elif re.match(r"\s*Circulante", l): out["circulante"] = cons(l)
        elif re.match(r"\s*N[aã]o Circulante", l): out["nao_circulante"] = cons(l)
    bk = [k for k in out if k[0] in "ma" and k not in ("total",) and not k.startswith("_")]
    if bk:
        out["soma_baldes"] = sum(out[k] or 0 for k in bk)
        out["_ok"] = True if out.get("total") is None else abs(out["soma_baldes"] - out["total"]) <= 3 or abs(out["soma_baldes"] + (out.get("circulante") or 0) - out["total"]) <= 3
    return out
def parse_prov(lines):
    out = {}
    sec = None
    i0 = next((i for i, l in enumerate(lines) if re.search(r"PROVIS[OÕ]ES PARA RISCOS", l) and not re.search(r"\d{1,3}\.\d{3}", l)), None)
    if i0 is not None:
        ic = next((i for i in range(i0, min(i0 + 80, len(lines))) if re.match(r"\s*Processos C[ií]veis", lines[i])), None)
        if ic is not None:
            ie = next((i for i in range(ic, min(ic + 14, len(lines))) if re.search(r"N[aã]o Circulante", lines[i], re.I)), ic + 10)
            sec = lines[ic:ie + 1]
    if sec:
        for l in sec:
            if re.match(r"\s*Processos C[ií]veis", l): out["provavel_civeis"] = cons(l, 2)
            elif re.match(r"\s*Processos Tribut", l): out["provavel_tributarios"] = cons(l, 2)
            elif re.match(r"\s*Processos Trabalh", l): out["provavel_trabalhistas"] = cons(l, 2)
            elif re.match(r"\s*Total\b", l): out["provavel_total"] = cons(l)
        # perda possivel: blocos 'Civel / Tributario / Trabalhista' (2 tokens); ultimo bloco = consolidado
        i0 = lines.index(sec[0]); blocos = []; cur = {}  # perda possivel vem depois da tabela de provavel
        for l in lines[i0:i0 + 120]:
            if re.match(r"\s*C[ií]vel\b", l): cur = {"civel": cons(l)}
            elif re.match(r"\s*Tribut[aá]rio\b", l) and cur: cur["tributario"] = cons(l)
            elif re.match(r"\s*Trabalhista\b", l) and cur: cur["trabalhista"] = cons(l); blocos.append(cur); cur = {}
        if blocos: b = blocos[-1]; out["possivel_civel"] = b.get("civel"); out["possivel_tributario"] = b.get("tributario"); out["possivel_trabalhista"] = b.get("trabalhista")
        circ = ncirc = None
        for l in sec:
            if re.match(r"\s*Circulante", l): circ = cons(l, 2)
            elif re.match(r"\s*N[aã]o Circulante", l): ncirc = cons(l, 2)
        soma = sum(out.get(k) or 0 for k in ("provavel_civeis", "provavel_tributarios", "provavel_trabalhistas"))
        out["provavel_total"] = soma
        out["_ok"] = (circ is not None and ncirc is not None and abs(circ + ncirc - soma) <= 3) or (out.get("provavel_total") and all(out.get(k) for k in ("provavel_civeis", "provavel_tributarios", "provavel_trabalhistas")))
    for l in lines:
        if re.search(r"Provis[aã]o para garantia de obra", l, re.I): out["garantia_obra"] = cons(l); break
    return out
out = {}
for q in TRIS:
    pdf = os.path.join(D, f"{q}.pdf"); txt = os.path.join(D, f"{q}.lay.txt")
    if not os.path.exists(pdf): out[q] = {"_erro": "sem pdf"}; continue
    if not os.path.exists(txt): subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", pdf, txt], capture_output=True)
    lines = io.open(txt, encoding="utf-8", errors="ignore").read().splitlines()
    rec = {"cr": parse_cr(lines), "adiant": parse_adiant(lines), "terrenos": parse_terrenos(lines), "prov": parse_prov(lines)}
    for k, v in rec.items():  # R$ mil -> mi
        if isinstance(v, dict):
            for kk, vv in list(v.items()):
                if isinstance(vv, (int, float)) and not kk.startswith("_"): v[kk] = round(vv / 1000, 3)
                elif kk == "_seq": v[kk] = [round(x / 1000, 1) for x in vv]
    out[q] = rec
    def f(x): return "ok" if isinstance(x, dict) and x.get("_ok") else ("None" if x is None else ("ERR " + str(x.get("_erro", "")) + " " + str(x.get("_seq", ""))[:80]))
    print(q, "| cr", f(rec["cr"]), "| adiant", f(rec["adiant"]), "| terr", f(rec["terrenos"]), "| prov", f(rec["prov"]), "| gar", (rec["prov"] or {}).get("garantia_obra"))
json.dump(out, io.open(os.path.join(here, "_notas_itr.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
