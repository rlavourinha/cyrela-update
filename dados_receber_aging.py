# -*- coding: utf-8 -*-
"""
Extrai, release a release (1T20..2T26), a secao "CONTAS A RECEBER" dos releases
trimestrais da Cyrela: a tabela de recebiveis totais e o CRONOGRAMA DE RECEBIMENTO
(aging) por faixa de prazo.

POR QUE LER O PDF E NAO O .TXT
------------------------------
Os arquivos fontes/release_*.txt (pdftotext -layout) embaralham as linhas nos
releases antigos (1T20..4T22): o rotulo fica numa linha e os numeros noutra
(ex.: em 1T22 "Unidades em construcao" aparece sem valor e os valores descem uma
linha, o que faria o parser atribuir 5.902 a "Unidades construidas"). Alem disso
os graficos de barras tem os rotulos e os valores em camadas de texto sobrepostas.

Aqui reconstruimos as linhas direto dos glifos do PDF (pdfplumber .chars):
  1. agrupa chars por coordenada vertical (`top`) com tolerancia de 1pt;
  2. dentro da linha, ordena por x e insere espaco so quando o gap horizontal
     entre glifos passa de 1pt.
O passo 2 e o que conserta os numeros quebrados por espacos de largura zero
(no 2T26 o texto bruto traz "1 8.685"; com gap-awareness vira "18.685") e ao
mesmo tempo separa a coluna de variacao colada no valor ("16.5753%" -> "16.575",
"3%"). Rotulo e valor de cada barra do grafico caem na mesma linha reconstruida
("12 Meses 7.552"), o que resolve a associacao rotulo->valor sem heuristica.

DE ONDE VEM CADA CAMPO
----------------------
Tabela "Contas a receber" (coluna do trimestre corrente = 1o numero apos o rotulo):
  unidades_em_construcao        <- linha "Unidades em construcao"
  unidades_construidas          <- linha "Unidades construidas"  (unidades ja
                                   entregues; e o recebivel de obra concluida)
  total_recebiveis              <- linha "Total dos Recebiveis"
  compromisso_custos_vendidas   <- 1a linha com numeros entre parenteses
                                   ("Compromisso com custos orcados ... unidades vendidas")
  compromisso_custos_estoque    <- 2a linha com numeros entre parenteses
                                   ("... unidades em estoque")
  contas_receber_liquido        <- linha "Contas a Receber Liquido"

Grafico "Cronograma de Recebiveis (em R$ milhoes)" — buckets lidos nas linhas
apos o titulo do grafico; o valor e o 1o numero a direita do rotulo da barra:
  cronograma_12m, cronograma_24m, cronograma_36m, cronograma_apos36
  cronograma_total              <- soma dos 4 buckets (calculado, nao lido)

ATENCAO: na mesma pagina existem DOIS graficos "Cronograma do Custo a Incorrer"
(saida de caixa: unidades vendidas e unidades em estoque), com os mesmos rotulos
de prazo. Eles sao ignorados por construcao: so lemos buckets que aparecem ABAIXO
do titulo "Cronograma de Recebiveis" (que vem por ultimo na pagina em todos os
trimestres). Os totais dos dois graficos de custo batem com as linhas
"Compromisso com custos orcados" da tabela — usamos isso no diagnostico.

Texto corrido da secao:
  prazo_medio_meses             <- "... de cerca de X anos (YY,Y meses)"
  pct_unidades_entregues        <- "Desse total, N% refere-se a unidades entregues"

Recebivel performado:
  receber_performado            <- ESPELHA `unidades_construidas`. O release nunca
       usa a palavra "performado" para um saldo (so em EVENTOS SUBSEQUENTES, ao
       descrever o lastro de CRIs da CashMe). Mas a nota de risco de mercado do
       ITR/DFP quantifica a "Carteira performada" e ela bate EXATAMENTE com a
       linha "Unidades construidas" do release:
           2T26  ITR  "Carteira performada 1.563.246" (R$ mil) = 1.563 -> release 1.563
           4T25  DFP  "Carteira performada 1.505.006" (R$ mil) = 1.505 -> release 1.505
       E a mesma coisa por definicao: recebivel de unidade ja concluida/entregue,
       corrigido por IGP-M + 12% a.a. (o resto da carteira e "nao performada",
       corrigida por INCC). Por isso o campo e preenchido, e nao inventado — o
       valor sai da linha "Unidades construidas" do proprio release.

Campo ausente (null em todos os trimestres):
  alienacao_fiduciaria          <- a expressao "alienacao fiduciaria" NAO ocorre em
       nenhum dos 26 releases (0 ocorrencias de "fiduc"). ITR e DFP citam alienacao
       fiduciaria apenas de forma descritiva, na politica de garantias do repasse
       ("a unidade concluida e dada em garantia por meio de alienacao fiduciaria a
       IF"), sem quantificar quanto da carteira esta nessa condicao. Nao ha numero
       para extrair — fica null.

QUEBRAS DE SERIE CONHECIDAS (nao sao erro de extracao; ver `_meta.notas`)
  3T20: a coluna comparativa vem rotulada "2T20 (pro forma)" e traz Total dos
        Recebiveis de 4.354 contra os 5.194 que o proprio release do 2T20 havia
        reportado. E restatement da companhia (desconsolidacao), nao erro daqui.
  3T25: a coluna comparativa restata "Unidades em construcao" do 2T25 de 14.051
        para 14.079 (Total 15.069 -> 15.097). Diferenca de 0,2%.
  Nos outros 23 encadeamentos a coluna comparativa do release seguinte bate
  exatamente (<=1) com o valor corrente extraido do release anterior — 70 de 75
  comparacoes (3 campos x 25 pares) conferem.

VALIDACOES (rodadas por trimestre, ver bloco "validacoes" do JSON)
  v_cronograma : |soma dos 4 buckets - total_recebiveis| <= 1% do total
  v_tabela     : |construcao + construidas - total_recebiveis| <= 1
  v_liquido    : |total - |vendidas| - |estoque| - liquido| <= 1
Um trimestre so conta como "validado" se passa em v_cronograma (o teste pedido).

Uso:  python dados_receber_aging.py            -> escreve _receber_aging.json
      python dados_receber_aging.py --debug 1T22  -> imprime as linhas da pagina
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

import pdfplumber

BASE = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.join(BASE, "fontes")
OUT = os.path.join(BASE, "_receber_aging.json")

TRIMESTRES = [f"{t}T{a}" for a in range(20, 27) for t in (1, 2, 3, 4)]
TRIMESTRES = [q for q in TRIMESTRES if q not in ("3T26", "4T26")]  # ate 2T26

# ---------------------------------------------------------------- utilidades

_NUM = re.compile(r"\(?-?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?\)?%?")


def strip_acc(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def norm_map(s: str):
    """Devolve (texto normalizado sem acento/espaco/caixa, indices p/ o original)."""
    out, idx = [], []
    for i, ch in enumerate(s):
        for c in strip_acc(ch).lower():
            if c.isspace():
                continue
            out.append(c)
            idx.append(i)
    return "".join(out), idx


def norm(s: str) -> str:
    return norm_map(s)[0]


def numbers(s: str):
    """Numeros no padrao BR (ponto=milhar, virgula=decimal). Ignora percentuais."""
    out = []
    for m in _NUM.finditer(s):
        tok = m.group(0)
        if tok.endswith("%"):
            continue
        neg = tok.startswith("(") or tok.startswith("-")
        raw = tok.strip("()-").replace(".", "").replace(",", ".")
        if not raw:
            continue
        try:
            v = float(raw)
        except ValueError:
            continue
        out.append(-v if neg else v)
    return out


def after_label(text: str, label: str):
    """Numeros que aparecem depois de `label` (comparacao sem acento/espaco)."""
    n, idx = norm_map(text)
    p = n.find(label)
    if p < 0:
        return None
    end = p + len(label) - 1
    cut = idx[end] + 1 if end < len(idx) else len(text)
    return numbers(text[cut:])


# ------------------------------------------------- reconstrucao das linhas

def page_rows(page, ytol: float = 1.0, gap: float = 1.0):
    """Linhas da pagina reconstruidas a partir dos glifos (ver docstring)."""
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
        parts, prev = [], None
        for c in cs:
            if prev is not None and c["x0"] - prev["x1"] > gap:
                parts.append(" ")
            parts.append(c["text"])
            prev = c
        rows.append({"top": top, "text": "".join(parts)})
    return rows


def read_txt(path: str) -> str:
    for enc in ("utf-8", "cp1252"):
        try:
            with open(path, encoding=enc) as fh:
                return fh.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return ""


def guess_page(tri: str) -> int | None:
    """Estimativa da pagina (0-based) da secao CONTAS A RECEBER via o .txt."""
    txt = read_txt(os.path.join(FONTES, f"release_{tri}.txt"))
    if not txt:
        return None
    if "===== PAGINA" in txt:                       # layout novo (1T23+)
        blocos = re.split(r"===== PAGINA (\d+) =====", txt)
        for i in range(1, len(blocos), 2):
            corpo = blocos[i + 1]
            if "CONTAS A RECEBER" in corpo and "Considerando a totalidade" in corpo:
                return int(blocos[i]) - 1
    else:                                            # layout antigo (\f)
        for i, p in enumerate(txt.split("\f")):
            if "CONTAS A RECEBER" in p and "Considerando a totalidade" in p:
                return i
    return None


def find_page(pdf, tri: str):
    """Pagina da secao: usa a estimativa do .txt e confere nos glifos do PDF."""
    guess = guess_page(tri)
    ordem = []
    if guess is not None:
        ordem = [guess] + [guess + d for d in (1, -1, 2, -2, 3, -3)]
    ordem += list(range(len(pdf.pages)))
    vistos = set()
    for i in ordem:
        if i in vistos or not (0 <= i < len(pdf.pages)):
            continue
        vistos.add(i)
        n = norm("".join(c["text"] for c in pdf.pages[i].chars))
        if "contasareceber" in n and "considerandoatotalidade" in n:
            return i
    return None


# ----------------------------------------------------------------- parsing

BUCKETS = [("cronograma_12m", "12meses"),
           ("cronograma_24m", "24meses"),
           ("cronograma_36m", "36meses"),
           ("cronograma_apos36", "apos36meses")]


def bucket_pos(n: str, key: str):
    """Posicao do rotulo do bucket no texto normalizado (None se ausente).

    '36meses' e sufixo de 'apos36meses': so aceita a ocorrencia que NAO vem
    precedida de 'apos'.
    """
    start = 0
    while True:
        p = n.find(key, start)
        if p < 0:
            return None
        if key == "36meses" and n[max(0, p - 4):p] == "apos":
            start = p + 1
            continue
        return p


def parse_cronograma(rows):
    """Le os 4 buckets do grafico 'Cronograma de Recebiveis'."""
    tit = None
    for i, r in enumerate(rows):
        if "cronogramaderecebiveis" in norm(r["text"]):
            tit = i
            break
    if tit is None:
        return {k: None for k, _ in BUCKETS}, False

    vals, alvo = {}, 0
    for r in rows[tit + 1:]:
        while alvo < len(BUCKETS):
            campo, key = BUCKETS[alvo]
            n, idx = norm_map(r["text"])
            p = bucket_pos(n, key)
            if p is None:
                break
            end = p + len(key) - 1
            cut = idx[end] + 1 if end < len(idx) else len(r["text"])
            nums = numbers(r["text"][cut:])
            if not nums:
                break
            vals[campo] = nums[0]
            alvo += 1
        if alvo >= len(BUCKETS):
            break
    return {k: vals.get(k) for k, _ in BUCKETS}, True


def parse_tabela(rows):
    d = {}
    labels = {
        "unidades_em_construcao": "unidadesemconstrucao",
        "unidades_construidas": "unidadesconstruidas",
        "total_recebiveis": "totaldosrecebiveis",
        "contas_receber_liquido": "contasareceberliquido",
    }
    for campo, lab in labels.items():
        d[campo] = None
        for r in rows:
            nums = after_label(r["text"], lab)
            if nums:
                d[campo] = nums[0]
                break

    # "Compromisso com custos orcados ..." tem o rotulo quebrado em duas linhas e
    # os valores frequentemente numa linha propria; sao as unicas linhas da secao
    # com numeros entre parenteses, na ordem vendidas -> estoque.
    par = []
    for r in rows:
        if re.search(r"\(\d[\d.,]*\)", r["text"]):
            nums = [v for v in numbers(r["text"]) if v < 0]
            if nums:
                par.append(nums[0])
    d["compromisso_custos_vendidas"] = par[0] if len(par) > 0 else None
    d["compromisso_custos_estoque"] = par[1] if len(par) > 1 else None
    return d


def parse_texto(rows):
    blob = " ".join(r["text"] for r in rows)
    flat = re.sub(r"\s+", " ", strip_acc(blob)).lower()
    d = {"prazo_medio_meses": None, "pct_unidades_entregues": None}
    # "... e de cerca de 2,0 anos (24,0 meses)". O "meses)" as vezes cai numa
    # linha separada por cima do grafico, entao ancoramos em "anos (" e nao em
    # "meses)".
    m = re.search(r"cerca de\s*[\d.,]+\s*anos?\s*\(\s*(\d+[.,]?\d*)", flat)
    if not m:
        m = re.search(r"\(\s*(\d+[.,]?\d*)\s*meses\s*\)", flat)
    if m:
        d["prazo_medio_meses"] = float(m.group(1).replace(".", "").replace(",", "."))
    m = re.search(r"desse total,?\s*(\d+[.,]?\d*)\s*%\s*refere", flat)
    if m:
        d["pct_unidades_entregues"] = float(m.group(1).replace(",", "."))
    return d


# --------------------------------------------------------------- overrides
# 1T22 e o UNICO trimestre em que os tres graficos da secao foram colados na
# pagina como imagem (pdfplumber ve 3 bitmaps em x 385-568 e nenhum glifo de
# rotulo/valor). Nao ha o que extrair da camada de texto. Os valores abaixo
# foram lidos do proprio grafico do release (fontes/release_1T22.pdf, pagina 26
# do documento / indice 25 do PDF), rasterizado a 400 dpi. Conferem com a
# validacao padrao: 2.917 + 1.737 + 1.801 + 345 = 6.800 vs "Total dos
# Recebiveis" 6.801 (dentro de 1%) e a serie fica continua entre 4T21
# (2.702/1.898/1.556/447) e 2T22 (2.964/1.789/1.912/428).
# Para auditar:  python dados_receber_aging.py --imagem 1T22
OVERRIDES = {
    "1T22": {"cronograma_12m": 2917.0, "cronograma_24m": 1737.0,
             "cronograma_36m": 1801.0, "cronograma_apos36": 345.0},
}
OVERRIDE_FONTE = "grafico em imagem, lido do PDF rasterizado (nao ha camada de texto)"

CAMPOS = [
    "unidades_em_construcao", "unidades_construidas", "total_recebiveis",
    "compromisso_custos_vendidas", "compromisso_custos_estoque",
    "contas_receber_liquido",
    "cronograma_12m", "cronograma_24m", "cronograma_36m", "cronograma_apos36",
    "cronograma_total", "receber_performado", "alienacao_fiduciaria",
    "prazo_medio_meses", "pct_unidades_entregues",
]


def parse_release(tri: str):
    pdf_path = os.path.join(FONTES, f"release_{tri}.pdf")
    if not os.path.exists(pdf_path):
        return None, {"erro": "pdf ausente"}
    with pdfplumber.open(pdf_path) as pdf:
        pg = find_page(pdf, tri)
        if pg is None:
            return None, {"erro": "secao CONTAS A RECEBER nao localizada"}
        rows = page_rows(pdf.pages[pg])
        n_img = len(pdf.pages[pg].images)

    rec = {c: None for c in CAMPOS}
    rec.update(parse_tabela(rows))
    cron, tem_titulo = parse_cronograma(rows)
    rec.update(cron)
    rec.update(parse_texto(rows))

    fonte = "camada de texto do PDF"
    if tri in OVERRIDES and all(rec[k] is None for k in OVERRIDES[tri]):
        rec.update(OVERRIDES[tri])
        fonte = OVERRIDE_FONTE

    # Carteira performada == recebivel de unidade concluida == "Unidades
    # construidas" (batido contra a nota de risco do ITR 2T26 e da DFP 2025).
    rec["receber_performado"] = rec["unidades_construidas"]

    b = [rec[k] for k, _ in BUCKETS]
    if all(v is not None for v in b):
        rec["cronograma_total"] = round(sum(b), 1)

    meta = {"pagina_pdf": pg, "titulo_grafico": tem_titulo,
            "imagens_na_pagina": n_img, "fonte_cronograma": fonte}
    return rec, meta


def validar(rec):
    v = {}
    tot, cron = rec.get("total_recebiveis"), rec.get("cronograma_total")
    v["v_cronograma"] = (tot is not None and cron is not None
                         and abs(cron - tot) <= max(1.0, 0.01 * tot))
    a, bb = rec.get("unidades_em_construcao"), rec.get("unidades_construidas")
    v["v_tabela"] = (None not in (a, bb, tot) and abs(a + bb - tot) <= 1)
    cv, ce, liq = (rec.get("compromisso_custos_vendidas"),
                   rec.get("compromisso_custos_estoque"),
                   rec.get("contas_receber_liquido"))
    v["v_liquido"] = (None not in (cv, ce, liq, tot)
                      and abs(tot + cv + ce - liq) <= 1)
    return v


def main():
    if "--imagem" in sys.argv:
        # Rasteriza a metade direita da pagina da secao (onde ficam os graficos)
        # para conferir a olho os trimestres em que o grafico e imagem.
        tri = sys.argv[sys.argv.index("--imagem") + 1]
        with pdfplumber.open(os.path.join(FONTES, f"release_{tri}.pdf")) as pdf:
            pg = find_page(pdf, tri)
            p = pdf.pages[pg]
            dest = os.path.join(BASE, f"_cronograma_{tri}.png")
            p.crop((p.width * 0.55, 0, p.width, p.height)).to_image(resolution=400).save(dest)
        print("->", dest)
        return

    if "--debug" in sys.argv:
        tri = sys.argv[sys.argv.index("--debug") + 1]
        with pdfplumber.open(os.path.join(FONTES, f"release_{tri}.pdf")) as pdf:
            pg = find_page(pdf, tri)
            print(f"{tri}: pagina {pg}")
            for r in page_rows(pdf.pages[pg]):
                print(round(r["top"], 1), repr(r["text"]))
        return

    dados, metas, vals = {}, {}, {}
    for tri in TRIMESTRES:
        rec, meta = parse_release(tri)
        if rec is None:
            dados[tri] = {c: None for c in CAMPOS}
            metas[tri] = meta
            vals[tri] = {"v_cronograma": False, "v_tabela": False, "v_liquido": False}
        else:
            dados[tri] = rec
            metas[tri] = meta
            vals[tri] = validar(rec)
        st = vals[tri]
        print(f"{tri}  pg={metas[tri].get('pagina_pdf')}  "
              f"tot={rec['total_recebiveis'] if rec else None}  "
              f"cron={rec['cronograma_total'] if rec else None}  "
              f"cron_ok={st['v_cronograma']} tab_ok={st['v_tabela']} liq_ok={st['v_liquido']}")

    payload = {
        "_meta": {
            "fonte": "releases trimestrais Cyrela (fontes/release_*.pdf), secao CONTAS A RECEBER",
            "unidade": "R$ milhoes (exceto prazo_medio_meses em meses e "
                       "pct_unidades_entregues em %)",
            "campos": CAMPOS,
            "paginas": metas,
            "notas": [
                "cronograma_* = grafico 'Cronograma de Recebiveis' (ENTRADA de caixa). "
                "Nao confundir com os dois graficos 'Cronograma do Custo a Incorrer' "
                "(SAIDA) da mesma pagina; a validacao soma-dos-buckets = "
                "Total dos Recebiveis separa os dois.",
                "receber_performado espelha 'Unidades construidas'. Conferido contra a "
                "nota de risco de mercado: ITR 2T26 'Carteira performada 1.563.246' "
                "(R$ mil) e DFP 2025 'Carteira performada 1.505.006' — batem exatamente.",
                "alienacao_fiduciaria: null em todos. A expressao nao aparece em nenhum "
                "release; ITR/DFP so a citam qualitativamente, sem quantificar.",
                "1T22: os tres graficos da secao sao IMAGEM (sem camada de texto). "
                "Buckets lidos do PDF rasterizado a 400 dpi (ver OVERRIDES no parser).",
                "QUEBRA DE SERIE 3T20: a coluna comparativa e '2T20 (pro forma)' e traz "
                "Total dos Recebiveis 4.354 vs os 5.194 reportados no release do 2T20 "
                "(restatement da companhia).",
                "QUEBRA DE SERIE 3T25: restata Unidades em construcao do 2T25 de 14.051 "
                "para 14.079 (Total 15.069 -> 15.097), 0,2%.",
                "Encadeamento: em 70 de 75 comparacoes (3 campos x 25 pares) a coluna "
                "comparativa do release seguinte reproduz o valor extraido do anterior.",
            ],
        },
        "validacoes": vals,
        "dados": dados,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)

    ok = sum(1 for t in TRIMESTRES if vals[t]["v_cronograma"])
    com = sum(1 for t in TRIMESTRES if dados[t].get("cronograma_total") is not None)
    print(f"\ntrimestres: {len(TRIMESTRES)} | com cronograma: {com} | v_cronograma ok: {ok}")
    print("faltando:", [t for t in TRIMESTRES if dados[t].get("cronograma_total") is None])
    print("->", OUT)


if __name__ == "__main__":
    main()
