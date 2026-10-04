# -*- coding: utf-8 -*-
"""Modelo de coortes: lançamentos por segmento → vendas (curva de VSO por coorte) → receita (curva de reconhecimento / PoC).
Calibra por segmento no histórico da CYRE (_cyre_oper_q.txt: lançamentos 401-403, vendas 436-439, estoque 517-520, receita 24-26,
trimestral 1T10-2T26) e devolve (a) a curva de VSO por coorte (fração vendida por trimestre desde o lançamento), (b) validação
vendas/receita modelo × real, (c) função `projetar(curvas)` para as curvas de lançamento do usuário. Pedido de 04/10/26.
Mecânica por coorte c (VGV 100%): vende s0 no trimestre de lançamento; depois q × (saldo) por trimestre; receita de uma unidade
vendida em t = PoC_c(t) no ato + Δ PoC a cada trimestre; PoC_c(t) = p0 + (1−p0) × clip((t − c − d0) / N, 0, 1); consolidação f (%CBR)."""
import io, json, os, itertools
here = os.path.dirname(os.path.abspath(__file__))
L = [l for l in io.open(os.path.join(here, "_cyre_oper_q.txt"), encoding="utf-8").read().split("\n") if l.strip()]
Q = L[0].rsplit("|", 1)[1].split(",")[:-1]; n = len(Q)
D = {}
for l in L[1:]:
    r = l.split("|", 1)[0]; vals = l.rsplit("|", 1)[1]; D[int(r)] = [float(x) if x not in ("", "﻿") else 0.0 for x in vals.split(",")[:-1]]   # rótulos contêm "|"
def add(a, b): return [x + y for x, y in zip(a, b)]
SEG = {"Alto Padrão": {"lan": D[401], "ven": D[436], "est": D[517], "rec": D[24]},
       "Médio": {"lan": D[402], "ven": add(D[437], D[438]), "est": add(D[518], D[519]), "rec": D[25]},   # Vivaz Prime (438/519) somada ao Médio
       "MCMV (Vivaz)": {"lan": D[403], "ven": D[439], "est": D[520], "rec": D[26]}}
qi = {q: i for i, q in enumerate(Q)}
def simulate(lan, s0, q, p0, N, d0, gp=0.0, horizon=None):
    """vendas e receita (base 100%) por trimestre a partir de lançamentos por trimestre; devolve (vendas, receita, estoque).
    gp = valorização trimestral do estoque não vendido (o estoque do RI é a valor de mercado; vendas saem a preço corrente)."""
    T = len(lan) if horizon is None else horizon
    ven = [0.0] * T; rec = [0.0] * T; est = [0.0] * T
    for c in range(T):
        Lc = lan[c] if c < len(lan) else 0.0
        if Lc <= 0: continue
        rem = Lc; sold = 0.0; poc_prev = 0.0
        for t in range(c, T):
            k = t - c
            if k > 0: rem *= (1 + gp)
            poc = p0 + (1 - p0) * min(max((k - d0) / N, 0.0), 1.0)
            s = s0 * Lc if k == 0 else q * rem
            s = min(s, rem); rem -= s
            rec[t] += s * poc + sold * (poc - poc_prev)   # venda nova no ato + evolução do PoC do já vendido
            sold += s; ven[t] += s; est[t] += rem; poc_prev = poc
    return ven, rec, est
def rmse(a, b, i0, i1): return (sum((a[i] - b[i]) ** 2 for i in range(i0, i1)) / (i1 - i0)) ** 0.5
# faixas por segmento: ciclo de obra N (trimestres) — Cyrela ~48 m (alongou de 36), Vivaz 30-36 m (calls 1T23-2T26)
RANGE = {"Alto Padrão": {"N": [12, 14, 16, 18]}, "Médio": {"N": [10, 12, 14, 16]}, "MCMV (Vivaz)": {"N": [8, 10, 12, 14]}}
FIT = {}; I0 = qi["1T18"]; I1 = n; R0 = qi["1T20"]
for name, s in SEG.items():
    best = None
    for s0, q, gp in itertools.product([x / 100 for x in range(20, 66, 5)], [x / 100 for x in range(4, 26)], [0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03]):
        ven, _, est = simulate(s["lan"], s0, q, 0.3, 12, 0, gp)
        e = rmse(ven, s["ven"], I0, I1) + 0.25 * rmse(est, s["est"], I0, I1)   # vendas e estoque (nível a mercado) juntos
        if best is None or e < best[0]: best = (e, s0, q, gp)
    e_v, s0, q, gp = best
    bestr = None
    for p0, N, d0 in itertools.product([x / 100 for x in range(10, 46, 5)], RANGE[name]["N"], [0, 1, 2, 3]):
        _, rec, _ = simulate(s["lan"], s0, q, p0, N, d0, gp)
        num = sum(rec[i] * s["rec"][i] for i in range(R0, I1)); den = sum(rec[i] ** 2 for i in range(R0, I1)); f = num / den if den else 1.0
        e = rmse([f * x for x in rec], s["rec"], R0, I1)
        if bestr is None or e < bestr[0]: bestr = (e, p0, N, d0, f)
    e_r, p0, N, d0, f = bestr
    ven, rec, est = simulate(s["lan"], s0, q, p0, N, d0, gp); recf = [f * x for x in rec]
    # curva de VSO por coorte: fração acumulada vendida k trimestres após o lançamento (em VGV de lançamento, sem valorização)
    rem = 1.0; cum = []
    for k in range(0, 21):
        sale = s0 if k == 0 else q * rem; rem -= sale; cum.append(round(1 - rem, 4))
    poc = [round(p0 + (1 - p0) * min(max((k - d0) / N, 0.0), 1.0), 4) for k in range(0, 21)]
    FIT[name] = {"s0": s0, "q": q, "gp": gp, "p0": p0, "N": N, "d0": d0, "f": round(f, 3), "rmse_vendas": round(rmse(ven, s["ven"], I0, I1)), "rmse_receita": round(e_r), "cum_vso": cum, "poc": poc,
                 "ven_model": ven, "rec_model": recf, "est_model": est, "est_2T26_real": round(s["est"][-1]), "est_2T26_model": round(est[-1])}
# VSO anual por segmento (vendas ÷ (estoque fim do ano anterior + lançamentos do ano)) e total
def anos():
    out = {y: [i for i, q in enumerate(Q) if q.endswith(str(y)[2:])] for y in range(2011, 2026)}
    out["LTM 2T26"] = [qi[q] for q in ("3T25", "4T25", "1T26", "2T26")]; return out
YS = anos(); VSO = {}
for name, s in SEG.items():
    VSO[name] = {}
    for y, idx in YS.items():
        i0 = idx[0] - 1; ven = sum(s["ven"][i] for i in idx); lan = sum(s["lan"][i] for i in idx); est0 = s["est"][i0]
        venm = sum(FIT[name]["ven_model"][i] for i in idx); est0m = FIT[name]["est_model"][i0]
        VSO[name][str(y)] = {"vso": round(100 * ven / (est0 + lan), 1) if est0 + lan > 0 else None, "ven": round(ven), "lan": round(lan), "est0": round(est0),
                             "vso_model": round(100 * venm / (est0m + lan), 1) if est0m + lan > 0 else None, "ven_model": round(venm), "rec": round(sum(s["rec"][i] for i in idx)), "rec_model": round(sum(FIT[name]["rec_model"][i] for i in idx))}
VSO["Total"] = {}
for y, idx in YS.items():
    i0 = idx[0] - 1; ven = sum(D[431][i] for i in idx); lan = sum(D[395][i] for i in idx); est0 = D[502][i0]
    VSO["Total"][str(y)] = {"vso": round(100 * ven / (est0 + lan), 1), "ven": round(ven), "lan": round(lan), "est0": round(est0)}
def projetar(curvas, anos_proj):
    """curvas: {segmento: {ano: VGV 100% R$ mi}} → vendas, receita consolidada e estoque por segmento e ano (lançamentos do ano em 4 parcelas iguais)."""
    out = {}
    for name, s in SEG.items():
        lan = list(s["lan"]) + [0.0] * (4 * len(anos_proj) + 2)   # 3T26, 4T26 = 0 → usuário pode informar
        for j, y in enumerate(anos_proj):
            v = curvas.get(name, {}).get(y, 0.0)
            for k in range(4): lan[n + 2 + 4 * j + k] = v / 4
        p = FIT[name]; ven, rec, est = simulate(lan, p["s0"], p["q"], p["p0"], p["N"], p["d0"], p["gp"])
        out[name] = {y: {"lan": curvas.get(name, {}).get(y, 0.0), "ven": sum(ven[n + 2 + 4 * j: n + 6 + 4 * j]), "rec": p["f"] * sum(rec[n + 2 + 4 * j: n + 6 + 4 * j]), "est_fim": est[n + 5 + 4 * j]} for j, y in enumerate(anos_proj)}
    return out
if __name__ == "__main__":
    for name, p in FIT.items():
        print(name, {k: v for k, v in p.items() if k in ("s0", "q", "gp", "p0", "N", "d0", "f", "rmse_vendas", "rmse_receita", "est_2T26_real", "est_2T26_model")})
        print("  VSO acumulada por coorte (k=0,1,2,3,4,6,8,12 tri):", [round(100 * p["cum_vso"][k]) for k in (0, 1, 2, 3, 4, 6, 8, 12)])
        print("  PoC (k=0,2,4,6,8,10,12,16):", [round(100 * p["poc"][k]) for k in (0, 2, 4, 6, 8, 10, 12, 16)])
        print("  ano: VSO real | modelo · vendas real | modelo · receita real | modelo")
        for y in ("2019", "2020", "2021", "2022", "2023", "2024", "2025", "LTM 2T26"):
            v = VSO[name][y]; print(f"   {y}: {v['vso']} | {v['vso_model']} · {v['ven']} | {v['ven_model']} · {v['rec']} | {v['rec_model']}")
    print("Total VSO anual:", {y: v["vso"] for y, v in VSO["Total"].items()})
    json.dump({"fit": {k: {kk: vv for kk, vv in v.items() if not kk.endswith("_model")} for k, v in FIT.items()}, "vso": VSO, "Q": Q,
               "series": {k: {"ven": v["ven_model"], "rec": v["rec_model"], "ven_real": SEG[k]["ven"], "rec_real": SEG[k]["rec"]} for k, v in FIT.items()}},
              io.open(os.path.join(here, "_vso_cohort.json"), "w", encoding="utf-8"), ensure_ascii=False)
