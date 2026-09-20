# -*- coding: utf-8 -*-
"""Caixa: imóveis retomados no balanço. Baixa as demonstrações contábeis BrGaap (RI da Caixa, mziq) de 2T e 4T de 2019-2026 para
fontes/mercado/caixa/ e extrai as linhas 'Bens não de uso próprio' (formato COSIF antigo, nota de outros valores e bens) e
'Ativos não financeiros mantidos para venda – recebidos' (formato Res. CMN 4.966, 2025+), mais a despesa 'Imóveis adjudicados/arrematados'.
Imprime as linhas encontradas com página; a consolidação em série fica em _caixa_bndu.json (preenchido à mão a partir do print)."""
import io, os, re, json, requests
from pypdf import PdfReader
here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "fontes", "mercado", "caixa"); os.makedirs(D, exist_ok=True)
B = "https://api.mziq.com/mzfilemanager/v2/d/fb86b0b8-b4e9-407b-a575-ba3668a566a9/"; H = {"User-Agent": "Mozilla/5.0"}
DOCS = {"4T25": "bce1f8c1-c985-98a4-a522-beff5d2833db", "2T25": "b2c3de23-f333-97a8-dc0a-edd7fa863c09", "4T24": "eeacbc99-375e-405e-7eba-fc29fa1e562f", "2T24": "b52ecdb4-8b1f-d310-5e6f-914b850611c0",
        "4T23": "682b56bc-dc00-86c2-bf26-0e031e9a45c0", "2T23": "378b959b-dab9-d7e3-fb70-5bf02937a1f4", "4T22": "7d72390a-6746-0436-0810-bb798f8f1b26", "2T22": "896660ab-98f2-b5eb-b054-e965d2d17460",
        "4T21": "ff25cf01-2f48-91cb-2e06-f5392aeda37c", "2T21": "cd24efea-c74c-59a3-7fcb-fc9b7cba54bb", "4T20": "ca650f80-7ad8-0cf9-d84c-2861e9432e28", "2T20": "038d663d-2eac-1be9-1b2f-d83d79ceb9b5",
        "4T19": "d1b103bf-b09f-14fd-0457-ee39ae61aa91", "2T19": "4dc18454-76c0-457c-bb88-15323424cd09"}
PAT = r"n[ãa]o de uso pr[óo]prio|mantidos para venda|adjudicados|arrematados|Outros valores e bens|bens n[ãa]o de uso"
out = io.open(os.path.join(here, "_caixa_bndu_linhas.txt"), "w", encoding="utf-8")
for q, u in DOCS.items():
    p = os.path.join(D, f"caixa_dc_brgaap_{q}.pdf")
    if not os.path.exists(p) or os.path.getsize(p) < 100000:
        r = requests.get(B + u + "?origin=2", headers=H, timeout=600); open(p, "wb").write(r.content)
    try: rd = PdfReader(p)
    except Exception as e: print(q, "ERR", e, flush=True); continue
    n = 0
    for i, pg in enumerate(rd.pages):
        t = pg.extract_text() or ""
        for l in t.splitlines():
            if re.search(PAT, l, re.I) and re.search(r"\d", l): out.write(f"{q} p{i+1} | {l.strip()[:200]}\n"); n += 1
    print(q, len(rd.pages), "pags,", n, "linhas", flush=True)
out.close(); print("fim")
