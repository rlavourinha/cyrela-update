# -*- coding: utf-8 -*-
"""Series historicas da Pesquisa Raio-X FipeZAP (Fipe/Grupo OLX, trimestral, nacional).

Baixa todas as edicoes em downloads.fipe.org.br/indices/fipezap/raiox/raio-x-fipezap-AAAAtN.pdf
(padrao estavel), extrai texto e reconstroi 3 series pelos paragrafos-padrao:
- % de transacoes com desconto ("...avancou de X% em <mes> de <ano> para Y% em <mes> de <ano>")
- desconto medio (total e apenas nas transacoes com desconto)
- % de transacoes classificadas como investimento (acum. 12m)
Cada edicao traz o dado corrente + o de 12m antes -> serie deduplicada (edicao mais nova vence).
Saida: _mercado_raiox.json {pontos: {"AAAA-MM": {dt, dm_cd, dm_tot, inv}}}.
"""
import io
import json
import os
import re
import urllib.request

from pypdf import PdfReader

here = os.path.dirname(os.path.abspath(__file__))
pasta = os.path.join(here, "fontes", "mercado", "raiox")
os.makedirs(pasta, exist_ok=True)
MES = {"janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4, "maio": 5, "junho": 6,
       "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}
PCT_EM = r"(\d{1,2})%[^.]{0,40}? em ([a-zç]+) de (\d{4})"

pontos = {}


def anota(campo, edicao_ord, chave, valor):
    p = pontos.setdefault(chave, {})
    if campo not in p or p[campo][1] < edicao_ord:
        p[campo] = (valor, edicao_ord)


for ano in range(2015, 2027):
    for t in (1, 2, 3, 4):
        nome = f"raio-x-fipezap-{ano}t{t}"
        pdf = os.path.join(pasta, nome + ".pdf")
        if not os.path.exists(pdf):
            try:
                req = urllib.request.Request(
                    f"https://downloads.fipe.org.br/indices/fipezap/raiox/{nome}.pdf",
                    headers={"User-Agent": "Mozilla/5.0"})
                dados_pdf = urllib.request.urlopen(req, timeout=60).read()
                if not dados_pdf.startswith(b"%PDF"):
                    continue
                open(pdf, "wb").write(dados_pdf)
            except Exception:
                continue
        try:
            with open(pdf, "rb") as f:
                if f.read(4) != b"%PDF":
                    os.remove(pdf)
                    continue
            txt = " ".join((p.extract_text() or "") for p in PdfReader(pdf).pages)
        except Exception as e:
            print(nome, "erro leitura", str(e)[:60])
            continue
        flat = re.sub(r"\s+", " ", txt)
        ed = ano * 4 + t
        chave_ed = f"{ano}-{t*3:02d}"
        ok = []

        def janela(chaves, tam=700):
            for c in chaves:
                i = flat.lower().find(c.lower())
                if i >= 0:
                    return flat[i:i + tam]
            return ""

        PAR = re.compile(r"de (\d{1,2})%[^%.]{0,90}?em ([a-zç]+) de (\d{4})[^%.]{0,110}?para (\d{1,2})%[^%.]{0,90}?em ([a-zç]+) de (\d{4})", re.I)
        SOLO = re.compile(r"(\d{1,2})% em ([a-zç]+) de (\d{4})")

        def extrai(campo, jan, lo, hi):
            achou = False
            for m in PAR.finditer(jan):
                v1, m1, a1, v2, m2, a2 = m.groups()
                if m1 in MES and m2 in MES and lo <= int(v1) <= hi and lo <= int(v2) <= hi:
                    anota(campo, ed, f"{a1}-{MES[m1]:02d}", int(v1))
                    anota(campo, ed, f"{a2}-{MES[m2]:02d}", int(v2))
                    achou = True
            return achou

        # 1) % transacoes com desconto
        jan = janela(["Descontos nas transações", "Transações e percentuais de desconto",
                      "transações efetivadas com desconto", "transações com descontos",
                      "transações que envolveram desconto"], 900)
        if jan and extrai("dt", jan, 45, 75):
            ok.append("dt")

        # 2) desconto medio (total e/ou so-com-desconto)
        jan = janela(["desconto médio", "percentual médio de descontos", "média do percentual de descontos"], 500)
        if jan:
            vals = [float(v.replace(",", ".")) for v in re.findall(r"(\d{1,2}(?:[.,]\d)?)%", jan)]
            vals = [v for v in vals if 3 <= v <= 22]
            if len(vals) >= 2 and "apenas" in jan:
                anota("dm_tot", ed, chave_ed, min(vals[0], vals[1]))
                anota("dm_cd", ed, chave_ed, max(vals[0], vals[1]))
                ok.append("dm")
            elif vals and ("últimos 12 meses" in jan or "12 meses" in jan) and ano <= 2018:
                anota("dm12", ed, chave_ed, vals[0])
                ok.append("dm12")

        # 3) investimento 12m
        jan = janela(["classificadas como investimento", "classificaram a transação como",
                      "fizeram como investimento", "objetivo de compra: investimento",
                      "compras classificadas como investimento"], 900)
        if jan and extrai("inv", jan, 30, 52):
            ok.append("inv")
        elif jan:
            m = re.search(r"(\d{1,2})% (?:o fizeram como investimento|dos respondentes)", jan)
            if m and 25 <= int(m.group(1)) <= 60:
                anota("inv", ed, chave_ed, int(m.group(1)))
                ok.append("inv~")

        print(nome, "->", ",".join(ok) if ok else "NADA")

# ---------- series completas: rotulos dos graficos vetoriais da edicao mais recente ----------
MABR = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
        "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
ultimo = sorted(f for f in os.listdir(pasta) if f.endswith(".pdf"))[-1]
print("extraindo series dos graficos de:", ultimo)
paginas = [re.sub(r"\s+", " ", p.extract_text() or "") for p in PdfReader(os.path.join(pasta, ultimo)).pages]
ROTULO = re.compile(r"([a-z]{3})/(\d{2}) (\d{1,3})%")


def runs(txt):
    """separa sequencias de rotulos (novo run quando o tempo retrocede)"""
    out, atual, ult = [], [], -1
    for m in ROTULO.finditer(txt):
        mes, aa, v = m.group(1), int(m.group(2)), int(m.group(3))
        if mes not in MABR:
            continue
        ym = (2000 + aa) * 12 + MABR[mes]
        if ym < ult and atual:
            out.append(atual)
            atual = []
        atual.append([f"{2000+aa}-{MABR[mes]:02d}", v])
        ult = ym
    if atual:
        out.append(atual)
    return out


series = {}
for pg in paginas:
    up = pg.upper()
    if "PERCENTUAL DE TRANSAÇÕES COM DESCONTO (ACUMULADO" in up:
        r = runs(pg)
        if r:
            series["dt"] = max(r, key=len)
    elif "PERCENTUAL MÉDIO DE DESCONTO EM TRANSAÇÕES" in up or "PERCENTUAL DE DESCONTO MÉDIO" in up:
        r = [x for x in runs(pg) if len(x) >= 5]
        if len(r) >= 2:
            r.sort(key=lambda run: sum(v for _, v in run) / len(run), reverse=True)
            series["dm_cd"], series["dm_tot"] = r[0], r[1]
    elif "CLASSIFICADAS COMO INVESTIMENTO (ACUMULADO" in up:
        r = runs(pg)
        if r:
            series["inv"] = max(r, key=len)
    elif "CLASSIFICADAS COMO INVESTIMENTO POR TIPO" in up:
        r = [x for x in runs(pg) if len(x) >= 5]
        if len(r) >= 2:
            r.sort(key=lambda run: sum(v for _, v in run) / len(run), reverse=True)
            series["inv_aluguel"], series["inv_revenda"] = r[0], r[1]
for k, v in series.items():
    print(f"  {k}: {len(v)} pontos | {v[0]} ... {v[-1]}")

saida = {k: {c: v[0] for c, v in p.items()} for k, p in sorted(pontos.items())}
saida = {"pontos_prosa": saida, "series": series}
io.open(os.path.join(here, "_mercado_raiox.json"), "w", encoding="utf-8").write(
    json.dumps(saida, ensure_ascii=False, indent=0))
print("\npontos:", len(saida))
for k in sorted(saida):
    print(k, saida[k])
