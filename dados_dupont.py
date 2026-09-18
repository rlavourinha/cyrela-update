# -*- coding: utf-8 -*-
"""DuPont trimestral (LTM) 2006-2026 a partir da planilha de demonstracoes do RI
(fontes/planilha_demonstracoes_financeiras.xlsx, formato Economatica, R$ mil,
consolidado, 3T05..2T26). ROE = LL atribuivel LTM / PL controladora medio;
margem = LL LTM / receita LTM; giro = receita LTM / ativo medio; alav = ativo medio /
PL medio. Identidade exata: ROE = margem x giro x alav (mesmas medias).
Tambem: ROE consolidado (lucro consolidado / PL consolidado), margem bruta, EBIT/receita,
resultado financeiro/receita, IR/LAIR. Saida: _dupont.json"""
import io, json, os, openpyxl
here = os.path.dirname(os.path.abspath(__file__))
wb = openpyxl.load_workbook(os.path.join(here, "fontes", "planilha_demonstracoes_financeiras.xlsx"), read_only=True, data_only=True)
ws = wb["CYRELA"]; rows = list(ws.iter_rows(values_only=True))
hdr = rows[3]; datas = [c for c in hdr[1:] if c is not None]
def row(i):  # 1-based como no dump
    r = rows[i - 1]; return [None if (c is None or c == "-") else float(c) for c in r[1:1 + len(datas)]]
ATIVO, PL, PLC, MIN, INV = row(10), row(57), row(55), row(56), row(31)
REC, CPV, EBIT, RFIN, LAIR, IR, LCONS, LL, EQ = row(71), row(72), row(81), row(82), row(85), row(86), row(93), row(95), row(80)
q = [f"{d.year}-{d.month:02d}" for d in datas]
def ltm(v, i):
    w = v[i - 3:i + 1]; return None if (i < 3 or any(x is None for x in w)) else sum(w)
def med(v, i):  # media dos 5 balancos (fim de 4 trimestres + inicial)
    w = v[i - 4:i + 1]; return None if (i < 4 or any(x is None for x in w)) else sum(w) / 5
out = {}
for i in range(4, len(q)):
    ll, rec, a, pl = ltm(LL, i), ltm(REC, i), med(ATIVO, i), med(PL, i)
    if None in (ll, rec, a, pl): continue
    d = {"roe": ll / pl * 100, "margem": ll / rec * 100, "giro": rec / a, "alav": a / pl,
         "roe_consolidado": ltm(LCONS, i) / med(PLC, i) * 100, "mb": (rec - ltm(CPV, i)) / rec * 100,
         "ebit_rec": ltm(EBIT, i) / rec * 100, "rfin_rec": ltm(RFIN, i) / rec * 100,
         "ir_lair": (ltm(IR, i) / ltm(LAIR, i) * 100) if ltm(LAIR, i) else None,
         "equiv_rec": ltm(EQ, i) / rec * 100, "min_lcons": (ltm(LCONS, i) - ll) / ltm(LCONS, i) * 100 if ltm(LCONS, i) else None,
         "ll_ltm": ll / 1000, "rec_ltm": rec / 1000, "ativo_med": a / 1000, "pl_med": pl / 1000,
         "eq_ltm": ltm(EQ, i) / 1000, "inv_med": (med(INV, i) or 0) / 1000,
         # ROE ex-equivalencia: tira o resultado de equivalencia do lucro e o book de 'Investimentos' do PL
         "roe_ex_eq": (ll - ltm(EQ, i)) / (pl - (med(INV, i) or 0)) * 100}
    out[q[i]] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
json.dump({"_meta": {"fonte": "RI Cyrela, planilha_demonstracoes_financeiras.xlsx (Economatica), consolidado R$ mil; LTM; medias de 5 balancos",
                     "nota": "PL = controladora (LL atribuivel); ativo total; identidade ROE = margem x giro x alav exata"}, "dados": out},
          io.open(os.path.join(here, "_dupont.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("tri | ROE | ROE ex-eq | equiv LTM | inv med | PL med | margem | giro | alav")
for k, d in out.items():
    if k.endswith("-12") or k == q[-1]:
        print(f"{k} {d['roe']:5.1f} {d['roe_ex_eq']:5.1f} {d['eq_ltm']:7.0f} {d['inv_med']:7.0f} {d['pl_med']:7.0f} {d['margem']:5.1f} {d['giro']:5.2f} {d['alav']:5.2f}")
