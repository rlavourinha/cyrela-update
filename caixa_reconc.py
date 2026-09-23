# -*- coding: utf-8 -*-
"""Reconciliação de caixa da Cyrela, de baixo para cima (pedido de 23/09/26): lucro bruto − Δ contas a receber − Δ estoque ex-terrenos
− caixa de terrenos (Δ terrenos a custo − Δ terrenos a pagar) + Δ adiantamentos de clientes (permuta) − SG&A − impostos correntes
+ resultado financeiro + outras receitas/despesas + dividendos recebidos de JVs = caixa operacional reconciliado; comparado com
(a) a 'geração de caixa operacional' que a companhia publica (release, ex-participações, ex-dividendos e recompra) e (b) a variação da
dívida líquida do balanço. 'Outros' = diferença. Fontes: planilha de DFs do RI (Economatica, _econ_trimestral.json: DRE, BS, DFC
trimestrais), notas de estoque dos ITR (_estoque_custo.json), balanço CVM (_balanco_cvm.json: terrenos a pagar, adiantamentos,
dívida e caixa), releases (_ger_caixa_release_clean.json). R$ mi. Saída: _caixa_reconc.json e tabela impressa."""
import io, json, os
here = os.path.dirname(os.path.abspath(__file__))
def J(n): return json.load(io.open(os.path.join(here, n), encoding="utf-8"))
E = J("_econ_trimestral.json"); EC = J("_estoque_custo.json"); B = J("_balanco_cvm.json"); G = J("_ger_caixa_release_clean.json")
ORD = lambda q: (int(q[2:]), int(q[0]))
def dl(q):   # dívida líquida do balanço CVM
    b = B[q]; return sum(b.get(k) or 0 for k in ("emp_cp", "deb_cp", "cri_cp", "emp_lp", "deb_lp", "cri_lp")) - sum(b.get(k) or 0 for k in ("caixa", "aplic_cp_vjr", "aplic_cp_vjora", "aplic_cp_ca", "aplic_lp_vjr", "aplic_lp_vjora", "aplic_lp_ca"))
def terr_pagar(q): b = B[q]; return (b.get("terr_cp") or 0) + (b.get("terr_lp") or 0)
def adiant(q): b = B[q]; return (b.get("adiant_cp") or 0) + (b.get("adiant_lp") or 0)
def cr(q): return (E[q]["cr_cp"] or 0) + (E[q]["cr_lp"] or 0)
def est_ex(q): e = EC[q]; return e["construcao"] + e["concluidos"] + e["encargos"]
def terr(q): e = EC[q]; return e["terrenos"] + e["adiant_terrenos"]
def flow(qs, k): return sum((E[q][k] or 0) for q in qs)
def bloco(q0, qs):
    r = {}
    r["receita"] = flow(qs, "rec"); r["cpv"] = -flow(qs, "cpv"); r["lucro_bruto"] = r["receita"] + r["cpv"]
    r["d_cr"] = -(cr(qs[-1]) - cr(q0)); r["d_est_ex"] = -(est_ex(qs[-1]) - est_ex(q0))
    r["terrenos"] = -((terr(qs[-1]) - terr(q0)) - (terr_pagar(qs[-1]) - terr_pagar(q0)))
    r["d_adiant"] = adiant(qs[-1]) - adiant(q0)
    r["sga"] = -(flow(qs, "vendas") + flow(qs, "adm")); r["impostos"] = -flow(qs, "ir_corr"); r["fin"] = flow(qs, "fin")
    r["outras_dre"] = flow(qs, "outras_rec") - flow(qs, "outras_desp"); r["div_jv"] = flow(qs, "dfc_divrec")
    r["caixa_rec"] = sum(r[k] for k in ("lucro_bruto", "d_cr", "d_est_ex", "terrenos", "d_adiant", "sga", "impostos", "fin", "outras_dre", "div_jv"))
    r["cia_oper"] = sum(G["oper"].get(q, 0) for q in qs); r["cia_ger"] = sum(G["ger"].get(q, 0) for q in qs); r["part"] = sum(-G["part"].get(q, 0) for q in qs)
    r["d_dl"] = -(dl(qs[-1]) - dl(q0)); r["div_pagos"] = flow(qs, "dfc_divpag"); r["dfc_oper"] = flow(qs, "dfc_oper"); r["ll"] = flow(qs, "ll"); r["equiv"] = flow(qs, "equiv")
    r["outros"] = r["cia_oper"] - r["caixa_rec"]
    return r
Q = sorted([q for q in E if q in EC and q in B and E[q]["rec"]], key=ORD)
PER = {}
for a in range(2021, 2026):
    qs = [f"{i}T{str(a)[2:]}" for i in range(1, 5)]; q0 = f"4T{str(a - 1)[2:]}"
    if all(q in Q for q in qs) and q0 in Q: PER[str(a)] = bloco(q0, qs)
L4 = Q[-4:]; PER["LTM " + L4[-1]] = bloco(Q[-5], L4)
LAB = [("receita", "receita líquida"), ("cpv", "(−) custo dos imóveis vendidos (com terreno e juros capitalizados)"), ("lucro_bruto", "= lucro bruto"), ("d_cr", "(−) Δ contas a receber (balanço, líquido)"), ("d_est_ex", "(−) Δ estoque a custo ex-terrenos (obra, pronto, encargos)"),
       ("terrenos", "(−) terrenos: Δ terrenos a custo − Δ terrenos a pagar"), ("d_adiant", "(+) Δ adiantamentos de clientes (permuta física)"), ("sga", "(−) despesas comerciais e administrativas"), ("impostos", "(−) IR/CS corrente (DRE)"), ("fin", "(+) resultado financeiro (DRE)"),
       ("outras_dre", "(+) outras receitas/despesas (DRE)"), ("div_jv", "(+) dividendos recebidos de JVs (DFC)"), ("caixa_rec", "= caixa operacional reconciliado (nosso)"), ("cia_oper", "geração de caixa operacional da companhia (release)"), ("outros", "outros = companhia − reconciliado"),
       ("cia_ger", "memo: geração de caixa total do release (com participações)"), ("part", "memo: caixa de venda de participações"), ("d_dl", "memo: −Δ dívida líquida do balanço (CVM)"), ("div_pagos", "memo: dividendos pagos (DFC)"), ("dfc_oper", "memo: caixa das operações (DFC)"), ("ll", "memo: lucro líquido"), ("equiv", "memo: equivalência (não caixa)")]
cols = list(PER); print("R$ mi".ljust(66) + "".join(c.rjust(11) for c in cols))
for k, lab in LAB: print(lab[:66].ljust(66) + "".join(f"{PER[c][k]:11,.0f}" for c in cols))
json.dump(PER, io.open(os.path.join(here, "_caixa_reconc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
