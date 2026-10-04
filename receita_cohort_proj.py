# -*- coding: utf-8 -*-
"""Receita 2026-31 a partir das curvas de lançamento do usuário na CYRE (04/10/26, linhas 21-23 = 3T26/4T26 trimestrais; 15/17/19 =
2027-31 anuais), em base CONSOLIDADA ('Launches | Consolidação'). Coortes antigas (histórico VGV 100% até 2T26) rendem receita × f;
coortes novas (consolidadas) rendem × 1 (o f calibrado por segmento = razão consolidado ÷ 100%: 0,90 / 0,86 / 0,63).
Dois ritmos de venda: (A) curva histórica 2018-2T26; (B) ritmo atual, s0 e q reajustados em 1T25-2T26 (Alto e Médio desaceleraram).
Saída: _receita_cohort_proj.json e impressão."""
import io, json, os, itertools
from vso_cohort import SEG, FIT, simulate, rmse, Q, qi, n, D
here = os.path.dirname(os.path.abspath(__file__))
# curvas do usuário (CYRE 04/10/26 16:40), base consolidada, R$ mi
USER = {"Alto Padrão": {"3T26": 2500, "4T26": 1500, 2027: 6881.0, 2028: 7225.0, 2029: 7586.3, 2030: 7965.6, 2031: 8363.9},
        "Médio": {"3T26": 450, "4T26": 450, 2027: 3078.3, 2028: 3232.2, 2029: 3393.8, 2030: 3563.5, 2031: 3741.7},
        "MCMV (Vivaz)": {"3T26": 1110, "4T26": 1110, 2027: 5000.0, 2028: 6000.0, 2029: 6240.0, 2030: 6489.6, 2031: 6749.2}}
YS = [2027, 2028, 2029, 2030, 2031]; T = n + 2 + 4 * len(YS)   # até 4T31
# ritmo atual: reajusta s0, q em 1T25-2T26 (PoC e gp mantidos)
ALT = {}
for name, s in SEG.items():
    p = FIT[name]; best = None; i0 = qi["1T25"]
    for s0, q in itertools.product([x / 100 for x in range(20, 66, 5)], [x / 100 for x in range(4, 26)]):
        ven, _, est = simulate(s["lan"], s0, q, p["p0"], p["N"], p["d0"], p["gp"])
        e = rmse(ven, s["ven"], i0, n) + 0.25 * rmse(est, s["est"], i0, n)
        if best is None or e < best[0]: best = (e, s0, q)
    ALT[name] = {"s0": best[1], "q": best[2]}
def run(name, s0, q):
    p = FIT[name]; s = SEG[name]
    hist = list(s["lan"]) + [0.0] * (T - n)                       # coortes antigas, VGV 100%
    new = [0.0] * T; u = USER[name]; new[qi["2T26"] + 1] = u["3T26"]; new[qi["2T26"] + 2] = u["4T26"]
    for j, y in enumerate(YS):
        for k in range(4): new[n + 2 + 4 * j + k] = u[y] / 4
    vh, rh, eh = simulate(hist, s0, q, p["p0"], p["N"], p["d0"], p["gp"]); vn, rn, en = simulate(new, s0, q, p["p0"], p["N"], p["d0"], p["gp"])
    out = {}
    cols = {"2026": list(range(qi["1T26"], qi["1T26"] + 4))}; cols.update({str(y): list(range(n + 2 + 4 * j, n + 6 + 4 * j)) for j, y in enumerate(YS)})
    for y, idx in cols.items():
        rec = sum(p["f"] * rh[i] + rn[i] for i in idx); ven = sum(p["f"] * vh[i] + vn[i] for i in idx); est_fim = p["f"] * eh[idx[-1]] + en[idx[-1]]; est_ini = p["f"] * eh[idx[0] - 1] + en[idx[0] - 1]
        lan = (sum(s["lan"][i] for i in idx if i < n) * p["f"]) + sum(new[i] for i in idx)
        out[y] = {"lan": lan, "ven": ven, "rec": rec, "est_fim": est_fim, "vso": ven / (est_ini + lan) if est_ini + lan else None}
    return out
RES = {"A · curva histórica": {name: run(name, FIT[name]["s0"], FIT[name]["q"]) for name in SEG},
       "B · ritmo atual (1T25-2T26)": {name: run(name, ALT[name]["s0"], ALT[name]["q"]) for name in SEG}}
real26 = {name: sum(SEG[name]["rec"][i] for i in range(qi["1T26"], n)) for name in SEG}   # 1S26 real
if __name__ == "__main__":
    print("ritmo atual (s0, q):", ALT)
    for sc, R in RES.items():
        print("\n==", sc, "(base consolidada, R$ mi)")
        print("segmento        ano   lanç   vendas  receita  estoque  VSO")
        tot = {y: [0, 0, 0, 0] for y in ["2026"] + [str(y) for y in YS]}
        for name, d in R.items():
            for y, v in d.items():
                print(f"{name:14} {y}  {v['lan']:6.0f}  {v['ven']:6.0f}  {v['rec']:6.0f}  {v['est_fim']:7.0f}  {100*v['vso']:4.0f}%")
                for k, kk in enumerate(("lan", "ven", "rec", "est_fim")): tot[y][k] += v[kk]
        for y, t in tot.items(): print(f"{'TOTAL':14} {y}  {t[0]:6.0f}  {t[1]:6.0f}  {t[2]:6.0f}  {t[3]:7.0f}")
    print("\n1S26 real por segmento:", {k: round(v) for k, v in real26.items()})
    json.dump({"user": {k: {str(kk): vv for kk, vv in v.items()} for k, v in USER.items()}, "alt": ALT, "res": RES}, io.open(os.path.join(here, "_receita_cohort_proj.json"), "w", encoding="utf-8"), ensure_ascii=False)
