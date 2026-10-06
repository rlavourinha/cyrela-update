# -*- coding: utf-8 -*-
"""Curva de entregas (VGV 100%) por segmento: entregas_t = s × Σ_k w_k × lançamentos_{t−k}, com w_k = distribuição discreta
(normal truncada em trimestres, média μ e desvio σ) do prazo lançamento → entrega. Calibrada no histórico trimestral da CYRE
(_cyre_oper_q.txt: lançamentos 100% 401-403, entregas 166-170; 1T10-2T26) sobre as somas anuais 2016-2025. Projeção 2026-31 com
as curvas de lançamento do usuário já em base 100% (CYRE linhas 253/255/257, 04-05/10/26). Pedido de 05/10/26. Saída: _entregas_cohort.json."""
import io, json, os, math, itertools
here = os.path.dirname(os.path.abspath(__file__))
L = [l for l in io.open(os.path.join(here, "_cyre_oper_q.txt"), encoding="utf-8").read().split("\n") if l.strip()]
Q = L[0].rsplit("|", 1)[1].split(",")[:-1]; n = len(Q); qi = {q: i for i, q in enumerate(Q)}
D = {}
for l in L[1:]:
    r = l.split("|", 1)[0]; vals = l.rsplit("|", 1)[1]; D[int(r)] = [float(x) if x not in ("", "﻿") else 0.0 for x in vals.split(",")[:-1]]
def add(a, b): return [x + y for x, y in zip(a, b)]
SEG = {"Alto Padrão": {"lan": D[401], "ent": D[167]}, "Médio": {"lan": D[402], "ent": add(D[168], D[169])}, "MCMV (Vivaz)": {"lan": D[403], "ent": D[170]}}   # Vivaz Prime entregue somado ao Médio
# curvas do usuário, base 100% (CYRE 253/255/257): 2026 = 1S26 real + 2S26E; 2027-31
USER = {"Alto Padrão": {2026: 7435, 2027: 7694, 2028: 8079, 2029: 8483, 2030: 8907, 2031: 9352}, "Médio": {2026: 3045, 2027: 3466, 2028: 3639, 2029: 3821, 2030: 4012, 2031: 4213},
        "MCMV (Vivaz)": {2026: 5755, 2027: 7551, 2028: 9061, 2029: 9424, 2030: 9800, 2031: 10192}}
U26 = {"Alto Padrão": (2795, 1677), "Médio": (507, 507), "MCMV (Vivaz)": (1676, 1676)}   # 3T26E, 4T26E (100%)
YEARS = list(range(2016, 2026)); PROJ = list(range(2026, 2032)); T = n + 2 + 4 * 5 + 24   # até 2037 (entregas das coortes de 2031)
def weights(mu, sd, kmax=40):
    w = [math.exp(-0.5 * ((k - mu) / sd) ** 2) for k in range(kmax + 1)]; t = sum(w); return [x / t for x in w]
def deliver(lan, w):
    out = [0.0] * len(lan)
    for c, Lc in enumerate(lan):
        if Lc <= 0: continue
        for k, wk in enumerate(w):
            if c + k < len(out): out[c + k] += Lc * wk
    return out
def yidx(y): return [i for i, q in enumerate(Q) if q.endswith(str(y)[2:])]
# prazo médio amarrado ao ciclo do modelo de receita (PoC = 100% em d0 + N trimestres: Alto 14, Médio 12, Vivaz 11; calls: Cyrela ~48 m, Vivaz 30-36 m), ±2 tri; só dispersão e escala livres
MU = {"Alto Padrão": [x / 2 for x in range(26, 33)], "Médio": [x / 2 for x in range(22, 29)], "MCMV (Vivaz)": [x / 2 for x in range(20, 27)]}
FIT = {}; RES = {}
for name, s in SEG.items():
    best = None
    for mu, sd in itertools.product(MU[name], [1.5, 2.0, 2.5, 3.0, 4.0]):
        w = weights(mu, sd); m = deliver(s["lan"], w)
        ya = [sum(s["ent"][i] for i in yidx(y)) for y in YEARS]; ym = [sum(m[i] for i in yidx(y)) for y in YEARS]
        sc = sum(a * b for a, b in zip(ya, ym)) / sum(b * b for b in ym)   # escala (preço na entrega vs no lançamento, distratos, perímetro)
        e = (sum((a - sc * b) ** 2 for a, b in zip(ya, ym)) / len(YEARS)) ** 0.5
        if best is None or e < best[0]: best = (e, mu, sd, sc)
    e, mu, sd, sc = best; w = weights(mu, sd)
    lan = list(s["lan"]) + [0.0] * (T - n); lan[n] = U26[name][0]; lan[n + 1] = U26[name][1]
    for j, y in enumerate(PROJ[1:]):
        for k in range(4): lan[n + 2 + 4 * j + k] = USER[name][y] / 4
    m = deliver(lan, w)
    hist = {str(y): {"real": round(sum(s["ent"][i] for i in yidx(y))), "model": round(sc * sum(m[i] for i in yidx(y))), "lan": round(sum(s["lan"][i] for i in yidx(y)))} for y in YEARS}
    hist["1S26"] = {"real": round(sum(s["ent"][i] for i in (qi["1T26"], qi["2T26"]))), "model": round(sc * sum(m[i] for i in (qi["1T26"], qi["2T26"]))), "lan": round(s["lan"][qi["1T26"]] + s["lan"][qi["2T26"]])}
    cols = {"2026": list(range(qi["1T26"], qi["1T26"] + 4))}; cols.update({str(y): list(range(n + 2 + 4 * j, n + 6 + 4 * j)) for j, y in enumerate(PROJ[1:])})
    proj = {y: {"ent": round(sc * sum(m[i] for i in idx)), "lan": round(USER[name][int(y)])} for y, idx in cols.items()}
    proj["2026"]["ent_2S26"] = round(sc * sum(m[i] for i in (qi["2T26"] + 1, qi["2T26"] + 2)))
    cum = []; acc = 0.0
    for k in range(0, 25): acc += w[k]; cum.append(round(100 * acc))
    FIT[name] = {"mu_tri": mu, "sd_tri": sd, "escala": round(sc, 3), "rmse": round(e), "meses": round(mu * 3), "cum": cum}; RES[name] = {"hist": hist, "proj": proj}
if __name__ == "__main__":
    for name in SEG:
        f = FIT[name]; print(name, f"prazo médio {f['meses']} meses (σ {f['sd_tri']} tri), escala {f['escala']}, RMSE anual {f['rmse']}")
        print("  % entregue por trimestre desde o lançamento (k=8,10,12,14,16,18,20):", [f["cum"][k] for k in (8, 10, 12, 14, 16, 18, 20)])
        print("  ano: lanç | entregas real | modelo"); h = RES[name]["hist"]
        for y in list(h): print(f"   {y}: {h[y]['lan']:6} | {h[y]['real']:6} | {h[y]['model']:6}")
        print("  proj: lanç | entregas"); p = RES[name]["proj"]
        for y in p: print(f"   {y}: {p[y]['lan']:6} | {p[y]['ent']:6}" + (f"  (2S26: {p[y]['ent_2S26']})" if y == "2026" else ""))
    tot = {y: sum(RES[s]["proj"][y]["ent"] for s in SEG) for y in RES["Médio"]["proj"]}; print("TOTAL entregas:", tot)
    th = {y: (sum(RES[s]["hist"][y]["real"] for s in SEG), sum(RES[s]["hist"][y]["model"] for s in SEG)) for y in RES["Médio"]["hist"]}; print("TOTAL hist real|modelo:", th)
    json.dump({"fit": FIT, "res": RES, "tot": tot, "tot_hist": th}, io.open(os.path.join(here, "_entregas_cohort.json"), "w", encoding="utf-8"), ensure_ascii=False)
