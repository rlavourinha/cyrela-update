# -*- coding: utf-8 -*-
"""Resultado financeiro dos releases (1T20-2T26), no padrao historico do CYREMod:
- r28 'Interest on Receivables (Var. Mon. + Outras)' = Variacoes Monetarias +
  Outras Receitas Financeiras (bloco RECEITAS da tabela de resultado financeiro);
- r30 'CashMe' = contribuicao da CashMe ao resultado financeiro liquido (PROSA do
  release, existe desde 3T23; o ITR nao decompoe o financeiro por veiculo);
- r31 = resultado financeiro DRE - r28 - r11 (padrao JGP validado em 2T19/3T19/4T19).

Validacoes: aplicacoes + var.mon. + outras = total de receitas (tabela) e total da
tabela ~= DRE (planilha do RI). Saida: _fin_releases.json.
"""
import datetime
import glob
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))

# ancora DRE (planilha RI)
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True, data_only=True)
G = list(wb["CYRELA"].iter_rows(min_row=1, max_row=100, values_only=True))
wb.close()
H = G[3]
FIN = {}
for j in range(1, len(H)):
    if isinstance(H[j], datetime.datetime) and isinstance(G[81][j], (int, float)):
        d = H[j]
        FIN[f"{(d.month-1)//3+1}T{d.year%100:02d}"] = G[81][j] / 1000

TOK = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})*\)?")


def nums(txt, n=40):
    out = []
    for t in TOK.findall(txt):
        v = float(t.strip("()").replace(".", ""))
        out.append(-v if t.startswith("(") else v)
        if len(out) >= n:
            break
    return out


def _num_apos(s, i, jan=220):
    m = TOK.search(s[i:i + jan])
    if not m:
        return None
    v = float(m.group(0).strip("()").replace(".", ""))
    return -v if m.group(0).startswith("(") else v


def extrai_r28(s, fin_dre):
    """Ancorado nos ROTULOS da tabela (o scan numerico casava lixo):
    Rendimento de Aplicacoes / Variacoes Monetarias (a que NAO e 'sobre
    Financiamentos') / Outras Receitas Financeiras / Total de Receitas.
    Aceita apenas se aplic+var+outras = total (+-1,5)."""
    for m in re.finditer(r"Rendimentos?\s+de\s+Aplica", s, re.I):
        a = _num_apos(s, m.end())
        jan = s[m.end():m.end() + 1200]
        v = o = t = None
        for mv in re.finditer(r"Varia[çc][õo]es\s+Monet[áa]rias(?!\s+sobre)", jan, re.I):
            v = _num_apos(jan, mv.end())
            break
        mo = re.search(r"Outras\s+Receitas\s+Financeiras", jan, re.I)
        if mo:
            o = _num_apos(jan, mo.end())
        mt = re.search(r"Total\s+de\s+Receitas\s+Financeiras", jan, re.I)
        if mt:
            t = _num_apos(jan, mt.end())
        if None in (a, v, o, t):
            continue
        if not (a > 0 and 0 <= v < a and 0 <= o < a and t >= a):
            continue
        if abs(a + v + o - t) > 1.5:
            continue
        return {"aplic": a, "var_mon": v, "outras": o, "tot_rec": t,
                "r28": round(v + o, 1)}
    return None


RE_CASH = re.compile(
    r"CashMe\s+no\s+resultado\s+financeiro\s+l[ií]quido\s+totalizou[^.]{0,400}", re.I | re.S)
RE_PAR = re.compile(r"R\$\s*([\d\.]+)\s*milh[õo]es?\s+no\s+(\dT\d\d)", re.I)
RE_TRI = re.compile(r"R\$\s*([\d\.]+)\s*milh[õo]es?\s+no\s+trimestre", re.I)
RE_ANO = re.compile(r"R\$\s*([\d\.]+)\s*milh[õo]es?\s+(?:no\s+ano|em\s+20\d\d|no\s+acumulado)", re.I)


ORD = lambda q: (int(q[2:]), int(q[0]))
out = {}
cash = {}
for f in sorted(glob.glob(os.path.join(here, "fontes", "release_????.txt"))):
    tri = os.path.basename(f)[8:12]
    d = {}
    for cand in (f, f.replace(".txt", ".raw.txt")):
        if not os.path.exists(cand):
            continue
        s = io.open(cand, encoding="utf-8", errors="ignore").read()
        r = extrai_r28(s, FIN.get(tri))
        if r:
            d.update(r)
        m = RE_CASH.search(s)
        if m:
            fr = m.group(0).replace("\n", " ")
            mt = RE_TRI.search(fr)
            if mt:
                cash[tri] = float(mt.group(1).replace(".", ""))
            for val, qq in RE_PAR.findall(fr):
                cash.setdefault(qq, float(val.replace(".", "")))
            # em release 4T sem "no trimestre", o 1o valor da frase e o ANUAL
            # (ex.: 4T23 "totalizou foi de R$ 185 milhoes, acima ... de 2022")
            if tri.startswith("4T") and not mt:
                mv = re.search(r"R\$\s*([\d\. ]+?)\s*milh", fr)
                if mv:
                    cash.setdefault("ANO" + tri[2:],
                                    float(mv.group(1).replace(".", "").replace(" ", "")))
        if d:
            break
    if d:
        out[tri] = d

# consolida com FIN e r11 (do modelo) para computar r31
p = r"D:\rlavourinha\Pictures\OneDrive\Área de Trabalho\JGP\RLavourinha\2. Homebuilders\1. Modelos\Cyrela\CYREMod_2T26.xlsx"
wv = openpyxl.load_workbook(p, data_only=True)["CYRE"]
mp = {}
for c in range(2, 107):
    v = wv.cell(1, c).value
    if isinstance(v, str) and len(v) == 4 and v[1] == "T":
        mp[v] = c
J11 = {q: wv.cell(11, mp[q]).value for q in mp if isinstance(wv.cell(11, mp[q]).value, (int, float))}

fin_ok = 0
for tri in sorted(out, key=ORD):
    d = out[tri]
    d["fin_dre"] = round(FIN.get(tri, 0), 1)
    d["cashme"] = cash.get(tri)
    j = J11.get(tri)
    if j is not None:
        d["r31"] = round(d["fin_dre"] - d["r28"] - j, 1)
    print(f"  {tri}: aplic {d['aplic']:6.0f} | var+outras (r28) {d['r28']:6.1f} | "
          f"tot_rec {d['tot_rec']:6.0f} | DRE {d['fin_dre']:6.1f} | cashme {str(d['cashme']):>6} | r31 {d.get('r31')}")

# 4T sem frase 'no trimestre': deriva do total anual (frase do release 4T) - 9M
for aa in (23, 24, 25):
    k4, ka = f"4T{aa}", f"ANO{aa}"
    if k4 not in cash and ka in cash:
        m9 = [cash.get(f"{t}T{aa}") for t in (1, 2, 3)]
        if all(x is not None for x in m9):
            cash[k4] = round(cash[ka] - sum(m9), 1)
cash = {k: v for k, v in cash.items() if not k.startswith("ANO")}

falt = [q for q in sorted(FIN, key=ORD) if ORD(q) >= (20, 1) and q not in out]
print("faltando:", falt)
print("cashme capturado:", {k: cash[k] for k in sorted(cash, key=ORD)})
io.open(os.path.join(here, "_fin_releases.json"), "w", encoding="utf-8").write(
    json.dumps({"fin": out, "cashme": cash}))
