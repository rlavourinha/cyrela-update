# -*- coding: utf-8 -*-
"""
Extensao HISTORICA de dados_receber_aging.py: le a secao "CONTAS A RECEBER" dos
releases trimestrais da Cyrela de 4T09 a 4T19 (41 trimestres) e escreve
_receber_aging_hist.json no MESMO formato (_meta / validacoes / dados).

Nao modifica nem depende de _receber_aging.json; reaproveita apenas as
utilidades do parser original (normalizacao de texto, leitura do .txt).

POR QUE UM PARSER SEPARADO
--------------------------
Os releases antigos mudam de layout varias vezes (ver "LAYOUTS" abaixo) e o
texto do pdftotext embaralha rotulos e valores. Aqui, como no original,
reconstruimos as linhas a partir dos glifos (pdfplumber .chars), mas com um
passo a mais: a pagina e DIVIDIDA EM DUAS COLUNAS (tabela/texto a esquerda,
graficos a direita) por uma coordenada x calculada a partir da posicao dos
rotulos das barras do grafico "Cronograma de Recebiveis". Sem isso, linhas
como "Total dos Recebiveis 10.394.725 9.695.948 7,2% 2013 896,5" (1T10)
misturam a tabela com o grafico.

LAYOUTS ENCONTRADOS (4T09..4T19)
--------------------------------
  4T09-4T10  tabela em R$ MIL (cabecalho "R$ mil"); convertida p/ R$ milhoes.
             4T09 e 1T10 trazem uma unica linha "Custo de Construcao a Incorrer"
             no lugar de "Compromisso com custos orcados" -> vai para
             compromisso_custos_vendidas; estoque fica null. 2T10-4T10 ja
             trazem "Compromisso com custos orcados de unidades vendidas"
             (so vendidas; a linha de estoque nasce no 2T11).
  4T09-2T12  grafico "Cronograma de Recebiveis" POR ANO ("2010", "2011", ...,
             "Ate 2028" / "Apos 2017" / "Demais Anos") -> cronograma_por_ano
             (dict) e buckets de meses null. Em 4T10 e 1T11 o grafico e em
             PERCENTUAL ("(em %)") -> cronograma_por_ano_pct; nao ha valor em
             R$ para extrair (v_cronograma falha por construcao).
  3T12-4T12  buckets 12/24/36/Apos 36 meses, uma serie (conceito economico).
  1T13-4T19  duas series por bucket: Conceito Economico (campos padrao) e
             Base Caixa (cronograma_caixa_*). 1T13 traz uma TERCEIRA coluna
             "CPC" (cronograma_cpc_*; ver notas).
  2T12-4T13  linha "Unidades em processo de entrega" na tabela (null fora).
  1T15-1T19  "Compromisso ... unidades em estoque" aberto em "Fases lancadas"
             e "Fases nao lancadas" (compromisso_custos_estoque_lancadas /
             _nao_lancadas); o total continua em compromisso_custos_estoque.
  1T13       tabela com TRES colunas (1T13 pos-CPC, 1T13 "com efeito CPC" e
             4T12). Campos padrao = 1a coluna (pos-CPC, base que segue de 2T13
             em diante); 2a coluna em `base_pre_cpc`; comparativo = 3a coluna.

CONVENCOES
----------
  - Coluna do trimestre corrente = 1o numero apos o rotulo (ou na linha
    seguinte, quando o rotulo e quebrado). A coluna comparativa (2o numero)
    e guardada em `comparativo` para a checagem de encadeamento.
  - "-" na coluna corrente (ex.: "Unidades em processo de entrega - 65 119",
    "Fases nao lancadas - (17) n.a") e lido como 0,0 (convencao contabil;
    fecha as validacoes v_tabela / soma lancadas+nao lancadas).
  - compromisso_* sempre negativos (alguns releases imprimem sem parenteses
    ou com sinal de menos: 4T10, 4T13).
  - prazo_medio_meses: valor entre parenteses "(20 meses)" quando o texto
    traz; ate 3T11 o texto so diz "cerca de 2,4 anos" -> prazo_medio_anos e
    prazo_medio_meses = anos x 12 (marcado em prazo_medio_fonte).
  - receber_performado espelha unidades_construidas e alienacao_fiduciaria e
    null, como no parser original (compatibilidade de formato).

VALIDACOES (por trimestre)
  v_tabela     : |construcao + processo_entrega + construidas - total| <= 1
  v_liquido    : |total + vendidas + estoque - liquido| <= 1 (estoque=0 se null)
  v_cronograma : |soma dos buckets economicos (ou dos anos) - total| <= 1%

Uso:  python dados_receber_aging_hist.py             -> _receber_aging_hist.json
      python dados_receber_aging_hist.py --debug 4T11 -> linhas esq./dir. da pagina
      python dados_receber_aging_hist.py --imagem 1T13 -> rasteriza os graficos
"""

from __future__ import annotations

import json
import os
import re
import sys

import pdfplumber

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dados_receber_aging import norm, norm_map, read_txt, strip_acc  # noqa: E402

BASE = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(BASE, "fontes")
OUT = os.path.join(BASE, "_receber_aging_hist.json")

TRIMESTRES = ["4T09"] + [f"{t}T{a}" for a in range(10, 20) for t in (1, 2, 3, 4)]

# ------------------------------------------------------------------ numeros

_YEAR = re.compile(r"^(20[0-3]\d)$")


def parse_num(tok: str):
    """Um token numerico -> float, ou None. Aceita 12.020 / 1.065,7 (BR),
    5,082.0 (US, usado no grafico do 1T13), (3.663) e -3.130 (negativos).
    Percentuais devolvem None (nao sao valores)."""
    t = tok.strip()
    if not t or t.endswith("%"):
        return None
    neg = False
    if t.startswith("(") and t.endswith(")"):
        neg, t = True, t[1:-1]
    if t.startswith("-") and len(t) > 1:
        neg, t = True, t[1:]
    if not re.fullmatch(r"\d[\d.,]*", t):
        return None
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        raw = t.replace("." if dec == "," else ",", "").replace(dec, ".")
    elif "." in t:
        raw = t.replace(".", "") if re.fullmatch(r"\d{1,3}(\.\d{3})+", t) else t
    else:
        raw = t.replace(",", ".")
    try:
        v = float(raw)
    except ValueError:
        return None
    return -v if neg else v


def parse_pct(tok: str):
    t = tok.strip()
    if not t.endswith("%"):
        return None
    t = t[:-1].strip("()")
    try:
        return float(t.replace(".", "").replace(",", "."))
    except ValueError:
        return None


# ---------------------------------------------------- linhas e colunas

def page_rows_words(page, ytol: float = 1.0, gap: float = 1.0):
    """Linhas da pagina como listas de palavras {text,x0,x1,top}."""
    chars = [c for c in page.chars if c["text"].strip()]
    chars.sort(key=lambda c: (round(c["top"], 1), c["x0"]))
    grouped, cur, cur_top = [], [], None
    for c in chars:
        if cur_top is None:
            cur_top, cur = c["top"], [c]
        elif abs(c["top"] - cur_top) <= ytol:
            cur.append(c)
        else:
            grouped.append((cur_top, cur))
            cur_top, cur = c["top"], [c]
    if cur:
        grouped.append((cur_top, cur))

    rows = []
    for top, cs in grouped:
        cs = sorted(cs, key=lambda c: c["x0"])
        words, buf = [], [cs[0]]
        for c in cs[1:]:
            if c["x0"] - buf[-1]["x1"] > gap:
                words.append(buf)
                buf = [c]
            else:
                buf.append(c)
        words.append(buf)
        rows.append({"top": top, "words": [
            {"text": "".join(b["text"] for b in w), "x0": w[0]["x0"], "x1": w[-1]["x1"], "top": top}
            for w in words]})
    return rows


def row_text(words):
    return " ".join(w["text"] for w in words)


def guess_page(tri: str):
    txt = read_txt(os.path.join(FONTES, f"release_{tri}.txt"))
    if not txt:
        return None
    for i, p in enumerate(txt.split("\f")):
        if re.search(r"unidades\s+em\s+constru", p, re.I) and re.search(r"contas\s+a\s+receber", p, re.I):
            return i
    return None


def is_section(page) -> bool:
    n = norm("".join(c["text"] for c in page.chars))
    return "contasareceber" in n and "unidadesemconstrucao" in n and "totaldosrecebiveis" in n


def find_page(pdf, tri: str):
    g = guess_page(tri)
    ordem = [g + d for d in (0, 1, -1, 2, -2)] if g is not None else []
    ordem += list(range(len(pdf.pages)))
    vistos = set()
    for i in ordem:
        if i in vistos or not (0 <= i < len(pdf.pages)):
            continue
        vistos.add(i)
        if is_section(pdf.pages[i]):
            return i
    return None


CHART_LABELS = {"12", "24", "36", "12meses", "24meses", "36meses", "apos", "apos36",
                "apos36meses", "ate", "demais"}


def find_title(rows):
    """(top, x0) da palavra 'Cronograma' do titulo 'Cronograma de Recebiveis'."""
    for r in rows:
        if "cronogramaderecebiveis" not in norm(row_text(r["words"])):
            continue
        ws = r["words"]
        for i in range(len(ws)):
            if norm("".join(w["text"] for w in ws[i:])).startswith("cronogramaderecebiveis"):
                return r["top"], ws[i]["x0"]
    # Sem titulo na camada de texto (1T13, 2T13, 4T13, 1T14, 2T14: o titulo e
    # desenho). Os tres graficos vem na ordem custo-vendidas, custo-estoque,
    # recebiveis, entao a ULTIMA linha "12 Meses" da pagina e a do grafico de
    # recebiveis: ancoramos 1pt acima dela, no x do rotulo.
    last = None
    for r in rows:
        ws = r["words"]
        for i in range(len(ws)):
            if norm("".join(w["text"] for w in ws[i:])).startswith("12meses"):
                last = (r["top"] - 1.0, ws[i]["x0"])
                break
    if last:
        return last
    return None, None


def column_split(rows, page_width):
    """x que separa tabela/texto (esq.) dos graficos (dir.).

    Usa o rotulo de barra mais a esquerda abaixo do titulo do grafico de
    recebiveis: palavra em CHART_LABELS ou um ano, seguida de um valor (ou de
    um ano / 'anos'), separada da palavra anterior por um vao de coluna.
    """
    ttop, tx0 = find_title(rows)
    if ttop is None:
        return page_width * 0.55, None, "titulo ausente; split=55% da largura"
    cands = []
    for r in rows:
        if r["top"] <= ttop:
            continue
        ws = r["words"]
        for i, w in enumerate(ws):
            t = norm(w["text"])
            if not (t in CHART_LABELS or _YEAR.match(t)):
                continue
            if not (tx0 - 100 <= w["x0"] <= tx0 + 80):
                continue
            if i > 0 and w["x0"] - ws[i - 1]["x1"] < 8:
                continue
            nxt = ws[i + 1] if i + 1 < len(ws) else None
            if nxt is None:
                continue
            nt = norm(nxt["text"])
            if parse_num(nxt["text"]) is not None or parse_pct(nxt["text"]) is not None \
                    or _YEAR.match(nt) or nt in ("anos", "meses", "36", "36meses"):
                cands.append(w["x0"])
    if not cands:
        return tx0 - 10, ttop, "sem rotulos de barra; split=titulo-10"
    return min(cands) - 2.0, ttop, None


def split_rows(rows, split):
    left, right = [], []
    for r in rows:
        lw = [w for w in r["words"] if w["x0"] < split]
        rw = [w for w in r["words"] if w["x0"] >= split]
        if lw:
            left.append({"top": r["top"], "words": lw, "text": row_text(lw)})
        if rw:
            right.append({"top": r["top"], "words": rw, "text": row_text(rw)})
    return left, right


# ------------------------------------------------------------------ tabela

LABELS = [
    ("unidadesemconstrucao", "unidades_em_construcao"),
    ("unidadesemprocessodeentrega", "unidades_em_processo_entrega"),
    ("unidadesconstruidas", "unidades_construidas"),
    ("unidadesentregues", "unidades_construidas"),          # 2T12
    ("totaldosrecebiveis", "total_recebiveis"),
    ("compromissocomcustos", "compromisso"),
    ("custodeconstrucaoaincorrer", "compromisso_custos_vendidas"),  # 4T09, 1T10
    ("contasareceberliquido", "contas_receber_liquido"),
]


def label_of(n: str):
    for key, campo in LABELS:
        if n.startswith(key):
            return campo
    return None


def row_values(words):
    """Valores numericos de uma linha na ordem; '-' isolado vale 0.0."""
    vals = []
    toks = [w["text"] for w in words]
    for i, tok in enumerate(toks):
        v = parse_num(tok)
        if v is not None:
            vals.append(v)
            continue
        if tok == "-":
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            if nxt is None or parse_num(nxt) is not None or nxt in ("-", "n.a", "n.a."):
                vals.append(0.0)
    return vals


def parse_tabela(left):
    """Le a tabela 'Contas a receber' (1a ocorrencia) a partir das linhas da
    coluna esquerda. Devolve (dados, comparativo, unidade, extras)."""
    # Ancora = 1a linha "Total dos Recebiveis" COM numero; a tabela comeca na
    # ultima linha "Unidades em construcao" acima dela (ate 60pt). Isso evita
    # confundir com o paragrafo "...unidades em construcao. O prazo medio de
    # realizacao ... e de cerca de 2,3 anos" (que faria construcao = 2,3).
    anchor = None
    for i, r in enumerate(left):
        if norm(r["text"]).startswith("totaldosrecebiveis") and row_values(r["words"]):
            anchor = i
            break
    if anchor is None:
        return {}, {}, None, {}
    start = None
    for i in range(anchor - 1, -1, -1):
        if left[anchor]["top"] - left[i]["top"] > 60:
            break
        if norm(left[i]["text"]).startswith("unidadesemconstrucao"):
            start = i
            break
    if start is None:
        return {}, {}, None, {}

    groups = []          # [campo, [textos], [valores]]
    for r in left[start:]:
        n = norm(r["text"])
        campo = label_of(n)
        if campo is not None:
            groups.append([campo, [n], row_values(r["words"])])
        elif groups:
            groups[-1][1].append(n)
            groups[-1][2].extend(row_values(r["words"]))
        if campo == "contas_receber_liquido":
            break

    # unidade: "R$ mil" no cabecalho (ate 45pt acima da 1a linha) -> /1000
    top0 = left[start]["top"]
    unidade = "R$ MM"
    for r in left:
        if top0 - 45 <= r["top"] <= top0 and "r$mil" in norm(r["text"]):
            unidade = "R$ mil"
    fator = 0.001 if unidade == "R$ mil" else 1.0

    dados, comp, extras = {}, {}, {}
    for campo, texts, vals in groups:
        blob = "".join(texts)
        if campo == "compromisso":
            if "vendidas" in blob:
                campo = "compromisso_custos_vendidas"
            elif "estoque" in blob and ("fasesnao" in blob or "naolancadas" in blob):
                campo = "compromisso_custos_estoque_nao_lancadas"
            elif "estoque" in blob and "lancadas" in blob:
                campo = "compromisso_custos_estoque_lancadas"
            elif "estoque" in blob:
                campo = "compromisso_custos_estoque"
            else:
                continue
        if campo in dados:            # so a 1a tabela da pagina (1T13 tem duas)
            continue
        vals = [round(v * fator, 3) for v in vals]
        if campo.startswith("compromisso"):
            vals = [-abs(v) if v else 0.0 for v in vals]
        if len(vals) >= 3 and campo != "unidades_em_processo_entrega":
            # 1T13: colunas = [1T13 pos-CPC, 1T13 com efeito CPC, 4T12]
            extras.setdefault("base_pre_cpc", {})[campo] = vals[1]
            dados[campo] = vals[0]
            comp[campo] = vals[2]
        else:
            dados[campo] = vals[0] if vals else None
            comp[campo] = vals[1] if len(vals) > 1 else None
    if len(groups) >= 1 and "base_pre_cpc" in extras and "unidades_em_processo_entrega" in dados:
        # na tabela de 3 colunas a linha "processo de entrega" tambem tem 3
        for campo, texts, vals in groups:
            if campo == "unidades_em_processo_entrega" and len(vals) >= 3:
                extras["base_pre_cpc"][campo] = vals[1]
                comp[campo] = vals[2]
    return dados, comp, unidade, extras


# --------------------------------------------------------------- graficos

BUCKETS = [("12m", "12meses"), ("24m", "24meses"), ("36m", "36meses"), ("apos36", "apos36meses")]


def bucket_pos(n: str, key: str):
    start = 0
    while True:
        p = n.find(key, start)
        if p < 0:
            return None
        if key == "36meses" and n[max(0, p - 4):p] == "apos":
            start = p + 1
            continue
        return p


def numbers_only(row) -> bool:
    return bool(row["words"]) and all(parse_num(w["text"]) is not None for w in row["words"])


def parse_buckets(right, ttop):
    """Buckets 12/24/36/Apos 36 meses abaixo do titulo; ate 3 series por linha."""
    rows = [r for r in right if r["top"] > ttop]
    out, alvo = {}, 0
    for i, r in enumerate(rows):
        while alvo < len(BUCKETS):
            campo, key = BUCKETS[alvo]
            n, idx = norm_map(r["text"])
            p = bucket_pos(n, key)
            if p is None:
                break
            end = p + len(key) - 1
            cut = idx[end] + 1 if end < len(idx) else len(r["text"])
            nums = [parse_num(t) for t in r["text"][cut:].split()]
            nums = [v for v in nums if v is not None]
            if not nums:                       # valor na linha vizinha
                for j in (i + 1, i - 1):
                    if 0 <= j < len(rows) and abs(rows[j]["top"] - r["top"]) <= 6 and numbers_only(rows[j]):
                        nums = [parse_num(w["text"]) for w in rows[j]["words"]]
                        break
            if not nums:
                break
            out[campo] = nums
            alvo += 1
            break
        if alvo >= len(BUCKETS):
            break
    return out


def parse_por_ano(right, ttop):
    """Grafico por ano (4T09..2T12). Devolve (dict rotulo->valor, em_pct)."""
    rows = [r for r in right if r["top"] > ttop]
    out, pct_mode = {}, False
    prefix = label = val = None
    stop = False
    for r in rows:
        n = norm(r["text"])
        if n.startswith("("):
            if "em%" in n:
                pct_mode = True
            continue
        for w in r["words"]:
            t = norm(w["text"])
            if t in ("ate", "apos", "demais"):
                prefix = {"ate": "Até", "apos": "Após", "demais": "Demais"}[t]
            elif _YEAR.match(t) or t == "anos":
                lab = w["text"] if t != "anos" else "anos"
                label = f"{prefix} {lab}" if prefix else lab
            elif parse_pct(w["text"]) is not None:
                val, pct_mode = parse_pct(w["text"]), True
            elif parse_num(w["text"]) is not None:
                val = parse_num(w["text"])
            else:
                stop = True
                break
            if label is not None and val is not None:
                out[label] = val
                done_last = prefix is not None
                prefix = label = val = None
                if done_last:
                    stop = True
                    break
        if stop:
            break
    return out, pct_mode


# ------------------------------------------------------------------ texto

def parse_texto(left):
    """Texto corrido: usa so as palavras da coluna esquerda, senao os rotulos
    do grafico se intercalam ('cerca de' / '6,7' / 'Apos 36 Meses' / '1,5 ano')."""
    blob = " ".join(r["text"] for r in left)
    flat = re.sub(r"\s+", " ", strip_acc(blob)).lower()
    d = {"prazo_medio_meses": None, "prazo_medio_anos": None, "prazo_medio_fonte": None,
         "pct_unidades_entregues": None}
    m = re.search(r"cerca de\s*(\d+[.,]?\d*)\s*anos?", flat)
    if m:
        d["prazo_medio_anos"] = float(m.group(1).replace(",", "."))
    m = re.search(r"\(\s*(\d+[.,]?\d*)\s*meses\s*\)", flat)
    if m:
        d["prazo_medio_meses"] = float(m.group(1).replace(".", "").replace(",", "."))
        d["prazo_medio_fonte"] = "meses entre parenteses no texto"
    elif d["prazo_medio_anos"] is not None:
        d["prazo_medio_meses"] = round(d["prazo_medio_anos"] * 12, 1)
        d["prazo_medio_fonte"] = "anos x 12 (texto so traz anos)"
    m = re.search(r"desse total,?\s*(\d+[.,]?\d*)\s*%\s*refere", flat)
    if m:
        d["pct_unidades_entregues"] = float(m.group(1).replace(",", "."))
    return d


# --------------------------------------------------------------- overrides
# Nenhum trimestre precisou de leitura visual: todas as 41 paginas tem camada
# de texto nos graficos. O mecanismo fica disponivel (mesma semantica do
# parser original: so aplica quando os campos vieram vazios da camada de texto).
OVERRIDES: dict = {}
OVERRIDE_FONTE = "grafico em imagem, lido do PDF rasterizado (nao ha camada de texto)"

CAMPOS = [
    "unidades_em_construcao", "unidades_em_processo_entrega", "unidades_construidas",
    "total_recebiveis",
    "compromisso_custos_vendidas", "compromisso_custos_estoque",
    "compromisso_custos_estoque_lancadas", "compromisso_custos_estoque_nao_lancadas",
    "contas_receber_liquido",
    "cronograma_12m", "cronograma_24m", "cronograma_36m", "cronograma_apos36",
    "cronograma_total",
    "cronograma_caixa_12m", "cronograma_caixa_24m", "cronograma_caixa_36m",
    "cronograma_caixa_apos36", "cronograma_caixa_total",
    "cronograma_por_ano", "cronograma_por_ano_pct",
    "receber_performado", "alienacao_fiduciaria",
    "prazo_medio_meses", "prazo_medio_anos", "prazo_medio_fonte",
    "pct_unidades_entregues",
    "comparativo",
]


def parse_release(tri: str):
    pdf_path = os.path.join(FONTES, f"release_{tri}.pdf")
    if not os.path.exists(pdf_path):
        return None, {"erro": "pdf ausente"}
    with pdfplumber.open(pdf_path) as pdf:
        pg = find_page(pdf, tri)
        if pg is None:
            return None, {"erro": "secao CONTAS A RECEBER nao localizada"}
        page = pdf.pages[pg]
        rows = page_rows_words(page)
        n_img = len(page.images)
        width = page.width

    split, ttop, aviso = column_split(rows, width)
    left, right = split_rows(rows, split)

    rec = {c: None for c in CAMPOS}
    tab, comp, unidade, extras = parse_tabela(left)
    rec.update(tab)
    rec["comparativo"] = comp
    for k, v in extras.items():
        rec[k] = v

    modo = None
    if ttop is not None:
        b = parse_buckets(right, ttop)
        if b:
            modo = "buckets"
            for campo, _ in BUCKETS:
                nums = b.get(campo, [])
                rec[f"cronograma_{campo}"] = nums[0] if nums else None
                if len(nums) > 1:
                    rec[f"cronograma_caixa_{campo}"] = nums[1]
                if len(nums) > 2:
                    rec.setdefault("cronograma_cpc", {})[campo] = nums[2]
        else:
            anos, pct = parse_por_ano(right, ttop)
            if anos:
                modo = "por_ano_pct" if pct else "por_ano"
                rec["cronograma_por_ano_pct" if pct else "cronograma_por_ano"] = anos

    rec.update(parse_texto(left))

    fonte = "camada de texto do PDF"
    if tri in OVERRIDES and all(rec.get(k) is None for k in OVERRIDES[tri]):
        rec.update(OVERRIDES[tri])
        fonte = OVERRIDE_FONTE

    rec["receber_performado"] = rec["unidades_construidas"]

    eco = [rec[f"cronograma_{c}"] for c, _ in BUCKETS]
    if all(v is not None for v in eco):
        rec["cronograma_total"] = round(sum(eco), 1)
    elif rec["cronograma_por_ano"]:
        rec["cronograma_total"] = round(sum(rec["cronograma_por_ano"].values()), 1)
    cx = [rec[f"cronograma_caixa_{c}"] for c, _ in BUCKETS]
    if all(v is not None for v in cx):
        rec["cronograma_caixa_total"] = round(sum(cx), 1)

    meta = {"pagina_pdf": pg, "split_x": round(split, 1), "modo_cronograma": modo,
            "unidade_tabela": unidade, "imagens_na_pagina": n_img,
            "fonte_cronograma": fonte}
    if aviso:
        meta["aviso"] = aviso
    return rec, meta


def validar(rec):
    v = {}
    tot, cron = rec.get("total_recebiveis"), rec.get("cronograma_total")
    v["v_cronograma"] = (tot is not None and cron is not None
                         and abs(cron - tot) <= max(1.0, 0.01 * tot))
    a, pe, bb = (rec.get("unidades_em_construcao"), rec.get("unidades_em_processo_entrega"),
                 rec.get("unidades_construidas"))
    v["v_tabela"] = (None not in (a, bb, tot) and abs(a + (pe or 0.0) + bb - tot) <= 1)
    cv, ce, liq = (rec.get("compromisso_custos_vendidas"), rec.get("compromisso_custos_estoque"),
                   rec.get("contas_receber_liquido"))
    v["v_liquido"] = (None not in (cv, liq, tot) and abs(tot + cv + (ce or 0.0) - liq) <= 1)
    return v


COMPARA_COM = {"4T10": "4T09"}   # release anual compara com dez/2009


def encadeamento(dados):
    """Compara a coluna comparativa de cada release com o valor corrente do
    release anterior. Devolve (n_ok, n_total, quebras[])."""
    campos = ["unidades_em_construcao", "unidades_construidas", "total_recebiveis"]
    ok = tot = 0
    quebras, reclass = [], []
    for prev, cur in zip(TRIMESTRES, TRIMESTRES[1:]):
        # 4T10 e o release anual: a coluna comparativa e "2009" (= 4T09), nao 3T10.
        prev = COMPARA_COM.get(cur, prev)
        comp = dados[cur].get("comparativo") or {}
        pe = dados[prev].get("unidades_em_processo_entrega") or 0.0
        cpe = comp.get("unidades_em_processo_entrega") or 0.0
        for c in campos:
            a, b = dados[prev].get(c), comp.get(c)
            if a is None or b is None:
                continue
            tot += 1
            if abs(a - b) <= 1.0:
                ok += 1
            elif pe and c != "total_recebiveis" and abs(a + pe - b) <= 1.0:
                # a linha "Unidades em processo de entrega" do release anterior
                # foi somada a esta linha na coluna comparativa (reclassificacao,
                # total inalterado) — nao e restatement.
                ok += 1
                reclass.append(f"{cur}: {c} de {prev} = {a} + processo de entrega {pe} = {b}")
            elif cpe and c != "total_recebiveis" and abs(a - cpe - b) <= 1.0:
                # sentido inverso: o release seguinte reabre a linha "processo de
                # entrega" e a separa desta linha na coluna comparativa.
                ok += 1
                reclass.append(f"{cur}: {c} de {prev} = {a} = {b} + processo de entrega {cpe}")
            else:
                quebras.append(f"{cur} restata {c} de {prev}: {a} -> {b}")
    return ok, tot, quebras, reclass


def main():
    if "--imagem" in sys.argv:
        tri = sys.argv[sys.argv.index("--imagem") + 1]
        with pdfplumber.open(os.path.join(FONTES, f"release_{tri}.pdf")) as pdf:
            pg = find_page(pdf, tri)
            p = pdf.pages[pg]
            dest = os.path.join(BASE, f"_cronograma_{tri}.png")
            p.crop((p.width * 0.5, 0, p.width, p.height)).to_image(resolution=400).save(dest)
        print("->", dest)
        return

    if "--debug" in sys.argv:
        tri = sys.argv[sys.argv.index("--debug") + 1]
        with pdfplumber.open(os.path.join(FONTES, f"release_{tri}.pdf")) as pdf:
            pg = find_page(pdf, tri)
            page = pdf.pages[pg]
            rows = page_rows_words(page)
            split, ttop, aviso = column_split(rows, page.width)
            print(f"{tri}: pagina {pg} split={split:.1f} titulo_top={ttop} {aviso or ''}")
            left, right = split_rows(rows, split)
            print("--- ESQUERDA")
            for r in left:
                print(round(r["top"], 1), repr(r["text"]))
            print("--- DIREITA")
            for r in right:
                print(round(r["top"], 1), repr(r["text"]))
        return

    dados, metas, vals = {}, {}, {}
    for tri in TRIMESTRES:
        rec, meta = parse_release(tri)
        if rec is None:
            rec = {c: None for c in CAMPOS}
        dados[tri], metas[tri] = rec, meta
        vals[tri] = validar(rec)
        st = vals[tri]
        print(f"{tri}  pg={meta.get('pagina_pdf')}  modo={meta.get('modo_cronograma')}  "
              f"tot={rec['total_recebiveis']}  cron={rec['cronograma_total']}  "
              f"cron_ok={st['v_cronograma']} tab_ok={st['v_tabela']} liq_ok={st['v_liquido']}")

    n_ok, n_tot, quebras, reclass = encadeamento(dados)

    notas = [
        "Serie historica 4T09..4T19 (41 trimestres) no mesmo formato de _receber_aging.json. "
        "Campos extras: unidades_em_processo_entrega (2T12-4T13), compromisso_custos_estoque_"
        "lancadas/_nao_lancadas (1T15-1T19), cronograma_caixa_* (1T13-4T19), cronograma_por_ano "
        "(4T09-2T12), cronograma_por_ano_pct (4T10, 1T11), comparativo (coluna comparativa da "
        "tabela, como impressa), prazo_medio_anos/prazo_medio_fonte.",
        "UNIDADE: 4T09-4T10 a tabela e em R$ mil (cabecalho 'R$ mil'); valores divididos por "
        "1.000 (3 casas). De 1T11 em diante a tabela ja vem em R$ MM.",
        "4T09 e 1T10: a tabela traz uma unica linha 'Custo de Construcao a Incorrer' -> "
        "compromisso_custos_vendidas; compromisso_custos_estoque = null. 2T10-1T11 trazem so "
        "'Compromisso com custos orcados de unidades vendidas' (estoque null); a linha de "
        "estoque surge no 2T11. v_liquido nesses trimestres usa estoque = 0 e fecha.",
        "CRONOGRAMA POR ANO (4T09-2T12): grafico 'Cronograma de Recebiveis' por ano-calendario "
        "('2010'...'2017', 'Ate 2028'/'Ate 2030'/'Apos 2017'/'Apos 2013'/'Apos 2014'/'Demais "
        "Anos'); guardado em cronograma_por_ano, buckets de meses null. v_cronograma compara a "
        "soma dos anos com o total.",
        "4T10 e 1T11: o grafico e em PERCENTUAL ('(em %)'), sem valor em R$; guardado em "
        "cronograma_por_ano_pct e v_cronograma falha por construcao (nada em R$ para somar). "
        "Nao foi derivado pct x total para nao inventar numero.",
        "4T09-3T11: o texto so informa o prazo medio em anos ('cerca de 3,0 anos'); "
        "prazo_medio_meses = anos x 12 (prazo_medio_fonte marca). De 1T12 em diante o texto "
        "traz os meses entre parenteses.",
        "'-' na coluna corrente lido como 0,0: 1T13 'Unidades em processo de entrega -' e 1T19 "
        "'Fases nao lancadas -' (fecham v_tabela e lancadas + nao lancadas = estoque).",
        "1T13 (adocao do CPC 19 R2 / IFRS 11): a tabela tem 3 colunas — 1T13 pos-CPC "
        "(campos padrao; base que continua de 2T13 em diante), 1T13 'com efeito CPC' "
        "(base_pre_cpc: total 11.513, comparavel ao 4T12 de 12.020) e 4T12 (comparativo). O "
        "grafico tambem traz uma 3a coluna 'CPC' por bucket (cronograma_cpc), cuja soma bate "
        "exatamente com o total pos-CPC de 11.135. Os campos padrao cronograma_* sao a serie "
        "'Conceito economico' (1a coluna do grafico, formato US '5,082.0').",
        "QUEBRA DE SERIE 2T13: a coluna comparativa de 1T13 (9.130 / 2.017 / 11.147) nao "
        "reproduz nem a base pos-CPC (9.349 / 1.786 / 11.135) nem a base 'com efeito' do "
        "release do 1T13.",
        "1T13-1T19: a soma dos buckets do Conceito Economico fica em ~84-88% do 'Total dos "
        "Recebiveis' (ex.: 4T13 9.016 vs 10.639; 4T17 3.508 vs 4.198) e a soma da Base Caixa "
        "fica ACIMA do total (juros/correcao). O release nao explica a diferenca (hipotese: "
        "grafico em %CBR); v_cronograma falha nesses trimestres por isso, nao por erro de "
        "leitura. 3T12-4T12 e 2T19-4T19 fecham com o total.",
        "1T19: o grafico nao imprime o valor da Base Caixa em 'Apos 36 Meses' (barra sem "
        "rotulo, conferido no PDF rasterizado) -> cronograma_caixa_apos36 = null e "
        "cronograma_caixa_total = null.",
        "2T17: a coluna comparativa e '1T17 (pro-forma)': Unidades em construcao 3.826 -> 3.859, "
        "construidas 1.319 -> 1.116, Total 5.145 -> 4.974 (restatement da companhia).",
        "1T11: a coluna comparativa (2010, ja em R$ MM) restata o 4T10: construcao 10.325 -> "
        "10.055, total 12.171 -> 11.901 (mesmas 'Unidades construidas' 1.846). Provavel "
        "adocao do IFRS/CPC nas DFs de 2010.",
        f"Encadeamento: em {n_ok} de {n_tot} comparacoes (3 campos x 40 pares) a coluna "
        f"comparativa do release seguinte reproduz (<=1) o valor extraido do anterior "
        f"(4T10, release anual, compara com dez/2009 = 4T09). Quebras: {quebras}",
        "Reclassificacoes (nao sao restatement; o total nao muda): a linha 'Unidades em "
        "processo de entrega' e somada a construcao/construidas na coluna comparativa do "
        f"release seguinte, ou reaberta a partir dela: {reclass}",
        "receber_performado espelha 'Unidades construidas' e alienacao_fiduciaria e null, "
        "como no parser original (compatibilidade de formato).",
    ]

    payload = {
        "_meta": {
            "fonte": "releases trimestrais Cyrela (fontes/release_*.pdf), secao CONTAS A RECEBER, 4T09..4T19",
            "unidade": "R$ milhoes (exceto prazo_medio_* e pct_unidades_entregues em %; "
                       "cronograma_por_ano_pct em %)",
            "campos": CAMPOS,
            "paginas": metas,
            "encadeamento": {"ok": n_ok, "total": n_tot, "quebras": quebras,
                             "reclassificacoes": reclass},
            "notas": notas,
        },
        "validacoes": vals,
        "dados": dados,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    print(f"\nencadeamento: {n_ok}/{n_tot} ok")
    for q in quebras:
        print("  quebra:", q)
    for q in reclass:
        print("  reclass:", q)
    print("->", OUT)


if __name__ == "__main__":
    main()
