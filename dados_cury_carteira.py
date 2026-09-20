# -*- coding: utf-8 -*-
"""Cury: carteira gerencial de recebíveis por trimestre (releases, seção 'Carteira e contas a receber'): carteira total, pró-soluto,
venda direta, obras concluídas/em andamento, contas a receber contábil. Baixa os releases do RI (mziq) para fontes/verificacao/,
extrai o texto e faz o parse. Saída: _cury_carteira.json (R$ mi)."""
import io, os, re, json, requests, pdfplumber
here = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(here, "fontes", "verificacao")
M = "https://api.mziq.com/mzfilemanager/v2/d/702b9586-4f10-4a79-a7e6-232ce8803136/"
REL = {"1T23": "9fe32ff7-ce58-0092-8e88-381d5c9a2a21", "2T23": "596eefe4-edb5-4103-7390-f2b047ad8d2b", "3T23": "2881faf6-150d-0fa0-e511-54176870db3e", "4T23": "b60b7f21-9943-3178-52eb-8441ca2873a2",
       "1T24": "bdac9baa-886d-b5e6-786c-759551477b7a", "2T24": "18ae7a92-e99b-8b52-bc9f-e9e7c93f46c6", "3T24": "fd006afc-e40d-17bc-1e33-7c5e6cbadb4f", "4T24": "0f61c6d0-4759-b8c6-d6dd-b8447ae0c077",
       "1T25": "b63ac452-760a-a97c-2602-4b5464961e96", "2T25": "46f51148-09b8-e8f1-1647-cc6f47375a96", "3T25": "7aaa6ee3-954f-0031-7993-e5c0124ee526", "4T25": "046b9f09-7cd2-8ac1-c625-000bafdd0768",
       "1T26": "6eee43ec-ffb1-f99b-7d41-3618f0b1fd67", "2T26": "8ffb3865-6cf8-f750-d1d6-aafbd22c8925"}
TRN = {"1T25": "0745f65a-bffb-72cc-9841-517b944a6184", "2T25": "80f251a5-3d09-d452-a136-bfe7a3edac29", "3T25": "e3bbad24-a64c-d5ba-64f2-0ee420f782bc", "4T25": "b542fca8-c626-979b-14d0-af1ad8b8e833",
       "1T26": "14d8973c-9a9e-a6c0-6d84-cf0034d78d8a", "2T26": "1c0c8ef8-70b4-61a5-8c28-efd1d5f0628e"}
def get(name, uid):
    pdf = os.path.join(D, name + ".pdf"); txt = os.path.join(D, name + ".txt")
    if not os.path.exists(txt):
        if not os.path.exists(pdf): open(pdf, "wb").write(requests.get(M + uid + "?origin=2", timeout=180, headers={"User-Agent": "Mozilla/5.0"}).content)
        with pdfplumber.open(pdf) as p: t = "\n".join((pg.extract_text() or "") for pg in p.pages)
        io.open(txt, "w", encoding="utf-8").write(t)
    return io.open(txt, encoding="utf-8").read()
num = lambda s: float(s.replace(".", "").replace(",", "."))
out = {}
for q, uid in REL.items():
    t = re.sub(r"[ \t]+", " ", get(f"cury_release_{q}", uid)); i = t.find("Carteira Cury"); seg = t[i:i + 3000] if i > 0 else ""
    r = {}
    for key, pat in (("carteira_total", r"Carteira Total ([\d.,]+) ([\d.,]+)"), ("pro_soluto", r"Pro-?[Ss]oluto ([\d.,]+) ([\d.,]+)"), ("venda_direta", r"Venda direta ([\d.,]+) ([\d.,]+)"), ("contas_receber", r"Contas a receber ([\d.,]+) ([\d.,]+)")):
        m = re.search(pat, seg)
        if m: r[key] = num(m.group(1)); r[key + "_ant"] = num(m.group(2))
    m = re.search(r"Obras em andamento ([\d.,]+) ([\d.,]+)", seg)
    if m: r["obras_andamento"] = num(m.group(1))
    out[q] = r; print(q, r if r else "SEM SEÇÃO 'Carteira Cury'", "|", re.sub(r"\s+", " ", seg[:160]) if not r else "")
for q, uid in TRN.items(): get(f"cury_transcricao_{q}", uid)
json.dump({"_meta": {"fonte": "releases trimestrais da Cury (RI, mziq), seção 'Carteira e contas a receber': carteira gerencial = recebíveis fora das instituições financeiras (pró-soluto + venda direta); R$ mi; *_ant = coluna comparativa (trimestre anterior)"}, "serie": out}, io.open(os.path.join(here, "_cury_carteira.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
