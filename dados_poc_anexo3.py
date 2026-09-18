# -*- coding: utf-8 -*-
"""Costura os Anexos III (reconhecimento por empreendimento) dos releases da Cyrela.

Seis PDFs (cada um traz o trimestre corrente + comparativo do ano anterior) cobrem
1T24-2T26. Como o anexo lista apenas os maiores projetos de cada trimestre, as
series individuais tem buracos; a curva robusta e a MEDIA de evolucao por idade.
Saida: _poc_curvas.json  {media, n, curvas individuais quase completas}
"""
import io
import json
import os
import re
from collections import defaultdict

from pypdf import PdfReader

here = os.path.dirname(os.path.abspath(__file__))
fontes = os.path.join(here, "fontes")

RELEASES = {
    "release_2T26": ("2T26", "2T25"),
    "release_1T26": ("1T26", "1T25"),
    "release_4T25": ("4T25", "4T24"),
    "release_3T25": ("3T25", "3T24"),
    "release_2T25": ("2T25", "2T24"),
    "release_1T25": ("1T25", "1T24"),
    "release_4T24": ("4T24", "4T23"),
    "release_3T24": ("3T24", "3T23"),
    "release_2T24": ("2T24", "2T23"),
    "release_1T24": ("1T24", "1T23"),
    "release_4T23": ("4T23", "4T22"),
    "release_3T23": ("3T23", "3T22"),
    "release_2T23": ("2T23", "2T22"),
    "release_1T23": ("1T23", "1T22"),
}
MESES = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
         "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}
PAT = re.compile(r"^(.*?)\s+(Alto Padrão|Médio|MCMV 2 e 3|Vivaz Prime|MCMV)\s+([a-z]{3})-(\d{2})\s+(\d+)%\s+(\d+)%\s+([\d\.]+|-)\s+([\d\.]+|-)\s*$")


def tri_num(q, aa):
    return (2000 + aa) * 4 + q - 1


def parse(arquivo):
    txt_path = os.path.join(fontes, arquivo + ".txt")
    if not os.path.exists(txt_path):
        r = PdfReader(os.path.join(fontes, arquivo + ".pdf"))
        io.open(txt_path, "w", encoding="utf-8").write(
            "\n".join((p.extract_text() or "") for p in r.pages))
    raw = io.open(txt_path, encoding="utf-8").read()
    i = raw.find("ANEXO III", 10000)
    j = raw.find("ANEXO IV", 10000)
    if i < 0 or j < 0:
        return []
    out = []
    for linha in raw[i:j].split("\n"):
        m = PAT.match(re.sub(r"\s+", " ", linha).strip())
        if m:
            out.append(m.groups())
    return out


def tri_de_nome(nome_tri):
    return tri_num(int(nome_tri[0]), int(nome_tri[2:]))


series = {}
for arq, (tri_c, tri_a) in RELEASES.items():
    for nome, seg, mes, ano, ec, ea, rc, ra in parse(arq):
        chave = nome.strip().lower()
        d = series.setdefault(chave, {"n": nome.strip(), "s": seg, "ini": f"{mes}-{ano}", "ev": {}})
        d["ev"][tri_de_nome(tri_c)] = int(ec)
        d["ev"].setdefault(tri_de_nome(tri_a), int(ea))
        d["ini_tri"] = tri_num((MESES[mes] - 1) // 3 + 1, int(ano))

# ---------- media de evolucao por idade ----------
IDMAX = 16
obs = defaultdict(list)
obs_safra = defaultdict(lambda: defaultdict(list))


def safra_de(d):
    ano = d["ini_tri"] // 4
    if ano <= 2022:
        return "até 2022"
    if ano >= 2025:
        return "2025–26"
    return str(ano)


for d in series.values():
    sf = safra_de(d)
    for t, e in d["ev"].items():
        idade = t - d["ini_tri"]
        if 0 <= idade <= IDMAX + 1:
            obs[idade].append(e)
            obs_safra[sf][idade].append(e)


def agrega(dic):
    media, ns, acum = [], [], []
    tot = 0.0
    for idade in range(0, IDMAX + 1):
        v = dic.get(idade, [])
        m = round(sum(v) / len(v), 1) if v else None
        media.append(m)
        ns.append(len(v))
        tot += (m or 0)
        acum.append(round(tot, 1))
    return media, ns, acum


media, ns, acum = agrega(obs)
print("idade :", list(range(IDMAX + 1)))
print("N     :", ns)
print("media :", media)
print("acum  :", acum)

safras = {}
for sf in sorted(obs_safra):
    m2, n2, a2 = agrega(obs_safra[sf])
    safras[sf] = {"media": m2, "n": n2, "acum": a2}
    print(f"safra {sf}: N={sum(n2)} obs | acum idade4={a2[4]} idade6={a2[6]} idade8={a2[8]} idade10={a2[10]}")

# ---------- media por segmento (familia MCMV agregada) ----------
SEG_MAP = {"MCMV 2 e 3": "MCMV (Vivaz)", "Vivaz Prime": "MCMV (Vivaz)", "MCMV": "MCMV (Vivaz)"}
obs_seg = defaultdict(lambda: defaultdict(list))
for d in series.values():
    sgm = SEG_MAP.get(d["s"], d["s"])
    for t, e in d["ev"].items():
        idade = t - d["ini_tri"]
        if 0 <= idade <= IDMAX + 1:
            obs_seg[sgm][idade].append(e)

segmentos = {}
for sgm in sorted(obs_seg):
    m3, n3, a3 = agrega(obs_seg[sgm])
    segmentos[sgm] = {"media": m3, "n": n3, "acum": a3}
    print(f"segmento {sgm}: acum idade0={a3[0]} idade4={a3[4]} idade8={a3[8]}")

# ---------- curvas individuais quase completas (inicio na janela; buracos de ate 1 tri interpolados) ----------
JAN_INI = min(min(d["ev"]) for d in series.values())
JAN_FIM = max(max(d["ev"]) for d in series.values())
curvas = []
for d in series.values():
    if d["ini_tri"] < JAN_INI:
        continue
    fim = min(JAN_FIM, d["ini_tri"] + 12)
    seq, buraco_seguidos, ok = [], 0, True
    for t in range(d["ini_tri"], fim + 1):
        if t in d["ev"]:
            seq.append(d["ev"][t])
            buraco_seguidos = 0
        else:
            seq.append(None)
            buraco_seguidos += 1
            if buraco_seguidos > 1:
                ok = False
                break
    while seq and seq[-1] is None:
        seq.pop()
    if not ok or len(seq) < 4:
        continue
    for i in range(len(seq)):          # interpola buraco unico com media dos vizinhos
        if seq[i] is None:
            viz = [x for x in (seq[i - 1] if i else None, seq[i + 1] if i + 1 < len(seq) else None) if x is not None]
            seq[i] = round(sum(viz) / len(viz), 1) if viz else 0
    ac, p = 0, []
    for e in seq:
        ac += e
        p.append(round(ac, 1))
    curvas.append({"n": d["n"], "s": d["s"], "ini": d["ini"], "p": p})

print("curvas individuais:", len(curvas))
for c in sorted(curvas, key=lambda x: -len(x["p"]))[:10]:
    print(" ", c["n"][:36], c["ini"], c["p"])

io.open(os.path.join(here, "_poc_curvas.json"), "w", encoding="utf-8").write(
    json.dumps({"media": media, "acum": acum, "n": ns, "curvas": curvas, "safras": safras,
                "segmentos": segmentos}, ensure_ascii=False))
