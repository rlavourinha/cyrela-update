# -*- coding: utf-8 -*-
"""
dados_desp_gea.py -- Despesas Gerais e Administrativas (G&A) por natureza, Cyrela.

Fonte
-----
Secao "DESPESAS GERAIS E ADMINISTRATIVAS" dos releases trimestrais da Cyrela
(fontes/release_<T><AA>.pdf), 1T20 ate 2T26.

Por que ler o PDF e nao o .txt
------------------------------
Nos releases de 1T20 a 4T22 o `pdftotext -layout` embaralha a tabela: os rotulos
saem numa coluna de texto e os numeros noutra, com deslocamento vertical de 1-2
linhas (ex.: em release_1T21.txt a linha "Honorarios da Administracao" aparece
com os numeros de "Salarios e Encargos Sociais"). Reconstruir isso por heuristica
de offset e fragil e ja produziu erro de alinhamento.

A extracao aqui e feita direto do PDF com pdfplumber, usando as COORDENADAS dos
caracteres:
  1. acha a pagina da secao (texto normalizado contem "geraiseadministrativas"
     + "honorarios"/"encargos", e nao e o Anexo II - DRE);
  2. agrupa caracteres em linhas por `top` (tolerancia 2 pt);
  3. dentro da linha, agrupa caracteres em CELULAS por salto horizontal > 8 pt
     (caracteres de espaco sao descartados antes, porque em algumas paginas o PDF
     usa espacos reais e noutras so posicionamento);
  4. a 1a celula e o rotulo, as demais sao as colunas da tabela.
Isso funciona identico para o layout antigo (1T20-4T22) e o novo (1T23-2T26).

De onde vem cada campo
----------------------
Da tabela "Despesas Gerais e Administrativas" da propria secao. O layout de
colunas e:
    <Rotulo> <tri corrente> <tri anterior> <var%> <mesmo tri ano anterior> <var%>
             [<acum ano> <acum ano anterior> <var%>]
=> o PRIMEIRO numero apos o rotulo e sempre o TRIMESTRE CORRENTE, que e o unico
   valor que este parser guarda (as demais colunas sao comparativos e, a partir
   do 3T20/1T24, vem "pro forma" reapresentados - ver Ressalvas).

Campos (R$ milhoes, como reportado - inteiros):
  salarios_encargos               <- "Salarios e Encargos Sociais"
  honorarios_administracao        <- "Honorarios da Administracao"
  participacao_empregados         <- "Participacao dos Empregados"
  stock_options                   <- "Stock Options"          (so ate 3T21)
  servicos_terceiros              <- "Servicos de Terceiros"
  aluguel_viagens_representacoes  <- "Aluguel, viagens e representacoes"
                                     (a partir do 3T25 grafado "Aluguel, Viagens
                                      e Representacoes" - mesma linha)
  indenizacoes                    <- "Indenizacoes"            (so ate 4T23)
  outros                          <- "Outros"
  total                           <- "Total" da propria tabela
  soma_componentes                <- soma dos 8 itens acima (calculado)
  total_texto                     <- numero da frase "As despesas gerais e
                                     administrativas do trimestre atingiram
                                     R$ X milhoes" (checagem independente)
  total_destaques                 <- linha "Despesas Gerais e Administrativas
                                     (R$ milhoes)" do quadro de destaques
                                     (so existe a partir do 3T23; null antes)
  ga_cashme                       <- frase "O G&A da CashMe totalizou R$ X
                                     milhoes no trimestre" (so a partir do 1T22;
                                     informativo, JA ESTA DENTRO do total)
  pagina_pdf                      <- pagina 0-indexada de onde saiu a tabela

Validacao
---------
Para cada trimestre:
  - |soma_componentes - total| <= 1  (tolerancia de arredondamento; a tabela e
    publicada em R$ MM inteiros, entao 8 itens arredondados podem desviar do
    total arredondado);
  - total == total_texto;
  - total == total_destaques quando o quadro de destaques traz a linha.
Um trimestre so conta como validado se passar nos tres testes aplicaveis.

Resultado: 23/26 passam. Os 3 que nao passam (1T20: soma 98 x total 96;
4T21: 136 x 134; 3T22: 153 x 151) falham por 2 unidades e o desvio esta NO
PROPRIO RELEASE, nao na extracao: o release seguinte repete, na coluna
comparativa, exatamente os mesmos componentes e o mesmo total. Nesses tres
trimestres o total_texto e o total da tabela coincidem, entao o Total esta certo
e a diferenca e acumulo de arredondamento dos 8 itens (a tabela e publicada em
R$ MM inteiros).

Checagem adicional (feita fora do parser, com o release n+1): cada trimestre foi
comparado com a coluna "trimestre anterior" do release seguinte. Todos batem,
exceto onde a Cyrela reapresentou pro forma - 2T20 (restatement no 3T20:
total 97 -> 80), 3T21 (pequeno restatement no 4T21 + saida da linha Stock
Options), 2T22 (restatement no 3T22: 143 -> 125) e 4T23 (saida de Indenizacoes
no 1T24: 135 -> 98). Nenhuma divergencia inexplicada.

Ressalvas importantes de serie
------------------------------
* "Stock Options" existe de 1T20 a 3T21 e some a partir do 4T21 (valores eram 0
  ou proximos de 0). Fica null depois disso.
* "Indenizacoes" saiu do G&A a partir do 1T24: o proprio release 1T24 avisa que
  "a linha de Indenizacoes passa a ser" reportada em Outras Despesas/Receitas
  Operacionais e reapresenta os periodos anteriores. Por isso o total 4T23
  reportado no release do 4T23 e 135 (com Indenizacoes = 37) e o mesmo 4T23
  aparece como 98 (pro forma) no release do 1T24. Este parser guarda SEMPRE o
  numero "as reported" no release do proprio trimestre. Para uma serie
  homogenea pos-1T24, use total - indenizacoes ate o 4T23.
* Houve outras reapresentacoes pro forma (consolidacao da CashMe, 3T20 e 3T22),
  que afetam apenas as colunas comparativas - nao o valor do trimestre corrente.

Uso
---
    python dados_desp_gea.py            # grava _desp_gea.json e imprime o QA
"""

import json
import os
import re
import sys
import unicodedata

import pdfplumber

BASE = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(BASE, "fontes")
SAIDA = os.path.join(BASE, "_desp_gea.json")

QUARTERS = ["%dT%02d" % (t, y) for y in range(20, 27) for t in (1, 2, 3, 4)][:26]

# rotulo normalizado (sem acento, sem espaco, minusculo) -> campo
LABELS = [
    ("salarioseencargossociais", "salarios_encargos"),
    ("honorariosdaadministracao", "honorarios_administracao"),
    ("participacaodosempregados", "participacao_empregados"),
    ("stockoptions", "stock_options"),
    ("servicosdeterceiros", "servicos_terceiros"),
    ("aluguelviagenserepresentacoes", "aluguel_viagens_representacoes"),
    ("indenizacoes", "indenizacoes"),
    ("outros", "outros"),
    ("total", "total"),
]
ITENS = [c for _, c in LABELS if c != "total"]

CAMPOS = ITENS + [
    "total",
    "soma_componentes",
    "total_texto",
    "total_destaques",
    "ga_cashme",
    "pagina_pdf",
]

NUM = re.compile(r"^\(?-?\d[\d\.]*(?:,\d+)?\)?$")


# ---------------------------------------------------------------- utilitarios
def _norm(s):
    """minusculo, sem acento."""
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _flat(s):
    """minusculo, sem acento, sem espaco nem pontuacao de rotulo."""
    return re.sub(r"[^a-z0-9%]", "", _norm(s))


def _to_num(txt):
    """'1.234' -> 1234 ; '(22)' -> -22 ; '-5' -> -5 ; '12,5' -> 12.5."""
    t = txt.strip().replace(" ", "")
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    t = t.replace(".", "").replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    if neg:
        v = -v
    return int(round(v)) if abs(v - round(v)) < 1e-9 else v


def _rows(page, tol=2.0):
    """agrupa chars da pagina em linhas por coordenada vertical."""
    buckets = {}
    for c in page.chars:
        buckets.setdefault(round(c["top"] / tol), []).append(c)
    return [buckets[k] for k in sorted(buckets)]


def _cells(chars, gap=8.0):
    """agrupa chars de uma linha em celulas por salto horizontal."""
    chars = [c for c in chars if not c["text"].isspace()]
    chars.sort(key=lambda c: c["x0"])
    out, cur = [], []
    for c in chars:
        if cur and c["x0"] - cur[-1]["x1"] > gap:
            out.append(cur)
            cur = [c]
        else:
            cur.append(c)
    if cur:
        out.append(cur)
    return ["".join(x["text"] for x in cl).strip() for cl in out]


def _page_text_flat(page):
    return _flat(page.extract_text() or "")


# ------------------------------------------------------------------- parsing
def _acha_pagina(pdf):
    """pagina da secao DESPESAS GERAIS E ADMINISTRATIVAS com a tabela por natureza."""
    for i, page in enumerate(pdf.pages):
        ft = _page_text_flat(page)
        if "anexoii" in ft or "demonstracaoderesultado" in ft:
            continue
        if "geraiseadministrativas" not in ft:
            continue
        if "honorarios" not in ft and "encargos" not in ft:
            continue
        # precisa ter as linhas da tabela, nao so a mencao no sumario
        achou = 0
        for row in _rows(page):
            lab = _flat(_cells(row)[0]) if _cells(row) else ""
            if any(lab.startswith(k) for k, _ in LABELS):
                achou += 1
        if achou >= 5:
            return i, page
    return None, None


def _tabela(page):
    """le a tabela por natureza; devolve {campo: valor_do_trimestre_corrente}."""
    dados = {}
    for row in _rows(page):
        cells = _cells(row)
        if len(cells) < 2:
            continue
        lab = _flat(cells[0])
        campo = None
        for chave, nome in LABELS:
            if lab == chave or lab.startswith(chave):
                campo = nome
                break
        if campo is None or campo in dados:
            continue
        # primeiro numero puro (sem %) depois do rotulo = trimestre corrente
        for cel in cells[1:]:
            c = cel.strip()
            if c.endswith("%") or not NUM.match(c):
                continue
            v = _to_num(c)
            if v is not None:
                dados[campo] = v
            break
    return dados


def _total_texto(page):
    """numero da frase 'as despesas ... atingiram R$ X milhoes'."""
    txt = _norm(re.sub(r"\s+", " ", page.extract_text() or ""))
    m = re.search(r"administrativas do trimestre atingiram r\$ ([\d\. ]+?) ?milh", txt)
    if not m:
        return None
    return _to_num(m.group(1).replace(" ", ""))


def _ga_cashme(page):
    """numero da frase 'O G&A da CashMe totalizou R$ X milhoes no trimestre'."""
    txt = _norm(re.sub(r"\s+", " ", page.extract_text() or ""))
    m = re.search(r"g&a da cashme totalizou r\$ ([\d\. ]+?) ?milh", txt)
    if not m:
        return None
    return _to_num(m.group(1).replace(" ", ""))


def _total_destaques(pdf, limite=16):
    """linha 'Despesas Gerais e Administrativas (R$ milhoes)' do quadro de destaques."""
    for page in pdf.pages[:limite]:
        for row in _rows(page):
            cells = _cells(row)
            if len(cells) < 3:
                continue
            if not _flat(cells[0]).startswith("despesasgeraiseadministrativas"):
                continue
            c = cells[1].strip()
            if c.endswith("%") or not NUM.match(c):
                continue
            return _to_num(c)
    return None


def extrai(q):
    caminho = os.path.join(FONTES, "release_%s.pdf" % q)
    if not os.path.exists(caminho):
        return None, "pdf inexistente"
    with pdfplumber.open(caminho) as pdf:
        idx, page = _acha_pagina(pdf)
        if page is None:
            return None, "secao G&A nao localizada"
        reg = {c: None for c in CAMPOS}
        reg.update(_tabela(page))
        reg["pagina_pdf"] = idx
        reg["total_texto"] = _total_texto(page)
        reg["ga_cashme"] = _ga_cashme(page)
        reg["total_destaques"] = _total_destaques(pdf)
    vals = [reg[c] for c in ITENS if reg[c] is not None]
    reg["soma_componentes"] = sum(vals) if vals else None
    return reg, None


# ---------------------------------------------------------------- validacao
def valida(reg):
    """devolve (ok, [mensagens de problema])."""
    problemas = []
    if reg.get("total") is None:
        return False, ["sem total"]
    if reg.get("soma_componentes") is None:
        problemas.append("sem componentes")
    elif abs(reg["soma_componentes"] - reg["total"]) > 1:
        problemas.append(
            "soma %s != total %s" % (reg["soma_componentes"], reg["total"])
        )
    if reg.get("total_texto") is None:
        problemas.append("sem frase de total")
    elif reg["total_texto"] != reg["total"]:
        problemas.append("texto %s != total %s" % (reg["total_texto"], reg["total"]))
    if reg.get("total_destaques") is not None and reg["total_destaques"] != reg["total"]:
        problemas.append(
            "destaques %s != total %s" % (reg["total_destaques"], reg["total"])
        )
    return (not problemas), problemas


def main():
    saida, qa = {}, []
    for q in QUARTERS:
        reg, erro = extrai(q)
        if reg is None:
            saida[q] = {c: None for c in CAMPOS}
            qa.append((q, False, [erro]))
            continue
        saida[q] = reg
        ok, probs = valida(reg)
        qa.append((q, ok, probs))

    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=1)

    print("arquivo: %s" % SAIDA)
    hdr = ("tri", "sal", "hon", "part", "stk", "terc", "alug", "inden", "out",
           "TOT", "soma", "txt", "dest", "cashme", "ok")
    print(("%-5s" + "%7s" * 13 + "  %s") % hdr)
    okc = 0
    for q, ok, probs in qa:
        r = saida[q]
        okc += 1 if ok else 0
        linha = [q] + [
            "-" if r[c] is None else r[c]
            for c in ITENS + ["total", "soma_componentes", "total_texto",
                              "total_destaques", "ga_cashme"]
        ]
        print(("%-5s" + "%7s" * 13 + "  %s")
              % (tuple(linha) + ("OK" if ok else "; ".join(probs),)))
    print("\nvalidados (tolerancia 1): %d/%d" % (okc, len(QUARTERS)))
    ok2 = sum(
        1
        for q in QUARTERS
        if saida[q]["total"] is not None
        and saida[q]["soma_componentes"] is not None
        and abs(saida[q]["soma_componentes"] - saida[q]["total"]) <= 2
        and saida[q]["total_texto"] == saida[q]["total"]
        and (saida[q]["total_destaques"] in (None, saida[q]["total"]))
    )
    print("validados (tolerancia 2): %d/%d" % (ok2, len(QUARTERS)))
    faltando = [q for q in QUARTERS if saida[q]["total"] is None]
    print("sem total: %s" % (faltando or "nenhum"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
