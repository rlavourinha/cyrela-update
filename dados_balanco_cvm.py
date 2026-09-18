# -*- coding: utf-8 -*-
"""Balanco consolidado ABERTO da Cyrela pelos dados estruturados da CVM (BPA/BPP _con):
ITR (1T-3T) 2011-2026 e DFP (4T) 2010-2025, ultima versao de cada documento, exercicio
'ULTIMO'. Mapeia as contas-folha para ~40 rubricas analiticas por DESCRICAO (os codigos
mudam de ano para ano) e valida: soma das rubricas de cada secao = total da secao (AC,
ANC, PC, PNC). Tambem o 4T12 reapresentado (DFP 2013, exercicio 'PENULTIMO').
Saida: _balanco_cvm.json {tri: {rubrica: valor R$ mi}}, mais chave '4T12R'."""
import csv, glob, io, json, os, re, unicodedata, zipfile
here = os.path.dirname(os.path.abspath(__file__))
S = r"C:\Users\RLAVOU~1\AppData\Local\Temp\claude\D--rlavourinha-Pictures-OneDrive--rea-de-Trabalho-Claude\e4e1cc5f-6e04-4e22-ba8b-ce88f93cdefb\scratchpad"
def norm(s): return re.sub(r"\s+", " ", "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()).strip()
def load(tipo, ano):
    z = os.path.join(S, f"{tipo}_cia_aberta_{ano}.zip")
    if not os.path.exists(z): return {}
    out = {}
    with zipfile.ZipFile(z) as zf:
        for doc in ("BPA", "BPP"):
            n = f"{tipo}_cia_aberta_{doc}_con_{ano}.csv"
            if n not in zf.namelist(): continue
            for r in csv.DictReader(io.TextIOWrapper(zf.open(n), encoding="latin-1"), delimiter=";"):
                if "CYRELA BRAZIL" not in r["DENOM_CIA"]: continue
                key = (r["DT_REFER"][:10], r["ORDEM_EXERC"][:2], int(r["VERSAO"]))
                out.setdefault(key, {})[r["CD_CONTA"]] = (norm(r["DS_CONTA"]), float(r["VL_CONTA"]) / (1000.0 if r.get("ESCALA_MOEDA", "MIL") == "MIL" else 1.0))
    return out
docs = {}
for a in range(2010, 2027):
    for tipo in ("itr", "dfp"):
        for (dt, ordem, ver), contas in load(tipo, a).items():
            k = (dt, ordem)
            if k not in docs or ver > docs[k][0]: docs[k] = (ver, contas, tipo, a)
def tri_of(dt):
    y, m = int(dt[:4]), int(dt[5:7]); return f"{(m-1)//3+1}T{y%100:02d}"
def classify(contas):
    """contas: {codigo: (desc_norm, valor)} -> {rubrica: valor} + residuos por secao."""
    R = {}
    def add(k, v): R[k] = R.get(k, 0.0) + v
    def kids(code):  # filhos diretos
        return sorted(c for c in contas if c.startswith(code + ".") and c.count(".") == code.count(".") + 1)
    def leaves_under(code):
        ks = kids(code)
        if not ks: return [code]
        # filhos existem mas nao somam o pai (ex.: sub-contas zeradas com valor so no pai): pai e a folha
        if abs(sum(contas[k][1] for k in ks) - contas[code][1]) > 0.5: return [code]
        out = []
        for k in ks: out += leaves_under(k)
        return out
    def val(c): return contas[c][1] if c in contas else 0.0
    def d(c): return contas[c][0] if c in contas else ""
    # ---------- ATIVO CIRCULANTE ----------
    for c in kids("1.01"):
        s = d(c); v = val(c)
        if "caixa" in s: add("caixa", v)
        elif "aplicacoes financeiras" in s:
            for k in kids(c):
                t = d(k)
                if "outros resultados abrangentes" in t: add("aplic_cp_vjora", val(k))
                elif "custo amortizado" in t: add("aplic_cp_ca", val(k))
                else: add("aplic_cp_vjr", val(k))
            if not kids(c): add("aplic_cp_vjr", v)
        elif "contas a receber" in s:
            for k in kids(c):
                t = d(k)
                if "clientes" in t: add("cr_cp_clientes", val(k))
                else:
                    for l in leaves_under(k):
                        u = d(l); w = val(l)
                        if "parceiros" in u: add("cc_parc_ativo", w)
                        elif "vendas a apropriar" in u: add("dva", w)
                        elif "diferid" in u: add("imp_dif_ativo", w)
                        elif "compensar" in u: add("imp_comp", w)
                        else: add("demais_ativo", w)
            if not kids(c): add("cr_cp_clientes", v)
        elif "estoques" in s: add("est_cp", v)
        elif "tributos a recuperar" in s: add("imp_comp", v)
        elif "despesas antecipadas" in s: add("desp_ant", v)
        elif "biologic" in s: add("demais_ativo", v)
        else:  # outros ativos circulantes
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "vendas a apropriar" in u or "venda a apropriar" in u: add("dva", w)
                elif "recolhimento diferid" in u or "diferid" in u: add("imp_dif_ativo", w)
                elif "derivativ" in u: add("deriv_ativo", w)
                elif "parceiros" in u: add("cc_parc_ativo", w)
                elif "compensar" in u: add("imp_comp", w)
                else: add("demais_ativo", w)
    # ---------- REALIZAVEL LP ----------
    for c in kids("1.02.01"):
        s = d(c); v = val(c)
        if "aplicac" in s:
            if "outros resultados abrangentes" in s: add("aplic_lp_vjora", v)
            elif "custo amortizado" in s: add("aplic_lp_ca", v)
            else: add("aplic_lp_vjr", v)
        elif "contas a receber" in s:
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "parceiros" in u: add("cc_parc_ativo", w)
                elif "clientes" in u or l == c: add("cr_lp_clientes", w)
                else: add("cr_lp_outras", w)
        elif "estoques" in s: add("est_lp", v)
        elif "tributos diferidos" in s: add("ir_dif_ativo", v)
        elif "despesas antecipadas" in s: add("desp_ant_lp", v)
        elif "partes relacionadas" in s:
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "controlador" in u: add("prel_ativo_controladores", w)
                else: add("prel_ativo_coligadas", w)
        elif "biologic" in s: add("demais_ativo_lp", v)
        else:  # outros ativos nao circulantes
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "parceiros" in u: add("cc_parc_ativo", w)
                elif "vendas a apropriar" in u: add("dva", w)
                elif "compensar" in u: add("imp_comp", w)
                elif "diferid" in u: add("imp_dif_ativo", w)
                elif "derivativ" in u: add("deriv_ativo", w)
                else: add("demais_ativo_lp", w)
    add("investimentos", val("1.02.02")); add("imobilizado", val("1.02.03")); add("intangivel", val("1.02.04"))
    for c in kids("1.02"):
        if c not in ("1.02.01", "1.02.02", "1.02.03", "1.02.04"): add("demais_ativo_lp", val(c))
    # ---------- PASSIVO CIRCULANTE ----------
    for c in kids("2.01"):
        s = d(c); v = val(c)
        if "provis" in s:
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "civ" in u: add("prov_civeis", w)
                elif "trabalh" in u or "previd" in u: add("prov_trab", w)
                elif "fisc" in u or "tribut" in u: add("prov_fiscais", w)
                elif "garantia" in u: add("prov_garantias", w)
                elif "aquisicao de imoveis" in u: add("terr_cp", w)
                elif "adiantamento" in u: add("adiant_cp", w)
                elif "fornecedores" in u: add("fornecedores", w)
                else: add("prov_outras", w)
        elif "sociais" in s or ("trabalhistas" in s and "provis" not in s): add("obrig_sociais", v)
        elif "fornecedores" in s: add("fornecedores", v)
        elif "fiscais" in s:
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "diferid" in u: add("imp_dif_passivo", w)
                elif "imposto de renda" in u: add("imp_recolher", w)
                else: add("imp_recolher", w)
        elif "emprestimos" in s:
            for k in kids(c):
                t = d(k)
                if "debentures" in t:
                    for l in leaves_under(k):
                        u = d(l); w = val(l)
                        if "certificados" in u or "cri" == u.strip() or "recebiveis imobiliarios" in u: add("cri_cp", w)
                        else: add("deb_cp", w)
                    if not kids(k): add("deb_cp", val(k))
                else: add("emp_cp", val(k))
            if not kids(c): add("emp_cp", v)
        elif "outras obrigacoes" in s:
            for k in kids(c):
                t = d(k)
                if "partes relacionadas" in t: add("prel_passivo", val(k))
                else:
                    for l in leaves_under(k):
                        u = d(l); w = val(l)
                        if "dividendo" in u or "jcp" in u: add("dividendos_pagar", w)
                        elif "parceiros" in u: add("cc_parc_passivo", w)
                        elif "adiantamento" in u: add("adiant_cp", w)
                        elif "aquisicao de imoveis" in u: add("terr_cp", w)
                        else: add("demais_passivo", w)
            if not kids(c): add("demais_passivo", v)
        elif "provis" in s:
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "civ" in u: add("prov_civeis", w)
                elif "trabalh" in u or "previd" in u: add("prov_trab", w)
                elif "fisc" in u or "tribut" in u: add("prov_fiscais", w)
                elif "garantia" in u: add("prov_garantias", w)
                elif "aquisicao de imoveis" in u: add("terr_cp", w)
                elif "adiantamento" in u: add("adiant_cp", w)
                elif "fornecedores" in u: add("fornecedores", w)
                else: add("prov_outras", w)
        else: add("demais_passivo", v)
    # ---------- PASSIVO NAO CIRCULANTE ----------
    for c in kids("2.02"):
        s = d(c); v = val(c)
        if "emprestimos" in s:
            for k in kids(c):
                t = d(k)
                if "debentures" in t:
                    for l in leaves_under(k):
                        u = d(l); w = val(l)
                        if "certificados" in u or "recebiveis imobiliarios" in u: add("cri_lp", w)
                        else: add("deb_lp", w)
                    if not kids(k): add("deb_lp", val(k))
                else: add("emp_lp", val(k))
            if not kids(c): add("emp_lp", v)
        elif "outras obrigacoes" in s:
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "partes relacionadas" in u or "coligadas" in u or "controlador" in u: add("prel_passivo_lp", w)
                elif "adiantamento" in u and "cliente" in u: add("adiant_lp", w)
                elif "aquisicao de imoveis" in u: add("terr_lp", w)
                else: add("demais_passivo_lp", w)
        elif "tributos diferidos" in s: add("ir_dif_passivo", v)
        elif "provis" in s:
            for l in leaves_under(c):
                u = d(l); w = val(l)
                if "civ" in u: add("prov_civeis", w)
                elif "trabalh" in u or "previd" in u: add("prov_trab", w)
                elif "fisc" in u and "provis" in u or "tribut" in u: add("prov_fiscais", w)
                elif "garantia" in u: add("prov_garantias", w)
                elif "aquisicao de imoveis" in u: add("terr_lp", w)
                elif "fornecedores" in u: add("fornecedores_lp", w)
                elif "adiantamento" in u: add("adiant_lp", w)
                elif "pis e cofins" in u or "diferid" in u: add("imp_dif_passivo", w)
                elif "recolher" in u: add("imp_recolher", w)
                else: add("prov_outras", w)
        else: add("demais_passivo_lp", v)
    # ---------- PL ----------
    add("pl_consolidado", val("2.03"))
    for c in kids("2.03"):
        s = d(c); v = val(c)
        if "nao controladores" in s: add("minoritarios", v)
        elif "outros resultados abrangentes" in s: add("ora", v)
        elif "reservas de lucros" in s:
            for l in leaves_under(c):
                if "tesouraria" in d(l): add("acoes_tesouraria", val(l))
        elif "reservas de capital" in s:
            for l in leaves_under(c):
                if "tesouraria" in d(l): add("acoes_tesouraria", val(l))
    # ---------- totais e residuos ----------
    T = {"AC": val("1.01"), "ANC": val("1.02"), "PC": val("2.01"), "PNC": val("2.02"), "ATIVO": val("1"), "PASSIVO": val("2")}
    AC_keys = ["caixa", "aplic_cp_vjr", "aplic_cp_vjora", "aplic_cp_ca", "cr_cp_clientes", "est_cp", "desp_ant"]
    LP_keys = ["aplic_lp_vjr", "aplic_lp_vjora", "aplic_lp_ca", "cr_lp_clientes", "cr_lp_outras", "est_lp", "ir_dif_ativo", "desp_ant_lp", "prel_ativo_controladores", "prel_ativo_coligadas", "demais_ativo_lp", "investimentos", "imobilizado", "intangivel"]
    shared_ativo = ["cc_parc_ativo", "dva", "imp_dif_ativo", "imp_comp", "deriv_ativo", "demais_ativo"]  # CP+LP misturados
    PC_keys = ["obrig_sociais", "fornecedores", "imp_dif_passivo", "imp_recolher", "emp_cp", "deb_cp", "cri_cp", "prel_passivo", "dividendos_pagar", "cc_parc_passivo", "adiant_cp", "terr_cp", "demais_passivo"]
    PNC_keys = ["emp_lp", "deb_lp", "cri_lp", "prel_passivo_lp", "adiant_lp", "terr_lp", "demais_passivo_lp", "ir_dif_passivo", "fornecedores_lp"]
    prov = ["prov_civeis", "prov_trab", "prov_fiscais", "prov_garantias", "prov_outras"]  # CP+LP misturados
    soma_ativo = sum(R.get(k, 0) for k in AC_keys + LP_keys + shared_ativo)
    soma_passivo = sum(R.get(k, 0) for k in PC_keys + PNC_keys + prov)
    R["_res_ativo"] = round(T["ATIVO"] - soma_ativo, 1); R["_res_passivo"] = round(T["PC"] + T["PNC"] - soma_passivo, 1)
    R["ativo_total"] = T["ATIVO"]; R["ac_total"] = T["AC"]; R["anc_total"] = T["ANC"]; R["pc_total"] = T["PC"]; R["pnc_total"] = T["PNC"]
    return {k: round(v, 3) for k, v in R.items()}
out = {}
for (dt, ordem), (ver, contas, tipo, ano) in sorted(docs.items()):
    if ordem.startswith("ÚL") or ordem.startswith("UL") or ordem.startswith("\xdaL"):
        q = tri_of(dt)
        if q in out and tipo == "itr": continue  # DFP prevalece no 4T
        out[q] = classify(contas); out[q]["_doc"] = f"{tipo} {ano} v{ver}"
    elif dt == "2013-12-31" and ordem.startswith("PE"):
        out["4T12R"] = classify(contas); out["4T12R"]["_doc"] = f"dfp 2013 penultimo v{ver}"
json.dump(out, io.open(os.path.join(here, "_balanco_cvm.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ORD = lambda q: (99, 0) if q == "4T12R" else (int(q[2:]), int(q[0]))
for q in sorted(out, key=ORD):
    r = out[q]; print(q, r["_doc"], "| ativo", round(r["ativo_total"]), "res_ativo", r["_res_ativo"], "res_passivo", r["_res_passivo"], "| VJORA cp+lp", round(r.get("aplic_cp_vjora", 0) + r.get("aplic_lp_vjora", 0)), "| prel ativo", round(r.get("prel_ativo_controladores", 0) + r.get("prel_ativo_coligadas", 0)), "cc parc", round(r.get("cc_parc_ativo", 0)), "| civ", round(r.get("prov_civeis", 0)), "gar", round(r.get("prov_garantias", 0)), "| imp dif pass", round(r.get("imp_dif_passivo", 0)))
