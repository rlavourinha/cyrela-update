# -*- coding: utf-8 -*-
"""Duracao lancamento -> entrega por projeto, do anexo 'Empreendimentos Entregues'
dos releases (lista anual nos 4T; 1T26/2T26 para 2026). Saida: _entregas_ciclo.json
e resumo por ano de entrega e por produto (MAP = Alto Padrao/Medio/outros; MCMV)."""
import glob, io, json, os, re, statistics as st
here = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(here, "fontes")
MES = {m: i for i, m in enumerate("jan fev mar abr mai jun jul ago set out nov dez".split(), 1)}
DT = re.compile(r"\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\s?-\s?(\d{2})\b", re.I)
def rd(p):
    raw = open(p, "rb").read()
    try: return raw.decode("utf-8")
    except UnicodeDecodeError: return raw.decode("cp1252", errors="replace")
def num(s):
    s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return None
rows = []
files = sorted(glob.glob(os.path.join(F, "release_4T*.txt"))) + [os.path.join(F, f"release_{q}.txt") for q in ("1T26", "2T26")]
for p in files:
    tri = re.search(r"release_(\dT\d\d)", p).group(1); t = rd(p)
    i = t.lower().find("empreendimentos entregues", max(0, t.lower().rfind("anexo")))  # anexo
    k = [m.start() for m in re.finditer(r"empreendimentos entregues", t, re.I)]
    if not k: continue
    seg = t[k[-1]:k[-1] + 60000]
    for ln in seg.splitlines():
        ds = list(DT.finditer(ln))
        if len(ds) < 2: continue
        l, e = ds[0], ds[1]
        lan = (2000 + int(l.group(2)), MES[l.group(1).lower()]); ent = (2000 + int(e.group(2)), MES[e.group(1).lower()])
        dur = (ent[0] - lan[0]) * 12 + (ent[1] - lan[1])
        if not (6 <= dur <= 120): continue
        nome = ln[:l.start()].strip(" 0123456789").strip()
        rest = ln[e.end():]
        low = ln.lower()
        if "mcmv" in low or "vivaz" in low or "cury" in low or "dez " in low[:12] or "certto" in low or "super citt" in low: prod = "MCMV"
        elif "alto padr" in low or "médio" in low or "medio" in low or "living" in low: prod = "MAP"
        else: prod = "outro"
        nums = [num(x) for x in re.findall(r"\d[\d.]*,?\d*", re.sub(r"\d+%", "", rest))]
        nums = [x for x in nums if x is not None]
        vgv = None
        if len(nums) >= 3: vgv = nums[1]
        elif len(nums) == 2: vgv = nums[0]
        if vgv and vgv > 5000: vgv = vgv / 1000  # R$ mil
        rows.append({"release": tri, "nome": nome[:60], "lanc": f"{lan[0]}-{lan[1]:02d}", "entrega": f"{ent[0]}-{ent[1]:02d}",
                     "meses": dur, "produto": prod, "vgv": vgv, "linha": ln.strip()[:140]})
# dedup (mesmo nome + entrega)
seen, out = set(), []
for r in rows:
    key = (r["nome"].lower(), r["entrega"], r["lanc"])
    if key in seen: continue
    seen.add(key); out.append(r)
json.dump(out, io.open(os.path.join(here, "_entregas_ciclo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("projetos:", len(out), "| releases:", sorted(set(r["release"] for r in out)))
def resumo(sel):
    m = [r["meses"] for r in sel]
    w = [(r["meses"], r["vgv"]) for r in sel if r["vgv"]]
    wm = sum(a * b for a, b in w) / sum(b for _, b in w) if w else None
    return f"n={len(m):3d} mediana={st.median(m):5.1f} media={st.mean(m):5.1f} pond.VGV={wm if wm is None else round(wm,1)}"
print("\nPOR ANO DE ENTREGA (todos | MAP | MCMV)")
for a in sorted(set(r["entrega"][:4] for r in out)):
    s = [r for r in out if r["entrega"].startswith(a)]
    print(a, resumo(s), "| MAP", resumo([r for r in s if r["produto"] == "MAP"]) if any(r["produto"] == "MAP" for r in s) else "-",
          "| MCMV", resumo([r for r in s if r["produto"] == "MCMV"]) if any(r["produto"] == "MCMV" for r in s) else "-")
print("\nTOTAL MAP", resumo([r for r in out if r["produto"] == "MAP"]))
print("TOTAL MCMV", resumo([r for r in out if r["produto"] == "MCMV"]))
print("TOTAL outro", resumo([r for r in out if r["produto"] == "outro"]))
print("\nsem produto (amostra):", [r["linha"][:90] for r in out if r["produto"] == "outro"][:6])
