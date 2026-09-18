# -*- coding: utf-8 -*-
"""Geração/consumo de caixa trimestral segundo os releases (definição da companhia: variação da dívida líquida ajustada,
excluindo recompra de ações e compra/venda de participações; dividendos excluídos desde 2017).
2020-2T26: tabela 'Geração/Consumo de Caixa' já parseada (_ger_caixa_release_clean.json, chave 'ger').
2011-2019: primeira menção na prosa do release ('geração/consumo de caixa de R$ X milhões' ou 'R$ X milhões de geração de caixa'),
que abre o texto com o trimestre corrente; conferido pelas somas semestrais/anuais (6M14 = 318; 2015 = 813).
Saída: _ger_caixa_hist.json {tri: valor R$ mi (consumo negativo)}."""
import io, json, os, re, glob
here = os.path.dirname(os.path.abspath(__file__))
def ord_(q): return (int(q[2:]), int(q[0]))
def num(s): return float(s.replace(".", "").replace(",", "."))
out = {}
for fp in sorted(glob.glob(os.path.join(here, "fontes", "release_?T??.txt")), key=lambda f: ord_(os.path.basename(f)[8:12])):
    q = os.path.basename(fp)[8:12]
    if not ((11, 1) <= ord_(q) <= (19, 4)): continue
    t = re.sub(r"\s+", " ", io.open(fp, encoding="utf-8", errors="ignore").read())
    m = re.search(r"(gera[çc][ãa]o|consumo) de caixa(?: operacional)?(?: positiva| negativa)? de R\$ ?([\d\.]+) (?:milh[õo]es|mm)", t, re.I)
    m2 = re.search(r"R\$ ?([\d\.]+) milh[õo]es de (gera[çc][ãa]o|consumo) de caixa", t, re.I)
    cand = []
    # prioridade: menção explícita ao trimestre ("no trimestre" / "no 4T15"); senão, a primeira menção do texto
    mt = re.search(r"(gera[çc][ãa]o|consumo) de caixa(?: operacional)?(?: positiva| negativa)? de R\$ ?([\d\.]+) milh[õo]es no (?:trimestre|" + q + ")", t, re.I)
    if mt: cand.append((-1, mt.group(1).lower(), mt.group(2)))
    if m: cand.append((m.start(), m.group(1).lower(), m.group(2)))
    if m2: cand.append((m2.start(), m2.group(2).lower(), m2.group(1)))
    if not cand: out[q] = None; continue
    pos, kind, val = min(cand)
    v = num(val); out[q] = -v if kind.startswith("consumo") else v
G = json.load(io.open(os.path.join(here, "_ger_caixa_release_clean.json"), encoding="utf-8"))["oper"]   # operacional: sem recompra e sem compra/venda de participação, como a definição antiga
for q, v in G.items(): out[q] = v
out = {q: out[q] for q in sorted(out, key=ord_)}
json.dump({"_meta": {"fonte": "releases da Cyrela: 2011-19 prosa (primeira menção do trimestre), 2020-2T26 tabela Geração/Consumo de Caixa; R$ mi; consumo negativo; definição da companhia (exclui recompra e participações; dividendos desde 2017)"}, "tri": out},
          io.open(os.path.join(here, "_ger_caixa_hist.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print({q: v for q, v in out.items()})
