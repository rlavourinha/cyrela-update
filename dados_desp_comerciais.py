#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""
Extrai a tabela DESPESAS COMERCIAIS POR NATUREZA dos releases trimestrais da
Cyrela (1T20..2T26) e grava _desp_comerciais.json.

------------------------------------------------------------------------------
DE ONDE VEM CADA CAMPO
------------------------------------------------------------------------------
Todos os campos saem da tabela "Despesas Comerciais" (secao DESPESAS COMERCIAIS
do release), coluna do TRIMESTRE CORRENTE (a primeira coluna numerica da tabela,
imediatamente a direita dos rotulos). Valores em R$ milhoes.

  estande     -> linha "Estande de Vendas"
  midia       -> linha "Midia"
  terceiros   -> linha "Servicos de Terceiros"
  manutencao  -> linha "Manutencao Estoque Pronto" (custo de condominio/IPTU do
                 estoque pronto; no layout antigo vem com asterisco)
  outros      -> linha "Outros"
  cashme      -> linha "CashMe" (no pdftotext antigo sai quebrada como "Cas hMe").
                 So passa a existir a partir do 3T22; antes disso fica null.
  total       -> linha "Total" da propria tabela (nao e soma calculada por nos)

------------------------------------------------------------------------------
OS DOIS LAYOUTS
------------------------------------------------------------------------------
NOVO (1T23..2T26) - o pdftotext entrega rotulo + numeros na MESMA linha:

    Estande de Vendas 92 94 -3% 57 62% 186 103 82%
    ^rotulo           ^tri  ^tri-1  ^ano-1     ^acumulados

  => basta pegar o PRIMEIRO numero apos o rotulo. Os demais sao trimestre
  anterior, mesmo trimestre do ano anterior e acumulado do ano - descartados.

ANTIGO (1T20..4T22) - o pdftotext -layout preserva as colunas em X mas os
rotulos e os numeros ficam DESSINCRONIZADOS em Y (os numeros aparecem uma linha
abaixo do rotulo, e cada coluna tem um deslocamento vertical proprio):

    Estande de Vendas           R$ MM           R$ MM                    6,1%
    Midia                                   22              21         -62,2%
    Servicos de Terceiros                   11              29         168,3%
    Manutencao Estoque Pronto*              22               8          -25,5%
    Outros                                   7              10           17,0%
    Total                                    8               7
                                            71              75          -5,5%

  Ler "Midia = 22" seria ERRADO: 22 e o Estande. A leitura correta e por COLUNA,
  nao por linha. Estrategia implementada em `_parse_antigo`:

    1. delimita o bloco a partir da linha "Estande de Vendas";
    2. tokeniza cada linha guardando a coluna FINAL de cada token que seja um
       inteiro puro (percentuais "6,1%", "R$", "MM", "(pro forma)" sao ignorados
       porque nao casam com ^\(?\d+\)?$);
    3. agrupa os tokens por coluna final (colunas sao alinhadas a direita,
       tolerancia de +/-1 caractere);
    4. o grupo mais a ESQUERDA com pelo menos N membros e a coluna do trimestre
       corrente (o rotulo, a esquerda dela, nunca contem inteiro puro);
    5. os N primeiros valores desse grupo, EM ORDEM DE LINHA, correspondem aos
       N rotulos na ordem em que aparecem (Estande, Midia, Terceiros,
       Manutencao, Outros, [CashMe], Total).

  No exemplo acima: coluna 1 = [22, 11, 22, 7, 8, 71] -> Estande 22, Midia 11,
  Terceiros 22, Manutencao 7, Outros 8, Total 71. Confere com o texto corrido do
  proprio release ("totalizaram R$ 71 milhoes") e com a narrativa
  ("Midia apresentou reducao de R$ 18 milhoes vs 4T20": 11 - 29 = -18).

------------------------------------------------------------------------------
COMO O PARSER ESCOLHE O LAYOUT
------------------------------------------------------------------------------
Nao da para decidir so olhando se ha digito na linha do rotulo: no layout antigo
a linha "Midia ... 22 ..." TAMBEM tem numero - so que esse 22 e o do Estande
(defasagem de uma linha). Por isso `extrair` roda AS DUAS leituras em todo
release e fica com a que passa na validacao (soma == total e total == total
citado no texto). A heuristica `_e_layout_novo` so serve de desempate.

------------------------------------------------------------------------------
VALIDACAO
------------------------------------------------------------------------------
  A) soma dos componentes == total reportado na propria tabela, tolerancia 1
     (os releases arredondam cada linha para o milhao, entao +/-1 e esperado);
  B) o total extraido == total citado no texto corrido
     ("As despesas comerciais do trimestre totalizaram R$ N milhoes");
  C) continuidade:
       C1 - salto > 2,2x entre trimestres vizinhos (sintoma de ter pego a coluna
            do acumulado do ano);
       C2 - o total do trimestre anterior citado NO TEXTO do release seguinte vs
            o total que extraimos daquele trimestre (`_total_tri_anterior`);
  D) `conferir_raw`: para 1T20..4T22 existe tambem o dump SEM -layout
     (release_XTYY.raw.txt), em que a coluna do trimestre sai inteira numa
     linha ("R$ MM 22 11 22 7 8 71"). Conferimos valor a valor. Os 12
     trimestres antigos batem 100%.

RESSALVAS CONHECIDAS (nao sao erro de parsing - C2 acusa e esta correto):
  * 3T20: apos os IPOs de Cury e Plano&Plano a Cyrela passa a apresentar 2020
    "pro forma". O release do 3T20 restata o 2T20 em R$ 63 MM, contra os R$ 89
    MM que o proprio release do 2T20 publicou.
  * 3T22: primeiro trimestre com a CashMe consolidada na tabela. O release do
    3T22 restata o 2T22 em R$ 126 MM pro forma, contra os R$ 108 MM publicados
    no release do 2T22. Idem 1T23, que mostra 1T22 = 112 pro forma vs 98.
  Guardamos SEMPRE o numero as reported no release do proprio trimestre. Ou
  seja: ate 2T22 o total NAO inclui CashMe; de 3T22 em diante inclui.

Uso:  python dados_desp_comerciais.py [--json]
"""

from __future__ import annotations

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(BASE, "fontes")
SAIDA = os.path.join(BASE, "_desp_comerciais.json")

# todos os releases presentes em fontes/, em ordem cronologica
TRIMESTRES = [q for q in ("%dT%02d" % (t, a)
                          for a in range(20, 27) for t in (1, 2, 3, 4))
              if os.path.exists(os.path.join(FONTES, "release_%s.txt" % q))]

CAMPOS = ["estande", "midia", "terceiros", "manutencao", "outros", "cashme", "total"]

# rotulos na ordem em que aparecem na tabela; cashme e opcional
ROTULOS = [
    ("estande", r"Estande\s+de\s+Vendas"),
    ("midia", r"M[ií]dia"),
    ("terceiros", r"Servi[cç]os\s+de\s+Terceiros"),
    ("manutencao", r"Manuten[cç][aã]o\s+Estoque\s+Pronto"),
    ("outros", r"Outros"),
    ("cashme", r"Cas\s?hMe"),          # "Cas hMe" no pdftotext do layout antigo
    ("total", r"Total"),
]

# linhas que encerram o bloco da tabela no layout antigo
_FIM_BLOCO = re.compile(
    r"(Release de Resultados|=====\s*PAGINA|DESPESAS GERAIS|^\s*\*\s*custo)", re.I)

_TOKEN_INT = re.compile(r"^\(?-?\d{1,4}\)?$")


def _ler(path: str) -> str:
    """Releases <=4T22 vem em cp1252; os novos em utf-8."""
    raw = open(path, "rb").read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", "replace")


def _num(tok: str):
    """'(12)' -> -12 ; '34' -> 34."""
    tok = tok.strip()
    neg = tok.startswith("(") and tok.endswith(")")
    tok = tok.strip("()")
    if not re.fullmatch(r"-?\d+", tok):
        return None
    v = int(tok)
    return -v if neg else v


# ----------------------------------------------------------------------------
# localizacao do bloco
# ----------------------------------------------------------------------------
def _achar_inicio(linhas):
    """Linha da tabela que comeca com 'Estande de Vendas'.

    Ignora mencoes no texto corrido ('...foi o item Estande de Vendas.'):
    exige que a linha COMECE com o rotulo (no maximo alguns espacos antes).
    """
    cands = []
    for i, l in enumerate(linhas):
        if re.match(r"^\s{0,4}Estande\s+de\s+Vendas\b", l):
            cands.append(i)
    return cands


def _rotulos_do_bloco(linhas, i0, janela=14):
    """Quais rotulos aparecem no bloco e em que linha (ordem da tabela)."""
    achados = []
    usados = set()
    for j in range(i0, min(len(linhas), i0 + janela)):
        l = linhas[j]
        if j > i0 and _FIM_BLOCO.search(l):
            break
        for campo, rx in ROTULOS:
            if campo in usados:
                continue
            if re.match(r"^\s{0,4}" + rx + r"\*?\b", l):
                achados.append((campo, j))
                usados.add(campo)
                break
        if "total" in usados:
            break
    return achados


# ----------------------------------------------------------------------------
# layout NOVO (1T23+): rotulo e numeros na mesma linha
# ----------------------------------------------------------------------------
_RX_ROT = dict(ROTULOS)


def _e_layout_novo(linhas, rots):
    """Heuristica de desempate: no layout novo a linha do 'Estande de Vendas'
    ja traz o numero do trimestre; no antigo ela traz o header de unidade
    ('R$ MM', '(pro forma)') porque os numeros descem uma linha.

    ATENCAO: nao adianta olhar as outras linhas - no layout antigo 'Midia' TEM
    um numero logo depois, so que esse numero e o do Estande (defasagem de uma
    linha). Por isso a decisao final nao e esta heuristica e sim a validacao em
    `extrair`, que roda as duas leituras e fica com a que fecha soma == total.
    """
    return bool(re.match(r"^\s{0,4}" + _RX_ROT["estande"] + r"\*?\s+\(?-?\d",
                         linhas[rots[0][1]]))


def _parse_novo(linhas, rots):
    out = {c: None for c in CAMPOS}
    for campo, j in rots:
        m = re.match(r"^\s{0,4}" + _RX_ROT[campo] + r"\*?\s+(.*)$", linhas[j])
        if not m:
            continue
        m2 = re.match(r"\(?-?[\d.]+\)?", m.group(1).strip())
        if not m2:
            continue
        v = _num(m2.group(0).replace(".", ""))
        if v is not None:
            out[campo] = v
    return out


# ----------------------------------------------------------------------------
# layout ANTIGO (<=4T22): leitura por coluna
# ----------------------------------------------------------------------------
def _tokens_inteiros(linha, idx):
    """[(linha, coluna_final, valor)] dos tokens que sao inteiros puros."""
    saida = []
    for m in re.finditer(r"\S+", linha):
        tok = m.group(0)
        if not _TOKEN_INT.match(tok):
            continue
        v = _num(tok)
        if v is None:
            continue
        saida.append((idx, m.end(), v))
    return saida


def _parse_antigo(linhas, i0, n_rotulos, janela=22):
    toks = []
    for j in range(i0, min(len(linhas), i0 + janela)):
        if j > i0 and _FIM_BLOCO.search(linhas[j]):
            break
        toks.extend(_tokens_inteiros(linhas[j], j))
    if not toks:
        return None

    # agrupa por coluna final (colunas sao alinhadas a direita; tolerancia +/-1)
    toks.sort(key=lambda t: (t[1], t[0]))
    grupos = []
    for t in toks:
        if grupos and abs(t[1] - grupos[-1][-1][1]) <= 1:
            grupos[-1].append(t)
        else:
            grupos.append([t])

    for g in grupos:                       # ja em ordem de coluna (esq -> dir)
        if len(g) >= n_rotulos:
            g = sorted(g, key=lambda t: t[0])[:n_rotulos]
            return [t[2] for t in g]
    return None


# ----------------------------------------------------------------------------
def _total_no_texto(txt):
    """'As despesas comerciais do trimestre totalizaram R$ 294 milhoes' -> 294."""
    m = re.search(
        r"despesas comerciais do trimestre\s+totalizaram\s+R\$\s*([\d.]+)\s*milh",
        txt, re.I)
    if not m:
        m = re.search(
            r"despesas comerciais do trimestre\s+atingiram\s+R\$\s*([\d.]+)\s*milh",
            txt, re.I)
    if not m:
        m = re.search(
            r"despesas comerciais\s+do\s+trimestre[^.]{0,80}?R\$\s*([\d.]+)\s*milh",
            txt, re.I | re.S)
    return int(m.group(1).replace(".", "")) if m else None


def _nota(vals, total_texto):
    """Quantos testes a leitura passa: soma==total e total==total do texto."""
    if not vals or vals.get("total") is None:
        return -1
    n = 0
    comps = [vals[c] for c in CAMPOS[:-1] if vals.get(c) is not None]
    if len(comps) >= 5 and abs(sum(comps) - vals["total"]) <= 1:
        n += 1
    if total_texto is not None and abs(vals["total"] - total_texto) <= 1:
        n += 1
    return n


def _tri_anterior(tri):
    t, a = int(tri[0]), int(tri[2:])
    return "%dT%02d" % (4, a - 1) if t == 1 else "%dT%02d" % (t - 1, a)


def extrair(tri):
    path = os.path.join(FONTES, "release_%s.txt" % tri)
    txt = _ler(path)
    linhas = txt.split("\n")
    txt_flat = re.sub(r"\s+", " ", txt)
    total_texto = _total_no_texto(txt_flat)

    melhor, melhor_nota = None, -1
    for i0 in _achar_inicio(linhas):
        rots = _rotulos_do_bloco(linhas, i0)
        nomes = [c for c, _ in rots]
        if "total" not in nomes or len(nomes) < 6:
            continue

        # roda AS DUAS leituras e fica com a que passa na validacao; a
        # heuristica de layout so desempata se ambas (ou nenhuma) passarem.
        cand = []
        v_novo = _parse_novo(linhas, rots)
        cand.append(("novo", v_novo))
        col = _parse_antigo(linhas, i0, len(nomes))
        if col is not None:
            v_ant = {c: None for c in CAMPOS}
            for (campo, _), v in zip(rots, col):
                v_ant[campo] = v
            cand.append(("antigo", v_ant))

        pref = "novo" if _e_layout_novo(linhas, rots) else "antigo"
        for nome, vals in sorted(cand, key=lambda c: c[0] != pref):
            n = _nota(vals, total_texto)
            if n > melhor_nota:
                melhor, melhor_nota = dict(vals, _layout=nome, _i0=i0), n
        if melhor_nota == 2:
            break

    if melhor is None:
        return None
    melhor["_total_texto"] = total_texto
    melhor["_total_tri_anterior"] = _total_tri_anterior(
        txt_flat, _tri_anterior(tri), melhor.get("total"))
    return melhor


_MAIS = ("superior", "maior", "acima", "superiores")
_MENOS = ("inferior", "menor", "abaixo", "inferiores")


def _total_tri_anterior(txt_flat, tri_ant, total):
    """Total do TRIMESTRE ANTERIOR segundo o TEXTO CORRIDO do release atual.

    Fonte independente da tabela - por isso serve de checagem cruzada (C2).
    Duas redacoes aparecem nos releases:

      novo  '...totalizaram R$ 294 milhoes, acima dos valores apresentados no
             2T25 (R$ 226 milhoes) e no 1T26 (R$ 277 milhoes).'   -> valor direto
      velho '...totalizaram R$ 72 milhoes, R$ 9 milhoes superior em relacao ao
             2T20 ...'                                            -> delta
    """
    if not tri_ant:
        return None
    # so vale a frase de abertura da secao DESPESAS COMERCIAIS; procurar o
    # padrao no documento inteiro pesca numeros de receita, G&A etc.
    ini = re.search(r"despesas comerciais do trimestre\s+totalizaram", txt_flat, re.I)
    if not ini:
        return None
    trecho = txt_flat[ini.start():ini.start() + 400].split(".")[0]

    m = re.search(r"n?[oa]s?\s+" + tri_ant + r"\s*\(\s*R\$\s*([\d.]+)\s*milh",
                  trecho, re.I)
    if m:
        return int(m.group(1).replace(".", ""))

    if total is None:
        return None
    m = re.search(
        r"totalizaram\s+R\$\s*[\d.]+\s*milh\w*,?\s*"
        r"R\$\s*([\d.]+)\s*milh\w*\s*(\w+)[^.]{0,60}?" + tri_ant,
        trecho, re.I)
    if not m:
        return None
    delta, palavra = int(m.group(1).replace(".", "")), m.group(2).lower()
    if palavra in _MAIS:
        return total - delta
    if palavra in _MENOS:
        return total + delta
    return None


# ----------------------------------------------------------------------------
def conferir_raw(tri):
    """(D) Conferencia independente pelo .raw.txt (pdftotext SEM -layout).

    So existe para 1T20..4T22. Nesse dump o pdftotext emite a tabela em ordem
    de leitura do PDF, entao os rotulos saem TODOS numa linha e logo abaixo vem
    'R$ MM' seguido da coluna do trimestre corrente:

        Estande de Vendas Midia Servicos de Terceiros ... Outros Total
        1T21
        R$ MM 22 11 22 7 8 71

    Isso confirma (por outro caminho) o que `_parse_antigo` le por coluna no
    .txt com -layout. Devolve a lista de valores ou None.
    """
    path = os.path.join(FONTES, "release_%s.raw.txt" % tri)
    if not os.path.exists(path):
        return None
    linhas = _ler(path).split("\n")
    for i, l in enumerate(linhas):
        if not re.match(r"^\s*Estande de Vendas\s+M", l):
            continue
        n = 7 if re.search(r"Cas\s?hMe", l) else 6
        vals = []
        for j in range(i + 1, min(len(linhas), i + 10)):
            toks = linhas[j].split()
            if not vals and not toks[:1] == ["R$"]:
                continue
            for t in toks:
                if _TOKEN_INT.match(t):
                    v = _num(t)
                    if v is not None:
                        vals.append(v)
            if len(vals) >= n:
                return vals[:n]
    return None


def _validar(dados):
    """(A) soma==total, (B) total==texto, (C) continuidade vs vizinho."""
    ok_soma, prob = [], []
    for tri, d in dados.items():
        if d is None:
            continue
        comps = [d[c] for c in CAMPOS[:-1] if d[c] is not None]
        soma, tot = sum(comps), d["total"]
        if tot is None:
            prob.append("%s: sem total" % tri)
            continue
        if abs(soma - tot) <= 1:
            ok_soma.append(tri)
        else:
            prob.append("%s: soma %d != total %d" % (tri, soma, tot))
        tt = d.get("_total_texto")
        if tt is not None and abs(tt - tot) > 1:
            prob.append("%s: total tabela %d != total texto %d" % (tri, tot, tt))
    return ok_soma, prob


def _continuidade(dados, tris):
    """(C) Duas checagens de continuidade.

    C1 - salto > 2,2x entre trimestres vizinhos (sintoma classico de ter pego a
         coluna do acumulado do ano em vez da do trimestre).
    C2 - o total do trimestre anterior REPORTADO no release seguinte tem que
         bater com o total que extraimos daquele trimestre.
         Excecao conhecida e esperada: o release do 3T22 (1o com CashMe
         consolidada) restata o 2T22 "pro forma" em 126 contra os 108 que o
         proprio release do 2T22 publicou. Nao e erro de leitura.
    """
    alertas = []
    ant_tri, ant = None, None
    for tri in tris:
        d = dados.get(tri)
        if not d or d.get("total") is None:
            ant_tri, ant = None, None
            continue
        if ant is not None and ant > 0:
            r = d["total"] / ant
            if r > 2.2 or r < 1 / 2.2:
                alertas.append("C1 %s: total %d vs anterior %d (%.1fx)"
                               % (tri, d["total"], ant, r))
            ref = d.get("_total_tri_anterior")
            if ref is not None and abs(ref - ant) > 1:
                alertas.append(
                    "C2 %s reporta %s = %d; extraimos %d do release do %s"
                    % (tri, ant_tri, ref, ant, ant_tri))
        ant_tri, ant = tri, d["total"]
    return alertas


def main():
    dados, faltando = {}, []
    for tri in TRIMESTRES:
        try:
            v = extrair(tri)
        except Exception as e:                      # noqa: BLE001
            v = None
            print("ERRO %s: %s" % (tri, e))
        if v is None:
            faltando.append(tri)
            dados[tri] = {c: None for c in CAMPOS}
        else:
            dados[tri] = v

    ok, prob = _validar(dados)
    alertas = _continuidade(dados, TRIMESTRES)

    # (D) confronto com o dump sem -layout, quando existe
    raw_ok, raw_dif = [], []
    for tri in TRIMESTRES:
        r = conferir_raw(tri)
        if r is None:
            continue
        d = dados[tri]
        campos = [c for c in CAMPOS if d.get(c) is not None]
        meus = [d[c] for c in campos]
        if len(meus) == len(r) and meus == r:
            raw_ok.append(tri)
        else:
            raw_dif.append("%s: layout=%s raw=%s" % (tri, meus, r))

    limpo = {t: {c: d.get(c) for c in CAMPOS} for t, d in dados.items()}
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(limpo, fh, ensure_ascii=False, indent=2)

    print("trimestres com dados : %d/%d" % (len(TRIMESTRES) - len(faltando),
                                            len(TRIMESTRES)))
    print("validados (soma=tot) : %d" % len(ok))
    print("conferidos vs .raw   : %d ok, %d divergentes" % (len(raw_ok), len(raw_dif)))
    for r in raw_dif:
        print("  DIVERGE RAW %s" % r)
    if faltando:
        print("faltando             : %s" % ", ".join(faltando))
    for p in prob:
        print("  PROBLEMA %s" % p)
    for a in alertas:
        print("  CONTINUIDADE %s" % a)
    print("-> %s" % SAIDA)

    if "--json" in sys.argv:
        print(json.dumps(limpo, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
