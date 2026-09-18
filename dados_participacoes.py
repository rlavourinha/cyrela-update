# -*- coding: utf-8 -*-
"""Historico das participacoes da Cyrela em Cury, Plano & Plano e Lavvi
(nota de investimentos dos ITR/DFP 1T20-2T26). Pega o menor % que aparece
logo apos o nome (a tabela de coligadas repete o nome em 2-3 tabelas; o %
direto e o que interessa; tambem guarda o maior, p/ % com indireta)."""
import io
import json
import os
import re

here = os.path.dirname(os.path.abspath(__file__))
SP = r"C:\Users\RLAVOU~1\AppData\Local\Temp\claude\D--rlavourinha-Pictures-OneDrive--rea-de-Trabalho-Claude\e4e1cc5f-6e04-4e22-ba8b-ce88f93cdefb\scratchpad\itrdocs"

ALVOS = {
    "cury": r"Cury Construtora",
    "pp": r"Plano\s*&\s*Plano (?:Constru|Desenvolvimento)",
    "lavvi": r"Lavvi Empreendimentos Imobili[áa]rios (?:S[./]|Ltda)",
}
PCT = re.compile(r"\b(\d{1,2},\d{2})\b")

out = {}
for a in range(20, 27):
    for t in range(1, 5):
        q = f"{t}T{a}"
        f = os.path.join(SP, f"{q}_0.lay.txt")
        if not os.path.exists(f):
            continue
        s = io.open(f, encoding="utf-8", errors="ignore").read()
        d = {}
        for nome, rx in ALVOS.items():
            pcts = []
            for m in re.finditer(rx, s):
                jan = s[m.end():m.end() + 120]
                two = PCT.findall(jan)
                if two:
                    v = float(two[0].replace(",", "."))
                    if 1 <= v <= 60:
                        pcts.append(v)
            if pcts:
                d[nome] = {"min": min(pcts), "max": max(pcts), "n": len(pcts)}
        out[q] = d
        print(q, " | ".join(f"{n}: {d[n]['min']:.2f}" + (f"/{d[n]['max']:.2f}" if d[n]["max"] != d[n]["min"] else "")
                            + f" ({d[n]['n']}x)" if n in d else f"{n}: —"
                            for n in ("cury", "pp", "lavvi")))

io.open(os.path.join(here, "_participacoes.json"), "w", encoding="utf-8").write(json.dumps(out))
