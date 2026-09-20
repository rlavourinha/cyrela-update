# -*- coding: utf-8 -*-
"""Anexo III dos releases (Reconhecimento de Receita por empreendimento): receita do trimestre de projetos cujo primeiro
reconhecimento ocorreu nos 12 meses anteriores ('Obras reconhecidas após <mês do ano anterior>') × demais projetos, e o PoC médio
(% de evolução financeira) dos projetos novos listados. Formato existe desde o release 1T23. Saída: _anexo3_novos.json (R$ mi)."""
import io, re, glob, json, os
here = os.path.dirname(os.path.abspath(__file__))
out = {}
for f in glob.glob(os.path.join(here, "fontes", "release_[1-4]T2[3-9].txt")):
    q = re.search(r"release_(\dT\d\d)", f).group(1); t = io.open(f, encoding="utf-8", errors="ignore").read()
    i = t.find("ANEXO III")
    if i < 0: continue
    i2 = t.find("ANEXO III", i + 10); i = i2 if i2 > 0 else i; seg = re.sub(r"[ \t]+", " ", t[i:i + 7000])
    m = re.search(r"Obras Reconhecidas ap[oó]s ([A-Za-zç]+ \d{4})(.*?)Sub-?Total", seg, re.S)
    sub = re.findall(r"Sub-?Total\s+([\d.]+)\s+([\d.\-]+)", seg); tot = re.search(r"\nTotal\s+([\d.]+)\s+([\d.\-]+)", seg)
    if not (m and len(sub) >= 2 and tot): print(q, "sem o padrão do anexo"); continue
    pocs = [int(x) for x in re.findall(r"\s(\d{1,2})% 0% [\d]", m.group(2))]
    num = lambda s: float(s.replace(".", ""))
    out[q] = {"apos": m.group(1), "antigos": num(sub[0][0]), "novos": num(sub[1][0]), "total": num(tot.group(1)), "n_novos_listados": len(pocs), "poc_medio_listado": (sum(pocs) / len(pocs) if pocs else None)}
ordq = lambda q: (int(q[2:]), int(q[0])); out = dict(sorted(out.items(), key=lambda kv: ordq(kv[0])))
json.dump({"_meta": {"fonte": "releases trimestrais, Anexo III Reconhecimento de Receita (incorporação residencial e loteamentos, R$ mi): 'Obras reconhecidas após <mês do ano anterior>' = receita do trimestre de projetos cujo primeiro reconhecimento ocorreu nos 12 meses anteriores; antigos = subtotal dos demais; PoC médio = média simples do % de evolução financeira dos projetos novos listados (top da lista)"}, "serie": out}, io.open(os.path.join(here, "_anexo3_novos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
for q, v in out.items(): print(q, v["apos"], v["antigos"], v["novos"], v["total"], v["n_novos_listados"], round(v["poc_medio_listado"] or 0))
