# -*- coding: utf-8 -*-
"""Receita BRUTA, deducoes e sua abertura, da NOTA EXPLICATIVA dos ITRs/DFPs.

A DVA da CVM NAO serve (testada e reprovada: no 4T19 deu 1.181 contra os 1.266 que a
JGP digitou, e produz deducoes positivas em varios trimestres). A fonte correta e a
nota "Receita bruta / Deducoes da receita bruta / Receita liquida" do ITR (ou da DFP,
para o 4T), no bloco CONSOLIDADO.

Metodo: baixa os documentos pelo indice IPE, valida por conteudo e localiza a coluna
certa ANCORANDO na receita liquida ja conhecida (planilha de DFs do RI): a coluna cujo
valor de "Receita liquida" casar com o acumulado do periodo e a coluna do periodo.
Trimestre = acumulado - acumulado anterior.
Saida: _receita_bruta_itr.json {tri: {bruta, deducoes, liquida, pct, incorp, loteam,
provisao_distrato, pcld, servicos}}
"""
import csv
import glob
import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import zipfile

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
tmp = sys.argv[1] if len(sys.argv) > 1 else here
docs = os.path.join(tmp, "itrdocs")
os.makedirs(docs, exist_ok=True)
BASE_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"


def baixa(tipo, ano):
    """zip do dataset estruturado (itr/dfp) daquele ano."""
    nome = f"{tipo}_cia_aberta_{ano}.zip"
    cam = os.path.join(tmp, nome)
    if not os.path.exists(cam):
        url = f"{BASE_CVM}/{tipo.upper()}/DADOS/{nome}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            io.open(cam, "wb").write(urllib.request.urlopen(req, timeout=600).read())
        except Exception as e:
            print(f"  ! {nome}: {e}")
            return None
    return cam

# ---------- ancora: receita liquida trimestral da planilha do RI ----------
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True, data_only=True)
ws = wb["CYRELA"]
G = list(ws.iter_rows(min_row=1, max_row=100, values_only=True))
wb.close()
import datetime
H = G[3]
liq_tri = {}
for j in range(1, len(H)):
    if isinstance(H[j], datetime.datetime) and isinstance(G[70][j], (int, float)):
        d = H[j]
        liq_tri[f"{(d.month-1)//3+1}T{d.year%100:02d}"] = G[70][j] / 1000

ORD = lambda q: (int(q[2:]), int(q[0]))


def acum_esperado(q):
    """receita liquida acumulada no exercicio ate o trimestre q (R$ mi)."""
    t, a = int(q[0]), int(q[2:])
    tot = 0.0
    for k in range(1, t + 1):
        v = liq_tri.get(f"{k}T{a:02d}")
        if v is None:
            return None
        tot += v
    return tot


# ---------- candidatos no indice IPE ----------
ALVO = {}
for t, mes in ((1, "03-31"), (2, "06-30"), (3, "09-30"), (4, "12-31")):
    for a in range(2020, 2027):
        if a == 2026 and t > 2:
            continue
        ALVO[f"{t}T{a%100:02d}"] = f"{a}-{mes}"

# os ITR/DFP NAO estao no IPE: sao documentos estruturados, indexados no proprio
# zip (itr_cia_aberta_YYYY.csv / dfp_cia_aberta_YYYY.csv), com LINK_DOC do ENETCONSULTA
import zipfile as _zf
cand = {k: [] for k in ALVO}
for ano in range(2020, 2027):
    for tipo in ("itr", "dfp"):
        cam = baixa(tipo, ano)
        if not cam:
            continue
        with _zf.ZipFile(cam) as zf:
            nome = f"{tipo}_cia_aberta_{ano}.csv"
            if nome not in zf.namelist():
                continue
            with zf.open(nome) as fh:
                linhas = list(csv.DictReader(io.TextIOWrapper(fh, encoding="latin-1"), delimiter=";"))
        for r in linhas:
            if "CYRELA BRAZIL" not in r.get("DENOM_CIA", ""):
                continue
            dt = r.get("DT_REFER", "")[:10]
            for tri, alvo in ALVO.items():
                if dt == alvo:
                    cand[tri].append((int(r.get("VERSAO", 1)), r["LINK_DOC"]))
for tri in cand:                      # versao mais recente primeiro
    cand[tri] = [u for _, u in sorted(cand[tri], key=lambda x: -x[0])]

RE_LIQ = re.compile(r"^Receita l[ií]quida\s+(.+)$", re.M | re.I)
RE_BRU = re.compile(r"^Dedu[çc][õo]es da receita bruta\s+(.+)$", re.M | re.I)
NUM = re.compile(r"\(?-?[\d.]+\)?")


def nums(linha):
    out = []
    for t in linha.split():
        t = t.strip()
        m = re.fullmatch(r"\(?(-?[\d]{1,3}(?:\.\d{3})*)\)?", t)
        if m:
            v = float(m.group(1).replace(".", ""))
            out.append(-v if t.startswith("(") else v)
    return out


TOKEN = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})*\)?")


def todos_numeros(bloco):
    out = []
    for t in TOKEN.findall(bloco):
        v = float(t.strip("()").replace(".", ""))
        out.append(-v if t.startswith("(") else v)
    return out


def extrai(txt, alvo_acum):
    """No texto 'raw' das notas os numeros saem agrupados por COLUNA, mas as linhas
    de 'Deducoes da receita bruta' e 'Receita liquida' aparecem como dois blocos
    consecutivos de K valores (K = numero de colunas do quadro). Achamos esses dois
    blocos ancorando na receita liquida acumulada ja conhecida; a bruta sai por
    identidade (bruta = liquida - deducoes), validada pela razao das deducoes."""
    for m in re.finditer(r"Dedu[çc][õo]es da receita bruta", txt, re.I):
        jan = txt[m.start():m.start() + 4000]
        seq = todos_numeros(jan)
        # K = numero de colunas do quadro, que varia por ano (2, 4, 5 e ate 8 -
        # controladora/consolidado x trimestre/acumulado x ano atual/anterior).
        # Testamos do maior para o menor: quanto maior o K, mais restritiva e a
        # checagem e menor o risco de casar por acaso. K=1 e o ultimo recurso
        # (ate 2023 o texto sai por coluna, com total/deducoes/liquida em sequencia).
        for K in (8, 6, 5, 4, 3, 2, 1):
            for i in range(len(seq) - 2 * K + 1):
                D, L = seq[i:i + K], seq[i + K:i + 2 * K]
                if not all(d <= 0 for d in D):
                    continue
                cand = [j for j in range(K)
                        if L[j] > 0 and abs(L[j] / 1000 - alvo_acum) < max(2, 0.004 * alvo_acum)]
                if not cand:
                    continue
                j = cand[-1]
                bruta = L[j] - D[j]
                if bruta <= 0:
                    continue
                razao = abs(D[j]) / bruta
                # deducoes acumuladas da Cyrela rodam em 2,4%-2,9% da bruta; fora de
                # 1,5%-8% e sinal de que casamos a coluna errada (foi o que aconteceu
                # no 3T21 antes de incluir K=5) - melhor recusar do que gravar errado.
                if not (0.015 < razao < 0.08):
                    continue
                return {"liquida_acum": round(L[j] / 1000, 1),
                        "deducoes_acum": round(D[j] / 1000, 1),
                        "bruta_acum": round(bruta / 1000, 1),
                        "colunas": K}
    return None


res = {}
for tri in sorted(ALVO, key=ORD):
    alvo = acum_esperado(tri)
    if alvo is None:
        continue
    achou = None
    for i, url in enumerate(cand.get(tri, [])):
        pdf = os.path.join(docs, f"{tri}_{i}.pdf")
        txt = pdf.replace(".pdf", ".txt")
        if not os.path.exists(txt):
            # o ENETCONSULTA derruba urllib e entrega um ZIP (xml + pdf + xlsx)
            zpath = pdf.replace(".pdf", ".zip")
            try:
                subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                "-o", zpath, url.replace("http://", "https://")],
                               check=True, capture_output=True, timeout=900)
                # o PDF solto do zip vem truncado em 8 MiB (xref quebrado). As notas
                # completas estao como PDFs em base64 DENTRO do xml do ITR.
                import base64
                partes = []
                with zipfile.ZipFile(zpath) as zf:
                    xmls = sorted((n for n in zf.namelist() if n.lower().endswith(".xml")),
                                  key=lambda n: -zf.getinfo(n).file_size)
                    bruto = zf.read(xmls[0]).decode("utf-8", "ignore") if xmls else ""
                    for b in re.findall(r">([A-Za-z0-9+/=]{5000,})<", bruto):
                        try:
                            d = base64.b64decode(b)
                        except Exception:
                            continue
                        if d.startswith(b"%PDF"):
                            partes.append(d)
                    if not partes:
                        # docs antigos (2020/inicio de 2021) nao trazem PDF no xml:
                        # usa o PDF solto do zip (nesses anos ele nao vem truncado)
                        soltos = [n for n in zf.namelist() if n.lower().endswith(".pdf")]
                        partes = [zf.read(n) for n in soltos]
                os.remove(zpath)
                if not partes:
                    print(f"  {tri} cand{i}: sem PDF (nem no xml, nem solto)")
                    continue
                partes.sort(key=len, reverse=True)
                io.open(pdf, "wb").write(partes[0])
                subprocess.run(["pdftotext", "-enc", "UTF-8", pdf, txt], check=True, capture_output=True)
            except Exception as e:
                print(f"  {tri} cand{i}: erro {str(e)[:90]}")
                continue
        s = io.open(txt, encoding="utf-8", errors="ignore").read()
        if "Dedu" not in s:
            continue
        achou = extrai(s, alvo)
        if achou:
            print(f"  {tri}: OK cand{i} | acum liq {achou['liquida_acum']:.0f} (alvo {alvo:.0f})")
            break
    if achou:
        res[tri] = achou
    else:
        print(f"  {tri}: FALHOU ({len(cand.get(tri,[]))} candidatos)")

# ---------- acumulado -> trimestre ----------
out = {}
for tri in sorted(res, key=ORD):
    t, a = int(tri[0]), int(tri[2:])
    cur = res[tri]
    if t == 1:
        b, d, l = cur["bruta_acum"], cur["deducoes_acum"], cur["liquida_acum"]
    else:
        ant = res.get(f"{t-1}T{a:02d}")
        if not ant:
            continue
        b = cur["bruta_acum"] - ant["bruta_acum"]
        d = cur["deducoes_acum"] - ant["deducoes_acum"]
        l = cur["liquida_acum"] - ant["liquida_acum"]
    out[tri] = {"bruta": round(b, 1), "deducoes": round(d, 1), "liquida": round(l, 1),
                "pct": round(100 * d / b, 2) if b else None}

io.open(os.path.join(here, "_receita_bruta_itr.json"), "w", encoding="utf-8").write(json.dumps(out))
print()
print(f"{len(out)} trimestres extraidos")
for q in sorted(out, key=ORD):
    v = out[q]
    ok = abs(v["liquida"] - liq_tri.get(q, 0)) < 2
    print(f"  {q}: bruta {v['bruta']:8.1f} | ded {v['deducoes']:8.1f} ({v['pct']:+5.2f}%) | "
          f"liq {v['liquida']:8.1f} vs DF {liq_tri.get(q,0):8.1f} {'OK' if ok else '<-- DIVERGE'}")
