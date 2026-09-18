# -*- coding: utf-8 -*-
"""Estoque A CUSTO e sua composicao (nota 'IMOVEIS A COMERCIALIZAR' dos ITRs/DFPs).

Reaproveita os textos ja baixados por dados_receita_bruta_itr.py (<tmp>/itrdocs/*.txt),
que vem dos PDFs embutidos no XML do ENET. Nada e baixado de novo.

A nota traz, no CONSOLIDADO: imoveis em construcao, imoveis concluidos, terrenos para
futuras incorporacoes, adiantamento para aquisicao de terrenos, encargos capitalizados
ao estoque, provisao para distratos, total, e a quebra circulante/nao circulante.
Diferente da receita, estes sao SALDOS (nao precisam de diferenca entre trimestres).

Validacao dupla:
 (a) soma dos componentes = total da nota (tolerancia 1);
 (b) total = Estoques CP + LP do balanco (planilha de DFs do RI).
Saida: _estoque_custo.json {tri: {construcao, concluidos, terrenos, adiant_terrenos,
encargos, prov_distrato, total, circulante, nao_circulante}}
"""
import datetime
import glob
import io
import json
import os
import re
import sys

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
tmp = sys.argv[1] if len(sys.argv) > 1 else here
docs = os.path.join(tmp, "itrdocs")

# ---------- ancora: estoques do balanco (planilha do RI), R$ mi ----------
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True, data_only=True)
ws = wb["CYRELA"]
G = list(ws.iter_rows(min_row=1, max_row=40, values_only=True))
wb.close()
H = G[3]
bs = {}
for j in range(1, len(H)):
    if isinstance(H[j], datetime.datetime):
        cp, lp = G[14][j], G[24][j]          # Estoques (circulante) e Estoques LP
        if isinstance(cp, (int, float)) and isinstance(lp, (int, float)):
            d = H[j]
            bs[f"{(d.month-1)//3+1}T{d.year%100:02d}"] = (cp + lp) / 1000

ROTULOS = [
    ("construcao", r"Im[óo]veis em constru[çc][ãa]o"),
    ("concluidos", r"Im[óo]veis conclu[íi]dos"),
    ("terrenos", r"Terrenos para futuras incorpora[çc][õo]es"),
    ("adiant_terrenos", r"Adiantamento para aquisi[çc][ãa]o de terrenos"),
    ("encargos", r"Encargos capitalizados ao estoque"),
    ("prov_distrato", r"Provis[ãa]o para distratos"),
]
TOKEN = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})*\)?")


def numeros(linha):
    out = []
    for t in TOKEN.findall(linha):
        v = float(t.strip("()").replace(".", ""))
        out.append(-v if t.startswith("(") else v)
    return out


def extrai(txt, alvo_total):
    """No PDF das notas o texto sai em modo 'raw': os rotulos vem todos primeiro e
    os numeros depois, em bloco. Entao varremos o bloco procurando os 6 componentes
    com um passo constante (a tabela tem 2 ou 4 colunas: controladora/consolidado x
    periodo atual/anterior), aceitando so a combinacao cuja SOMA bate com o total de
    estoques do balanco (ancora independente, da planilha do RI)."""
    if not alvo_total:
        return None
    alvo = alvo_total * 1000
    # o titulo aparece varias vezes (sumario, remissoes no texto "conforme nota 6");
    # so uma delas e a tabela, entao testamos todas ate uma fechar com o balanco
    for m0 in re.finditer(r"IM[ÓO]VEIS A COMERCIALIZAR", txt, re.I):
        r = _tenta(txt[m0.start():m0.start() + 9000], alvo)
        if r:
            return r
    return None


def _tenta_exato(txt, alvo):
    """Como extrai(), mas exigindo casamento ao milhar - usado na busca cruzada
    entre documentos, onde o risco de falso positivo e muito maior."""
    for m0 in re.finditer(r"IM[ÓO]VEIS A COMERCIALIZAR", txt, re.I):
        r = _tenta(txt[m0.start():m0.start() + 9000], alvo, tol=1000)
        if r:
            return r
    return None


def _tenta(bloco, alvo, tol=None):
    fim = re.search(r"\(a\)\s*A classifica", bloco, re.I)
    if fim:
        bloco = bloco[:fim.start()]
    seq = numeros(bloco)
    melhor = None
    for passo in (1, 2, 3, 4, 5, 6):
        for i in range(len(seq) - 5 * passo):
            v = [seq[i + k * passo] for k in range(6)]
            if any(x < 0 for x in v):
                continue
            # sanidade de magnitude (R$ mil): a Cyrela nunca teve construcao < 300 mi,
            # terrenos < 500 mi nem pronto < 100 mi no periodo
            if v[0] < 300_000 or v[2] < 500_000 or v[1] < 100_000:
                continue
            # valores repetidos em sequencia denunciam passo errado (mesma celula lida
            # duas vezes) - foi o que contaminou 3T20 antes desta trava
            if len(set(v)) < 6:
                continue
            s = sum(v)
            # o total tem que bater praticamente exato com o balanco; folga so para
            # arredondamento (0,1%). Tolerancia frouxa gerava falso positivo.
            if abs(s - alvo) < (tol if tol is not None else max(500, 0.001 * alvo)):
                erro = abs(s - alvo)
                if melhor is None or erro < melhor[0]:
                    melhor = (erro, v, passo)
        if melhor:
            break
    if not melhor:
        return None
    _, v, passo = melhor
    d = {chave: round(v[k] / 1000, 1) for k, (chave, _) in enumerate(ROTULOS)}
    d["total"] = round(sum(v) / 1000, 1)
    d["passo"] = passo
    return d


ORD = lambda q: (int(q[2:]), int(q[0]))
arquivos = sorted(glob.glob(os.path.join(docs, "*.txt")))
textos = {os.path.basename(c).split("_")[0]: io.open(c, encoding="utf-8", errors="ignore").read()
          for c in arquivos}
out = {}
for tri, s in textos.items():
    if tri not in bs:
        continue
    r = extrai(s, bs[tri])
    if r:
        out[tri] = r

# Toda nota traz tambem a coluna do periodo anterior. Para o que faltou no proprio
# documento, procuramos nos demais - mas SO nos 26 trimestres alvo e exigindo que a
# soma bata com o balanco ao milhar (tolerancia frouxa aqui gera falso positivo:
# a primeira versao desta busca chegou a "achar" trimestres de 2010).
ALVOS = [f"{t}T{a:02d}" for a in range(20, 27) for t in range(1, 5)
         if not (a == 26 and t > 2)]
for tri in ALVOS:
    if tri in out or tri not in bs:
        continue
    for outro, s in sorted(textos.items()):
        if outro == tri:
            continue
        r = _tenta_exato(s, bs[tri] * 1000)
        if r:
            r["origem"] = outro
            out[tri] = r
            break

io.open(os.path.join(here, "_estoque_custo.json"), "w", encoding="utf-8").write(json.dumps(out))
print(f"{len(out)} trimestres com estoque a custo")
for q in sorted(out, key=ORD):
    v = out[q]
    print(f"  {q}: constr {v['construcao']:8.1f} | pronto {v['concluidos']:7.1f} | terrenos {v['terrenos']:8.1f} | "
          f"adiant {v['adiant_terrenos']:6.1f} | encargos {v['encargos']:6.1f} | distrato {v['prov_distrato']:7.1f} | "
          f"TOTAL {v['total']:8.1f} vs BS {bs[q]:8.1f}")
