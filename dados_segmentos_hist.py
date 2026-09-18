# -*- coding: utf-8 -*-
"""Nota 'Informacoes por Segmento' HISTORICA (1T13-4T19), docs em itrdocs2/ (.lay.txt).

Metodo: nesta era a tabela tem coluna Corporativo + Total e o pdftotext -layout
quebra linhas (valores vazam p/ linha de baixo), mas PRESERVA o alinhamento
horizontal. Entao:
  1. recorta a regiao da tabela corrente (entre o 1o e o 2o 'Consolidado <data>')
  2. tokeniza valores com a posicao x da borda direita (numeros alinhados a direita)
  3. agrupa em colunas por clusterizacao de x (gap > 5)
  4. le cada coluna de cima p/ baixo: rec, custo, lb, desp, lop, ativo, passivo, pl
  5. VALIDA por identidades (rec+custo=lb, lb+desp=lop, ativo-passivo=pl, +-3)
     e ancoras da planilha RI (receita/lucro bruto acumulados, PL consolidado)
Segmentos: 1T13-1T19 -> cyrela (MAP), living (inclui MCMV), demais;
           2T19-4T19 -> cyrela, living, mcmv, demais. Colunas extras: corporativo
(so desp/lop/ativo/passivo/pl) e total (validacao).
Campos invalidados sao OMITIDOS do json (nao chuta).
Saida: _segmentos_hist.json {tri: {seg: {rec, lb, desp, lop, ativo, passivo, pl}}}
Valores em R$ mi, ACUMULADO do ano (como na nota)."""
import datetime
import io
import json
import os
import re

import openpyxl

here = os.path.dirname(os.path.abspath(__file__))
SP2 = r"C:\Users\RLAVOU~1\AppData\Local\Temp\claude\D--rlavourinha-Pictures-OneDrive--rea-de-Trabalho-Claude\e4e1cc5f-6e04-4e22-ba8b-ce88f93cdefb\scratchpad\itrdocs2"

wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"),
                            read_only=True, data_only=True)
G = list(wb["CYRELA"].iter_rows(min_row=1, max_row=100, values_only=True))
wb.close()
REC, LB, PLC = {}, {}, {}
for j in range(1, len(G[3])):
    if isinstance(G[3][j], datetime.datetime) and isinstance(G[70][j], (int, float)):
        d = G[3][j]
        q = f"{(d.month-1)//3+1}T{d.year%100:02d}"
        REC[q] = G[70][j] / 1000
        LB[q] = G[72][j] / 1000
        PLC[q] = G[54][j] / 1000 if isinstance(G[54][j], (int, float)) else None


def acum(q):
    t, a = int(q[0]), q[2:]
    return (sum(REC[f"{i}T{a}"] for i in range(1, t + 1)),
            sum(LB[f"{i}T{a}"] for i in range(1, t + 1)))


VALTOK = re.compile(r"\(?-?\d{1,3}(?:\.\d{3})+\)?|\(\d{1,3}\)")
LIXO = re.compile(r"PGINA|P.GINA|Vers.o|Verso|CNPJ|Informa..es Trimestrais|"
                  r"Financeiras Padronizadas|Notas Explicativas")
ROWS = ["rec", "custo", "lb", "desp", "lop", "ativo", "passivo", "pl"]


BARE = re.compile(r"(?<![\d./$-])\d{1,3}(?![\d./%])")


def parse_tokens(region):
    """(fortes, soltos): [(linha, x_fim_digito, valor R$ mi)].
    'soltos' sao inteiros de 1-3 digitos sem separador de milhar (ex.: lb=235),
    usados apenas quando a coluna nao fecha so com os fortes."""
    fortes, soltos = [], []
    for li, ln in enumerate(region.split("\n")):
        if LIXO.search(ln):
            continue
        spans = []
        for m in VALTOK.finditer(ln):
            w = m.group()
            if re.match(r"^\d{2}[./]\d{4}$", w):
                continue
            v = float(w.strip("()").replace(".", "")) / 1000
            if w.startswith("("):
                v = -v
            x = m.end() - (1 if w.endswith(")") else 0)
            fortes.append((li, x, v))
            spans.append((m.start(), m.end()))
        for m in BARE.finditer(ln):
            if any(a <= m.start() < b for a, b in spans):
                continue
            soltos.append((li, m.end(), float(m.group()) / 1000))
    return fortes, soltos


def cluster_cols(toks, soltos, gap=5):
    """clusters de x construidos so com tokens fortes; soltos sao atribuidos
    a um cluster existente (+-2) ou descartados. Retorna (grupos, grupos_ext)."""
    xs = sorted({x for _, x, _ in toks})
    cols, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] <= gap:
            cur.append(x)
        else:
            cols.append(cur)
            cur = [x]
    cols.append(cur)

    def atribui(ts):
        grupos = [[] for _ in cols]
        for t in ts:
            for ci, c in enumerate(cols):
                if c[0] - 2 <= t[1] <= c[-1] + 2:
                    grupos[ci].append(t)
                    break
        for g in grupos:
            g.sort(key=lambda t: (t[0], t[1]))
        return grupos

    return atribui(toks), atribui(toks + soltos)


def id_ok(sq):
    """checa as 3 identidades num vetor de 8 valores"""
    e1 = abs(sq[0] + sq[1] - sq[2])
    e2 = abs(sq[2] + sq[3] - sq[4])
    e3 = abs(sq[5] - sq[6] - sq[7])
    return e1 <= 3 and e2 <= 3 and e3 <= 3, (e1, e2, e3)


def parse_q(q, s, NS):
    i = s.find("POR SEGMENTO")
    if i < 0:
        print(f"  {q}: sem nota")
        return None
    w = s[i:i + 18000]
    cons = [m.start() for m in re.finditer(r"Consolidado[ -]*\d{0,2}/?\d{4}", w)]
    if not cons:
        print(f"  {q}: sem marcador Consolidado")
        return None
    hi = cons[1] if len(cons) > 1 else len(w)
    region = w[cons[0]:hi]
    toks, soltos = parse_tokens(region)
    if not toks:
        print(f"  {q}: sem tokens")
        return None
    grupos, grupos_ext = cluster_cols(toks, soltos)
    # descarta clusters-ruido (1 token), exceto se precisarmos deles
    ncols = NS + 2
    if len(grupos) > ncols:
        keep = [gi for gi, g in enumerate(grupos) if len(g) >= 3]
        if len(keep) == ncols:
            grupos = [grupos[gi] for gi in keep]
            grupos_ext = [grupos_ext[gi] for gi in keep]
    if len(grupos) != ncols:
        print(f"  {q}: {len(grupos)} colunas (esperava {ncols}): "
              f"{[(len(g), round(g[0][1])) for g in grupos]}")
        return None

    nomes = (["cyrela", "living", "demais"] if NS == 3
             else ["cyrela", "living", "mcmv", "demais"])
    rec_a, lb_a = acum(q)
    pl_c = PLC.get(q)

    def monta(vals, nm):
        """sequencia de linhas validada por identidades, ou None"""
        if nm == "corporativo":
            # corp nao tem rec/custo/lb ('-'): esperado 5 valores
            if len(vals) == 5:
                sq = [0.0, 0.0, 0.0] + vals
            elif len(vals) == 4:  # desp/lop as vezes viram '-' tambem
                sq = [0.0, 0.0, 0.0, vals[0], vals[1], vals[2], vals[3], None]
            else:
                return None, f"{len(vals)} valores"
        else:
            if len(vals) != 8:
                return None, f"{len(vals)} valores {['%.1f' % v for v in vals]}"
            sq = vals
        if sq[7] is not None:
            ok, errs = id_ok(sq)
            if not ok:
                return None, (f"identidades falham {tuple(round(e,1) for e in errs)} "
                              f"vals={['%.1f' % v for v in sq]}")
        return dict(zip(ROWS, sq)), None

    seqs = {}
    probs = []
    for ci, nm in enumerate(nomes + ["corporativo", "total"]):
        sq, err = monta([v for _, _, v in grupos[ci]], nm)
        if sq is None:  # 2a chance: inclui inteiros sem separador (ex.: lb=235)
            sq, err2 = monta([v for _, _, v in grupos_ext[ci]], nm)
            if sq is None:
                probs.append(f"{nm}: {err} | com soltos: {err2}")
        seqs[nm] = sq

    # ---- validacoes cruzadas ----
    checks = []
    tot = seqs.get("total")
    segs = [seqs[nm] for nm in nomes]
    if all(segs):
        soma_rec = sum(sg["rec"] for sg in segs)
        soma_lb = sum(sg["lb"] for sg in segs)
        drec = soma_rec - rec_a
        checks.append(("Srec vs planilha", soma_rec, rec_a, abs(drec) <= max(4, rec_a * .015)))
        checks.append(("Slb vs planilha", soma_lb, lb_a, abs(soma_lb - lb_a) <= max(4, abs(lb_a) * .02)))
        if tot:
            checks.append(("Srec vs total nota", soma_rec, tot["rec"], abs(soma_rec - tot["rec"]) <= 4))
    if tot and pl_c:
        checks.append(("PL total vs planilha", tot["pl"], pl_c, abs(tot["pl"] - pl_c) <= max(4, pl_c * .01)))
    if all(segs) and seqs.get("corporativo") and tot and seqs["corporativo"].get("pl") is not None:
        spl = sum(sg["pl"] for sg in segs) + seqs["corporativo"]["pl"]
        checks.append(("Spl+corp vs total", spl, tot["pl"], abs(spl - tot["pl"]) <= 4))
        sat = sum(sg["ativo"] for sg in segs) + seqs["corporativo"]["ativo"]
        checks.append(("Sativo+corp vs total", sat, tot["ativo"], abs(sat - tot["ativo"]) <= 4))

    falhas = [c for c in checks if not c[3]]
    print(f"  {q} (NS={NS}): " + ("OK" if not falhas and not probs else "PROBLEMAS"))
    for c in checks:
        flag = "ok" if c[3] else "FALHA"
        print(f"      [{flag}] {c[0]}: {c[1]:.1f} vs {c[2]:.1f}")
    for p in probs:
        print(f"      ! {p}")
    if all(segs):
        for nm in nomes:
            r = seqs[nm]
            print(f"      {nm:7s} rec {r['rec']:8.1f} lb {r['lb']:8.1f} desp {r['desp']:8.1f} "
                  f"lop {r['lop']:8.1f} ativo {r['ativo']:9.1f} pass {r['passivo']:9.1f} pl {r['pl']:9.1f}")

    # ---- monta saida: so campos validados ----
    if not all(segs):
        return None
    # se a soma da receita nao bate nem com planilha nem com o total da nota, aborta
    rec_ok = any(c[0].startswith("Srec") and c[3] for c in checks)
    if not rec_ok:
        print(f"      -> receita nao ancora; trimestre descartado")
        return None
    bal_ok = not any(("PL total" in c[0] or "Spl" in c[0] or "Sativo" in c[0]) and not c[3] for c in checks)
    d = {}
    for nm in nomes:
        r = seqs[nm]
        reg = {"rec": round(r["rec"], 1) + 0.0, "lb": round(r["lb"], 1) + 0.0,
               "desp": round(r["desp"], 1) + 0.0, "lop": round(r["lop"], 1) + 0.0}
        if bal_ok:
            reg.update({"ativo": round(r["ativo"], 1) + 0.0,
                        "passivo": round(r["passivo"], 1) + 0.0,
                        "pl": round(r["pl"], 1) + 0.0})
        d[nm] = reg
    return d


def main():
    out = {}
    for a in range(13, 20):
        for t in range(1, 5):
            q = f"{t}T{a}"
            NS = 4 if (a == 19 and t >= 2) else 3
            f = os.path.join(SP2, f"{q}_0.lay.txt")
            if not os.path.exists(f) or q not in REC:
                print(f"  {q}: sem arquivo/anchor")
                continue
            s = io.open(f, encoding="utf-8", errors="ignore").read()
            d = parse_q(q, s, NS)
            if d:
                out[q] = d
    io.open(os.path.join(here, "_segmentos_hist.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False))
    print(f"\nsalvo _segmentos_hist.json com {len(out)} trimestres")


if __name__ == "__main__":
    main()
