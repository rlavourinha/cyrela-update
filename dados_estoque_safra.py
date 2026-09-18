# -*- coding: utf-8 -*-
"""
dados_estoque_safra.py -- Estoque de VGV a valor de mercado por SAFRA DE ENTREGA,
extraido dos releases trimestrais da Cyrela (CYRE3), 1T20 .. 2T26.

SAIDA: _estoque_safra.json  ->  {"1T20": {campo: valor|null, ...}, ...}

--------------------------------------------------------------------------------
DE ONDE VEM CADA CAMPO
--------------------------------------------------------------------------------
total_100 : R$ MM. Quadro de destaques, linha
            "VGV Estoque a Valor de Mercado - R$ Milhoes (100%)", PRIMEIRO numero
            apos o rotulo (= trimestre corrente). Fallback (releases antigos, que
            nao trazem essa linha no quadro): frase da secao ESTOQUES
            "o estoque a valor de mercado somava R$ X milhoes (100%)".
total_cbr : idem, base %CBR ("... e R$ Y milhoes (%CBR)").
            total_100 e total_cbr sao o FATOR DE CONVERSAO pedido: para levar um
            valor %CBR a base 100% multiplique por total_100/total_cbr.
fator_cbr : total_cbr / total_100 (calculado, nao reportado). Arredondado a 6 casas.

pronto, m12, m24, m36, m48_mais, total_safra
          : coluna "Total" da tabela "Estoque (%CBR) por Safra de Entrega (R$ MM)",
            linhas Pronto / 12 Meses / 24 Meses / 36 Meses / (48 Meses | +36 meses)
            / Total. R$ MM.
consolidacao_*, equivalencia_*
          : as outras duas colunas da mesma tabela (uteis para checar a soma).
            Ficam null quando o texto extraido do PDF perdeu algum valor.

rotulo_5a_safra : "48 Meses" (1T20..3T24) ou "+36 meses" (4T24..2T26). A Cyrela
            trocou o rotulo do ultimo balde no 4T24; o conteudo economico e o
            mesmo (entrega para alem de 36 meses).

base_tabela : "100%" ou "%CBR".  *** ATENCAO, PEGADINHA ***
            De 1T20 ate 3T25 a tabela por safra e reportada em VGV 100%
            (titulo "Estoque por Safra de Entrega"); a partir do 4T25 ela passou
            a ser reportada em %CBR (titulo "Estoque %CBR por Safra de Entrega").
            O parser NAO assume: ele compara total_safra com total_100 e com
            total_cbr e classifica pelo que bate (tolerancia 2).

*_cbr     : SO preenchido quando a tabela do trimestre ja e %CBR (4T25..2T26).
            Nos demais trimestres fica null -- a Cyrela nao publica o breakdown
            por safra em %CBR antes do 4T25.
*_cbr_aprox : os cinco baldes 100% multiplicados pelo fator_cbr do trimestre.
            E APROXIMACAO, NAO DADO REPORTADO. O %CBR nao e uniforme entre as
            safras (as parcerias se concentram em certas safras), entao o fator
            agregado erra balde a balde. Medido contra o unico balde cujo %CBR e
            publicado (Pronto, na secao ESTOQUE PRONTO), o erro vai de -0,4% a
            -14% -- ver aprox_erro_pronto_pct, gravado em cada trimestre. Use
            *_cbr_aprox so para forma/participacao; para nivel em %CBR use
            total_cbr (esse sim reportado e exato).
share_*   : balde / total_safra (fracao, 4 casas). E exato e comparavel ao longo
            do tempo DENTRO da base da tabela; e a forma segura de olhar mix.

validado  : True se sum(5 baldes) == total_safra E total_safra == total_100 ou
            total_cbr, ambos com tolerancia de 2 (os releases arredondam cada
            celula, entao a soma das partes erra ate ~1-2 unidades no total).

--------------------------------------------------------------------------------
DOIS LAYOUTS DE PDF
--------------------------------------------------------------------------------
NOVO (1T23..2T26), lido de release_XTYY.txt (pdftotext -layout, UTF-8):
    a tabela sai limpa, um rotulo por linha seguido dos 3 numeros:
        Pronto      1.714      1.560      154
    Basta casar ^<rotulo>\\s+n\\s+n\\s+n a partir do cabecalho
    "Safra de Entrega Total Consolidacao Equivalencia".

ANTIGO (1T20..4T22), lido de release_XTYY.raw.txt (pdftotext SEM -layout, cp1252):
    o .txt com -layout embaralha a tabela (numeros deslocados de uma linha em
    relacao ao rotulo -- ver 1T20). O .raw.txt preserva a ordem de leitura do PDF
    e sai em um de dois padroes:
      (a) COLUNA-A-COLUNA: 6 numeros da coluna Total, depois 6 de Consolidacao,
          depois 6 de Equivalencia.   Ex. 1T20, 3T20, 1T21, 1T22, 3T22, 4T22.
      (b) LINHA-A-LINHA: trincas (Total, Consolidacao, Equivalencia) por safra,
          6 trincas.                  Ex. 2T20, 4T20, 2T21, 4T21, 2T22.
    O parser coleta os numeros do bloco e TESTA as duas hipoteses, aceitando a
    que fecha a conta (soma dos 5 baldes = 6o numero = total publicado). Nao ha
    palpite: se nenhuma fecha, os campos ficam null.
    Um "-" isolado no bloco vale 0 (safra sem saldo).
    Em alguns trimestres a coluna Equivalencia (ou Consolidacao) tem so 5 numeros
    porque o PDF omitiu uma celula vazia; o parser tambem testa essa variante
    (4 baldes + total, com o balde faltante = 0), e so a aceita se somar.

3T21 nao sai em NENHUMA extracao de texto: naquele release a tabela foi colada
como BITMAP na pagina 13. Ver _TABELA_IMAGEM, mais abaixo, para a transcricao e
as quatro checagens que a confirmam.

--------------------------------------------------------------------------------
ALERTAS DE CONTINUIDADE JA CONFERIDOS (nao sao erro de parse)
--------------------------------------------------------------------------------
O balde "48 Meses" despenca de 419 (1T20) para 66 (2T20) e 25 (3T20), e volta a
782 no 4T20. Conferido lendo as tabelas direto dos PDFs do 2T20 (pag. 13) e do
3T20 (pag. 15): os numeros sao esses mesmos e as colunas fecham exatamente
(1.649+1.122+1.754+1.101+66 = 5.692; 1.551+987+2.003+1.307+25 = 5.872). E dado
real: em 2020 a Cyrela quase nao tinha projeto com entrega prevista para 4 anos
a frente, e o balde so se recompoe com a safra recorde de lancamentos do 2S20.
"""

import json
import os
import re
import unicodedata

DIR = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(DIR, "fontes")
SAIDA = os.path.join(DIR, "_estoque_safra.json")

TRIMESTRES = ["%dT%02d" % (t, y) for y in range(20, 27) for t in (1, 2, 3, 4)]
TRIMESTRES = TRIMESTRES[: TRIMESTRES.index("2T26") + 1]

TOL = 2.0  # tolerancia de arredondamento, em R$ MM

# ------------------------------------------------------------------ utilitarios


def _ler(path):
    """Le o .txt tentando UTF-8 (releases novos) e caindo para cp1252 (antigos)."""
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", "replace")


def _sem_acento(s):
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


_NUM = re.compile(r"^\(?-?[\d.]{1,3}(?:\.\d{3})*(?:,\d+)?\)?$")


def _num(tok):
    """'1.714' -> 1714.0 ; '(1.234,5)' -> -1234.5 ; '-' -> 0.0 ; senao None."""
    tok = tok.strip()
    if tok in ("-", "--", "–", "—"):
        return 0.0
    neg = tok.startswith("(") and tok.endswith(")")
    tok = tok.strip("()")
    if tok.startswith("-") and len(tok) > 1:
        neg, tok = True, tok[1:]
    if not re.fullmatch(r"\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?", tok):
        return None
    v = float(tok.replace(".", "").replace(",", "."))
    return -v if neg else v


def _numeros(linha):
    """Todos os numeros de uma linha, na ordem (inclui '-' isolado como 0)."""
    out = []
    for tok in re.split(r"\s+", linha.strip()):
        if not tok:
            continue
        v = _num(tok)
        if v is not None:
            out.append(v)
    return out


def _perto(a, b, tol=TOL):
    return a is not None and b is not None and abs(a - b) <= tol


# ------------------------------------------------------- totais 100% e %CBR


def _totais(txt):
    """
    total_100 / total_cbr do trimestre corrente.
    1a fonte: quadro de destaques ("VGV Estoque a Valor de Mercado - R$ Milhoes (X)"),
              primeiro numero apos o rotulo.
    2a fonte: frase da secao ESTOQUES ("somava R$ X milhoes (100%) e R$ Y (%CBR)").
    """
    plano = _sem_acento(txt)
    t100 = tcbr = None

    for linha in plano.split("\n"):
        if "VGV Estoque a Valor de Mercado - R$" not in linha:
            continue
        nums = _numeros(linha.split(")", 1)[1] if ")" in linha else linha)
        if not nums:
            continue
        if re.search(r"\(\s*100\s*%\s*\)", linha) and t100 is None:
            t100 = nums[0]
        elif re.search(r"\(\s*%\s*CBR\s*\)", linha) and tcbr is None:
            tcbr = nums[0]

    if t100 is None or tcbr is None:
        # NB: nao use [^.] aqui -- os proprios numeros tem ponto de milhar.
        frase = re.search(r"estoque a valor de mercado.{0,400}", plano, re.S)
        if frase:
            s = re.sub(r"\s+", " ", frase.group(0))
            m = re.search(r"R\$\s*([\d.]+)\s*milhoes\s*\(\s*100\s*%\s*\)", s)
            if m and t100 is None:
                t100 = _num(m.group(1))
            m = re.search(r"R\$\s*([\d.]+)\s*milhoes\s*\(\s*%\s*CBR\s*\)", s)
            if m and tcbr is None:
                tcbr = _num(m.group(1))
            if tcbr is None:
                m = re.search(
                    r"estoque a valor de mercado\s*\(\s*%\s*CBR\s*\)\s*somava\s*R\$\s*([\d.]+)",
                    s,
                )
                if m:
                    tcbr = _num(m.group(1))
    return t100, tcbr


# ------------------------------- checagem independente do balde "Pronto"


def _pronto_narrativa(txt, tri):
    """
    Fonte INDEPENDENTE da tabela por safra, usada so para conferir (e para o 3T21,
    unico trimestre sem a tabela). A secao ESTOQUE PRONTO traz sempre:
        "o estoque pronto da Companhia aumentou de R$ A milhoes (100%) (%CBR R$ B
         milhoes) no <tri-1> para R$ C milhoes (100%) (%CBR R$ D milhoes) no <tri>"
    Devolve (C, D) = (100%, %CBR). No 2T26 o release ja e todo %CBR e omite o
    "(100%)": nesse caso o unico numero publicado e o %CBR, e o outro fica None.
    """
    s = re.sub(r"\s+", " ", _sem_acento(txt))
    m = re.search(
        r"estoque pronto da Companhia.{0,220}?para R\$ ([\d.]+) milhoes"
        r"(?:\s*\(100%\)\s*\(%\s*CBR\s*R\$ ([\d.]+) milhoes\))?"
        r"\s*no " + re.escape(tri),
        s,
    )
    if not m:
        return None, None
    a, b = _num(m.group(1)), (_num(m.group(2)) if m.group(2) else None)
    if b is None:
        return None, a  # release ja publicado em %CBR (2T26)
    return a, b


# ------------------------------------------------------- tabela: layout NOVO

ROTULOS = [
    ("pronto", r"Pronto"),
    ("m12", r"12\s*Meses"),
    ("m24", r"24\s*Meses"),
    ("m36", r"36\s*Meses"),
    ("m48_mais", r"(?:48\s*Meses|\+\s*36\s*meses)"),
    ("total_safra", r"Total"),
]


def _tabela_nova(txt):
    """Casa o cabecalho 'Safra de Entrega Total Consolidacao Equivalencia' e le
    as 6 linhas seguintes no formato '<rotulo> <total> <consolidacao> <equiv>'."""
    plano = _sem_acento(txt).split("\n")
    ini = None
    for i, linha in enumerate(plano):
        if re.search(r"Safra de Entrega\s+Total\s+Consolidacao", linha):
            ini = i + 1
            break
    if ini is None:
        return None

    linhas = plano[ini : ini + 12]
    cols, rot5 = {}, None
    for chave, pat in ROTULOS:
        for linha in linhas:
            m = re.match(r"^\s*(" + pat + r")\s+(.+)$", linha)
            if not m:
                continue
            nums = _numeros(m.group(2))
            if len(nums) < 3:
                continue
            cols[chave] = nums[:3]
            if chave == "m48_mais":
                rot5 = re.sub(r"\s+", " ", m.group(1)).strip()
            break
    if len(cols) != 6:
        return None
    return cols, rot5


# ------------------------------------------------------ tabela: layout ANTIGO

_PARA = re.compile(
    r"Varia[cç][aã]o do Estoque|Breakdown|Estoque Pronto|Release de Resultados"
    r"|VGV Estoque|Cronograma|CONTAS A RECEBER",
    re.I,
)


_ROTULO_LINHA = re.compile(
    r"Pronto|Meses|Total|Consolidacao|Equivalencia|Safra", re.I
)


def _bloco_antigo(raw):
    """Numeros do bloco 'Estoque por Safra de Entrega' do .raw.txt, em ordem."""
    linhas = _sem_acento(raw).split("\n")
    ini = None
    for i, linha in enumerate(linhas):
        if "Safra de Entrega" in linha and "Estoque" in linha:
            ini = i + 1
            break
    if ini is None:
        return []
    toks = []
    for linha in linhas[ini : ini + 60]:
        s = linha.strip()
        if not s:
            continue
        if _PARA.search(s):
            break
        # No raw.txt antigo os rotulos vem sempre em linha propria; a linha
        # "Pronto 12 Meses 24 Meses 36 Meses 48 Meses Total" injetaria os
        # numeros 12/24/36/48, entao rotulos sao descartados por inteiro.
        if _ROTULO_LINHA.search(s):
            continue
        toks.extend(_numeros(s))
        if len(toks) >= 24:
            break
    return toks


def _fecha(vals):
    """vals = [b1..b5, total]; True se b1..b5 somam o total."""
    return len(vals) == 6 and _perto(sum(vals[:5]), vals[5])


def _coluna(toks, alvo=None):
    """Extrai uma coluna de 6 valores de `toks`, aceitando a variante em que o
    PDF omitiu uma celula (5 numeros = 4 baldes + total, balde faltante = 0).
    Devolve (valores, quantos tokens consumiu) ou (None, 0)."""
    if len(toks) >= 6 and _fecha(toks[:6]):
        if alvo is None or _perto(toks[5], alvo):
            return toks[:6], 6
    if len(toks) >= 5 and _perto(sum(toks[:4]), toks[4]):
        vals = toks[:4] + [0.0, toks[4]]
        if alvo is None or _perto(toks[4], alvo):
            return vals, 5
    return None, 0


def _tabela_antiga(raw, alvo):
    """Testa as duas ordens de leitura do PDF antigo e devolve a que fecha."""
    toks = _bloco_antigo(raw)
    if len(toks) < 6:
        return None

    # (a) coluna-a-coluna
    tot, n = _coluna(toks, alvo)
    if tot:
        resto = toks[n:]
        con, m = _coluna(resto)
        eqv, _ = _coluna(resto[m:]) if con else (None, 0)
        return _monta(tot, con, eqv)

    # (b) linha-a-linha (trincas)
    tri_t, tri_c, tri_e = toks[0::3][:6], toks[1::3][:6], toks[2::3][:6]
    if _fecha(tri_t) and _perto(tri_t[5], alvo):
        con = tri_c if _fecha(tri_c) else None
        eqv = tri_e if _fecha(tri_e) else None
        return _monta(tri_t, con, eqv)

    return None


# ------------------------------------------- tabela embutida como IMAGEM (3T21)

# No release_3T21.pdf a tabela por safra NAO e texto: e um bitmap colado na
# pagina 13 (pdfplumber lista 3 imagens; a de bbox ~(330, 392, 571, 486) e a
# tabela). Nem `pdftotext` nem `pdfplumber.extract_text()` a enxergam -- por isso
# o 3T21 saia vazio. Os numeros abaixo sao a TRANSCRICAO dessa imagem, feita
# renderizando o recorte a 600 dpi e lendo-o.
#
# Nao e chute: os tres totais transcritos batem com numeros publicados EM TEXTO
# no mesmo release, o que fecha a checagem por tres caminhos independentes:
#   Total        6.481 == "o estoque a valor de mercado somava R$ 6.481 milhoes (100%)"
#   Consolidacao 5.810 == "reconhecida de forma consolidada na receita e de R$ 5.810 milhoes"
#   Equivalencia   671 == "enquanto R$ 671 milhoes ... na linha de equivalencia"
#   Pronto         973 == "para R$ 973 milhoes (100%) ... no 3T21" (secao ESTOQUE PRONTO)
# e as colunas somam (973+821+1.500+2.342+845 = 6.481 exato).
# Ainda assim o registro sai marcado com fonte_tabela = "imagem (transcrito)".
_TABELA_IMAGEM = {
    # tri:  [(total, consolidacao, equivalencia)] em Pronto, 12m, 24m, 36m, 48m, Total
    "3T21": [
        (973.0, 755.0, 217.0),
        (821.0, 706.0, 115.0),
        (1500.0, 1275.0, 224.0),
        (2342.0, 2228.0, 114.0),
        (845.0, 845.0, 0.0),
        (6481.0, 5810.0, 671.0),
    ],
}


def _tabela_imagem(tri):
    linhas = _TABELA_IMAGEM.get(tri)
    if not linhas:
        return None
    return _monta(
        [l[0] for l in linhas], [l[1] for l in linhas], [l[2] for l in linhas]
    )


def _monta(tot, con, eqv):
    cols = {}
    for i, (chave, _) in enumerate(ROTULOS):
        cols[chave] = [
            tot[i],
            con[i] if con else None,
            eqv[i] if eqv else None,
        ]
    return cols, "48 Meses"


# ------------------------------------------------------------------- pipeline


def extrair(tri):
    p_lay = os.path.join(FONTES, "release_%s.txt" % tri)
    p_raw = os.path.join(FONTES, "release_%s.raw.txt" % tri)
    if not os.path.exists(p_lay):
        return None

    txt = _ler(p_lay)
    t100, tcbr = _totais(txt)

    layout = "antigo" if os.path.exists(p_raw) else "novo"
    fonte = None

    res = _tabela_nova(txt)
    if res is not None:
        layout, fonte = "novo", "texto (pdftotext -layout)"
    if res is None and os.path.exists(p_raw):
        res = _tabela_antiga(_ler(p_raw), t100)
        if res is not None:
            fonte = "texto (pdftotext raw)"
    if res is None:
        res = _tabela_imagem(tri)
        if res is not None:
            fonte = "imagem (transcrito)"

    reg = {
        "layout": layout,
        "fonte_tabela": fonte,
        "total_100": t100,
        "total_cbr": tcbr,
        "fator_cbr": round(tcbr / t100, 6) if (t100 and tcbr) else None,
        "rotulo_5a_safra": None,
        "base_tabela": None,
        "pronto": None,
        "m12": None,
        "m24": None,
        "m36": None,
        "m48_mais": None,
        "total_safra": None,
        "consolidacao_pronto": None,
        "consolidacao_m12": None,
        "consolidacao_m24": None,
        "consolidacao_m36": None,
        "consolidacao_m48_mais": None,
        "consolidacao_total": None,
        "equivalencia_pronto": None,
        "equivalencia_m12": None,
        "equivalencia_m24": None,
        "equivalencia_m36": None,
        "equivalencia_m48_mais": None,
        "equivalencia_total": None,
        "share_pronto": None,
        "share_m12": None,
        "share_m24": None,
        "share_m36": None,
        "share_m48_mais": None,
        "pronto_cbr": None,
        "m12_cbr": None,
        "m24_cbr": None,
        "m36_cbr": None,
        "m48_mais_cbr": None,
        "total_safra_cbr": None,
        "pronto_cbr_aprox": None,
        "m12_cbr_aprox": None,
        "m24_cbr_aprox": None,
        "m36_cbr_aprox": None,
        "m48_mais_cbr_aprox": None,
        "aprox_erro_pronto_pct": None,
        "pronto_narrativa_100": None,
        "pronto_narrativa_cbr": None,
        "check_pronto": None,
        "validado": False,
    }
    reg["pronto_narrativa_100"], reg["pronto_narrativa_cbr"] = _pronto_narrativa(
        txt, tri
    )
    if res is None:
        return reg

    cols, rot5 = res
    reg["rotulo_5a_safra"] = rot5
    for chave, _ in ROTULOS:
        tot, con, eqv = cols[chave]
        reg[chave] = tot
        sufixo = "total" if chave == "total_safra" else chave
        reg["consolidacao_" + sufixo] = con
        reg["equivalencia_" + sufixo] = eqv

    baldes = [reg["pronto"], reg["m12"], reg["m24"], reg["m36"], reg["m48_mais"]]
    total = reg["total_safra"]

    # base da tabela: comparar com os dois totais publicados no proprio release
    if _perto(total, tcbr):
        reg["base_tabela"] = "%CBR"
    elif _perto(total, t100):
        reg["base_tabela"] = "100%"

    # checagem cruzada: o balde "Pronto" da tabela tem que ser igual ao estoque
    # pronto citado na secao ESTOQUE PRONTO, na MESMA base da tabela.
    alvo_pronto = (
        reg["pronto_narrativa_cbr"]
        if reg["base_tabela"] == "%CBR"
        else reg["pronto_narrativa_100"]
    )
    if alvo_pronto is not None:
        reg["check_pronto"] = _perto(reg["pronto"], alvo_pronto)

    reg["validado"] = bool(
        _perto(sum(baldes), total)
        and reg["base_tabela"] is not None
        and reg["check_pronto"] is not False
    )

    # mix (exato, na base da propria tabela)
    if total:
        for c in ("pronto", "m12", "m24", "m36", "m48_mais"):
            reg["share_" + c] = round(reg[c] / total, 4)

    # base %CBR: so e DADO quando a tabela ja vem em %CBR
    if reg["base_tabela"] == "%CBR":
        for c in ("pronto", "m12", "m24", "m36", "m48_mais", "total_safra"):
            reg[c + "_cbr"] = reg[c]

    # aproximacao 100% -> %CBR pelo fator agregado (com o erro medido junto)
    if reg["base_tabela"] == "100%" and reg["fator_cbr"]:
        for c in ("pronto", "m12", "m24", "m36", "m48_mais"):
            reg[c + "_cbr_aprox"] = round(reg[c] * reg["fator_cbr"], 1)
        if reg["pronto_narrativa_cbr"]:
            reg["aprox_erro_pronto_pct"] = round(
                100
                * (reg["pronto_cbr_aprox"] - reg["pronto_narrativa_cbr"])
                / reg["pronto_narrativa_cbr"],
                1,
            )
    return reg


def main():
    dados, faltando, validos = {}, [], 0
    for tri in TRIMESTRES:
        reg = extrair(tri)
        if reg is None:
            faltando.append(tri + " (release ausente)")
            continue
        dados[tri] = reg
        if reg["total_safra"] is None:
            faltando.append(tri)
        if reg["validado"]:
            validos += 1

    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False, indent=2)

    print("trimestres no json      :", len(dados))
    print("com breakdown por safra :", sum(1 for r in dados.values() if r["total_safra"]))
    print("validados (soma = total):", validos)
    print("sem breakdown           :", faltando or "-")
    print()
    print(
        "tri   base   pronto     12m      24m      36m   +36/48    total"
        "   pub100   pubCBR  soma  pronto"
    )
    for tri, r in dados.items():
        print(
            "%-5s %-6s %8s %8s %8s %8s %8s %8s %8s %8s  %-4s  %s"
            % (
                tri,
                r["base_tabela"] or "-",
                r["pronto"], r["m12"], r["m24"], r["m36"], r["m48_mais"],
                r["total_safra"], r["total_100"], r["total_cbr"],
                "OK" if r["validado"] else "??",
                {True: "OK", False: "DIFF", None: "-"}[r["check_pronto"]],
            )
        )
    ck = [r["check_pronto"] for r in dados.values()]
    print()
    print("check cruzado do balde Pronto: %d OK, %d DIFF, %d sem fonte"
          % (ck.count(True), ck.count(False), ck.count(None)))

    # continuidade: nenhum balde pode saltar >5x contra o trimestre vizinho
    # (salto assim = coluna errada, ou acumulado do ano no lugar do trimestre)
    tris = list(dados)
    alertas = []
    for c in ("pronto", "m12", "m24", "m36", "m48_mais", "total_safra"):
        for a, b in zip(tris, tris[1:]):
            x, y = dados[a][c], dados[b][c]
            if x and y and (y / x > 5 or x / y > 5):
                alertas.append("%s: %s %s -> %s %s" % (c, a, x, b, y))
    print("continuidade (salto >5x entre trimestres vizinhos):",
          alertas or "nenhum alerta")

    # 3a checagem, independente: em toda linha Consolidacao + Equivalencia = Total
    ok_lin = ruim = 0
    for r in dados.values():
        for b in ("pronto", "m12", "m24", "m36", "m48_mais", "total"):
            k = "total_safra" if b == "total" else b
            c, e, t = r["consolidacao_" + b], r["equivalencia_" + b], r[k]
            if None in (c, e, t):
                continue
            if _perto(c + e, t):
                ok_lin += 1
            else:
                ruim += 1
    print("consolidacao + equivalencia = total: %d linhas OK, %d fora"
          % (ok_lin, ruim))

    err = [r["aprox_erro_pronto_pct"] for r in dados.values()
           if r["aprox_erro_pronto_pct"] is not None]
    if err:
        print("erro da conversao aproximada 100%%->%%CBR (balde Pronto): "
              "min %.1f%% / max %.1f%% em %d trimestres"
              % (min(err), max(err), len(err)))


if __name__ == "__main__":
    main()
