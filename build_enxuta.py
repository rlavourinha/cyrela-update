# -*- coding: utf-8 -*-
"""Gera enxuta.html — a versão enxuta (45-60 min) da apresentação de Cyrela.
Reaproveita CSS, navegação e alguns slides de index.html (recorte por índice de slide,
com kicker trocado) e gera os slides novos a partir dos JSONs e do dump do modelo
(_modelo_dump.tsv, gerado via COM a partir do CYREMod). Roteiro do usuário (17/09/2026):
1 companhia · 2 acionistas/conselho/diretoria · 3 overview operacional · 4 momento do ciclo ·
5 atualização operacional (≈80% do conteúdo final)."""
import io, json, os, re, math
here = os.path.dirname(os.path.abspath(__file__))
J = lambda f: json.load(io.open(os.path.join(here, f), encoding="utf-8"))
VERSAO = "v1.1 · 17/09/2026"

# ---------------------------------------------------------------- deck atual
H = io.open(os.path.join(here, "index.html"), encoding="utf-8").read()
CSS = H[H.index("<style>"):H.index("</style>") + 8]
JS = H[H.index("// ================= APRESENTACAO (v5)"):H.rindex("</script>")]
JS = JS.replace('var a = document.createElement("a");', 'var a = document.createElement("a"); if (sl.querySelector(".tag-novo")) a.classList.add("novo");', 1)   # bolinha amarela nos slides novos (19/09/26)
deck = H[H.index('<div class="deck"'):H.index('<section class="tab on"')]
SECS = re.split(r'(?=<section class="slide")', deck)[1:]

def take(i, kick, teoria=False, strip_viz=False, title=None, callout=None, append=None, repl=None):
    """recorta o slide i (1-based, numeração do deck atual) e troca o kicker (e, se pedido, título, callout e um bloco no fim)."""
    s = SECS[i - 1]
    for a_, b_ in (repl or []): s = s.replace(a_, b_)
    if append:
        j = s.rfind("</section>"); k = s.rfind("</div>", 0, j)
        s = s[:k] + append + s[k:]
    if strip_viz: s = re.sub(r'<div class="viz">.*?</svg></div>', '', s, flags=re.S)
    if title: s = re.sub(r'<h2 class="head-xl">.*?</h2>', '<h2 class="head-xl">' + title + '</h2>', s, count=1, flags=re.S)
    if callout is not None: s = re.sub(r'<div class="sl-callout">.*?</div>', callout, s, count=(0 if callout == '' else 1), flags=re.S)  # '' remove todos
    s = re.sub(r'<p class="kick"[^>]*>.*?</p>', '<p class="kick">' + kick + '</p>', s, count=1, flags=re.S)
    s = re.sub(r'<div class="slidenum">.*?</div>', '', s)
    if teoria:
        s = s.replace('<section class="slide">', '<section class="slide teoria">', 1)
        s = s.replace('<p class="kick">' + kick + '</p>', '<p class="kick">' + kick + ' ' + PILL + '</p>', 1)
    return s.strip() + "\n"

PILL = '<span class="pill-teoria">teoria</span>'

# ---------------------------------------------------------------- dados
def load_model():
    lines = io.open(os.path.join(here, "_modelo_dump.tsv"), encoding="utf-8").read().split("\n")
    hdr = lines[0].split("\t")[2].split(",")
    rows = {}
    for l in lines[1:]:
        p = l.split("\t")
        if len(p) >= 3:
            v = [None if x == "null" else float(x) for x in p[2].split(",")]
            rows[int(p[0])] = (p[1], dict(zip(hdr, v)))
    return hdr, rows
HDR, M = load_model()
QS = [h for h in HDR if len(h) == 4 and h[1] == "T"]      # 1T06..2T26 (inclui 3T26 vazio)
QS = [q for q in QS if M[21][1].get(q) is not None]         # até 2T26
YRS = [h for h in HDR if len(h) == 4 and h.isdigit()]
def mrow(r): return M[r][1]
def q12(row, q):  # soma 12m terminando em q
    i = QS.index(q)
    if i < 3: return None
    v = [row.get(x) for x in QS[i - 3:i + 1]]
    return None if any(x is None for x in v) else sum(v)
def ord_(q): return (int(q[2:]), int(q[0]))

LTMQ = ["3T25", "4T25", "1T26", "2T26"]
def ltm(d): return sum(d.get(q, 0) or 0 for q in LTMQ)
LR = J("_lancamentos_ri.json"); LC = J("_lancamentos_consol.json"); RI = J("_ri_regioes_vendas.json")
PR = J("_pracas_lanc.json"); CBR = J("_cbr_lanc.json"); EQ = J("_equiv_investidas_v5.json")["trimestre"]
CM = J("_cashme_entidade.json"); GEO = J("_geoimovel.json"); DIST = J("_prov_distrato_mov.json")["trimestre"]
INAD = J("_inad_imob.json"); INCC = J("_incc_series.json")["incc_di"]; GOV = J("_governanca_cvm.json")
SKR = J("_skr_rows.json") if os.path.exists(os.path.join(here, "_skr_rows.json")) else {}
INV = J("_invest_book.json")

def fmt(v, d=1):
    if v is None: return "—"
    s = f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s
def pct(v, d=1): return "—" if v is None else fmt(v * 100, d) + "%"

# ---------------------------------------------------------------- gráficos
class Chart:
    def __init__(s, x0, x1, y0, y1, vmin, vmax, n):
        s.x0, s.x1, s.y0, s.y1, s.vmin, s.vmax, s.n = x0, x1, y0, y1, vmin, vmax, n
        s.g = []; s.pend = []
    def y(s, v): return s.y1 - (s.y1 - s.y0) * (v - s.vmin) / (s.vmax - s.vmin)
    def x(s, i): return s.x0 + (s.x1 - s.x0) * (i + 0.5) / s.n
    def grid(s, ticks, f=lambda t: f"{t:g}"):
        for t in ticks:
            y = s.y(t)
            s.g.append(f'<line x1="{s.x0}" y1="{y:.1f}" x2="{s.x1}" y2="{y:.1f}" stroke="var(--grid)" opacity=".55"/>'
                       f'<text x="{s.x0-6}" y="{y+4:.1f}" class="axq" text-anchor="end" opacity=".85">{f(t)}</text>')
        yb = s.y(0) if s.vmin <= 0 <= s.vmax else s.y1
        s.g.append(f'<line x1="{s.x0}" y1="{yb:.1f}" x2="{s.x1}" y2="{yb:.1f}" stroke="var(--baseline)"/>')
    def xlabels(s, labels, every=4, off=0, fmtl=lambda l: l):
        for i, l in enumerate(labels):
            if (i - off) % every == 0:
                s.g.append(f'<text x="{s.x(i):.1f}" y="{s.y1+15}" class="axq" text-anchor="middle" opacity=".75">{fmtl(l)}</text>')
    def line(s, vals, color, w=2.2, dash="", lab=None, labval=True, opacity=1, last_opac=None):
        pts = [(s.x(i), s.y(v)) for i, v in enumerate(vals) if v is not None]
        if not pts: return
        if last_opac is not None and len(pts) >= 2:
            # ultimo ponto (LTM) em tom mais claro: segmento final tracejado e marcador translucido
            (xa, ya), (xb, yb_) = pts[-2], pts[-1]
            s.g.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb_:.1f}" stroke="{color}" stroke-width="{w}" stroke-dasharray="3 3" opacity="{last_opac}"/><circle cx="{xb:.1f}" cy="{yb_:.1f}" r="3.4" fill="{color}" opacity="{last_opac}"/>')
            if lab:
                last = [v for v in vals if v is not None][-1]
                s.pend.append((yb_, xb + 7, color, lab + (" " + labval(last) if callable(labval) else "")))
            vals = vals[:-1]; pts = pts[:-1]; lab = None
        # segmentos contínuos (quebra em None)
        segs, cur = [], []
        for i, v in enumerate(vals):
            if v is None:
                if cur: segs.append(cur); cur = []
            else: cur.append((s.x(i), s.y(v)))
        if cur: segs.append(cur)
        for sg in segs:
            if len(sg) == 1:
                s.g.append(f'<circle cx="{sg[0][0]:.1f}" cy="{sg[0][1]:.1f}" r="2.5" fill="{color}"/>')
            else:
                s.g.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in sg)}" fill="none" stroke="{color}" stroke-width="{w}" stroke-dasharray="{dash}" opacity="{opacity}"/>')
        x, y = pts[-1]
        s.g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="{color}"/>')
        if lab:
            last = [v for v in vals if v is not None][-1]
            s.pend.append((y, x + 7, color, lab + (" " + labval(last) if callable(labval) else "")))
    def bars(s, vals, color, w=0.62, labels=None, rx=2, fill=True, base=None, opac=None):
        slot = (s.x1 - s.x0) / s.n; bw = slot * w
        yb = s.y(0) if s.vmin <= 0 <= s.vmax else s.y1
        for i, v in enumerate(vals):
            if v is None: continue
            x = s.x(i) - bw / 2; y = s.y(v)
            top, h = (min(y, yb), abs(yb - y))
            f = color if fill else "none"; st = "none" if fill else color
            op = opac[i] if opac and i < len(opac) else 1
            s.g.append(f'<rect x="{x:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{max(h,0.5):.1f}" rx="{rx}" fill="{f}" stroke="{st}" stroke-width="1.4" opacity="{op}"/>')
            if labels and labels[i]:
                yy = y - 4 if v >= 0 else y + 12
                s.g.append(f'<text x="{s.x(i):.1f}" y="{yy:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="middle">{labels[i]}</text>')
    def vline(s, i, text=None, color="var(--muted)"):
        x = s.x(i)
        s.g.append(f'<line x1="{x:.1f}" y1="{s.y0}" x2="{x:.1f}" y2="{s.y1}" stroke="{color}" stroke-dasharray="3 3" opacity=".7"/>')
        if text: s.g.append(f'<text x="{x+4:.1f}" y="{s.y0+10}" class="fw-s2" fill="{color}">{text}</text>')
    def flush(s, gap=12, leader=False):
        P = sorted(s.pend)
        ys = [p[0] for p in P]
        for k in range(1, len(ys)):
            if ys[k] - ys[k - 1] < gap: ys[k] = ys[k - 1] + gap
        out = []
        for (y0, x, c, t), y in zip(P, ys):
            if leader and abs(y - y0) > 3:   # rótulo empurrado pelo gap: traço fino do ponto até o rótulo
                out.append(f'<line x1="{x-4:.1f}" y1="{y0:.1f}" x2="{x-1:.1f}" y2="{y:.1f}" stroke="{c}" stroke-width="1" opacity=".6"/>')
            out.append(f'<text x="{x:.1f}" y="{y+4:.1f}" class="fw-t2" fill="{c}">{t}</text>')
        s.pend = []
        return "\n".join(s.g + out)

def svg(W, Hh, body, title=None, sub=None, x=60):
    t = f'<text x="{x}" y="18" class="gtit">{title}</text>' if title else ""
    su = f'<text x="{x}" y="34" class="gsub">{sub}</text>' if sub else ""
    return f'<div class="viz"><svg viewBox="0 0 {W} {Hh}">{t}{su}{body}</svg></div>'

def nice_max(v, steps=(1, 2, 2.5, 5, 10)):
    if v <= 0: return 1
    e = 10 ** math.floor(math.log10(v))
    for st in steps:
        if v <= st * e: return st * e
    return 10 * e
def ticks(vmax, n=4):
    step = vmax / n
    return [round(step * i, 6) for i in range(0, n + 1)]

def sl(kick, title, body, cls="", nota=None):
    n = f'<p class="sl-nota">{nota}</p>' if nota else ""
    return f'<section class="slide{(" " + cls) if cls else ""}"><div class="sl-in"><p class="kick">{kick}</p><h2 class="head-xl">{title}</h2>{body}{n}</div></section>\n'

def callout(tag, text, color=None):
    st = f' style="border-left-color:{color}"' if color else ""
    st2 = f' style="color:{color}"' if color else ""
    return f'<div class="sl-callout"{st}><span class="ct-tag"{st2}>{tag}</span><p>{text}</p></div>'

def output(msg, sub=None):
    """caixa verde de fechamento: a mensagem que o slide deve deixar."""
    s = f'<span class="out-sub">{sub}</span>' if sub else ""
    return f'<div class="sl-output"><span class="out-tag">o que fica</span><span class="out-msg">{msg}</span>{s}</div>'
def _obox18(msg, sub=None, px=18):   # 22/09/26: caixa verde para mensagens de 100-120 caracteres (decisões editoriais do autor): 18px (17px quando sobra uma palavra), tag alinhada à 1ª linha, apoio numa linha inteira embaixo
    return (output(msg, sub).replace('<div class="sl-output">', '<div class="sl-output" style="row-gap:3px;margin-top:6px;align-items:flex-start;padding:7px 16px">', 1)
            .replace('<span class="out-tag">', '<span class="out-tag" style="margin-top:3px">', 1)
            .replace('<span class="out-msg">', f'<span class="out-msg" style="flex:1 1 600px;line-height:1.2;font-size:{px}px">', 1).replace('<span class="out-sub">', '<span class="out-sub" style="flex:1 1 100%;line-height:1.35">', 1))
S1, S2, S3, MU = "var(--s1)", "var(--s2)", "var(--s3)", "var(--muted)"
slides = []

# ================================================================ capa e roteiro
slides.append('''<section class="slide" id="sl0"><div class="sl-in">
  <p class="kick">apresentação · 18 de setembro de 2026</p>
  <div class="ticker-hero">CYRE3</div>
  <div class="chips2" style="margin-top:30px">
    <span class="chip2"><b>1</b> · dono, conselho e diretoria</span><span class="chip2"><b>2</b> · a companhia</span>
    <span class="chip2"><b>3</b> · a operação hoje</span><span class="chip2"><b>4</b> · onde estamos no ciclo</span><span class="chip2"><b>5</b> · atualização operacional</span>
  </div>
  <p class="byline">Apresentação de <b>Rafael Lavourinha</b> · 18/09/2026.</p>
</div></section>
''')
# (o slide de roteiro foi removido a pedido do usuário: o conteúdo dele está espalhado pelos slides)

# ================================================================ PARTE 1 · a companhia
P1 = "parte 2 · a companhia"
# --- história (linha do tempo)
marcos = [(1962, "Elie Horn funda|a Cyrela", S1), (1981, "Cria a construtora|e a Seller (vendas)", MU),
          (2005, "IPO no Novo Mercado|22 de setembro", S1, "end"), (2006, "Incorpora a RJZ|e entra no Rio", MU), (2007, "Cria a Living,|marca de médio padrão", S2, "start"),
          (2010, "Auge da expansão:|9 regiões, 109 projetos", S3), (2014, "Elie deixa o executivo;|filhos viram co-CEOs", S1),
          (2016, "Subscreve 13,6%|da Tecnisa", MU), (2018, "Cria a Vivaz|e a CashMe", S2),
          (2020, "IPOs de Lavvi,|P&amp;P e Cury", S1), (2021, "Cria a Cy.Capital: escritórios,|galpões e crédito", S2), (2025, "VGV recorde, PN especiais,|dividendo extra de R$ 1 bi", S3),
          (2026, "MoU com a TRX, encerrado em ago;|sai dos conselhos das JVs", S1)]
W, Hh = 980, 250
g = [f'<line x1="60" y1="120" x2="930" y2="120" stroke="var(--baseline)" stroke-width="2"/>']
def tx(ano):  # eixo comprimido antes de 2005
    return 60 + (300 - 60) * (ano - 1962) / (2005 - 1962) if ano <= 2005 else 300 + (930 - 300) * (ano - 2005) / (2026 - 2005)
for k, m_ in enumerate(marcos):
    ano, txt, c = m_[:3]; anc_ = m_[3] if len(m_) > 3 else None
    x = tx(ano)
    up = k % 2 == 0
    lvl = (k // 2) % 3
    y = 120 - (26 + 24 * lvl) if up else 120 + (26 + 24 * lvl)
    g.append(f'<line x1="{x:.1f}" y1="120" x2="{x:.1f}" y2="{y + (6 if up else -6):.1f}" stroke="{c}" opacity=".6"/><circle cx="{x:.1f}" cy="120" r="5" fill="{c}"/>')
    anchor = anc_ or ("middle" if 120 < x < 860 else ("start" if x <= 120 else "end"))
    g.append(f'<text x="{x:.1f}" y="{y + (0 if up else 12):.1f}" class="fw-t2" fill="{c}" text-anchor="{anchor}">{ano}</text>')
    l1, l2 = (txt.split("|") + [""])[:2]
    # ano junto ao eixo; texto na ordem de leitura (1ª linha sempre acima da 2ª)
    if up:
        y1 = y - 24 if l2 else y - 13
        g.append(f'<text x="{x:.1f}" y="{y1:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="{anchor}">{l1}</text>')
        if l2: g.append(f'<text x="{x:.1f}" y="{y - 13:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="{anchor}">{l2}</text>')
    else:
        g.append(f'<text x="{x:.1f}" y="{y + 24:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="{anchor}">{l1}</text>')
        if l2: g.append(f'<text x="{x:.1f}" y="{y + 35:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="{anchor}">{l2}</text>')
body = svg(W, Hh, "\n".join(g))
body += ('<div class="tiles" style="margin-top:14px"><div class="tile"><span class="n">64</span><span class="l">anos · fundador ainda preside o conselho</span></div>'
         '<div class="tile"><span class="n">28,6%</span><span class="l">bloco Elie Horn · sem acordo de acionistas</span></div>'
         '<div class="tile"><span class="n">2</span><span class="l">co-CEOs, filhos do fundador (desde 2014)</span></div>'
         '<div class="tile"><span class="n">21</span><span class="l">anos listada · 1.369 projetos lançados desde 2005</span></div></div>')
body += output('Incorporadora pura há 64 anos: já atravessou três ciclos inteiros.')
slides.append(sl("a companhia · 1962-2026", "Incorporação.", body,
  nota="Fontes: FR 2026 item 1.1 (histórico), 6.1 e 7.5; site do RI (ri.cyrela.com.br, Sobre a Cyrela: Living 2007, CashMe 2018, Cy.Capital 2021); planilha de lançamentos do RI (lista de empreendimentos 2005-2T26); atas e fatos relevantes de 2025-26. Tecnisa: FR 1.1 (R$ 74,5 mi em 2016 + R$ 20,4 mi em 2017)."))

# --- linhas de negócio + geografias
LREG = RI["lanc_regiao_100"]; anos = [str(a) for a in range(2005, 2026)] + ["LTM"]
def reg(k): return [(ltm(LREG[k]) if a == "LTM" else LREG[k].get(a, 0)) / 1e6 for a in anos]
sp = reg("São Paulo"); rj = reg("Rio de Janeiro"); spi = reg("São Paulo - Interior"); sul = reg("Sul")
outras = [sum((ltm(LREG[k]) if a == "LTM" else LREG[k].get(a, 0)) for k in ["Minas Gerais", "Espírito Santo", "Norte", "Centro Oeste", "Nordeste"]) / 1e6 for a in anos]
c = Chart(60, 870, 46, 178, 0, 14, len(anos)); c.grid([0, 3.5, 7, 10.5, 14], lambda t: f"{t:g}"); c.xlabels(anos, 2)
c.line(sp, S1, lab="SP capital", labval=lambda v: fmt(v, 1), last_opac=.45); c.line(rj, S2, lab="Rio", labval=lambda v: fmt(v, 1), last_opac=.45)
c.line(spi, S3, lab="SP interior", labval=lambda v: fmt(v, 1), last_opac=.45); c.line(sul, MU, lab="Sul", labval=lambda v: fmt(v, 1), dash="4 3", last_opac=.45)
c.line(outras, "var(--ink-2)", lab="outras", labval=lambda v: fmt(v, 1), dash="2 3", last_opac=.45)
body = svg(980, 200, c.flush() + '<text x="60" y="18" class="gtit">Lançamentos por região (VGV 100%, R$ bi por ano)</text><text x="60" y="34" class="gsub">planilha operacional do RI; "outras" = MG, ES, Norte, Nordeste e Centro-Oeste · LTM = 3T25-2T26, em tom claro</text>')
sp25 = LREG["São Paulo"]["2025"] / LREG["Total"]["2025"]; rj25 = LREG["Rio de Janeiro"]["2025"] / LREG["Total"]["2025"]
body += ('<div class="fwgrid" style="margin-top:10px"><div class="fwcard map"><header>três marcas, uma máquina</header><dl>'
         '<dt>Cyrela · alto padrão</dt><dd>Receita 2025 <b>R$ 5,25 bi</b> (56%), margem 31,5%; ticket de R$ 1,65 mi por unidade lançada.</dd>'
         '<dt>Living · médio</dt><dd>R$ 2,73 bi (29%), margem 31,4%.</dd>'
         '<dt>Vivaz · MCMV</dt><dd>R$ 1,38 bi (15%), margem 34,5%, a maior das três; 68% das unidades lançadas hoje.</dd>'
         '<dt>Demais</dt><dd>Loteamento e serviços (Seller), CashMe (crédito com garantia), Cy.Capital (gestora de 2021: escritórios, galpões e financiamento imobiliário) e participações: Cury, Lavvi, Plano&amp;Plano, SKR, Cyma.</dd></dl></div>'
         f'<div class="fwcard mcmv"><header>geografia: voltou para casa</header><dl><dt>2010</dt><dd>9 regiões com lançamento, de Norte a Sul — a expansão nacional do superciclo.</dd>'
         f'<dt>2025</dt><dd>5 praças: <b>SP capital = {pct(sp25,0)}</b> do VGV lançado, Rio {pct(rj25,0)}, Sul e Centro-Oeste residuais. Landbank: SP capital 56%, Rio 34% (2T26).</dd>'
         '<dt>leitura</dt><dd>Uma incorporadora paulistana com uma perna carioca; a "regional Sul sem liquidez" (call) é resto do passado.</dd></dl></div></div>')
body += output('Uma incorporadora paulistana com uma perna carioca.')
slides.append(sl(P1, "Três marcas, duas cidades.", body, nota="Fontes: FR 2026 item 1.3 (DRE por marca, 2025); planilha operacional do RI (lançamentos por região e por segmento, VGV 100% com permuta); lista de empreendimentos (praças = locais distintos com lançamento no ano); CYREMod (landbank por praça)."))

# --- momentos marcantes: lançamentos e lucro por ano
anos2 = [str(a) for a in range(2005, 2026)] + ["LTM"]
lanc = [PR[a]["vgv"] / 1000 for a in anos2[:-1]] + [ltm(LR["vgv_total"]) / 1e6]
lucro = [mrow(73).get(a) / 1000 if mrow(73).get(a) is not None else None for a in anos2[1:-1]]  # 2006..2025 reportado, R$ bi
lucro = [None] + lucro + [ltm(mrow(73)) / 1000]
OP2 = [1] * (len(anos2) - 1) + [.45]
c = Chart(60, 330, 46, 178, 0, 20, len(anos2)); c.grid([0, 5, 10, 15, 20]); c.xlabels(anos2, 4)
c.bars(lanc, S1, labels=[fmt(v, 1) if a in ("2010", "2016", "2025", "LTM") else "" for v, a in zip(lanc, anos2)], opac=OP2)
c.g.append('<text x="60" y="18" class="gtit">Lançamentos (R$ bi/ano)</text><text x="60" y="34" class="gsub">VGV 100%; LTM = 3T25-2T26, em tom claro</text>')
# participação de cada segmento no VGV lançado (planilha do RI, 100%)
def seg_ano(keys, a):
    return sum(LR[k].get(q, 0) for k in keys for q in LR["vgv_total"] if q.endswith(a[2:]))
shA, shM, shC = [], [], []
for a in anos2:
    if a == "LTM":
        tot = ltm(LR["vgv_total"]); shA.append(ltm(LR["vgv_alto"]) / tot); shM.append(ltm(LR["vgv_medio"]) / tot); shC.append(sum(ltm(LR[k]) for k in ("vgv_mcmv23", "vgv_mcmv1", "vgv_prime")) / tot); continue
    tot = seg_ano(["vgv_total"], a)
    if tot <= 0: shA.append(None); shM.append(None); shC.append(None); continue
    shA.append(seg_ano(["vgv_alto"], a) / tot); shM.append(seg_ano(["vgv_medio"], a) / tot); shC.append(seg_ano(["vgv_mcmv23", "vgv_mcmv1", "vgv_prime"], a) / tot)
cs = Chart(420, 660, 46, 178, 0, 1, len(anos2)); cs.grid([0, 0.25, 0.5, 0.75, 1], lambda t: f"{t*100:g}%"); cs.xlabels(anos2, 4)
cs.line(shA, S1, lab="alto", labval=lambda v: pct(v, 0), last_opac=.45); cs.line(shM, S2, lab="médio", labval=lambda v: pct(v, 0), last_opac=.45); cs.line(shC, S3, lab="MCMV", labval=lambda v: pct(v, 0), w=2.8, last_opac=.45)
cs.g.append('<text x="420" y="18" class="gtit">% do VGV por segmento</text><text x="420" y="34" class="gsub">MCMV inclui Vivaz Prime e MCMV 1</text>')
c2 = Chart(760, 960, 46, 178, -0.3, 2.1, len(anos2)); c2.grid([0, 0.7, 1.4, 2.1], lambda t: f"{t:g}"); c2.xlabels(anos2, 4)
c2.bars(lucro, S2, labels=[fmt(v, 1) if a in ("2010", "2017", "2025", "LTM") and v is not None else "" for v, a in zip(lucro, anos2)], opac=OP2)
c2.g.append('<text x="760" y="18" class="gtit">Lucro líquido (R$ bi)</text><text x="760" y="34" class="gsub">2020 inclui R$ 1,2 bi dos IPOs; LTM claro</text>')
body = svg(980, 200, c.flush() + cs.flush() + c2.flush())
body += ('<div class="cards3" style="margin-top:12px"><div class="c3"><span class="c3n">2007-2011</span><b>Superciclo e expansão nacional.</b> Lançamentos de R$ 5-8 bi/ano em nove regiões, lucro de R$ 729 mi em 2009. A conta veio depois: estouro de orçamento, distratos e saída das praças fora do eixo.</div>'
         '<div class="c3"><span class="c3n">2012-2018</span><b>Sete anos de desalavancagem.</b> PL parado em R$ 5-6 bi, receita de R$ 6,1 bi para R$ 2,7 bi (2017), dois anos de prejuízo. A companhia encolheu para SP e Rio e trocou volume por margem.</div>'
         '<div class="c3"><span class="c3n">2019-2026</span><b>Novo ciclo, agora com Vivaz e sócios listados.</b> VGV de R$ 18,6 bi em 2025 (recorde), lucro R$ 2,0 bi, ROE reportado ~20%. Em 2026 o dono está monetizando: PN especiais, dividendo extra e a tentativa de vender torre e galpões (MoU com a TRX, encerrado em ago/26).</div></div>')
body += output('O ciclo manda: volume e lucro vão embora, o balanço e a família ficam.')
slides.append(sl(P1, "Vinte anos, três ciclos.", body, nota="Fontes: lista de empreendimentos do RI (VGV 100% com permuta, por ano de lançamento); CYREMod linha 'Reported Net Income' (planilha de DFs do RI / ITR-DFP)."))

# --- vantagens competitivas (tese do usuário, 17/09/26: a vantagem é o acesso ao terreno; marca, engenharia e velocidade não são)
body = ('<p style="margin:2px 2px 8px;font-size:13.5px;line-height:1.4"><b>Por que o mercado é fragmentado:</b> terreno se compra por permuta, projeto se terceiriza, obra se contrata e o crédito é do banco. A barreira de entrada é <b>reputação e balanço, não escala</b> — milhares de players médios lançam no mesmo bairro.</p>'
        '<div class="fwgrid" style="margin-top:6px"><div class="fwcard map"><header>a vantagem: todo terreno passa pela mesa da Cyrela</header><dl>'
        '<dt>Escala que vira fluxo de terrenos</dt><dd>Com <b>~10% do mercado</b> de SP capital (10,9% das unidades em 2025; 13,5% do VGV na base Geoimóvel), a Cyrela é a primeira ligação de quem tem terreno para vender ou permutar. Ver tudo antes dos outros é a vantagem: escolhe o melhor, paga o preço certo, recusa o resto.</dd>'
        '<dt>Permuta e compra a prazo</dt><dd><b>46% do landbank em permuta</b> (2T26): o terrenista aceita ser sócio de quem entrega há 60 anos. Pelo mesmo motivo, a <b>compra a prazo</b> é mais factível para ela: o dono do terreno confia que vai receber (terrenos a pagar de R$ 3,2 bi, pagos ao longo do ciclo, com pouco caixa na largada).</dd>'
        '<dt>Balanço que financia o cliente</dt><dd>Rating brAAA, CRI a ~96% do CDI e caixa: quando o banco não repassa, a companhia <b>financia o comprador diretamente</b> (recebível performado de R$ 1,6 bi a 12% + inflação) e segura a venda que o concorrente sem balanço perde.</dd>'
        '</dl></div>'
        '<div class="fwcard mcmv"><header>o que não é vantagem</header><dl>'
        '<dt>Marca</dt><dd>Imóvel não é compra recorrente: o cliente compra o <b>sonho</b> (bairro, planta, preço), não a construtora. Não há fidelidade a monetizar; o "prêmio de marca" do sell-side é, no máximo, posicionamento de preço e produto. O que tamanho e histórico dão é acesso a <b>parcerias com grandes marcas</b> (Pininfarina, Porsche, Dolce&amp;Gabbana) — produto, não fidelidade.</dd>'
        '<dt>Engenharia própria</dt><dd>Pela classificação do RI, <b>73% dos canteiros estão em JV e 14% com terceiros</b>; só 13% na CBR. A Cyrela é incorporadora, não construtora. Não é a execução que se destaca — é a escolha do que executar.</dd>'
        '<dt>Vender rápido no alto padrão</dt><dd>88% vendido em 6-12 meses (slide seguinte) <b>não precisa ser bom</b>: quem vende tudo na largada pode ter deixado preço na mesa. Velocidade é caixa; margem é valor.</dd></dl></div></div>')
body += output('A vantagem é ver todo terreno primeiro — marca e engenharia não são.', 'Balanço e histórico ajudam duas vezes: garantem o repasse (financiando o cliente quando o banco não aprova) e permitem comprar o terreno a prazo, porque o terrenista confia que vai receber.')
slides.append(sl(P1, "A vantagem competitiva é o acesso ao terreno — não a marca, nem a obra.", body, nota="Fontes: Secovi-SP e Geoimóvel (share em SP capital), deck institucional 4T25 (permuta), FR 2026 2.1 (dívida e ratings), CYREMod (terrenos a pagar, recebível performado, equivalência), planilha operacional do RI (gestão de obra)."))
slides.append(take(40, P1, title="Velocidade de venda contra o mercado —<br>base Geoimóvel, SP capital.",
  callout='',
  append=output('A Cyrela não opera o ciclo; opera o presente.', 'Não há um fair share perseguido: a companhia vai sentindo o mercado e, conforme vende bem, aumenta o pipeline de projetos. É bom no sentido de não congelar na loucura que é o Brasil — e é o que dá mais problema quando o ciclo vira, porque o pipeline montado no topo chega à obra e à entrega na descida.')
  + '<p class="sl-nota">Base: Geoimóvel, SP capital, foto de mai/26, comparação na mesma idade (% vendido por faixa de meses desde o lançamento; mercado ex-Cyrela do mesmo segmento).</p>'))   # 22/09/26: base e data na nota (decisão editorial do autor)

TBL37 = ('<div class="viz" style="margin-top:8px"><table class="tl" style="width:100%;font-size:10.5px;line-height:1.1;border:2px solid var(--s2);border-collapse:collapse;text-align:center"><thead>'
       '<tr style="background:var(--s2);color:#fff"><th rowspan="2" style="text-align:left;padding:3px 8px;vertical-align:middle">P/B implícito = (ROE − g) ÷ (Ke − g)</th><th colspan="4" style="padding:2px 8px;border-left:1px solid rgba(255,255,255,.5)">g = 0%</th><th colspan="4" style="padding:2px 8px;border-left:1px solid rgba(255,255,255,.5)">g = 4%</th></tr>'
       '<tr style="background:var(--s2);color:#fff">' + ''.join(f'<th style="padding:2px 6px{";border-left:1px solid rgba(255,255,255,.5)" if k == 14 else ""}">Ke {k}%</th>' for g_ in (0, 4) for k in (14, 15, 17, 19)) + '</tr></thead><tbody>'
       + ''.join('<tr' + (' style="background:rgba(70,110,170,.12);font-weight:600"' if lab.startswith("ajustado,") else '') + f'><td style="text-align:left;padding:3px 8px">{lab}</td>' + ''.join(f'<td style="padding:3px 6px{";border-left:1px solid var(--s2)" if k == 14 else ""}">{fmt((roe - g_) / (k - g_), 2)}x</td>' for g_ in (0, 4) for k in (14, 15, 17, 19)) + '</tr>' for lab, roe in (("reportado, 19,5%", 19.5), ("ajustado, 16,7% (hoje: 1,0x book)", 16.7), ("ajustado ex-Cury, 15,4% (hoje: 0,89x)", 15.4)))
       + '</tbody></table><p class="sl-nota" style="margin:3px 2px 0;color:var(--s2)">Ke de ~17% é a premissa da apresentação: com ela o ROE ajustado de hoje vale 0,98x book, ou seja, o preço está justo; ex-Cury (0,89x) o mercado já desconta a máquina própria.</p></div>')
P3 = "parte 3 · a operação hoje"
PD = P3 + " · demanda"
P4 = "parte 4 · onde estamos no ciclo"
PO = "parte 4 · operacional"
qs_l = sorted(LR["vgv_total"], key=ord_)
def s12(k, q):
    i = qs_l.index(q); return sum((LR[k].get(x) or 0) for x in qs_l[i - 3:i + 1]) if i >= 3 else None
# --- variáveis recuperadas (18/09/26): os blocos operacionais que as definiam vêm agora de _enxuta_base.html
OP = J("_operacional_ri.json"); VS = J("_vso_seg.json"); MVC = J("_meses_venda_cyrela.json")
oT = [sum((LR["vgv_total"].get(q) or 0) for q in LTMQ) / 1e6]; oA = [sum((LR["vgv_alto"].get(q) or 0) for q in LTMQ) / 1e6]
vA = VS["100"]["alto"]; eT = [OP["estoque"]["vgv100_total"]["2T26"] / 1e3]; mv = [MVC["2T26"]]
# --- estoque e landbank (bloco regenerado em 18/09/26; o painel de anos de lançamento virou % de estoque pronto)
def _o12(d, q, div=1e6):
    i = qs_l.index(q); ks = qs_l[i - 3:i + 1]
    return sum((d.get(x) or 0) for x in ks) / div if i >= 3 else None
qe = [q for q in OP["tris"] if ord_(q) >= (19, 1)]
eA = [OP["estoque"]["vgv100_seg"]["alto"][q] / 1e3 for q in qe]; eM = [OP["estoque"]["vgv100_seg"]["medio"][q] / 1e3 for q in qe]; eC = [(OP["estoque"]["vgv100_seg"]["mcmv23"][q] + (OP["estoque"]["vgv100_seg"]["prime"][q] or 0)) / 1e3 for q in qe]
eT = [OP["estoque"]["vgv100_total"][q] / 1e3 for q in qe]; ePr = [OP["pronto"]["vgv100_total"][q] / 1e3 for q in qe]
c3 = Chart(60, 420, 46, 130, 0, 20, len(qe)); c3.grid([0, 5, 10, 15, 20]); c3.xlabels(qe, 4, 3, lambda l: "20" + l[2:])
c3.line(eT, "var(--ink-2)", lab="total", labval=lambda v: fmt(v, 1), dash="3 3"); c3.line(eA, S1, lab="alto", labval=lambda v: fmt(v, 1), w=2.4); c3.line(eM, S2, lab="médio", labval=lambda v: fmt(v, 1)); c3.line(eC, S3, lab="MCMV", labval=lambda v: fmt(v, 1), w=2.4); c3.line(ePr, MU, lab="pronto", labval=lambda v: fmt(v, 1), dash="4 3")
c3.g.append('<text x="60" y="18" class="gtit">Estoque a valor de mercado por segmento (R$ bi)</text><text x="60" y="34" class="gsub">VGV 100%, planilha do RI, pro forma ex-Cury e P&amp;P; pronto = unidades concluídas</text>')
qm = sorted(MVC, key=ord_); mv = [MVC[q] for q in qm]
def _v12(q):
    i = OP["tris"].index(q); ks = OP["tris"][i - 3:i + 1]
    return sum(OP["vendas"]["vgv100_total"][x] for x in ks) if i >= 3 else None
mv2 = [12 * OP["estoque"]["vgv100_total"][q] / _v12(q) if q in OP["estoque"]["vgv100_total"] and _v12(q) else None for q in qm]
c4 = Chart(540, 870, 46, 130, 0, 40, len(qm)); c4.grid([0, 10, 20, 30, 40]); c4.xlabels(qm, 8, 2, lambda l: "20" + l[2:])
c4.line(mv2, MU, lab="÷ vendas 12m", labval=lambda v: fmt(v, 0), dash="4 3"); c4.line(mv, S1, lab="RI", labval=lambda v: fmt(v, 1), w=2.6)
c4.g.append('<text x="540" y="18" class="gtit">Meses para vender o estoque</text><text x="540" y="34" class="gsub">RI (estoque ÷ vendas do trimestre × 3) e estoque ÷ vendas de 12 meses (100%)</text>')
ql = [q for q in OP["tris"] if q in LR["vgv_total"] and qs_l.index(q) >= 3]
lb = [OP["landbank"]["vgv100_total"][q] / 1e3 for q in ql]; lbc = [OP["landbank"]["vgvcbr_total"][q] / 1e3 for q in ql]
lby = [OP["landbank"]["vgv100_total"][q] / 1e3 / _o12(LR["vgv_total"], q) if _o12(LR["vgv_total"], q) else None for q in ql]
c5 = Chart(60, 420, 198, 286, 0, 60, len(ql)); c5.grid([0, 20, 40, 60]); c5.xlabels(ql, 8, 3, lambda l: "20" + l[2:])
c5.line(lb, S1, lab="100%", labval=lambda v: fmt(v, 1), w=2.6); c5.line(lbc, S1, lab="%Cyrela", labval=lambda v: fmt(v, 1), dash="4 3", opacity=.75)
c5.g.append('<text x="60" y="172" class="gtit">Banco de terrenos (VGV potencial, R$ bi)</text><text x="60" y="188" class="gsub">planilha do RI; ' + fmt(OP["landbank"]["n_terrenos"][ql[-1]], 0) + ' terrenos, ' + fmt(100 * OP["landbank"]["pct_permuta"][ql[-1]], 0) + '% em permuta no 2T26</text>')
qp = [q for q in OP["tris"] if OP["estoque"]["vgv100_total"].get(q) and OP["pronto"]["vgv100_total"].get(q) is not None]
prt = [100 * OP["pronto"]["vgv100_total"][q] / OP["estoque"]["vgv100_total"][q] for q in qp]
c6 = Chart(540, 870, 198, 286, 0, 50, len(qp)); c6.grid([0, 10, 20, 30, 40, 50], lambda t: f"{t:g}%"); c6.xlabels(qp, 8, 1, lambda l: "20" + l[2:])
c6.line(prt, S1, lab="pronto", labval=lambda v: fmt(v, 0) + "%", w=2.6)
c6.g.append('<text x="540" y="172" class="gtit">Estoque pronto como % do estoque</text><text x="540" y="188" class="gsub">VGV 100%, planilha do RI (série desde 4T12); pico de ' + fmt(max(prt), 0) + '% em ' + qp[prt.index(max(prt))] + '</text>')
body = svg(980, 306, c3.flush(15) + c4.flush(15) + c5.flush(15) + c6.flush(15))
_e = qe[-1]; _m = qm[-1]; _l = ql[-1]
body += ('<div class="cards3" style="margin-top:8px">'
         f'<div class="c3"><span class="c3n">estoque</span><b>R$ {fmt(eT[-1], 1)} bi a 100%</b> (R$ {fmt(OP["estoque"]["vgvcbr_total"][_e] / 1e3, 1)} bi %Cyrela), o maior da série pro forma: {fmt(100 * eA[-1] / eT[-1], 0)}% alto padrão. Pronto: R$ {fmt(ePr[-1], 1)} bi ({fmt(100 * ePr[-1] / eT[-1], 0)}% do total, {fmt(OP["pronto"]["un_total"][_e], 0)} unidades).</div>'
         f'<div class="c3"><span class="c3n">meses de venda</span><b>{fmt(mv[-1], 1)} meses</b> pelo RI ({fmt(mv2[-1], 0)} pelas vendas de 12 meses), de ~10 em 2024. Mais estoque com VSO caindo: é o número a vigiar no médio e alto padrão.</div>'
         f'<div class="c3"><span class="c3n">landbank</span><b>R$ {fmt(lb[-1], 1)} bi</b> = <b>{fmt(lby[-1], 1)} ano</b> de lançamentos, contra R$ 53,9 bi em 2015 e 3-4 anos na década passada. A companhia compra terreno para o ciclo, não para o estoque.</div></div>')
body += output('Estoque no recorde e landbank de um ano: a Cyrela carrega produto, não terreno.', 'O landbank curto é escolha (terreno a prazo e permuta, comprado quando o projeto fecha); o estoque longo é consequência da VSO caindo no alto padrão.')
slides.append(sl(PO, "Operacional: estoque, meses de venda e banco de terrenos.", body, nota="Fontes: planilha de dados operacionais do RI (Estoque, Estoque Pronto, Terrenos, Vendas; VGV 100% e %CBR; pro forma ex-Cury e P&amp;P de 2019 em diante), planilha de lançamentos do RI; meses de venda pelo RI = estoque ÷ vendas do trimestre × 3."))
# --- ROE ajustado pelo estoque pronto: se o pronto passa de 15% do estoque, o excesso (a custo) sai do PL; lucro não muda
DPJ = J("_dupont.json")["dados"]
def _qk(q): return "20" + q[2:] + "-" + {"1": "03", "2": "06", "3": "09", "4": "12"}[q[0]]
def _exc(q):
    es_, pr_ = OP["estoque"]["vgv100_total"].get(q), OP["pronto"]["vgv100_total"].get(q); c_ = mrow(206).get(q)
    if not es_ or pr_ is None or c_ is None: return None
    s_ = pr_ / es_; return c_ * (s_ - 0.15) / s_ if s_ > 0.15 else 0.0
qs_pr = []; roe_r = []; roe_a = []; exc_b = []; exc_pl = []
for q in QS:
    if ord_(q) < (13, 4): continue
    d = DPJ.get(_qk(q)); i = QS.index(q); e, e4 = _exc(q), _exc(QS[i - 4])
    if not d or e is None or e4 is None: continue
    pl_adj = d["pl_med"] - (e + e4) / 2
    qs_pr.append(q); roe_r.append(d["roe"]); roe_a.append(100 * d["ll_ltm"] / pl_adj); exc_b.append(e / 1000); exc_pl.append(100 * e / mrow(199)[q])
c = Chart(60, 440, 46, 178, -5, 40, len(qs_pr)); c.grid([-5, 0, 10, 20, 30, 40], lambda t: f"{t:g}%"); c.xlabels(qs_pr, 8, 1, lambda l: "20" + l[2:])
c.line(roe_a, S3, lab="PL ex-pronto", labval=lambda v: fmt(v, 1) + "%", w=2.8); c.line(roe_r, S1, lab="reportado", labval=lambda v: fmt(v, 1) + "%", w=2.4)
c.g.append('<text x="60" y="18" class="gtit">ROE reportado × ROE com o PL sem o pronto excedente</text><text x="60" y="34" class="gsub">LTM; excedente = pronto a custo × (share − 15%) ÷ share, quando o pronto passa de 15%; lucro inalterado</text>')
c2 = Chart(600, 900, 46, 178, 0, 25, len(qs_pr)); c2.grid([0, 5, 10, 15, 20, 25], lambda t: f"{t:g}%"); c2.xlabels(qs_pr, 8, 1, lambda l: "20" + l[2:])
c2.line(exc_pl, S2, lab="% do PL", labval=lambda v: fmt(v, 0) + "%", w=2.6)
c2.g.append('<text x="600" y="18" class="gtit">Excedente de pronto a custo, % do PL</text><text x="600" y="34" class="gsub">pico de R$ ' + fmt(max(exc_b), 1) + ' bi em ' + qs_pr[exc_b.index(max(exc_b))] + '</text>')
body = svg(980, 200, c.flush(15) + c2.flush(15))
_ipk = exc_b.index(max(exc_b)); _dmax = max(a - r for a, r in zip(roe_a, roe_r)); _iq = [a - r for a, r in zip(roe_a, roe_r)].index(_dmax)
_dx = [(a - r, q) for a, r, q in zip(roe_a, roe_r, qs_pr) if not ((20, 3) <= ord_(q) <= (21, 2))]; _dmax2, _q2 = max(_dx)   # janelas LTM com os IPOs de Cury e Lavvi (3T20-2T21) fora
body += ('<div class="cards3" style="margin-top:8px">'
         f'<div class="c3"><span class="c3n">a conta</span><b>Se o estoque pronto fosse sempre ~15% do estoque</b>, o que passa disso não deveria estar no book: sai do PL o pronto a custo na proporção do excesso (share de 30% = metade do pronto), o lucro fica como está, e o ROE é recalculado sobre o PL menor.</div>'
         f'<div class="c3"><span class="c3n">R$ {fmt(max(exc_b), 1)} bi · +{fmt(_dmax2, 1)} p.p.</span><b>No pico (' + qs_pr[_ipk] + f'), o excedente valia R$ {fmt(max(exc_b), 1)} bi, {fmt(exc_pl[_ipk], 0)}% do PL</b>; o ajuste move o ROE em no máximo {fmt(_dmax2, 1)} p.p. ({_q2}). Os +{fmt(_dmax, 1)} p.p. do {qs_pr[_iq]} vêm de um ROE inflado pelos IPOs da Cury e da Lavvi (janelas 3T20-2T21 fora). O problema de 2016-19 foi lucro, não book.</div>'
         f'<div class="c3"><span class="c3n">{fmt(roe_a[-1], 1)}% = {fmt(roe_r[-1], 1)}%</span><b>Hoje o ajuste é zero</b>: pronto em {fmt(100 * OP["pronto"]["vgv100_total"]["2T26"] / OP["estoque"]["vgv100_total"]["2T26"], 0)}% do estoque, abaixo da régua de 15%. O ROE de {fmt(roe_r[-1], 1)}% não carrega estoque encalhado; carrega estoque em obra (35% do PL) e recebível (58%).</div></div>')
body += output('Pronto acima de 15% fora do book: o ROE muda +' + fmt(_dmax2, 1) + ' p.p. no pior ano normal; hoje, zero.', 'O estoque pronto é pequeno em relação ao PL; o que pesa no balanço da Cyrela é obra e recebível, não unidade encalhada.')
slides.append(sl(P4, "ROE ajustado pelo estoque pronto: o excesso pesa pouco no book.", body, nota="Fontes: _dupont.json (lucro atribuível LTM e PL médio dos controladores, planilha de DFs do RI); CYREMod linha 206 (imóveis prontos a custo, notas de estoque dos ITR); planilha operacional do RI (VGV do estoque total e pronto, 100%, desde 4T12). Régua de 15% = premissa da apresentação; excedente médio de dois fechamentos, como o PL."))

# --- lucro LTM × geração de caixa 12m × dívida líquida × alavancagem × payout 12m (pedido de 18/09/26)
GC = J("_ger_caixa_hist.json")["tri"]; BCV = J("_balanco_cvm.json"); DIVS = J("_cotacao_cyre3.json")["divs"]; ACV = J("_cvm_acoes.json")
_SHY = {2011: 410668, 2012: 412106, 2013: 407260, 2014: 395417, 2015: 379000, 2016: 384400, 2017: 384400, 2018: 384400, 2019: 384400}   # ações ex-tesouraria (mil): DFs 2011-14, CYREMod 2015-19
def _shares_mi(d):   # milhões de ações na data ex
    y = int(d[:4]); q = f"{(int(d[5:7]) - 1) // 3 + 1}T{d[2:4]}"
    return ACV.get(q) or (_SHY.get(y, 384400) / 1000)
def _qof(d): return f"{(int(d[5:7]) - 1) // 3 + 1}T{d[2:4]}"
DIV_Q = {}
for d, v, _k in DIVS: DIV_Q[_qof(d)] = DIV_Q.get(_qof(d), 0) + v * _shares_mi(d)   # R$ mi por trimestre (data ex)
def _sum4(dct, q, need_all=True):
    i = QS.index(q); ks = QS[i - 3:i + 1]
    if need_all and any(dct.get(x) is None for x in ks): return None
    return sum(dct.get(x) or 0 for x in ks)
qs_f = [q for q in QS if (12, 4) <= ord_(q) <= ord_("2T26")]
ll12 = [_sum4(mrow(73), q) / 1000 for q in qs_f]; gc12 = [(_sum4(GC, q) / 1000) if _sum4(GC, q) is not None else None for q in qs_f]
def _nd(q):
    b = BCV.get(q)
    if not b or b.get("emp_cp") is None: return None
    return sum(b.get(k) or 0 for k in ("emp_cp", "deb_cp", "cri_cp", "emp_lp", "deb_lp", "cri_lp")) - sum(b.get(k) or 0 for k in ("caixa", "aplic_cp_vjr", "aplic_cp_vjora", "aplic_cp_ca", "aplic_lp_vjr", "aplic_lp_vjora", "aplic_lp_ca"))
nd_bi = [_nd(q) / 1000 if _nd(q) is not None else None for q in qs_f]; nd_pl = [100 * _nd(q) / mrow(199)[q] if _nd(q) is not None and mrow(199).get(q) else None for q in qs_f]
pay12 = [100 * _sum4(DIV_Q, q, False) / (_sum4(mrow(73), q)) if _sum4(mrow(73), q) and _sum4(mrow(73), q) > 0 else None for q in qs_f]
# layout (18/09/26): painéis de 75px; A/C terminam em x=400 e B/D começam em 560 para os rótulos de fim de linha
# ("dív. líq. ÷ PL 10%", ~95 un.) não invadirem o eixo do painel vizinho; B/D terminam em 850 para "payout 12m 49%" caber em 980
cA = Chart(60, 400, 48, 123, -1, 3, len(qs_f)); cA.grid([-1, 0, 1, 2, 3]); cA.xlabels(qs_f, 8, 0, lambda l: "20" + l[2:])
dv12 = [_sum4(DIV_Q, q, False) / 1000 for q in qs_f]   # proventos com data ex nos 4 trimestres (R$ bi)
cA.line(dv12, S3, lab="proventos 12m", labval=lambda v: fmt(v, 2), w=2.2, dash="4 3"); cA.line(gc12, S2, lab="caixa 12m", labval=lambda v: fmt(v, 2), w=2.4); cA.line(ll12, S1, lab="lucro LTM", labval=lambda v: fmt(v, 2), w=2.8)
cA.g.append('<text x="60" y="18" class="gtit">Lucro LTM, caixa 12m e proventos 12m (R$ bi)</text><text x="60" y="34" class="gsub">DRE (CYREMod); releases (geração de caixa, linha operacional); B3 (proventos por data ex)</text>')
cB = Chart(560, 850, 48, 123, -1, 3, len(qs_f)); cB.grid([-1, 0, 1, 2, 3]); cB.xlabels(qs_f, 8, 0, lambda l: "20" + l[2:])
cB.line(nd_bi, S1, lab="dív. líquida", labval=lambda v: fmt(v, 2), w=2.8)
cB.g.append('<text x="560" y="18" class="gtit">Dívida líquida (R$ bi)</text><text x="560" y="34" class="gsub">balanço CVM: empréstimos, debêntures e CRI (inclui CashMe) − caixa e aplicações</text>')
cC = Chart(60, 400, 188, 263, -20, 80, len(qs_f)); cC.grid([-20, 0, 20, 40, 60, 80], lambda t: f"{t:g}%"); cC.xlabels(qs_f, 8, 0, lambda l: "20" + l[2:])
cC.line(nd_pl, S1, lab="dív. líq. ÷ PL", labval=lambda v: fmt(v, 0) + "%", w=2.8)
cC.g.append('<text x="60" y="160" class="gtit">Alavancagem: dívida líquida ÷ PL dos controladores</text><text x="60" y="176" class="gsub">negativo = caixa líquido</text>')
# payout: eixo 0-200% (2017-21 tem 106-200%) e a linha recortada ao painel — o pico de 1T19 (lucro LTM ≈ 0) sai pelo topo em vez de atravessar o painel B e os títulos
cD = Chart(560, 850, 188, 263, 0, 200, len(qs_f)); cD.grid([0, 50, 100, 150, 200], lambda t: f"{t:g}%"); cD.xlabels(qs_f, 8, 0, lambda l: "20" + l[2:])
_nD = len(cD.g); cD.line(pay12, S3, lab="payout 12m", labval=lambda v: fmt(v, 0) + "%", w=2.8)
cD.g[_nD:] = ['<clipPath id="clip-payout"><rect x="556" y="185" width="300" height="82"/></clipPath><g clip-path="url(#clip-payout)">' + "".join(cD.g[_nD:]) + '</g>']
cD.g.append('<text x="560" y="160" class="gtit">Payout 12m: proventos declarados ÷ lucro LTM</text><text x="560" y="176" class="gsub">proventos B3 (data ex) × ações ex-tesouraria; sem recompra; lucro ≤ 0 omitido</text>')
body = svg(980, 284, cA.flush(15) + cB.flush(15) + cC.flush(15) + cD.flush(15))
_gcL = gc12[-1]; _llL = ll12[-1]; _ndL = nd_bi[-1]; _plL = nd_pl[-1]; _payL = pay12[-1]
_ipk = max(range(len(nd_pl)), key=lambda i: nd_pl[i] if nd_pl[i] is not None else -1e9)
body += ('<div class="cards3 tight" style="margin-top:8px">'
         f'<div class="c3"><span class="c3n">R$ {fmt(_llL, 2)} bi · R$ {fmt(_gcL, 2)} bi</span><b>Lucro LTM e caixa gerado em 12 meses</b>: o caixa é {fmt(100 * _gcL / _llL, 0)}% do lucro. A diferença é estoque em obra e recebível crescendo (slide anterior). Em 2016-19 foi o contrário: lucro perto de zero e caixa positivo, capital de giro devolvido.</div>'
         f'<div class="c3"><span class="c3n">R$ {fmt(_ndL, 2)} bi · {fmt(_plL, 0)}% do PL</span><b>Dívida líquida e alavancagem</b>, contra {fmt(nd_pl[_ipk], 0)}% no pico ({qs_f[_ipk]}). O balanço está leve porque o terreno virou prazo e permuta: os R$ 3,2 bi de terrenos a pagar ficam fora dessa conta e levariam a alavancagem de {fmt(_plL, 0)}% para ~{fmt(100 * (_ndL + 3.2) / (mrow(199)["2T26"] / 1000), 0)}% do PL.</div>'   # 22/09/26: (dívida líquida + 3,2 bi) ÷ PL dos controladores, números do próprio slide
         f'<div class="c3"><span class="c3n">{fmt(_payL, 0)}%</span><b>Payout dos últimos 12 meses</b> (proventos declarados ÷ lucro LTM), sem contar recompra. Com caixa gerado de R$ {fmt(_gcL, 2)} bi e proventos de R$ {fmt(_sum4(DIV_Q, qs_f[-1], False) / 1000, 2)} bi no período, o dividendo saiu de dívida ou de venda de ativo, não de geração operacional.</div></div>')
_i22 = qs_f.index('4T22'); _plg = 100 * (mrow(199)['2T26'] / mrow(199)['4T22'] - 1)
body += _obox18('Lucro 12m de R$ ' + fmt(ll12[_i22], 1) + ' bi (2022) para ' + fmt(_llL, 1) + ' bi com PL +' + fmt(_plg, 0) + '% e dívida líquida em ' + fmt(_plL, 0) + '% do PL (ex-terrenos a pagar), sem emissão.', 'O balanço não inchou: o MCMV gira com pouco capital (a CEF financia a obra sobre o vendido) e o terreno entra a prazo e em permuta. O dividendo de R$ ' + fmt(_sum4(DIV_Q, qs_f[-1], False) / 1000, 1) + ' bi saiu dessa folga, não do caixa operacional de R$ ' + fmt(_gcL, 1) + ' bi.')   # 22/09/26: mensagem no formato do autor (decisão editorial); caixa a 18px, tag alinhada à 1ª linha
slides.append(sl(P4, "Lucro, caixa, dívida e payout: a foto de 12 meses.", body, nota="Fontes: CYREMod (lucro líquido reportado trimestral; PL dos controladores); releases (Geração/Consumo de Caixa: 2011-19 pela prosa, 2020-2T26 pela tabela, linha operacional; _ger_caixa_hist.json); balanço CVM (dívida bruta e caixa); B3 (proventos por ação e datas ex), ações ex-tesouraria da CVM/DFs. Payout = proventos com data ex nos 4 trimestres ÷ lucro dos 4 trimestres. A carteira da CashMe (slide 8) também fica fora da dívida líquida."))

# --- o preço: P/B em vinte anos e a ação contra o CDI (slide 53 do deck completo)
COT = J("_cotacao_cyre3.json"); PLC = J("_pl_controladora.json")   # PL controladora, R$ mil, por mês de fechamento de trimestre
# ações ex-tesouraria no fim de cada ano (mil): DF 2007 (2005-07), DF 2008, DFP 2010 (2009-10), DFP 2012 (2011-12), DFP 2014 (2013-14); de 2015 em diante, CYREMod linha 99 (ON + PN especiais)
SH_Y = {2005: 148712, 2006: 354465, 2007: 355647, 2008: 355724, 2009: 422387, 2010: 422998, 2011: 410668, 2012: 412106, 2013: 407260, 2014: 395417}
def _split_f(m):   # ações de hoje por ação da época (desdobramento 2:1 em dez/06; bonificação de 0,19 PN em jan/26)
    f = 1.0
    for ex, k in COT["splits"]:
        if m < ex[:7]: f *= k
    return f
def _sh(m):
    y = int(m[:4]); q = f"{(int(m[5:7]) - 1) // 3 + 1}T{m[2:4]}"
    v = mrow(99).get(q)
    if v: return v * 1000
    yy = y if m.endswith("-12") else y - 1   # ações do fim do ano anterior até o 4T (o fim de 2006 já é pós-desdobramento)
    return SH_Y.get(yy) or SH_Y[max([k for k in SH_Y if k < yy] or [min(SH_Y)])]
_pxm = {x["m"]: x["px"] for x in COT["mensal"]}
ms_pb = [m for m in sorted(PLC) if m in _pxm]
pb = [_pxm[m] * _sh(m) * _split_f(m) / PLC[m] for m in ms_pb]
_PBMAX = 5   # eixo 0-5x: cabe o prêmio de 2007-09 (3,4-4,5x); 2006 (>6x) sai pelo topo, recortado pelo clipPath
cpb = Chart(60, 590, 46, 178, 0, _PBMAX, len(ms_pb)); cpb.grid([0, 1, 2, 3, 4, 5], lambda t: f"{t:g}" + "x"); cpb.xlabels(ms_pb, 12, 1, lambda l: l[:4])   # off=1: "2005" em dez/05, sem encostar no "0x"
_med = sorted(pb)[len(pb) // 2]; _med10 = sorted(v for m, v in zip(ms_pb, pb) if m >= "2010-01")[len([1 for m in ms_pb if m >= "2010-01"]) // 2]
cpb.g.append(f'<line x1="60" y1="{cpb.y(_med10):.1f}" x2="590" y2="{cpb.y(_med10):.1f}" stroke="{MU}" stroke-dasharray="4 3" opacity=".8"/><text x="394" y="{cpb.y(_med10) - 5:.1f}" class="fw-s2" fill="{MU}" text-anchor="end">mediana 2010-26: {fmt(_med10, 2)}x</text>')   # sobre o trecho 2014-18 (linha toda abaixo de 1,03x); à esquerda a linha de 2008-10 cruzava o texto, à direita 2021-26 oscila em torno da mediana
cpb.line(pb, S1, lab="P/B", labval=lambda v: fmt(v, 2) + "x", w=2.8)
_imax = pb.index(max(pb)); _imin = pb.index(min(pb))
if pb[_imax] > _PBMAX:   # pico fora da escala: rótulo no alto da área do gráfico, à direita do ponto onde a linha volta a entrar
    _pk = f'<text x="{cpb.x(_imax) + 22:.1f}" y="{cpb.y0 + 8:.1f}" class="fw-s2" fill="var(--ink-2)">pico: {fmt(pb[_imax], 1)}x · {ms_pb[_imax][:7]} (fora da escala)</text>'
else:
    _pk = f'<text x="{cpb.x(_imax) + 6:.1f}" y="{cpb.y(pb[_imax]) + 4:.1f}" class="fw-s2" fill="var(--ink-2)">{fmt(pb[_imax], 1)}x · {ms_pb[_imax][:7]}</text>'
cpb.g.append(_pk + f'<text x="{cpb.x(_imin):.1f}" y="{cpb.y(pb[_imin]) + 13:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="middle">{fmt(pb[_imin], 2)}x · {ms_pb[_imin][:7]}</text>')
cpb.g.append('<text x="60" y="18" class="gtit">P/B da Cyrela em vinte anos</text><text x="60" y="34" class="gsub">preço de fechamento do trimestre × ações ex-tesouraria (ON + PN especiais desde 2026) ÷ PL dos controladores; B3, DFs</text>')
_pbsvg = '<clipPath id="pbclip"><rect x="60" y="38" width="530" height="144"/></clipPath>' + re.sub(r'<polyline ', '<polyline clip-path="url(#pbclip)" ', cpb.flush(15))
_viz53 = re.search(r'<div class="viz"[^>]*><svg viewBox="0 0 900 259">.*?</svg></div>', SECS[52], re.S).group(0)
# gráfico reaproveitado: os rótulos de fim de linha ficavam sobre a cauda das linhas (anchor end em x=826, linhas até 830);
# passam para a direita das linhas, encurtados, e o viewBox alarga 30 unidades; os quatro traços-guia (830 -> 763) saem
_viz53 = re.sub(r'<line x1="830\.0" y1="[\d.]+" x2="763" y2="[\d.]+" stroke="[^"]+" stroke-width="1" opacity="[^"]+"/>', '', _viz53)
for _a, _b in (("CDI · 8,0×", "CDI · 8,0×"), ("CYRE3 total · 7,5×", "CYRE3 · 7,5×"), ("Ibovespa · 5,9×", "Ibov. · 5,9×"), ("só preço · 3,3×", "só preço · 3,3×")):
    _viz53 = re.sub(r'<text x="826(?:\.0)?" y="([\d.]+)" class="fw-t2" fill="([^"]+)" text-anchor="end">' + re.escape(_a) + '</text>',
                    lambda m, _b=_b: f'<text x="836" y="{m.group(1)}" class="fw-t2" fill="{m.group(2)}">{_b}</text>', _viz53)
_viz53 = _viz53.replace('<svg viewBox="0 0 900 259">', '<svg viewBox="0 0 930 259">', 1)
body = '<div class="fwgrid" style="grid-template-columns:1fr 1.1fr;align-items:start">' + svg(660, 200, _pbsvg) + re.sub(r' style="[^"]*"', '', _viz53, count=1) + '</div>'
ST = COT["stats"]
body += ('<div class="cards3" style="margin-top:8px">'
         f'<div class="c3"><span class="c3n">{fmt(pb[-1], 2)}x</span><b>P/B no fim de junho</b> (1,0x a R$ 25,68, 17/09), contra {fmt(pb[0], 1)}x na oferta de 2005, {fmt(min(pb), 2)}x no fundo ({ms_pb[_imin][:7]}) e mediana de {fmt(_med10, 2)}x desde 2010. Com Ke de ~17% (premissa da apresentação) e g de 4%, ROE ajustado de 16,7% vale 0,98x book: o preço está justo, e ex-Cury (0,89x, ROE 15,4%) o mercado já desconta a máquina própria.</div>'
         f'<div class="c3"><span class="c3n">{fmt(ST["total_x"], 1)}x · {fmt(ST["cdi_x"], 1)}x</span><b>Ação contra CDI em 21 anos</b>: retorno total de {fmt(ST["total_x"], 1)}x ({fmt(ST["total_cagr"], 1)}% a.a.) contra {fmt(ST["cdi_x"], 1)}x do CDI ({fmt(ST["cdi_cagr"], 1)}% a.a.) e {fmt(ST["ibov_x"], 1)}x do Ibovespa; só preço {fmt(ST["so_preco_x"], 1)}x ({fmt(ST["so_preco_cagr"], 1)}% a.a.). Empate com o CDI, com queda de {fmt(abs(ST["max_dd"]), 0)}% no meio (2007-08).</div>'
         '<div class="c3"><span class="c3n">2016-26</span><b>O retorno veio do rerating e do book, meio a meio</b>: P/B 2,08x (+7,1% a.a.), book por ação 1,95x (+6,4% a.a.), distribuições 1,69x (+5,0% a.a.). De 2005 a 2026 o P/B caiu 0,38x (−4,5% a.a.) e o book por ação subiu 8,8x: a ação só pagou o CDI porque o múltiplo da oferta era 2,6x.</div></div>')
body += output('A ação empatou com o CDI em 21 anos; a 1,0x book, o que sobe daqui é o book, não o múltiplo.', 'O rerating de 2016-26 (0,48x → 1,0x) já aconteceu; repetir o retorno exige ROE acima do Ke, que o mercado não precifica.')
slides.append(sl("parte 6 · o preço", "O preço: P/B em vinte anos, e a ação contra o CDI.", body, nota="Fontes: B3 (COTAHIST, preços ajustados por desdobramento de 2006 e bonificação de PN de 2026; proventos reinvestidos), BCB SGS 12 (CDI), IPEADATA (Ibovespa); PL dos controladores (planilha do RI / DFs); ações ex-tesouraria: DFs 2007-2014 (fim de ano; mantidas no ano) e CYREMod de 2015 em diante (trimestral). Decomposição 2016-26 = slide do deck completo."))

# --- terreno e capital de giro: terreno a custo × a pagar × permuta; estoque ex-terrenos e contas a receber sobre o PL e sobre os lançamentos 12m
EC = J("_estoque_custo.json"); BCV = J("_balanco_cvm.json")
qs_c = sorted(LC, key=ord_)
qs_t = [q for q in QS if mrow(223).get(q) is not None and mrow(220).get(q) is not None and ord_(q) >= (11, 1)]
t_cst = [mrow(223)[q] / 1000 for q in qs_t]; t_pag = [mrow(220)[q] / 1000 for q in qs_t]; t_perm = [mrow(221).get(q) / 1000 if mrow(221).get(q) else None for q in qs_t]
# dois svgs de 600×200 empilhados (um por linha, cartões à direita): a área do gráfico vai de 60 a 470 nos dois (eixos alinhados) para o rótulo mais largo do segundo ("obra + pronto 35%", ~105 unidades a partir de 477) fechar antes de 600
ct = Chart(60, 470, 46, 178, 0, 4, len(qs_t)); ct.grid([0, 1, 2, 3, 4]); ct.xlabels(qs_t, 8, 3, lambda l: "20" + l[2:])
ct.line(t_cst, S1, lab="a custo", labval=lambda v: fmt(v, 1), w=2.8); ct.line(t_pag, S2, lab="a pagar", labval=lambda v: fmt(v, 1), w=2.4); ct.line(t_perm, S3, lab="permuta", labval=lambda v: fmt(v, 1), dash="4 3")
ct.g.append('<text x="60" y="18" class="gtit">Terreno (R$ bi)</text><text x="60" y="34" class="gsub">a custo; a pagar; adiantamento por permuta</text>')
# estoque a custo sem terrenos = imóveis em construção + prontos (CYREMod 205-206); contas a receber = clientes CP + LP (balanço CVM); lançamentos consolidados 12m (aba Launches - Equiv.)
def _lc12(q):
    i = qs_c.index(q); return sum(LC[x]["vgv_c"]["A"] + LC[x]["vgv_c"]["M"] + LC[x]["vgv_c"]["C"] for x in qs_c[i - 3:i + 1]) if i >= 3 and q in qs_c else None
e_ex = [(mrow(205)[q] + mrow(206)[q]) / 1000 if mrow(205).get(q) is not None and mrow(206).get(q) is not None else None for q in qs_t]
cr_t = [(BCV[q]["cr_cp_clientes"] + BCV[q]["cr_lp_clientes"]) / 1000 if q in BCV and BCV[q].get("cr_cp_clientes") is not None else None for q in qs_t]
l12 = [_lc12(q) / 1000 if _lc12(q) else None for q in qs_t]; plq = [mrow(199)[q] / 1000 for q in qs_t]
def _pct(num, den): return [100 * n / d if n is not None and d else None for n, d in zip(num, den)]
cp = Chart(60, 470, 46, 178, 0, 200, len(qs_t)); cp.grid([0, 50, 100, 150, 200], lambda t: f"{t:g}%"); cp.xlabels(qs_t, 8, 3, lambda l: "20" + l[2:])   # 0-200%: lançamentos 12m chegam a 181% do PL em 2015-16 (a 160% a linha atravessava o título)
cp.line(_pct(l12, plq), "var(--ink-2)", lab="lanç. 12m", labval=lambda v: fmt(v, 0) + "%", dash="3 3"); cp.line(_pct(cr_t, plq), S2, lab="CR", labval=lambda v: fmt(v, 0) + "%", w=2.4); cp.line(_pct(e_ex, plq), S3, lab="obra + pronto", labval=lambda v: fmt(v, 0) + "%", w=2.6); cp.line(_pct(t_cst, plq), S1, lab="terreno", labval=lambda v: fmt(v, 0) + "%", w=2.4)
cp.g.append('<text x="60" y="18" class="gtit">Como % do PL dos controladores</text><text x="60" y="34" class="gsub">lanç. 12m; CR (contas a receber); obra + pronto (estoque a custo sem terreno); terreno</text>')   # subtítulo curto: precisa caber em 560-975 (~415 unidades) sem alargar o viewBox
SVG_T = svg(600, 200, ct.flush(15)).replace('<div class="viz">', '<div class="viz" style="margin-top:4px">', 1); SVG_P = svg(600, 200, cp.flush(15)).replace('<div class="viz">', '<div class="viz" style="margin-top:4px">', 1)
_i15 = qs_t.index("4T15"); _lb_perm = OP["landbank"]["pct_permuta"]["2T26"]
_pE = _pct(e_ex, plq); _pC = _pct(cr_t, plq); _pT = _pct(t_cst, plq); _lE = _pct(e_ex, l12); _lC = _pct(cr_t, l12); _lT = _pct(t_cst, l12)
# cartões em 4 linhas (18/09): texto enxuto com todos os números; variante .tight (12px) só neste slide
body = ('<div class="fwgrid" style="grid-template-columns:1.55fr 1fr;align-items:center">' + SVG_T + '<div class="cards3 tight" style="grid-template-columns:1fr;margin-top:0">'   # margin-top:0 — o .cards3 do deck tem 26px de margem, que aqui só alongava a linha
         f'<div class="c3"><span class="c3n">R$ {fmt(t_cst[-1], 1)} bi · R$ {fmt(t_pag[-1] + t_perm[-1], 1)} bi</span><b>Terreno parado contra obrigações de terreno</b> (R$ {fmt(t_pag[-1], 1)} bi a pagar, R$ {fmt(t_perm[-1], 1)} bi de permuta): o a pagar e a permuta cobrem também terreno que já virou obra, <b>os terrenistas financiam a companhia</b>. Em 2015 o terreno era {fmt(_pT[_i15], 0)}% do PL com {fmt(100 * (1 - t_pag[_i15] / t_cst[_i15]), 0)}% pago; hoje {fmt(_pT[-1], 0)}% e {fmt(100 * (1 - t_pag[-1] / t_cst[-1]), 0)}%. {fmt(100 * _lb_perm, 0)}% do landbank é permuta.</div>'
         '</div></div><div class="fwgrid" style="grid-template-columns:1.55fr 1fr;align-items:center;margin-top:6px">' + SVG_P + '<div class="cards3 tight tight2r" style="grid-template-columns:1fr;gap:4px;margin-top:0">'   # tight2r: os dois cartões somados não passam da altura do gráfico (204px)
         f'<div class="c3"><span class="c3n">{fmt(_pE[-1], 0)}% do PL</span><b>Estoque a custo sem terreno</b>: obra R$ {fmt(mrow(205)["2T26"] / 1000, 1)} bi + pronto R$ {fmt(mrow(206)["2T26"] / 1000, 1)} bi = R$ {fmt(e_ex[-1], 1)} bi, contra {fmt(_pE[_i15], 0)}% do PL em 2015. O capital de giro saiu do terreno e foi para a obra: é o estoque de 15 meses no balanço.</div>'
         f'<div class="c3"><span class="c3n">{fmt(_pC[-1], 0)}% do PL</span><b>Contas a receber</b> de R$ {fmt(cr_t[-1], 1)} bi, contra {fmt(_pC[_i15], 0)}% em 2015; lançamentos consolidados de 12 meses valem {fmt(_pct(l12, plq)[-1], 0)}% do PL. Recebível cresce com a venda na planta e com o performado que o banco não repassa; obra, pronto e recebível somam {fmt(_pE[-1] + _pC[-1], 0)}% do PL.</div>'
         '</div></div>')
body += output('O terreno saiu do caixa (prazo e permuta); o capital de giro foi para a obra e o recebível.', 'Terreno a pagar não entra na dívida líquida; obra, pronto e recebível somam ' + fmt(_pE[-1] + _pC[-1], 0) + '% do PL.')
slides.append(sl(P4, "Terreno a prazo, obra e recebível: onde o PL está aplicado.", body, nota="Fontes: CYREMod (linhas 199, 205-207, 220-221, 223: PL dos controladores, imóveis em construção, prontos e terrenos a custo, terrenos a pagar, adiantamentos por permuta física), das DFs/ITR; balanço CVM (clientes circulante e não circulante); aba 'Launches - Equiv.' (lançamentos consolidados, 12 meses); planilha do RI (landbank em permuta). Permuta física antes de 4T22 = 80% dos adiantamentos de clientes (premissa do modelo)."))

# --- a ação e o juro de 10 anos (slide 54 do deck completo), com o callout virando cartões
_s54 = take(54, "parte 6 · o preço", callout='', repl=[('>juro volta a subir,<', '>juro sobe,<'),   # rótulo de fase encostava em "pandemia" (1px)
        ('<div class="viz"><svg viewBox="0 0 900 292">', '<div class="viz" style="max-width:930px;margin:0 auto"><svg viewBox="0 0 900 292">')],   # svg 900×292 esticado a 1020px dava 331px de altura; a 930px cabe com os cartões e a pílula (≤ 740px)
    append=('<div class="cards3 tight" style="margin-top:8px;grid-template-columns:1fr 1fr">'
    '<div class="c3"><span class="c3n">−0,6 · −10% por +100 bp</span><b>A ação segue o juro de 10 anos</b>: correlação de −0,6 nas variações mensais desde 2016 e ~−10% a cada +100 bp, o dobro do Ibovespa (−10,4% contra −5,1% desde 2010; −13,9% contra −6,4% desde 2016, regressões mensais). Nos ciclos de 2015-23 as duas curvas viraram juntas.</div>'
    '<div class="c3"><span class="c3n">2024-26</span><b>A exceção</b>: o juro de 10 anos voltou ao nível de 2015-16 e a ação, em vez de voltar ao vale, subiu, com lucro recorde, distribuições e rerating de P/B. Se o juro cede para 11-12% (−250 a −350 bp), a sensibilidade histórica dá +25-35%; se não cede, o preço está caro pela régua dos outros ciclos.</div></div>')
    + output('A ação cai ~10% a cada +100 bp no juro de 10 anos, o dobro do Ibovespa; 2024-26 é a exceção.', 'Juro a 11-12% (−250 a −350 bp): a régua histórica dá +25-35%; sem queda, o preço está caro.')[:-6].replace('<div class="sl-output">', '<div class="sl-output" style="row-gap:8px">', 1)
    + '<span class="pill-teoria" style="background:#c5003e;flex:1 1 100%;white-space:normal;line-height:1.3;margin-left:0">o papel tende a outperformar se o macro Brasil ajudar: Ke menor, mas também o operacional do SBPE melhorando e a perspectiva de retomada de vendas e lançamentos</span></div>')
slides.append(_s54)

# ================================================================ PARTE 5 · atualização operacional
P5 = "parte 5 · atualização operacional"
qs_c = sorted(LC, key=ord_)
def c12(seg, q, key="vgv_c"):
    i = qs_c.index(q); return sum(LC[x][key][seg] for x in qs_c[i - 3:i + 1]) / 1000 if i >= 3 else None
qs_c4 = qs_c[3:]
tA = [c12("A", q) for q in qs_c4]; tM = [c12("M", q) for q in qs_c4]; tC = [c12("C", q) for q in qs_c4]; tT = [a + m + cc for a, m, cc in zip(tA, tM, tC)]
# receita por segmento = lucro bruto do segmento ÷ margem bruta do segmento (nota de segmentos, CYREMod 35-42), 12 meses
def _rev(rgp, rmg): return {q: (mrow(rgp).get(q) / mrow(rmg).get(q)) for q in QS if mrow(rgp).get(q) is not None and mrow(rmg).get(q)}
REV = {"alto": _rev(35, 36), "medio": _rev(37, 38), "mcmv": _rev(39, 40), "outros": _rev(41, 42)}
qs_r = [q for q in QS if ord_(q) >= (20, 4) and q in REV["alto"]]
def _r12(k, q):
    i = QS.index(q); v = [REV[k].get(x) for x in QS[i - 3:i + 1]]
    return sum(v) / 1000 if all(x is not None for x in v) else None
rvA = [_r12("alto", q) for q in qs_r]; rvM = [_r12("medio", q) for q in qs_r]; rvC = [_r12("mcmv", q) for q in qs_r]; rvO = [_r12("outros", q) for q in qs_r]
rvT = [sum(x for x in v if x) for v in zip(rvA, rvM, rvC, rvO)]
c = Chart(60, 330, 46, 178, 0, 12, len(qs_r)); c.grid([0, 3, 6, 9, 12]); c.xlabels(qs_r, 4, 0, lambda l: "20" + l[2:])
c.line(rvT, "var(--ink-2)", lab="total", labval=lambda v: fmt(v, 1), dash="3 3"); c.line(rvA, S1, lab="alto", labval=lambda v: fmt(v, 1), w=2.6); c.line(rvM, S2, lab="médio", labval=lambda v: fmt(v, 1)); c.line(rvC, S3, lab="MCMV", labval=lambda v: fmt(v, 1), w=2.6); c.line(rvO, MU, lab="outros", labval=lambda v: fmt(v, 1), dash="3 3")
c.g.append('<text x="60" y="18" class="gtit">Receita por segmento, 12m (R$ bi)</text><text x="60" y="34" class="gsub">nota de segmentos dos ITR (lucro bruto ÷ margem)</text>')
c2 = Chart(440, 640, 46, 178, 0, 16, len(qs_c4)); c2.grid([0, 4, 8, 12, 16]); c2.xlabels(qs_c4, 16, 1, lambda l: "20" + l[2:])
c2.line(tT, "var(--ink-2)", lab="total", labval=lambda v: fmt(v, 1), dash="3 3"); c2.line(tA, S1, lab="alto", labval=lambda v: fmt(v, 1)); c2.line(tM, S2, lab="médio", labval=lambda v: fmt(v, 1)); c2.line(tC, S3, lab="MCMV", labval=lambda v: fmt(v, 1), w=2.8)
c2.g.append('<text x="440" y="18" class="gtit">Lançamentos consolidados, 12m</text><text x="440" y="34" class="gsub">VGV dos projetos consolidados, R$ bi; vira receita</text>')
def _v12t(d, q):
    i = qs_l.index(q); ks = qs_l[i - 3:i + 1]
    return sum((d.get(x) or 0) for x in ks) / 1e6 if i >= 3 else None
qs_v = [q for q in qs_l if ord_(q) >= (7, 1)]
lv_l = [_v12t(LR["vgv_total"], q) for q in qs_v]; lv_v = [_v12t(RI["vendas_seg_100"]["Total"], q) for q in qs_v]
c3 = Chart(740, 880, 46, 178, 0, 20, len(qs_v)); c3.grid([0, 5, 10, 15, 20]); c3.xlabels(qs_v, 32, 3, lambda l: "20" + l[2:])
c3.line(lv_l, S1, lab="lanç.", labval=lambda v: fmt(v, 1), w=2.6); c3.line(lv_v, S2, lab="vendas", labval=lambda v: fmt(v, 1), w=2.4)
c3.g.append('<text x="740" y="18" class="gtit">Lançado × vendido, 12m</text><text x="740" y="34" class="gsub">VGV 100%, R$ bi (RI)</text>')
body = svg(980, 200, c.flush(15) + c2.flush(15) + c3.flush(15))  # 15: bbox do rótulo (12px) tem 14,4 unidades; 14 deixava as caixas encostadas
i26 = qs_c4.index("2T26"); iP = qs_c4.index("4T10"); iL = qs_c4.index("4T16")
body += ('<div class="cards3" style="margin-top:12px;grid-template-columns:1fr 1fr">'
         f'<div class="c3"><span class="c3n">R$ {fmt(rvT[-1],1)} bi</span><b>Receita LTM por segmento</b>: alto padrão R$ {fmt(rvA[-1],1)} bi ({fmt(100*rvA[-1]/rvT[-1],0)}%), médio R$ {fmt(rvM[-1],1)} bi, MCMV R$ {fmt(rvC[-1],1)} bi ({fmt(100*rvC[-1]/rvT[-1],0)}%). A Vivaz é {fmt(100*rvC[-1]/rvT[-1],0)}% da receita, mas {fmt(100*tC[i26]/tT[i26],0)}% do lançado em consolidação: o mix ainda vai migrar por dois anos.</div>'
         f'<div class="c3"><span class="c3n">R$ {fmt(tT[i26],1)} bi</span><b>Lançados em consolidação, 12 meses</b>: {fmt(tT[i26]/tT[iP],1)}× o pico do superciclo (4T10: R$ {fmt(tT[iP],1)} bi) e {fmt(tT[i26]/tT[iL],1)}× o fundo de 2016. Alto padrão R$ {fmt(tA[i26],1)} bi (pico: R$ {fmt(max(tA),1)} bi), médio R$ {fmt(tM[i26],1)} bi, MCMV R$ {fmt(tC[i26],1)} bi. O lançado de 2027-28 já existe; vira receita só depois de vendido e construído.</div></div>')
body += output('O que pode virar receita em 2027-28 já foi lançado, e cada vez mais dentro do perímetro consolidado.', 'Receita segue o lançado consolidado dois anos depois; a Vivaz vai de ' + fmt(100*rvC[-1]/rvT[-1],0) + '% da receita para perto dos ' + fmt(100*tC[i26]/tT[i26],0) + '% que tem no lançado.')
slides.append(sl(P5, "Receita por segmento, e o que vai virar receita.", body, nota="Fontes: CYREMod linhas 35-42 (nota de segmentos dos ITR/DFP, 1T20-2T26; receita = lucro bruto ÷ margem do segmento); aba 'Launches - Equiv.' (consolidação a partir da lista de empreendimentos do RI, _lancamentos_consol.json); planilha operacional do RI (VGV 100% e %CBR de lançamentos e vendas); 12 meses móveis."))

# --- praças e canteiros
anos_p = [str(a) for a in range(2005, 2026)] + ["LTM"]
import openpyxl as _ox
_ws = _ox.load_workbook(os.path.join(here, "fontes", "planilha_lancamentos.xlsx"), read_only=True).worksheets[0]
_nltm = sum(1 for r_ in _ws.iter_rows(min_row=4, max_row=_ws.max_row, min_col=5, max_col=7, values_only=True) if r_[0] in LTMQ and r_[2])
nproj = [PR[a]["n"] for a in anos_p[:-1]] + [_nltm]; OPP = [1] * (len(anos_p) - 1) + [.45]
qs_k = [q for q in sorted(LR["cant_total"], key=ord_) if LR["cant_total"].get(q)]
cant_t = [LR["cant_total"][q] for q in qs_k]; upc = [s12("un_total", q) / LR["cant_total"][q] if q in qs_l and s12("un_total", q) else None for q in qs_k]
c = Chart(60, 420, 46, 178, 0, 120, len(anos_p)); c.grid([0, 40, 80, 120]); c.xlabels(anos_p, 3)
c.bars(nproj, S2, labels=[str(v) if a in ("2010", "2016", "2025", "LTM") else "" for v, a in zip(nproj, anos_p)], opac=OPP)
c.g.append('<text x="60" y="18" class="gtit">Projetos lançados por ano</text><text x="60" y="34" class="gsub">LTM = 3T25-2T26, em tom claro</text>')
c2 = Chart(520, 860, 46, 178, 0, 250, len(qs_k)); c2.grid([0, 50, 100, 150, 200, 250]); c2.xlabels(qs_k, 8, 0)
c2.line(cant_t, S1, lab="canteiros", labval=lambda v: fmt(v, 0)); c2.line(upc, S3, lab="un/canteiro", labval=lambda v: fmt(v, 0))
c2.g.append('<text x="520" y="18" class="gtit">Canteiros e unidades lançadas (12m) por canteiro</text><text x="520" y="34" class="gsub">planilha operacional do RI (Canteiros)</text>')
body = svg(980, 200, c.flush() + c2.flush())
body += ('<div class="fwgrid" style="margin-top:10px"><div class="fwcard map"><header>praças: hoje × crise</header><dl>'
         f'<dt>2010 · auge</dt><dd>{PR["2010"]["n_locais"]} regiões, {PR["2010"]["n"]} projetos, R$ {fmt(PR["2010"]["vgv"]/1000,1)} bi — equipe, terreno e sócio em cada praça.</dd>'
         f'<dt>2016 · fundo</dt><dd>{PR["2016"]["n_locais"]} praças, {PR["2016"]["n"]} projetos, R$ {fmt(PR["2016"]["vgv"]/1000,1)} bi.</dd>'
         f'<dt>2025 · recorde</dt><dd>{PR["2025"]["n_locais"]} praças, {PR["2025"]["n"]} projetos, R$ {fmt(PR["2025"]["vgv"]/1000,1)} bi — <b>2,4× o VGV de 2010 com metade das praças</b>. O crescimento é de tíquete e de tamanho de projeto, não de geografia.</dd></dl></div>'
         '<div class="fwcard mcmv"><header>complexidade operacional: caiu, e foi para o sócio</header><dl>'
         f'<dt>canteiros</dt><dd>{int(cant_t[0])} ({qs_k[0]}) → {int(cant_t[-1])} ({qs_k[-1]}): menos obras simultâneas com {fmt(upc[-1],0)} unidades por canteiro (eram {fmt([u for u in upc if u][0],0)}). Torres grandes de Vivaz no lugar de muitos prédios médios.</dd>'
         '<dt>quem toca a obra</dt><dd>73% dos canteiros em JV e 14% com terceiros (classificação do RI; a série muda de critério no 4T20, quando a linha CBR cai de 45 para 1). Incorporadora, não construtora — bom para o capital, ruim para a vantagem de execução.</dd>'
         '<dt>leitura</dt><dd>O risco migrou de execução para <b>concentração</b> (SP capital, MCMV, CEF).</dd></dl></div></div>')
body += output('Menos complexidade operacional, mais concentração.')
slides.append(sl(P5, "Menos praças, menos canteiros, projetos maiores: a complexidade caiu.", body, nota="Fontes: lista de empreendimentos do RI (praças = locais distintos com lançamento no ano; nº de projetos); planilha operacional do RI (canteiros por segmento e por gestão de obra)."))
# --- caixa do MAP × MCMV (teoria) + retorno por segmento e o take-away de mix (pedido de 18/09/26)
RSG = J("_roe_seg_serie.json"); _rs_last = {k: v[sorted(v, key=ord_)[-1]] for k, v in RSG.items()}
_mix10 = 0.10 * (_rs_last["mcmv"] - _rs_last["cyrela"])
# 22/09/26: pesos reais da tabela de mix. w hoje = 11% do PL atribuído (nota de segmentos 2T26: alto padrão 65,6%, Living 22,3%, Vivaz 11,2%), cenário = 33% (o triplo);
# retornos LTM 2T26 do slide 49 (_roe_seg_serie: Vivaz 39,9%, alto padrão 23,4%); "médio e alto padrão" da fórmula fica no retorno do alto padrão, como o slide já fazia (23%)
_rvz, _rmap = _rs_last["mcmv"], _rs_last["cyrela"]; _W_HOJE, _W_CEN = 0.11, 0.33
_WLAB = {_W_HOJE: " (hoje, nota de segmentos 2T26)", _W_CEN: " (cenário: o triplo)", 0.5: ""}
_mix_hi = (_W_CEN - _W_HOJE) * (_rvz - _rmap); _mix_lo = (_W_CEN - _W_HOJE) * (30 - _rmap)     # +3,6 p.p. (Vivaz a 39,9%) e +1,5 p.p. (Vivaz a 30%)
_z18 = _W_CEN * _rvz + (1 - _W_CEN) * 3.6; _z18_lo = _W_CEN * 30 + (1 - _W_CEN) * 3.6            # 15,6% e 12,3%
_s8 = take(8, P5, teoria=True)
# título a 38px (duas linhas, 81px; em uma linha só caberia a 30px): o slide tem duas curvas, premissas, retorno por segmento, tabela e caixa verde
_s8 = re.sub(r'<h2 class="head-xl">(.*?)<br>(.*?)</h2>', r'<h2 class="head-xl" style="font-size:38px">\1 \2</h2>', _s8, count=1, flags=re.S)
# as duas curvas de caixa lado a lado (svgs de 900×252 herdados do deck completo; o tamanho é dado pelo contêiner)
_vz8b = re.findall(r'<div class="viz"[^>]*><svg viewBox="0 0 900 252">.*?</svg></div>', _s8, re.S)
_s8 = _s8.replace(_vz8b[0], '<div class="fwgrid" style="max-width:890px;margin:2px auto 0;gap:10px">' + re.sub(r' style="[^"]*"', ' style="margin-top:4px"', _vz8b[0], count=1), 1).replace(_vz8b[1], re.sub(r' style="[^"]*"', ' style="margin-top:4px"', _vz8b[1], count=1) + '</div>', 1)   # ~440px por curva
# premissas: os dois cartões (MAP e MCMV) viram um parágrafo compacto cada (3 linhas), com os mesmos números do deck completo
_s8 = re.sub(r'<div class="fwgrid" style="margin-top:16px">\s*<div class="fwcard map">.*?</div>\s*</div>\s*(?=</div>)',
    '<div class="fwgrid compact" style="margin-top:6px;gap:10px"><div class="fwcard map"><header>Premissas · médio e alto padrão</header>'
    '<p>Terreno <b>18% do VGV</b> · margem bruta <b>~33%</b> · VSO <b>33-45% na largada</b>, ~8%/tri depois, liquida nas chaves (na prática 88% vendido em 6-12 meses; o repasse só chega nas chaves) · <b>30% na obra · 70% no repasse</b> (chaves) · tracejada: terreno <b>100% em permuta</b>.</p></div>'
    '<div class="fwcard mcmv"><header>Premissas · MCMV (Vivaz)</header>'
    '<p>Terreno <b>10% do VGV</b> · margem bruta <b>~32%</b> (abaixo dos 36% LTM 2T26, por conservadorismo) · VSO <b>~25% na largada</b>, ~30%/tri, esgota no mês 30 · <b>90% na obra</b> (CEF, medição sobre o vendido) · <b>10% na entrega</b> · tracejada: terreno <b>100% em permuta</b>.</p></div></div>', _s8, count=1, flags=re.S)
_viz41 = re.search(r'<div class="viz"[^>]*><svg viewBox="0 0 900 277">.*?</svg></div>', SECS[40], re.S).group(0)
_s8_add = ('<div class="fwgrid" style="grid-template-columns:1.15fr 1fr;margin-top:6px;gap:10px;align-items:start">' + re.sub(r' style="[^"]*"', ' style="margin-top:0"', _viz41, count=1)
    + f'<div class="c3 tight2"><span class="c3n">{fmt(_rs_last["mcmv"], 0)}% · {fmt(_rs_last["living"], 0)}% · {fmt(_rs_last["cyrela"], 0)}%</span><b>Retorno operacional sobre o capital, LTM</b> (MCMV, Living, alto padrão: lucro operacional ÷ PL médio do segmento, nota do ITR; antes de juros e IR, não é ROE). Alto padrão fez a travessia do ciclo: 20% em 2014, 3,6% em 2018, 23% hoje. MCMV de 17% para 40% em cinco trimestres, com base de capital pequena. <b>Cada 10 p.p. de mix</b> que migra do alto padrão para a Vivaz, a retorno constante, valem <b>+{fmt(_mix10, 1)} p.p.</b> no retorno consolidado.</div></div>'
    + '<div class="viz" style="margin-top:6px"><table class="tl" style="width:100%;font-size:10px;line-height:1.1;border:2px solid var(--s2);border-collapse:collapse;text-align:center"><thead>'
       f'<tr style="background:var(--s2);color:#fff"><th rowspan="2" style="text-align:left;padding:2px 6px;vertical-align:middle;width:27%">retorno consolidado = w × Vivaz + (1 − w) × médio e alto padrão</th><th colspan="4" style="padding:2px 6px;border-left:1px solid rgba(255,255,255,.5)">Vivaz a {fmt(_rvz, 1)}% (hoje, LTM 2T26)</th><th colspan="4" style="padding:2px 6px;border-left:1px solid rgba(255,255,255,.5)">Vivaz a 30% (margem cai a 30%)</th></tr>'
       '<tr style="background:var(--s2);color:#fff">' + ''.join(f'<th style="padding:2px 4px{";border-left:1px solid rgba(255,255,255,.5)" if k == 0 else ""}">MAP {lab}</th>' for _ in (0, 1) for k, lab in enumerate((f"{fmt(_rmap, 1)}% (hoje)", "15% (2015-16)", "8% (2019)", "3,6% (fundo 2018)"))) + '</tr></thead><tbody>'
       + ''.join('<tr' + (' style="background:rgba(70,110,170,.12);font-weight:600"' if w == _W_CEN else '') + f'><td style="text-align:left;padding:2px 6px">Vivaz com {fmt(100 * w, 0)}% do capital{_WLAB[w]}</td>' + ''.join(f'<td style="padding:2px 5px{";border-left:1px solid var(--s2)" if k == 0 else ""}">{fmt(w * rv + (1 - w) * rm, 1)}%</td>' for rv in (_rvz, 30) for k, rm in enumerate((_rmap, 15, 8, 3.6))) + '</tr>' for w in (_W_HOJE, _W_CEN, 0.5))
       + f'</tbody></table><p class="sl-nota" style="margin:2px 2px 0;color:var(--s2)">Cenários: retorno operacional (antes de juros e IR); w = parcela do PL atribuído à Vivaz (11% no 2T26, nota de segmentos); MAP = alto padrão nos níveis que o próprio ciclo já mostrou. De 11% para 33% a MAP constante: +{fmt(_mix_hi, 1)} p.p. com a Vivaz a {fmt(_rvz, 1)}%, +{fmt(_mix_lo, 1)} p.p. a 30%. Com um terço na Vivaz e o MAP no fundo de 2018, o consolidado cai a {fmt(_z18, 1)}% ({fmt(_z18_lo, 1)}% se a Vivaz cair a 30%): o mix segura, mas não repõe um ciclo ruim.</p></div>'
    + _obox18(f'Mix ajuda, ciclo manda: Vivaz de 11% para 33% do capital vale +{fmt(_mix_lo, 1)} a {fmt(_mix_hi, 1)} p.p.; MAP no fundo de 2018 derruba o retorno a ~{fmt(_z18, 0)}%.',
              f'Vivaz: 11% do PL, 18% da receita, 26% do lançado consolidado; o mix segura, não repõe o ciclo — e depende da margem sobreviver ao INCC e à Caixa.'))   # 22/09/26: pesos reais (11% hoje, 33% = o triplo) na própria fórmula do slide, com os retornos do slide 49 (Vivaz 39,9%, alto padrão 23,4%)
# o bloco entra DENTRO de .sl-in (antes do último </div> que fecha o .sl-in); colado em </section> ele virava irmão flex de .sl-in e o slide quebrava em colunas
_j8 = _s8.rfind("</section>"); _k8 = _s8.rfind("</div>", 0, _j8)
_s8 = _s8[:_k8] + _s8_add + _s8[_k8:]
slides.append(_s8)

# --- receita × lançamentos consol 12m × vendas 12m
VC = RI["vendas_seg_cbr"]["Total"]
qs_r = [q for q in QS if ord_(q) >= (7, 1)]
rec12 = [q12(mrow(21), q) / 1000 if q12(mrow(21), q) else None for q in qs_r]
lan12 = [c12("A", q) + c12("M", q) + c12("C", q) if q in qs_c4 else None for q in qs_r]
def v12(q):
    i = qs_r.index(q); ks = qs_r[i - 3:i + 1]
    return sum(VC.get(k, 0) for k in ks) / 1e6 if i >= 3 and all(k in VC for k in ks) else None
ven12 = [v12(q) for q in qs_r]
c = Chart(60, 830, 46, 178, 0, 16, len(qs_r)); c.grid([0, 4, 8, 12, 16]); c.xlabels(qs_r, 8, 3)
c.line(lan12, S1, lab="lançamentos", labval=lambda v: fmt(v, 1)); c.line(ven12, S3, lab="vendas %CBR", labval=lambda v: fmt(v, 1)); c.line(rec12, S2, lab="receita", labval=lambda v: fmt(v, 1), w=2.8)
c.g.append('<text x="60" y="18" class="gtit">Receita líquida × lançamentos em consolidação × vendas, 12 meses (R$ bi)</text><text x="60" y="34" class="gsub">receita consolidada (DFs); lançamentos = base consolidação; vendas = VGV %CBR (não há série de vendas em consolidação)</text>')
body = svg(980, 200, c.flush())
i = qs_r.index("2T26")
body += ('<div class="cards3" style="margin-top:12px">'
         f'<div class="c3"><span class="c3n">{fmt(lan12[i]/rec12[i],2)}×</span><b>Lançamentos ÷ receita (12m).</b> Cada real lançado em consolidação vira receita ao longo de ~3 anos pela curva de obra. Com {fmt(lan12[i],1)} bi lançados e {fmt(rec12[i],1)} bi de receita, o funil está cheio — mas <b>só vira receita depois de vendido</b>: com a VSO do alto padrão em 11% (slide 41), o crescimento de 2027-28 depende de vender o estoque.</div>'
         f'<div class="c3"><span class="c3n">{fmt(ven12[i]/rec12[i],2)}×</span><b>Vendas ÷ receita.</b> Vendas de R$ {fmt(ven12[i],1)} bi (%CBR) contra receita de R$ {fmt(rec12[i],1)} bi: vender o mesmo que reconhece não enche o funil. O vendido e não reconhecido (REF de R$ 12,2 bi no 2T26) entrega R$ 5,6 bi em 12 meses; o resto depende de venda nova.</div>'
         '<div class="c3"><span class="c3n">2010-14</span><b>O precedente.</b> No superciclo as três curvas também se descolaram — lançamento à frente, receita atrás — e a receita continuou subindo até 2011-14 enquanto o lançamento já caía. A conta fechou em margem, não em volume.</div></div>')
body += _obox18(f'Lançado consolidado {fmt(lan12[i]/rec12[i],1)}x a receita, vendas {fmt(ven12[i]/rec12[i],1)}x: o crescimento depende de vender o estoque.',
                'Sem venda, o lançado vira estoque e trava capital no pronto (slide 60); o consenso trata a venda que falta como dada (slide 41).')   # 22/09/26: sem "contratado" (decisão editorial do autor)
slides.append(sl(P5, "Receita segue o lançamento com atraso — se ele virar venda.", body, nota="Fontes: CYREMod (receita líquida, DFs do RI); _lancamentos_consol (aba do usuário); planilha operacional do RI (vendas VGV %CBR). Bases diferentes por indisponibilidade: leia a forma das curvas, não a razão exata.")
              .replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1))   # 22/09/26: título em uma linha a 38px

def _obox36(msg, sub):   # caixa verde no padrão dos slides novos (mensagem numa linha a 19px, follow-up embaixo)
    return (output(msg, sub).replace('<div class="sl-output">', '<div class="sl-output" style="row-gap:3px;margin-top:6px">', 1).replace('<span class="out-msg">', '<span class="out-msg" style="flex:1 1 600px;line-height:1.2;font-size:19px">', 1).replace('<span class="out-sub">', '<span class="out-sub" style="flex:1 1 100%;line-height:1.35">', 1))
# --- teoria: anatomia da receita (refeito em 20/09/26 com a série medida do Anexo III dos releases: projetos com 1º reconhecimento nos 12 meses × antigos)
RO = J("_receita_origem.json")
# dados para o slide seguinte (usinagem) — mantidos
_VQ = ["3T25", "4T25", "1T26", "2T26"]
import openpyxl as _ox
_wsV = _ox.load_workbook(os.path.join(here, "fontes", "planilha_dados_operacionais.xlsx"), read_only=True, data_only=True)["Vendas"]
_rowsV = list(_wsV.iter_rows(values_only=True)); _colV = {h: i for i, h in enumerate(_rowsV[3]) if isinstance(h, str)}
def _ltmV(r): return sum((_rowsV[r - 1][_colV[q]] or 0) for q in _VQ) / 1e6
vL, vE, vP = _ltmV(102), _ltmV(141), _ltmV(128)   # vendas de lançamento, de estoque em construção, de estoque pronto (VGV 100%, R$ bi)
US = J("_usinagem.json"); _u26 = US["2T26"]
POC_E26 = _u26["estoque_custo_construcao"] / (_u26["estoque_custo_construcao"] + _u26["a_incorrer_estoque"])
REC_LTM = ltm(mrow(21)) / 1000; SH_C = 0.90; POC = {"lanc": 0.15, "obra": POC_E26, "pronto": 1.0}
eL, eE, eP = SH_C * vL * POC["lanc"], SH_C * vE * POC["obra"], SH_C * vP * POC["pronto"]; eU = REC_LTM - eL - eE - eP
# série medida (Anexo III): novos × antigos, LTM
A3x = J("_anexo3_novos.json")["serie"]
def _a3(q, k): return A3x[q][k] / 1000 * (mrow(21)[q] / 1000) / (A3x[q]["total"] / 1000)   # escalado para a receita líquida da DRE
nov_ltm = sum(_a3(q, "novos") for q in _VQ); ant_ltm = sum(_a3(q, "antigos") for q in _VQ)
nov_run = sum(_a3(q, "novos") for q in ("1T25", "2T25", "3T25", "1T26", "2T26")) / 5 * 4   # ritmo sem o 4T25
rep_4t = _a3("4T25", "novos") - nov_run / 4                                                  # excesso do 4T25 sobre o ritmo (represado)
est_ltm = eE + eP; usin_ant = ant_ltm - est_ltm
poc_in = {q: A3x[q]["poc_medio_listado"] for q in A3x if A3x[q]["poc_medio_listado"]}
poc_4t = sum(poc_in[q] for q in poc_in if q.startswith("4T")) / len([q for q in poc_in if q.startswith("4T")]); poc_n4 = sum(poc_in[q] for q in poc_in if not q.startswith("4T")) / len([q for q in poc_in if not q.startswith("4T")])
body = ('<div class="viz" style="margin-top:6px"><svg viewBox="0 0 980 150">'
        f'<rect x="20" y="10" width="270" height="112" rx="14" fill="var(--surface-1)" stroke="var(--s1)" stroke-width="1.5"/><text x="155" y="33" class="fw-t" text-anchor="middle" fill="var(--s1)">1 · projeto novo</text><text x="155" y="54" class="fw-s" text-anchor="middle">1º reconhecimento nos últimos 12 meses</text><text x="155" y="71" class="fw-s" text-anchor="middle">entra com PoC de ~{fmt(poc_n4, 0)}% (trimestre normal)</text><text x="155" y="88" class="fw-s" text-anchor="middle">e ~{fmt(poc_4t, 0)}% no 4T (renúncia em ata)</text><text x="155" y="109" class="fw-t2" text-anchor="middle">R$ {fmt(nov_ltm, 1)} bi · {fmt(100 * nov_ltm / REC_LTM, 0)}% da receita LTM</text>'
        f'<rect x="355" y="10" width="270" height="112" rx="14" fill="var(--surface-1)" stroke="var(--s2)" stroke-width="1.5"/><text x="490" y="33" class="fw-t" text-anchor="middle" fill="var(--s2)">2 · venda de estoque</text><text x="490" y="54" class="fw-s" text-anchor="middle">unidade em obra vendida hoje</text><text x="490" y="71" class="fw-s" text-anchor="middle">receita = preço × PoC já incorrido</text><text x="490" y="88" class="fw-s" text-anchor="middle">estoque a {fmt(100 * POC_E26, 0)}% de obra; pronto a 100%</text><text x="490" y="109" class="fw-t2" text-anchor="middle">R$ {fmt(est_ltm, 1)} bi · {fmt(100 * est_ltm / REC_LTM, 0)}% (estimado)</text>'
        f'<rect x="690" y="10" width="270" height="112" rx="14" fill="var(--surface-1)" stroke="var(--s3)" stroke-width="1.5"/><text x="825" y="33" class="fw-t" text-anchor="middle" fill="var(--s3)">3 · usinagem</text><text x="825" y="54" class="fw-s" text-anchor="middle">obra avançando sobre o já vendido</text><text x="825" y="71" class="fw-s" text-anchor="middle">projetos antigos menos venda de estoque</text><text x="825" y="88" class="fw-s" text-anchor="middle">mais a obra dos novos, que o anexo não separa</text><text x="825" y="109" class="fw-t2" text-anchor="middle">R$ {fmt(usin_ant, 1)} bi · {fmt(100 * usin_ant / REC_LTM, 0)}% (piso)</text>'
        '<text x="322" y="71" class="fw-c" text-anchor="middle">+</text><text x="657" y="71" class="fw-c" text-anchor="middle">+</text>'
        f'<text x="490" y="142" class="fw-s2" text-anchor="middle">receita LTM 3T25-2T26 = R$ {fmt(REC_LTM, 1)} bi; 1 é medido (Anexo III dos releases), 2 é estimado com o PoC do estoque, 3 é o resíduo dos antigos</text></svg></div>')
_rows36 = [("projetos novos, 1º reconhecimento nos 12 meses", nov_ltm, "Anexo III dos releases, soma dos 4 trimestres", 100 * nov_ltm / REC_LTM),
           ("   dos quais represado do 4T25 (acima do ritmo)", rep_4t, f"4T25 menos o ritmo dos outros trimestres (R$ {fmt(nov_run / 4, 1)} bi/tri)", 100 * rep_4t / REC_LTM),
           ("projetos antigos", ant_ltm, "Anexo III, subtotal dos demais", 100 * ant_ltm / REC_LTM),
           ("   venda de estoque em obra e pronto (est.)", est_ltm, f"R$ {fmt(vE, 1)} bi × {fmt(100 * POC_E26, 0)}% + R$ {fmt(vP, 1)} bi × 100%, × 90% de perímetro", 100 * est_ltm / REC_LTM),
           ("   usinagem sobre os antigos (piso)", usin_ant, "antigos − venda de estoque", 100 * usin_ant / REC_LTM)]
body += ('<div class="viz" style="margin-top:8px"><table class="tl compact" style="width:100%"><thead><tr><th>receita LTM 3T25-2T26 por origem</th><th style="text-align:right">R$ bi</th><th>como</th><th style="text-align:right">% da receita</th></tr></thead><tbody>'
         + ''.join(f'<tr{" class=\"total\"" if not a.startswith("   ") else ""}><td style="white-space:pre">{a}</td><td style="text-align:right">{fmt(b, 1)}</td><td>{c_}</td><td style="text-align:right">{fmt(d, 0)}%</td></tr>' for a, b, c_, d in _rows36)
         + f'<tr class="total"><td>receita líquida LTM (DRE)</td><td style="text-align:right">{fmt(REC_LTM, 1)}</td><td>o modelo anterior (lançamento a 15% na venda) dava usinagem de {fmt(100 * eU / REC_LTM, 0)}%: o 4T25 inflava o resíduo</td><td style="text-align:right">100%</td></tr></tbody></table></div>')
body += _obox36(f'Lançar não é faturar, mas fatura mais cedo: novos são {fmt(100 * nov_ltm / REC_LTM, 0)}% da receita, com PoC de ~{fmt(poc_n4, 0)}% na entrada.',
                f'Desde o 4T25 a renúncia sai a cada fechamento: o projeto entra antes; usinagem sobre os antigos é piso de {fmt(100 * usin_ant / REC_LTM, 0)}%, não {fmt(100 * eU / REC_LTM, 0)}%.')
slides.append(sl(P5 + " " + PILL, "De onde vem a receita: estoque, lançamento e usinagem.", body, cls="teoria", nota="Fontes: releases trimestrais, Anexo III (reconhecimento de receita por empreendimento; subtotal 'obras reconhecidas após <mês do ano anterior>' = projetos com 1º reconhecimento nos 12 meses anteriores; escalado para a receita líquida da DRE); PoC na entrada = média do % de evolução financeira dos projetos novos listados (trimestres normais ~15%, 4T ~30%); planilha do RI (vendas de estoque em construção e pronto, VGV 100%); ITR (nota de estoques e custo a incorrer) para o PoC do estoque; call 4T25 (renúncia em ata ao direito de desistir, a cada fechamento). A venda de estoque em projetos novos está contada nos novos, então a usinagem sobre os antigos é piso e a venda de estoque, teto."))
# --- histórico: peso da usinagem na receita 12m e avanço de PoC implícito (por que é difícil acertar a receita)
def _qV(r, q): return (_rowsV[r - 1][_colV[q]] or 0) / 1e6 if q in _colV else None
_uq = [q for q in QS if ord_(q) >= (21, 1) and ord_(q) <= ord_("2T26")]
def _pocE(q):
    d = US.get(q, {})
    if d.get("poc_estoque_construcao") and ord_(q) > (21, 1): return d["poc_estoque_construcao"]
    i = _uq.index(q); prev = [US[x]["poc_estoque_construcao"] for x in _uq[:i] if US.get(x, {}).get("poc_estoque_construcao") and ord_(x) > (21, 1)]
    nxt = [US[x]["poc_estoque_construcao"] for x in _uq[i + 1:] if US.get(x, {}).get("poc_estoque_construcao")]
    return (prev[-1] + nxt[0]) / 2 if prev and nxt else (nxt[0] if nxt else None)
_usq = {}
for q in _uq:
    L, E, P = _qV(102, q), _qV(141, q), _qV(128, q); rev = mrow(21).get(q)
    if None in (L, E, P, rev) or _pocE(q) is None: continue
    rs = SH_C * (L * POC["lanc"] + E * _pocE(q) + P); _usq[q] = (rev / 1000, rs, rev / 1000 - rs)
qs_u = [q for q in _uq if q in _usq]
def _sumw(k, q):
    i = qs_u.index(q); return sum(_usq[x][k] for x in qs_u[i - 3:i + 1]) if i >= 3 else None
qs_u4 = qs_u[3:]
uRev = [_sumw(0, q) for q in qs_u4]; uSale = [_sumw(1, q) for q in qs_u4]; uUs = [_sumw(2, q) for q in qs_u4]
uShare = [100 * u / r for u, r in zip(uUs, uRev)]; sShare = [100 - s for s in uShare]
def _sh12m(q):
    d = US.get(q, {}); c1, c2_ = d.get("custo_incorrer_12m"), d.get("custo_incorrer_alem_12m")
    if c1 and c2_: return c1 / (c1 + c2_)
    i = QS.index(q); prev = [x for x in QS[:i] if US.get(x, {}).get("custo_incorrer_12m")]; nxt = [x for x in QS[i + 1:] if US.get(x, {}).get("custo_incorrer_12m")]
    if prev and nxt:
        f = lambda x: US[x]["custo_incorrer_12m"] / (US[x]["custo_incorrer_12m"] + US[x]["custo_incorrer_alem_12m"])
        return (f(prev[-1]) + f(nxt[0])) / 2
    return None
def _lag4(q): i = QS.index(q); return QS[i - 4]
uPrev = [100 * _sh12m(_lag4(q)) if _sh12m(_lag4(q)) else None for q in qs_u4]
uReal = [100 * u / (US[_lag4(q)]["ref_itr"] / 1e3) if US.get(_lag4(q), {}).get("ref_itr") else None for u, q in zip(uUs, qs_u4)]
uCron = [100 * _sh12m(q) if _sh12m(q) else None for q in qs_u4]
uPocB = [100 * US[q]["poc_base_vendida"] if US.get(q, {}).get("poc_base_vendida") else None for q in qs_u4]
uPoc = [100 * _pocE(q) for q in qs_u4]
c = Chart(60, 440, 46, 178, 0, 100, len(qs_u4)); c.grid([0, 25, 50, 75, 100], lambda t: f"{t:g}%"); c.xlabels(qs_u4, 4, 1, lambda l: "20" + l[2:])   # rótulo no 1T de cada ano (off=1: o 1º rótulo não encosta no "0%")
c.line(uShare, S1, lab="usinagem", labval=lambda v: fmt(v, 0) + "%", w=2.8); c.line(sShare, S2, lab="na venda", labval=lambda v: fmt(v, 0) + "%", w=2.2)
c.g.append('<text x="60" y="18" class="gtit">De onde veio a receita, 12m (% da receita líquida)</text><text x="60" y="34" class="gsub">usinagem = receita − "na venda" (lançamento 15%, estoque ao PoC do trimestre, pronto 100%)</text>')
c2 = Chart(560, 840, 46, 178, 0, 100, len(qs_u4)); c2.grid([0, 25, 50, 75, 100], lambda t: f"{t:g}%"); c2.xlabels(qs_u4, 4, 1, lambda l: "20" + l[2:])   # x1=840: rótulos de fim de linha cabem no viewBox de 980
c2.line(uPocB, MU, lab="PoC base vendida", labval=lambda v: fmt(v, 0) + "%", dash="4 3"); c2.line(uCron, S3, lab="cronograma 12m", labval=lambda v: fmt(v, 0) + "%", w=2.6); c2.line(uReal, S1, lab="realizado", labval=lambda v: fmt(v, 0) + "%", w=2.6)
c2.g.append('<text x="560" y="18" class="gtit">Quanto da REF vira receita em um ano</text><text x="560" y="34" class="gsub">cronograma: custo a incorrer em 12m ÷ total; realizado: usinagem ÷ REF 1 ano antes</text>')
body = svg(980, 200, c.flush(15) + c2.flush(15))
_b26 = US["2T26"]["rec_total_vendas"] / 1e3; _pp = _b26 * 0.01
body += ('<div class="cards3" style="margin-top:10px">'
         # 22/09/26: a usinagem tem duas medidas — 32% só com os projetos antigos (medido no Anexo III dos releases) e o modelo (58%), que inclui a obra dos projetos novos já vendidos
         f'<div class="c3"><span class="c3n">32-{fmt(uShare[-1], 0)}%</span><b>da receita LTM é obra do já vendido</b>: entre 32% (só projetos antigos, medido no Anexo III) e {fmt(uShare[-1], 0)}% (incluindo a obra dos projetos novos já vendidos, modelo). No modelo o peso foi de {fmt(min(uShare), 0)}% a {fmt(max(uShare), 0)}% desde {"20" + qs_u4[0][2:]}: quando a venda acelera, a parcela "na venda" sobe e a usinagem só aparece dois anos depois.</div>'
         f'<div class="c3"><span class="c3n">{fmt(uCron[-1], 0)}%</span><b>da REF cai em 12 meses</b>, pelo cronograma do ITR; era {fmt(max(x for x in uCron if x), 0)}% no {qs_u4[uCron.index(max(x for x in uCron if x))]}. Base vendida mais nova (PoC médio de {fmt(max(x for x in uPocB if x), 0)}% para {fmt(uPocB[-1], 0)}%): lançamento vendido entra com PoC baixo. LTM: usinagem = {fmt(uReal[-1], 0)}% da REF de um ano antes.</div>'
         f'<div class="c3"><span class="c3n">{fmt(uPoc[-1], 0)}%</span><b>PoC do estoque em construção</b>, de {fmt(max(uPoc), 0)}% em {qs_u4[uPoc.index(max(uPoc))]}: o estoque ficou mais novo (safra 2025), então cada venda de estoque reconhece menos receita no ato e empurra mais para a usinagem.</div></div>')
body += ('<p style="margin:8px 2px 0;padding:6px 10px;border-left:3px solid #c5003e;color:#c5003e;font-size:12.5px;line-height:1.35"><b>O mercado viu isso na Cury:</b> na semana de 14/09/26 a ação caiu ~6% num dia, após a companhia dizer que as chuvas recordes em SP (temporais desde 11/09) atrasam a obra, ou seja, a usinagem. A Cyrela, com a mesma exposição a SP e canteiros debaixo da mesma chuva, não caiu nada: ou a obra da Cyrela não molha, ou o mercado ainda não fez a conta.</p>')
body += _obox36('32% (só antigos) a ' + fmt(uShare[-1], 0) + '% (com obra dos novos) da receita é obra do já vendido: o ritmo de obra decide.', 'A REF de R$ 12,2 bi diz quanto; o cronograma, que menos da metade cai em um ano; 1 p.p. de PoC na base vendida vale R$ ' + fmt(_pp, 1) + ' bi.').replace('font-size:19px', 'font-size:18px', 1)   # 22/09/26: faixa 32-58%; a 18px a mensagem (100 caracteres, 834px) cabe numa linha de 872px; a 19px com "Entre … e" abria duas
slides.append(sl(P5, "Usinagem: o que a receita deve à obra, e por que ela é difícil de acertar.", body, nota="Fontes: DRE (CYREMod, receita líquida trimestral); planilha do RI (vendas de lançamento, de estoque em construção e de estoque pronto, VGV 100%); ITR (nota de estoques: imóveis a comercializar em construção; nota de obras em andamento: receita total de vendas e apropriada); releases (custo orçado a incorrer das unidades em estoque), em _usinagem.json. Estimativa com as premissas do slide anterior, mas com o PoC do estoque de cada trimestre (o slide anterior usa o de jun/26); PoC interpolado em 3T21 e 4T22."))
# --- slide 'Receita por trimestre' (20/09/26, refeito à noite): série MEDIDA do Anexo III dos releases (_anexo3_novos.json): receita do trimestre de
# projetos cujo primeiro reconhecimento ocorreu nos 12 meses anteriores ('obras reconhecidas após <mês do ano anterior>') × projetos antigos.
# Venda de estoque (obra × PoC do trimestre + pronto, × 90%) e usinagem (= antigos − venda de estoque) continuam estimativas.
def _obox37(msg, sub):   # mesma caixa de _obox (definida mais abaixo)
    return (output(msg, sub).replace('<div class="sl-output">', '<div class="sl-output" style="row-gap:3px;margin-top:6px">', 1).replace('<span class="out-msg">', '<span class="out-msg" style="flex:1 1 600px;line-height:1.2;font-size:19px">', 1).replace('<span class="out-sub">', '<span class="out-sub" style="flex:1 1 100%;line-height:1.35">', 1))
A3 = J("_anexo3_novos.json")["serie"]; _qs37 = [q for q in QS if q in A3 and mrow(21).get(q)]; _n37 = len(_qs37)
_cq = {}
for q in _qs37:
    rev = mrow(21)[q] / 1000; k = rev / (A3[q]["total"] / 1000)   # escala o anexo (incorporação + loteamentos) para a receita líquida da DRE
    nov = A3[q]["novos"] / 1000 * k; ant = A3[q]["antigos"] / 1000 * k
    E, P = _qV(141, q), _qV(128, q); pe = _pocE(q) or POC_E26; est = SH_C * (E * pe + P)
    _cq[q] = {"rev": rev, "novos": nov, "antigos": ant, "est": est, "usin": ant - est, "poc": A3[q]["poc_medio_listado"], "pn": 100 * nov / rev}
_sv = lambda key: [_cq[q][key] for q in _qs37]; _sp = lambda key: [100 * _cq[q][key] / _cq[q]["rev"] for q in _qs37]
_vmax = 0.5 * (int(max(_sv("rev")) / 0.5) + 1)
c = Chart(60, 395, 46, 190, 0, _vmax, _n37); c.grid([i * 0.5 for i in range(int(_vmax / 0.5) + 1)], lambda t: fmt(t, 1)); c.xlabels(_qs37, 4, 0, lambda l: "20" + l[2:])
c.line(_sv("rev"), "#2b2a26", w=2.8, lab="receita", labval=lambda v: fmt(v, 1)); c.line(_sv("antigos"), S2, w=2.4, lab="antigos", labval=lambda v: fmt(v, 1))
c.line(_sv("novos"), S1, w=2.6, lab="novos", labval=lambda v: fmt(v, 1)); c.line(_sv("usin"), MU, w=1.8, dash="4 3", lab="usinagem", labval=lambda v: fmt(v, 1))
c.g.append('<text x="60" y="18" class="gtit">Receita do trimestre: projetos novos × antigos, R$ bi</text><text x="60" y="34" class="gsub">novos = 1º reconhecimento nos 12 meses anteriores (Anexo III); usinagem = antigos − estoque (est.)</text>')
c2 = Chart(560, 845, 46, 190, 0, 60, _n37); c2.grid([0, 20, 40, 60], lambda t: f"{t:g}%"); c2.xlabels(_qs37, 4, 0, lambda l: "20" + l[2:])
c2.line(_sp("novos"), S1, w=2.6, lab="novos, % da receita", labval=lambda v: fmt(v, 0) + "%"); c2.line([_cq[q]["poc"] for q in _qs37], S3, w=2.2, dash="5 3", lab="PoC na entrada", labval=lambda v: fmt(v, 0) + "%")
c2.g.append('<text x="560" y="18" class="gtit">Peso dos novos e PoC na entrada</text><text x="560" y="34" class="gsub">PoC médio dos projetos novos listados no anexo; o pulo é sempre no 4T</text>')
body = svg(980, 212, c.flush(15) + c2.flush(15))
_th = "".join(f'<th style="text-align:right;padding:2px 4px">{q}</th>' for q in _qs37)
def _tr37(lab, f, cls="", pct=False):
    cells = "".join(f'<td style="text-align:right;padding:2px 4px{";color:var(--s1);font-weight:700" if q in ("4T24", "4T25") and lab.startswith("projetos novos") else ""}">{("—" if f(q) is None else (fmt(f(q), 0) + "%" if pct else fmt(f(q), 1)))}</td>' for q in _qs37)
    return f'<tr class="{cls}"><td style="white-space:nowrap;padding:2px 6px 2px 2px">{lab}</td>{cells}</tr>'
body += ('<div class="viz" style="margin-top:6px"><table class="tl compact" style="width:100%;font-size:10px"><thead><tr><th style="text-align:left;padding:2px 6px 2px 2px">R$ bi</th>' + _th + '</tr></thead><tbody>'
         + _tr37("receita líquida (DRE)", lambda q: _cq[q]["rev"], cls="total") + _tr37("projetos novos (1º reconhecimento < 12 m)", lambda q: _cq[q]["novos"]) + _tr37("projetos antigos", lambda q: _cq[q]["antigos"])
         + _tr37("novos, % da receita", lambda q: _cq[q]["pn"], pct=True) + _tr37("PoC médio no 1º reconhecimento", lambda q: _cq[q]["poc"], pct=True)
         + _tr37("venda de estoque em obra e pronto (est.)", lambda q: _cq[q]["est"]) + _tr37("usinagem = antigos − estoque (est.)", lambda q: _cq[q]["usin"], cls="total") + _tr37("usinagem, % da receita", lambda q: 100 * _cq[q]["usin"] / _cq[q]["rev"], pct=True)
         + '</tbody></table></div>')
_u4 = _cq["4T25"]; _u3 = _cq["3T25"]
body += _obox37(f'4T25: R$ {fmt(_u4["novos"], 1)} bi ({fmt(_u4["pn"], 0)}%) de projetos novos, com PoC de {fmt(_u4["poc"], 0)}% na entrada; o 4T24 teve R$ {fmt(_cq["4T24"]["novos"], 1)} bi.',
              f'Projeto novo entra com PoC de ~30%, não 15%: a renúncia ao direito de desistir sai no fechamento, sobretudo no 4T; antigos rendem R$ {fmt(min(_sv("antigos")[-8:]), 1)} a {fmt(max(_sv("antigos")[-8:]), 1)} bi.')
_s37 = sl(P5, "Receita por trimestre: projeto novo entra com PoC de 30%.", body, nota="Fontes: releases trimestrais, Anexo III (reconhecimento de receita por empreendimento, incorporação residencial e loteamentos; subtotais 'obras reconhecidas após <mês do ano anterior>' = projetos com 1º reconhecimento nos 12 meses anteriores, e demais; escalado para a receita líquida da DRE, diferença de 1 a 4%); PoC na entrada = média simples do % de evolução financeira dos projetos novos listados; DRE (CYREMod); planilha do RI (vendas de estoque em construção e pronto, VGV 100%) e PoC do estoque em construção (_usinagem.json) para a venda de estoque estimada (× 90% de perímetro); usinagem = antigos − venda de estoque, aproximação (a venda de estoque em projetos novos está contada nos novos).").replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
# --- consenso de receita (Bloomberg, telas de 18/09/26) contra a mecânica da receita
CONS = {"2026": 10.050, "2027": 11.606, "2028": 12.207, "2029": 13.442}   # R$ bi, consenso Bloomberg (8/8/7/2 estimativas), fontes/consenso_bloomberg_set26.md
anos_cs = [a for a in YRS if mrow(21).get(a)]; rev_h = [mrow(21)[a] / 1000 for a in anos_cs]
lab_cs = anos_cs + list(CONS); vals_h = rev_h + [None] * len(CONS); vals_c = [None] * (len(anos_cs) - 1) + [rev_h[-1]] + list(CONS.values())
_vcbr = RI["vendas_seg_cbr"]["Total"]
def _vyear(a):
    qs = [q for q in _vcbr if len(q) == 4 and q[2:] == a[2:]]
    return sum((_vcbr[q] or 0) for q in qs) / 1e6 if len(qs) == 4 else ((_vcbr.get(a) or 0) / 1e6 if _vcbr.get(a) else None)
vals_v = [_vyear(a) for a in anos_cs] + [None] * len(CONS)
IBBA = {"rec": {"2026": 10.023, "2027": 11.374, "2028": 12.684, "2029": 13.774}, "lanc26": 15.7, "lanc25": 18.6, "vso_lanc": 35, "vso_est25": 62, "vso_est30": 76, "cancel": 14, "ll26": 1.887, "ll27": 2.362, "div26": 0, "div27": 0.943, "tp": 35, "ke": 16.3, "g": 3.5, "data": "25/05/26"}   # modelo Itaú BBA (fontes/sellside/CYRE_Model_1Q26_IBBA.xlsx), abas Operating, IS, Valuation
vals_i = [None] * (len(anos_cs) - 1) + [rev_h[-1]] + [IBBA["rec"][a] for a in CONS]
c = Chart(60, 470, 46, 178, 0, 16, len(lab_cs)); c.grid([0, 4, 8, 12, 16]); c.xlabels(lab_cs, 3, 1, lambda l: l[2:] if len(l) == 4 else l)
c.line(vals_v, S2, w=2.2); c.line(vals_h, S1, w=2.6); c.line(vals_c, S1, lab="consenso", labval=lambda v: fmt(v, 1), dash="5 3", opacity=.6, w=2.6)
# rótulos manuais no último ponto (2025): "reportada" acima e à esquerda; "vendas %Cyrela" abaixo e à direita.
# O rótulo padrão (flush: à direita, na altura do ponto) cruzaria o tracejado do consenso, que sai desse ponto para cima.
_xl, _yv = c.x(len(anos_cs) - 1), c.y([v for v in vals_v if v is not None][-1])
c.g.append(f'<text x="{_xl - 5:.1f}" y="{c.y(rev_h[-1]) - 8:.1f}" class="fw-t2" fill="{S1}" text-anchor="end">reportada</text>'
           f'<text x="{_xl + 7:.1f}" y="{_yv + 15:.1f}" class="fw-t2" fill="{S2}">vendas %Cyrela {fmt([v for v in vals_v if v is not None][-1], 1)}</text>')
c.g.append(f'<text x="60" y="18" class="gtit">Receita líquida anual (R$ bi): reportada e consenso</text><text x="60" y="34" class="gsub">receita: DFs {anos_cs[0]}-{anos_cs[-1][2:]}; consenso: Bloomberg 18/09/26; vendas %Cyrela: RI, pro forma ex-Cury/P&amp;P 2019</text>')
_h1 = (mrow(21).get("1T26", 0) + mrow(21).get("2T26", 0)) / 1000; _h2 = CONS["2026"] - _h1; _ltm = ltm(mrow(21)) / 1000
_ref = US["2T26"]["ref_itr"] / 1e3; _cr = US["2T26"]["custo_incorrer_12m"] / (US["2T26"]["custo_incorrer_12m"] + US["2T26"]["custo_incorrer_alem_12m"])
_usin12 = _ref * _cr; _need = CONS["2027"] - _usin12
# barras em 600-820 (mesma escala 0-16 do painel 1); a linha do contratado é rotulada à direita, fora das barras
c2 = Chart(600, 820, 46, 178, 0, 16, 4); c2.grid([0, 4, 8, 12, 16]); c2.xlabels(["LTM 2T26", "2026E", "2027E", "2028E"], 1, 0)
_bars = [_ltm, CONS["2026"], CONS["2027"], CONS["2028"]]
c2.bars(_bars, S1, w=0.5, labels=[fmt(v, 1) for v in _bars], opac=[1, .55, .55, .55])
_yl = c2.y(_usin12)
c2.g.append(f'<line x1="600" y1="{_yl:.1f}" x2="820" y2="{_yl:.1f}" stroke="{S3}" stroke-dasharray="4 3" stroke-width="1.6"/>'
            f'<text x="826" y="{_yl - 2:.1f}" class="fw-t2" fill="{S3}">R$ {fmt(_usin12, 1)} bi contratados</text><text x="826" y="{_yl + 11:.1f}" class="fw-s2" fill="{S3}">REF × cronograma 12m</text>')
c2.g.append('<text x="600" y="18" class="gtit">O que o consenso exige</text><text x="600" y="34" class="gsub">receita anual × o que a REF de R$ ' + fmt(_ref, 1) + ' bi entrega em 12m (cronograma: ' + fmt(100 * _cr, 0) + '%)</text>')
body = svg(980, 200, c.flush(15) + c2.flush(15))
body += ('<div class="cards3" style="margin-top:10px">'
         f'<div class="c3"><span class="c3n">+{fmt(100 * (CONS["2026"] / rev_h[-1] - 1), 0)}% · +{fmt(100 * (CONS["2027"] / CONS["2026"] - 1), 0)}%</span><b>Consenso: R$ {fmt(CONS["2026"], 1)} bi em 2026 e R$ {fmt(CONS["2027"], 1)} bi em 2027</b> (8 estimativas; R$ {fmt(CONS["2028"], 1)} bi em 2028 com 7, R$ {fmt(CONS["2029"], 1)} bi em 2029 com 2). O 1S26 fez R$ {fmt(_h1, 1)} bi: 2026 pede R$ {fmt(_h2, 1)} bi no 2S26, contra R$ {fmt(_ltm - _h1, 1)} bi no 2S25.</div>'
         f'<div class="c3"><span class="c3n">R$ {fmt(_usin12, 1)} bi</span><b>já contratados para os próximos 12 meses</b>: REF de R$ {fmt(_ref, 1)} bi × {fmt(100 * _cr, 0)}% do cronograma. O resto do consenso de 2027 (R$ {fmt(_need, 1)} bi) vem de venda nova reconhecida no ato e da obra dessas vendas: é aí que mora o erro, nos dois sentidos.</div>'
         '<div class="c3"><span class="c3n">premissas</span><b>A Bloomberg não traz lançamento nem VSO por trás da receita</b>; as casas modelam por fora. O que uma delas assume (Itaú BBA) está no anexo sell-side, separado da série primária: a receita de 2027-28 depende de vender o que está lançado, e o consenso trata isso como dado.</div></div>')
body += ('<p style="margin:8px 2px 0;padding:6px 10px;border-left:3px solid #c5003e;color:#c5003e;font-size:12.5px;line-height:1.35"><b>Leitura contrária ao consenso:</b> a companhia lançou (R$ ' + fmt(oT[-1], 1) + ' bi em 12 meses), não vendeu no ritmo (VSO do alto padrão em ' + fmt(vA[-1], 0) + '%, o menor desde 2019), <b>recuou o lançamento</b> (alto padrão de R$ 10,3 bi em 2025 para R$ ' + fmt(oA[-1], 1) + ' bi no LTM) e está com o <b>maior estoque da série</b> (R$ ' + fmt(eT[-1], 1) + ' bi, ' + fmt(mv[-1], 1) + ' meses de venda). Muito difícil acreditar em aceleração de vendas com o lançamento apontando para baixo.</p>')
body += output('O consenso pede dois dígitos em 2027 com menos da metade da REF caindo em um ano.','Metade da receita de 2027 ainda não foi vendida; sem premissa de lançamento e VSO, o consenso extrapola.')
slides.append(sl(P5 + ' <span class="pill-teoria" style="background:#c5003e">to-do · pedir às casas a premissa de lançamento, VSO e obra</span>', "Consenso de receita: o que ele exige, e o que já está contratado.", body, nota="Fontes: consenso Bloomberg (Standard, BRL, 18/09/2026; fontes/consenso_bloomberg_set26.md); DFs/ITR (receita líquida, CYREMod linha 21); ITR 2T26 (nota de obras em andamento: REF e cronograma do custo a incorrer); notas Itaú BBA (13/08/26) e BTG (13/08/26)."))
# --- margens: reportada (DRE, ex-juros), da REF (a apropriar) e do estoque (VGV líquido de impostos − custo total)
EC = J("_estoque_custo.json")
TAXR = 124 / (_h1 * 1000 + 124)   # deduções da receita bruta ÷ receita bruta, 1S26 (release 2T26): ~2,5%
qs_mg = [q for q in QS if ord_(q) >= (20, 1) and ord_(q) <= ord_("2T26")]
mg_rep = [100 * mrow(32).get(q) if mrow(32).get(q) else None for q in qs_mg]
def _mref(q):
    d = US.get(q, {})
    if d.get("margem_ref"): return d["margem_ref"]
    c1, c2_, r = d.get("custo_incorrer_12m"), d.get("custo_incorrer_alem_12m"), d.get("ref_itr")
    return 100 * (1 - (c1 + c2_) / r) if c1 and c2_ and r else None
mg_ref = [_mref(q) for q in qs_mg]
def _mest(q):
    d = US.get(q, {}); ec = EC.get(q, {}); vg = OP["estoque"]["vgvcbr_total"].get(q)
    if not (d.get("a_incorrer_estoque") and ec.get("construcao") and vg): return None
    custo = ec["construcao"] + ec.get("concluidos", 0) + d["a_incorrer_estoque"]
    return 100 * (1 - custo / (vg * (1 - TAXR)))
mg_est = [_mest(q) if ord_(q) >= (25, 4) else None for q in qs_mg]
MG0, MG1 = 30, 62   # escala: as três séries ficam em 32-40%; a antiga vai a 60,2% (3T25). Fora da escala fica só o 8,0% de 1T21 da série antiga (não comparável), omitido.
mg_est_old = [_mest(q) if ord_(q) < (25, 4) else None for q in qs_mg]
mg_est_old = [v if v is not None and MG0 <= v <= MG1 else None for v in mg_est_old]
c = Chart(60, 820, 46, 178, MG0, MG1, len(qs_mg)); c.grid([30, 40, 50, 60], lambda t: f"{t:g}%"); c.xlabels(qs_mg, 4, 0, lambda l: "20" + l[2:])   # x1=820: rótulos de fim de linha (≤ ~95 un.) cabem no viewBox de 980
c.line(mg_est_old, S3, dash="2 3", opacity=.35, w=1.6)
c.line(mg_rep, S1, lab="reportada", labval=lambda v: fmt(v, 1) + "%", w=2.8); c.line(mg_ref, S2, lab="REF", labval=lambda v: fmt(v, 1) + "%", w=2.4); c.line(mg_est, S3, lab="estoque", labval=lambda v: fmt(v, 1) + "%", w=2.6)
c.g.append('<text x="60" y="18" class="gtit">Margem bruta: reportada, da REF e do estoque (%)</text><text x="60" y="34" class="gsub">reportada ex-juros (DRE); REF = a apropriar (release/ITR); estoque = 1 − custo ÷ VGV líquido de impostos; pontilhado claro = série antes do 4T25, não comparável</text>')
_e26 = US["2T26"]; _ec26 = EC["2T26"]; _vg26 = OP["estoque"]["vgvcbr_total"]["2T26"]
_custo26 = _ec26["construcao"] + _ec26["concluidos"] + _e26["a_incorrer_estoque"]
body = svg(980, 200, c.flush(15, leader=True))   # valores próximos (40,1 / 37,3 / 36,2): rótulos espaçados com traço até o ponto
body += ('<div class="cards3" style="margin-top:10px">'
         f'<div class="c3"><span class="c3n">{fmt(mg_rep[-1], 1)}%</span><b>Margem reportada no 2T26</b>: média ponderada da usinagem (obra do já vendido, à margem contratada na REF), da venda de estoque (margem do estoque) e do lançamento novo, que reconhece pouco no ato mas entra na REF com a margem orçada.</div>'
         f'<div class="c3"><span class="c3n">{fmt(mg_ref[-1], 1)}%</span><b>Margem da REF</b>: o já contratado sobre R$ {fmt(_e26["ref_itr"] / 1e3, 1)} bi. Estável em 35-36% desde 2023 e, como a usinagem é entre 32% (só projetos antigos, Anexo III) e {fmt(uShare[-1], 0)}% (com a obra dos novos já vendidos, modelo) da receita, é a âncora da margem dos próximos dois anos. A margem dos lançamentos novos não é divulgada: só aparece quando entra na REF.</div>'
         f'<div class="c3"><span class="c3n">{fmt(mg_est[-1], 1)}%</span><b>Margem do estoque</b>: VGV %Cyrela de R$ {fmt(_vg26 / 1e3, 1)} bi, menos {fmt(100 * TAXR, 1)}% de impostos, contra custo total de R$ {fmt(_custo26 / 1e3, 1)} bi (incorrido em obra {fmt(_ec26["construcao"] / 1e3, 1)}, concluído {fmt(_ec26["concluidos"] / 1e3, 1)}, a incorrer {fmt(_e26["a_incorrer_estoque"] / 1e3, 1)}). Acima da REF: o estoque é, em média, produto mais novo, vendido a preço de hoje.</div></div>')
body += output('Reportada = REF (36%) ponderada com estoque (~40%); o lançamento novo move a média.', f'Perímetros diferentes (VGV %Cyrela contra custo consolidado) e impostos de ~{fmt(100 * TAXR, 1)}% estimados; a série do estoque só é comparável a partir do 4T25.')
slides.append(sl(P5 + ' <span class="pill-teoria" style="background:#c5003e">to-do · quebra do custo a incorrer do estoque (4T25) e perspectiva de margem bruta com o RI: lançamentos novos podem ter margem melhor</span>', "Margem: reportada, da REF e do estoque.", body, nota="Fontes: DRE (CYREMod linha 32, margem bruta ex-juros capitalizados); releases (margem a apropriar; custo orçado a incorrer das unidades em estoque; deduções da receita bruta 1S26) e ITR (nota de obras em andamento; nota de estoques: imóveis a comercializar em construção e concluídos); planilha do RI (VGV do estoque %Cyrela). Margem do estoque = 1 − (custo incorrido + a incorrer) ÷ (VGV × (1 − impostos))."))

# --- receita e margem bruta ex-juros, total (anual) + por segmento (receita 12m)
anos_r = [a for a in YRS if mrow(21).get(a)]
rec = [mrow(21).get(a) / 1000 for a in anos_r]; mbx = [mrow(32).get(a) for a in anos_r]; mbr = [mrow(34).get(a) for a in anos_r]
anos_r2 = anos_r + ["LTM"]; rec.append(ltm(mrow(21)) / 1000)
lb26 = ltm(mrow(30)); j26 = ltm(mrow(29)); r26 = ltm(mrow(21)); OPR = [1] * len(anos_r) + [.45]
mbx.append(lb26 / r26); mbr.append((lb26 - j26) / r26)
c = Chart(60, 470, 46, 178, 0, 10, len(anos_r2)); c.grid([0, 2.5, 5, 7.5, 10]); c.xlabels(anos_r2, 3)
c.bars(rec, S2, labels=[fmt(v, 1) if a in ("2011", "2017", "2025", "LTM") else "" for v, a in zip(rec, anos_r2)], opac=OPR)
c.g.append('<text x="60" y="18" class="gtit">Receita líquida (R$ bi por ano)</text><text x="60" y="34" class="gsub">LTM = 3T25-2T26, em tom claro</text>')
c2 = Chart(560, 860, 46, 178, 0.2, 0.46, len(anos_r2)); c2.grid([0.2, 0.26, 0.32, 0.38, 0.44], lambda t: f"{t*100:g}%"); c2.xlabels(anos_r2, 3)
c2.line(mbx, S1, lab="ex-juros", labval=lambda v: pct(v, 1), w=2.8, last_opac=.45); c2.line(mbr, MU, lab="reportada", labval=lambda v: pct(v, 1), dash="4 3", last_opac=.45)
c2.g.append('<text x="560" y="18" class="gtit">Margem bruta: ex-juros × reportada</text><text x="560" y="34" class="gsub">juros do SFH no custo: 1,5-3 p.p.; série ex-juros desde 2006 (CYREMod)</text>')
body = svg(980, 200, c.flush() + c2.flush())
med = sorted(x for x in mbx[:-1])[len(mbx[:-1]) // 2]
body += ('<div class="cards3" style="margin-top:12px">'
         f'<div class="c3"><span class="c3n">{pct(mbx[-1],1)}</span><b>Margem ex-juros LTM (3T25-2T26)</b>. Alta, mas não inédita: a série anual esteve acima em {sum(1 for v in mbx[:-1] if v > mbx[-1])} dos {len(mbx)-1} anos (2006-09 e 2015-16 passaram de 38%). A mediana de vinte anos é <b>{pct(med,1)}</b>: o mercado capitaliza a parte alta da série, não o meio.</div>'
         f'<div class="c3"><span class="c3n">{fmt(j26,0)}</span><b>Juros capitalizados no custo, LTM (R$ mi)</b>, contra 133 em 2024: a Selic a 15% e o SFH mais caro comprimem a margem reportada em ~3 p.p. — sem piora operacional. Comparar sempre ex-juros.</div>'
         '<div class="c3"><span class="c3n">pares</span><b>Pendente: comparar contra Lavvi, EZTEC, Even, MDNE e os puros de MCMV</b> na mesma base (ex-juros, %CBR). Está no TO-DO da versão completa (item 4); sem isso o "topo da década" é auto-referente.</div></div>')
body += output('O mercado capitaliza a parte alta de uma série de vinte anos — que já esteve mais alta.')
slides.append(sl(P5, "Receita e margem: o topo da série — mas a régua tem vinte anos.", body, nota="Fontes: CYREMod (receita líquida, lucro bruto e juros apropriados ao custo, das DFs/ITR-DFP e releases; 2006-2T26). Margem ex-juros = lucro bruto antes dos juros capitalizados ÷ receita."))

# --- por segmento: receita 12m e margem (nota de segmentos)
qs_s2 = [q for q in QS if ord_(q) >= (20, 4)]
def r12(row): return [q12(row, q) / 1000 if q12(row, q) else None for q in qs_s2]
rA, rM, rC, rO = r12(mrow(35)), r12(mrow(37)), r12(mrow(39)), r12(mrow(41))
c = Chart(60, 500, 46, 178, 0, 2, len(qs_s2)); c.grid([0, 0.5, 1, 1.5, 2], lambda t: f"{t:g}".replace(".", ",")); c.xlabels(qs_s2, 4, 0)
c.line(rA, S1, lab="alto padrão", labval=lambda v: fmt(v, 1)); c.line(rM, S2, lab="médio", labval=lambda v: fmt(v, 1)); c.line(rC, S3, lab="MCMV", labval=lambda v: fmt(v, 1), w=2.8); c.line(rO, MU, lab="demais", labval=lambda v: fmt(v, 1), dash="3 3")
c.g.append('<text x="60" y="18" class="gtit">Lucro bruto por segmento, 12 meses (R$ bi)</text><text x="60" y="34" class="gsub">nota de segmentos dos ITR (base com juros capitalizados)</text>')
shC = [cc / (a + m + cc + (o or 0)) if all(x is not None for x in (a, m, cc)) else None for a, m, cc, o in zip(rA, rM, rC, rO)]
c2 = Chart(600, 880, 46, 178, 0, 0.4, len(qs_s2)); c2.grid([0, 0.1, 0.2, 0.3, 0.4], lambda t: f"{t*100:g}%"); c2.xlabels(qs_s2, 4, 0)
c2.line(shC, S3, lab="MCMV", labval=lambda v: pct(v, 0), w=2.8)
c2.g.append('<text x="600" y="18" class="gtit">MCMV no lucro bruto (12m)</text><text x="600" y="34" class="gsub">' + pct([x for x in shC if x][0], 0) + ' → ' + pct([x for x in shC if x][-1], 0) + ' em cinco anos</text>')
body = svg(980, 200, c.flush() + c2.flush())
body += output('A Vivaz faz um quinto do lucro bruto com 18% da receita (LTM 2T26).', 'Alto padrão estável em R$ 1,6-1,7 bi com margem caindo de 34% para 31%. A Vivaz a 36% é meio de tabela do MCMV (Cury 39-40%, MRV 30-31%).')   # 22/09/26: período padrão LTM 2T26 (receita 18%, margem 36%)
slides.append(sl(P5, "Por segmento: a Vivaz já é um quinto do lucro bruto.", body, nota="Fontes: CYREMod linhas 35-42 (nota de informações por segmento dos ITR/DFP, 1T20-2T26); pares: releases 1S26 (analise_fr_e_decks.md §8.1)."))

# ================================================================ fechamento
slides.append(sl("próximos passos", "O que falta para os 100%.",
  '<div class="fwgrid" style="margin-top:6px"><div class="fwcard map"><header>conteúdo a adicionar (o usuário definirá)</header><dl>'
  '<dt>~20% restante</dt><dd>Blocos que o roteiro ainda não fixou. Candidatos naturais: balanço e caixa (dívida, terrenos a pagar, geração recorrente), o preço da ação e a sensibilidade ao juro longo, a tese em uma página.</dd>'
  '<dt>conta de valor do MCMV</dt><dd>Indicada na parte 4: quanto vale a Vivaz dentro da Cyrela e por que a ação não reage proporcionalmente.</dd>'
  '<dt>pares</dt><dd>Margem ex-juros, ROE, alavancagem e P/B de Lavvi, EZTEC, Even, MDNE e puros de MCMV na mesma base (item 4 do TO-DO).</dd></dl></div>'
  '<div class="fwcard mcmv"><header>dados pendentes</header><dl>'
  '<dt>RJ de construtoras</dt><dd>Sem fonte primária com abertura setorial; pedir série ao Serasa/TMA ou usar TJ-SP por CNAE.</dd>'
  '<dt>vendas em consolidação</dt><dd>Não existe série; o gráfico de receita × lançamentos × vendas usa %CBR para vendas.</dd>'
  '<dt>RI</dt><dd>Perguntas 27 (juros do performado na receita) e 35 (SK Realty) seguem sem resposta; critério de consolidação por projeto.</dd>'
  '<dt>anexo</dt><dd>A <a href="index.html" style="color:var(--s1)">versão completa</a> (54 slides + abas de contabilidade, mercado e gestão) permanece publicada como referência.</dd></dl></div></div>'))

# ================================================================ monta o arquivo
# ---- montagem (18/09/26, recuperação): a ordem e os slides cujo gerador se perdeu vêm de _enxuta_base.html (última versão
# publicada); os blocos gerados acima substituem a seção publicada de mesmo título. Slides novos entram por título.
_HB = io.open(os.path.join(here, "_enxuta_base.html"), encoding="utf-8").read()
_HS = re.findall(r'<section class="slide[^"]*"[^>]*>.*?</section>', _HB, re.S)
def _h2(s):
    m = re.search(r'<h2[^>]*>(.*?)</h2>', s, re.S); return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', m.group(1))).strip() if m else ''
_gen = {_h2(s): s for s in slides if _h2(s)}
# 22/09/26: o slide de receita × lançamento mudou de título no gerador; a seção publicada de mesmo tema continua sendo substituída por ele
_gen["Receita segue lançamento com dois anos de atraso — e o lançamento já aconteceu."] = next(s for s in slides if "virar venda" in _h2(s))
_static_titles = set()
final = []
SKIP = ('Vinte anos, três ciclos', 'Receita e margem: o topo da série', 'O que falta para os 100%')   # removidos a pedido (18/09/26)
for sec in _HS:
    h = _h2(sec)
    if any(s in h for s in SKIP): continue
    if h in _gen: final.append(_gen[h])
    else: final.append(sec); _static_titles.add(h)
GEN_SET = set(id(s) for s in _gen.values())
# slide 37 (publicado): troca a tabela de sensibilidade pela versão com g = 0% e g = 4%
for k, s in enumerate(final):
    if "a DuPont diz de onde veio" in _h2(s):
        s2 = re.sub(r'<div class="viz" style="margin-top:8px"><table class="tl".*?</table><p class="sl-nota"[^>]*>.*?</p></div>', lambda m: TBL37, s, count=1, flags=re.S)
        assert s2 != s, "tabela do 37 não encontrada"; final[k] = s2
# slide novo: a ação e o juro de 10 anos, logo após o P/B
_dpr = next(s for s in slides if "ROE ajustado pelo estoque pronto" in _h2(s))
_dgc = next(s for s in slides if "Lucro, caixa, dívida e payout" in _h2(s))
final.insert(next(i for i, s in enumerate(final) if "Terreno a prazo, obra e recebível" in _h2(s)) + 1, _dgc)
# (18/09/26) slide 'ROE ajustado pelo estoque pronto' retirado do deck a pedido; _dpr continua gerado, não inserido
_dj = next(s for s in slides if "um título de juros" in _h2(s))
final.insert(next(i for i, s in enumerate(final) if "O preço: P/B em vinte anos" in _h2(s)) + 1, _dj)
# --- slide 'MCMV por dentro' (vem pronto da base): gráfico de share regenerado com a Cury desde 2017 e Cury ÷ SP+RJ (19/09/26)
_LR = J("_lancamentos_ri.json"); _MM = J("_mcmv_mensal.json"); _MU = J("_mcmv_uf_mensal.json"); _CH = J("_cury_hist.json")
_cu = next(v for k, v in _CH.items() if k.endswith("Número de unidades") and "LANÇ" in k.upper())
_YS = [str(y) for y in range(2009, 2026)]
def _ann(d, key=None):
    a = {}
    for k, v in d.items(): a[k[:4]] = a.get(k[:4], 0) + (v[key] if key else v)
    return a
_fin = _ann(_MM["mensal"], "un"); _ogu = _ann(_MM["ogu_mensal"]); _spr = _ann(_MU["sp_rj"])
_cy = {}; _cy1 = {}
for q in _LR["un_mcmv23"]:
    y = "20" + q[2:]; _cy[y] = _cy.get(y, 0) + (_LR["un_mcmv23"].get(q) or 0); _cy1[y] = _cy1.get(y, 0) + (_LR["un_mcmv1"].get(q) or 0)
_L4 = ("3T25", "4T25", "1T26", "2T26"); _lw = lambda k: "2025-07" <= k <= "2026-06"
_ltm = {"fin": sum(v["un"] for k, v in _MM["mensal"].items() if _lw(k)), "ogu": sum(v for k, v in _MM["ogu_mensal"].items() if _lw(k)), "spr": sum(v for k, v in _MU["sp_rj"].items() if _lw(k)),
        "cy": sum(_LR["un_mcmv23"].get(q) or 0 for q in _L4), "cu": sum(_cu.get(q, 0) for q in _L4)}
_sh_cy = {y: 100 * _cy[y] / _fin[y] for y in _YS}; _sh_cy1 = {y: 100 * (_cy[y] + _cy1[y]) / (_fin[y] + _ogu.get(y, 0)) for y in _YS if _cy1.get(y)}
_sh_cu = {y: 100 * _cu[y] / _fin[y] for y in _YS if _cu.get(y)}; _sh_cs = {y: 100 * _cu[y] / _spr[y] for y in _YS if _cu.get(y)}
_ltm["sh_cy"] = 100 * _ltm["cy"] / _ltm["fin"]; _ltm["sh_cu"] = 100 * _ltm["cu"] / _ltm["fin"]; _ltm["sh_cs"] = 100 * _ltm["cu"] / _ltm["spr"]
# geometria da base: barras x = 62,7 + 22,75·i (FGTS) e +8,7 (OGU), base y=137, 800 mil → y=53; share x = 564,2 + 18,33·i, LTM em 875,8; eixo 0-12%
_g = []
def _yb(v): return 137 - 84 * v / 800000
def _ys(v): return 137 - 84 * v / 12
for tval in (0, 200, 400, 600, 800):
    _g.append(f'<line x1="60" y1="{_yb(tval*1000):.1f}" x2="470" y2="{_yb(tval*1000):.1f}" stroke="var(--grid)" opacity=".55"/><text x="54" y="{_yb(tval*1000)+4:.1f}" class="axq" text-anchor="end" opacity=".85">{tval}</text>')
_g.append('<line x1="60" y1="137" x2="470" y2="137" stroke="var(--baseline)"/>')
for i, y in enumerate(_YS):
    x0 = 62.7 + 22.75 * i
    _g.append(f'<rect x="{x0:.1f}" y="{_yb(_fin[y]):.1f}" width="7.7" height="{137-_yb(_fin[y]):.1f}" rx="1.5" fill="var(--s3)"/>')
    if _ogu.get(y): _g.append(f'<rect x="{x0+8.7:.1f}" y="{_yb(_ogu[y]):.1f}" width="7.7" height="{137-_yb(_ogu[y]):.1f}" rx="1.5" fill="var(--muted)"/>')
    if i % 2 == 0: _g.append(f'<text x="{x0+8.7:.1f}" y="152" class="axq" text-anchor="middle" opacity=".75">{y[2:]}</text>')
_xl = 62.7 + 22.75 * 17 + 10   # 19/09/26: barra LTM 10 un. à direita (o rótulo "LTM" encostava no "25": 1,3 un. de folga → 8)
_g.append(f'<rect x="{_xl:.1f}" y="{_yb(_ltm["fin"]):.1f}" width="7.7" height="{137-_yb(_ltm["fin"]):.1f}" rx="1.5" fill="var(--s3)" opacity=".45"/><text x="{_xl+5:.1f}" y="152" class="axq" text-anchor="middle" opacity=".75">LTM</text>')
for y, dx in (("2009", 0), ("2013", -1.5), ("2021", 0), ("2025", 0)):
    i = _YS.index(y); _g.append(f'<text x="{62.7+22.75*i+3.9+dx:.1f}" y="{_yb(_fin[y])-4:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="middle">{round(_fin[y]/1000)}</text>')
_g.append(f'<text x="{_xl+3.9:.1f}" y="{_yb(_ltm["fin"])-4:.1f}" class="fw-s2" fill="var(--ink-2)" text-anchor="middle">{round(_ltm["fin"]/1000)}</text>')
# "390" (OGU 2013) na mesma linha do "443", à direita do par de barras: antes (x0+18, y da barra OGU) cobria o topo da barra FGTS de 2014 e encostava no "443" (3 un.)
_i13 = _YS.index("2013"); _g.append(f'<text x="{62.7+22.75*_i13+20.5:.1f}" y="{_yb(_fin["2013"])-4:.1f}" class="fw-s2" fill="var(--muted)">{round(_ogu["2013"]/1000)}</text>')
_g.append('<text x="60" y="15" class="gtit">Unidades contratadas no MCMV por ano (mil)</text><text x="60" y="31" class="gsub">MCid; escuro = financiadas FGTS/FS (Faixas 1-4); claro = Faixa 1 OGU/FAR</text><text x="60" y="44" class="gsub">LTM = jul/25-jun/26, tom claro; FGTS financiou R$ 14 → 116 bi (2009-25)</text>')
# painel da direita
for tval in (0, 3, 6, 9, 12):
    _g.append(f'<line x1="555" y1="{_ys(tval):.1f}" x2="875" y2="{_ys(tval):.1f}" stroke="var(--grid)" opacity=".55"/><text x="549" y="{_ys(tval)+4:.1f}" class="axq" text-anchor="end" opacity=".85">{tval}%</text>')
_g.append('<line x1="555" y1="137" x2="875" y2="137" stroke="var(--baseline)"/>')
def _xs(y): return 564.2 + 18.33 * _YS.index(y)
for i, y in enumerate(_YS):
    if i % 2 == 0: _g.append(f'<text x="{_xs(y):.1f}" y="152" class="axq" text-anchor="middle" opacity=".75">{y[2:]}</text>')
_x14 = _xs("2014"); _g.append(f'<line x1="{_x14:.1f}" y1="52" x2="{_x14:.1f}" y2="137" stroke="var(--muted)" stroke-dasharray="3 3" opacity=".6"/><text x="{_x14+4:.1f}" y="58" class="fw-s2" fill="var(--muted)">fim da Faixa 1 (Cury/FAR)</text>')
def _pl(d, col, w, dash="", op=1):
    pts = " ".join(f"{_xs(y):.1f},{_ys(d[y]):.1f}" for y in _YS if y in d)
    return f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{w}"{f" stroke-dasharray=\"{dash}\"" if dash else ""} opacity="{op}" stroke-linejoin="round"/>'
def _tail(d, lv, col, w):   # trecho tracejado até o LTM (x=875,8)
    return f'<line x1="{_xs("2025"):.1f}" y1="{_ys(d["2025"]):.1f}" x2="875.8" y2="{_ys(lv):.1f}" stroke="{col}" stroke-width="{w}" stroke-dasharray="3 3" opacity=".45"/><circle cx="875.8" cy="{_ys(lv):.1f}" r="3.2" fill="{col}" opacity=".45"/>'
_g.append(_pl(_sh_cy1, "var(--s3)", 2.2, "4 3", .7))
_g.append(_pl(_sh_cy, "var(--s3)", 2.8) + _tail(_sh_cy, _ltm["sh_cy"], "var(--s3)", 2.8))
_g.append(_pl(_sh_cu, "var(--s1)", 2.4) + _tail(_sh_cu, _ltm["sh_cu"], "var(--s1)", 2.4))
_g.append(_pl(_sh_cs, "var(--s1)", 2.2, "5 3") + _tail(_sh_cs, _ltm["sh_cs"], "var(--s1)", 2.2))
_g.append(f'<text x="882.8" y="{_ys(_ltm["sh_cs"])+4:.1f}" class="fw-t2" fill="var(--s1)">SP+RJ {fmt(_ltm["sh_cs"], 1)}%</text>')
_g.append(f'<text x="882.8" y="{_ys(_ltm["sh_cu"])-1:.1f}" class="fw-t2" fill="var(--s1)">Cury {fmt(_ltm["sh_cu"], 1)}%</text>')
_g.append(f'<text x="882.8" y="{_ys(_ltm["sh_cy"])+12:.1f}" class="fw-t2" fill="var(--s3)">Cyrela {fmt(_ltm["sh_cy"], 1)}%</text>')
_g.append(f'<text x="{_xs("2017")-2:.1f}" y="{_ys(_sh_cs["2017"])-6:.1f}" class="fw-s2" fill="var(--s1)" text-anchor="end">{fmt(_sh_cs["2017"], 1)}%</text>')
_g.append('<text x="555" y="15" class="gtit">Share no MCMV: lançadas ÷ financiadas FGTS</text><text x="555" y="31" class="gsub">Cyrela = un. MCMV 2 e 3 (100%, ex-Cury/P&amp;P); dourado tracejado = incl. Faixa 1</text><text x="555" y="44" class="gsub">Cury = RI (2017-25, LTM); vermelho tracejado = Cury ÷ financiadas em SP+RJ</text>')
_SVG23 = '<svg viewBox="0 0 980 158">' + "".join(_g) + '</svg>'
for _k, _s in enumerate(final):
    if "MCMV por dentro" in _h2(_s):
        _s2 = re.sub(r'<svg viewBox="0 0 980 158">.*?</svg>', lambda m: _SVG23, _s, count=1, flags=re.S)
        _s2 = _s2.replace("Cury, só em SP e RJ: 3,9%", f"Cury, só em SP e RJ: {fmt(_sh_cu['2025'], 1)}% do programa nacional em 2025, mas {fmt(_sh_cs['2025'], 1)}% do MCMV financiado em SP e RJ ({fmt(_sh_cs['2017'], 1)}% em 2017): triplicou a fatia no próprio mercado em oito anos", 1)
        _s2 = _s2.replace(" (3,4-3,9% desde 2021) num programa nacional", "", 1)
        _s2 = _s2.replace("prévias operacionais da Cury (unidades lançadas)", "planilha de fundamentos do RI da Cury (unidades lançadas, 2017-2T26); base MCid por UF (_mcmv_uf_mensal.json: financiadas em SP e RJ)", 1)
        # 19/09/26: o cartão da esquerda ("Cyrela e Cury no programa" mais longo) tinha 282px de texto contra 249 do direito (grade a 314px). Só a proporção da grade não
        # ajuda (as linhas são discretas: 1,09fr → 266/282); dd a 12px/1,3 (classe .dense, em EXTRA_CSS) + coluna esquerda 1,07fr → 255/255, grade 287px, slide 772 → 744
        _s2 = _s2.replace('<div class="fwgrid" style="margin-top:6px"><div class="fwcard mcmv">', '<div class="fwgrid dense" style="margin-top:6px;grid-template-columns:1.07fr .93fr"><div class="fwcard mcmv">', 1)
        final[_k] = _s2; break
# pílulas de to-do em slides que vêm prontos da base (18/09/26)
def _add_todo(title_sub, txt):
    for k, s in enumerate(final):
        if title_sub in _h2(s):
            final[k] = re.sub(r'(<p class="kick"[^>]*>)(.*?)</p>', lambda m: m.group(1) + m.group(2) + ' <span class="pill-teoria" style="background:#c5003e">' + txt + '</span></p>', s, count=1, flags=re.S); return
    raise KeyError(title_sub)
_add_todo("Menos canteiros, mais unidades por canteiro", "to-do · conversar com o RI sobre as perspectivas de lançamento")
# slides 19 (SBPE) e 22 (perspectivas), que vêm prontos da base: "da TR para o CDI" descrevia o custo marginal de funding, não o indexador da poupança (19/09/26)
_REPL_TXT = [
    ("A renda cresceu — e foi ela, não o crédito, que sustentou a demanda.", "A renda cresceu, mas não explica o 3x: a demanda veio do topo e do investidor."),   # 22/09/26: título alinhado à caixa verde (revisão contrarian)
 ("Muda o preço do funding, da TR para o CDI, um fator de cada vez.", "Não muda o indexador da poupança, que segue em TR: muda o peso dela no funding. O crédito novo nasce lastreado em LCI, a CDI, um fator de cada vez."),
 ("Do lado do funding, o novo modelo troca TR por CDI ao longo de dez anos e não cria captação: o SBPE segue sistema fechado.", "Do lado do funding, a poupança segue em TR, mas perde peso: o crédito novo é lastreado em LCI a CDI ao longo de dez anos, sem captação nova. O SBPE segue sistema fechado."),
 # slide "O risco do SBPE" (vem pronto da base), formatação 21/09/26: título numa linha (a 46px quebrava em duas), caixa verde no padrão dos slides novos (mensagem numa linha, apoio embaixo) e rótulo "chaves · mês 60" à esquerda da linha (a curva tracejada da margem cruzava o texto)
 ('<h2 class="head-xl">O risco do SBPE: ciclo longo, caixa fundo e o banco só na entrega.</h2>', '<h2 class="head-xl" style="font-size:36px;margin-bottom:4px">O risco do SBPE: ciclo longo, caixa fundo, banco só na entrega.</h2>'),
 ('<div class="sl-output"><span class="out-tag">o que fica</span><span class="out-msg">SBPE: ciclo mais longo, caixa mais fundo e o cliente só chega ao banco na entrega — o INCC protege o contrato, não a demanda.</span><span class="out-sub">A incorporadora carrega o projeto e o risco de repasse por dois anos; o balanço, o CRI e a entrada de 30% são o que sustenta isso.</span></div>',
  _obox36("SBPE: ciclo mais longo, caixa mais fundo e o cliente só chega ao banco na entrega.", "O INCC protege o contrato, não a demanda: a incorporadora carrega o projeto e o risco de repasse por dois anos; o balanço, o CRI e a entrada de 30% sustentam isso.")),
 # ---- decisões editoriais de 22/09/26 (slides que vêm prontos da base)
 # J · slide 5 (bônus): o pool secou em 2015-16, os anos de prejuízo; a frase vizinha perde o "bônus zero em 2015-16" para não repetir
 ("A diretoria atual ganha dinheiro pela primeira vez (bônus zero em 2015-16, R$ 3-6 mi por ano em 2017-20 e R$ 15-22 mi desde 2021): nunca viu o pool secar, e isso pesa na virada do ciclo.",
  "A diretoria atual ganha dinheiro pela primeira vez (R$ 3-6 mi por ano em 2017-20 e R$ 15-22 mi desde 2021): o pool só secou em 2015-16, os anos de prejuízo, e isso pesa na virada do ciclo."),
 # G · slide 6 (Tecnisa): números do slide 61 (anexo), que é a referência
 ("Subscreveu 13,6% a R$ 2,00/ação:", "Subscreveu 13,6% a R$ 2,60/ação:"),
 ("Em jan/19 vendeu até 7,5%;", "No 2S17 vendeu de 13,6% para 7,9%;"),
 ("derreteu: R$ 43,9 mi (4T19) → R$ 7,5 mi", "derreteu: R$ 37 mi → R$ 7,5 mi"),
 # F · slide 9: contas a receber = saldo do balanço (R$ 6,5 bi), líquido de provisão para distrato e PDD; R$ 7,1 bi é o apropriado antes das provisões
 ("PDD de R$ 96 mi sobre R$ 7,1 bi (1,3%);", "PDD de R$ 96 mi sobre R$ 6,5 bi (líquido; R$ 7,1 bi apropriados antes das provisões: 1,3%);"),
 # E · slide 10: Rio no VGV lançado, período padrão LTM 2T26
 ("<b>SP capital = 73%</b> do VGV lançado, Rio 16%, Sul e Centro-Oeste residuais.", "<b>SP capital = 73%</b> do VGV lançado, Rio 22% do VGV lançado (12 meses até 2T26), Sul e Centro-Oeste residuais."),
 # B · slide 13 (tabela no svg): duas métricas nomeadas — retorno sobre o book da Cyrela (equivalência 12m ÷ book médio: Cury 74%, Lavvi 17%, P&P 12%, total 17%) e ROE das investidas (Cury 75%, P&P 30%, Lavvi 24%)
 ("book 2T26 (nota 7) · retorno LTM</text>", "book 2T26 (nota 7) · equiv. 12m ÷ book</text>"),
 ('<text x="235" y="26" class="axq" text-anchor="end">75%*</text>', '<text x="235" y="26" class="axq" text-anchor="end">74%</text>'),
 ('<text x="235" y="45" class="axq" text-anchor="end">16%</text>', '<text x="235" y="45" class="axq" text-anchor="end">17%</text>'),
 ('<text x="0" y="146" class="fw-s2">* Cury: é o ROE da própria Cury — o book é 15,08% do PL dela, sem ágio;</text><text x="0" y="158" class="fw-s2">PL pequeno porque distribui quase todo o lucro</text>',
  '<text x="0" y="146" class="fw-s2">ROE das investidas: Cury 75%, P&amp;P 30%, Lavvi 24%</text>'),   # uma linha só: a 2ª linha (y=158 no grupo, 204 no svg de 200) saía clipada
 # H · slide 22: o investidor não saiu (slide 23 diz que a demanda veio do topo da renda e do investidor); o retorno dele ficou abaixo da Selic
 ('<span class="out-msg">O imóvel entrega ~10% contra 15% do CDI: o investidor parou de comprar.</span><span class="out-sub">A demanda do investidor só volta com juro baixo ou preço amassado — e o preço real em SP ainda não amassou.</span>',
  '<span class="out-msg">O imóvel entrega ~10% contra 15% do CDI: o retorno do investidor ficou abaixo da Selic.</span><span class="out-sub">O investidor compra menos, não some: a demanda dele ganha força com juro baixo ou preço amassado — e o preço real em SP ainda não amassou.</span>'),
 # I · slide 27: o teto é revisto por portaria, mas fica atrás do INCC entre uma revisão e outra (mensagem curta na linha; a frase inteira no apoio)
 ('<span class="out-msg">Regras por portaria, balcão único (CEF), teto parado contra INCC e o emprego do cliente.</span><span class="out-sub">Inadimplência em alta já virou régua mais dura na CEF;',
  '<span class="out-msg">Regras por portaria, balcão único (CEF), teto atrás do INCC entre revisões e o emprego do cliente.</span><span class="out-sub">O teto é revisto por portaria, mas fica atrás do INCC entre uma revisão e outra. Inadimplência em alta já virou régua mais dura na CEF;'),
 # K e E · slide 28: custo total do MCMV = 68% do VGV (obra 58% + terreno 10%, mesma base do slide 45); margem da Vivaz 36% (LTM 2T26)
 ("Com custo de ~63% do VGV,", "Com custo de 68% do VGV (obra e terreno),"),
 ("sensibilidade = premissa do apresentador (custo de 63% do VGV, obra de dois anos).", "sensibilidade = premissa do apresentador (custo total do projeto = 68% do VGV, mesma base do slide 45; obra de dois anos)."),
 ("<dt>A margem de 37% é uma safra</dt>", "<dt>A margem de 36% (LTM 2T26) é uma safra</dt>"),
 ("A Vivaz chegou a 37% porque acertou a aposta em 2023-24;", "A Vivaz chegou a 36% (LTM 2T26) porque acertou a aposta em 2023-24;"),
 # E · slide 43: o 36,6% do MCMV é o trimestre 2T26
 ('text-anchor="end">MCMV · 36,6%</text>', 'text-anchor="end">MCMV · 36,6% (2T26, trimestre)</text>'),
 # A · slide 46: ROE da Cury = 75% (lucro atribuível 12m ÷ PL médio dos controladores); 74% é a equivalência sobre o book de R$ 250 mi
 ("<b>Só a Cury</b> (à venda; 70% sobre R$ 250 mi):", "<b>Só a Cury</b> (à venda; ROE de 75%, e 74% de equivalência sobre o book de R$ 250 mi):"),
 # ---- 2ª rodada de decisões editoriais (22/09/26), slides que vêm prontos da base
 # item 6 · slide 18 (parcela tira o meio): os três números são os do próprio slide (215% hoje; ITBI: acima de 3 mi 12%, 1,5-3 mi 35% em 2026)
 ('<div class="sl-output"><span class="out-tag">o que fica</span><span class="out-msg">A parcela a 215% da renda tira o meio da pirâmide; acima de R$ 1,5 mi ninguém precisa do banco.</span><span class="out-sub">Por isso o aperto do SBPE morde o médio padrão, não o luxo — e o teto do SFH é a régua que decide quem financia.</span></div>',
  _obox18("Parcela a 215% da renda tira o meio; acima de R$ 3 mi, 12% usam banco; de 1,5 a 3 mi, 35% após o novo teto.", "Por isso o aperto do SBPE morde o médio padrão, não o luxo — e o teto do SFH (R$ 2,25 mi desde out/25) é a régua que decide quem financia.", px=17)),   # 17px: a 18px sobrava "teto." na 2ª linha
 # item 2 · slide 23 (renda × crédito): a demanda do MAP não veio da renda média (+14% em 12 anos não explica 3x de lançamento); "topo da renda" é leitura (slide 18: quem compra acima de R$ 1,5 mi quase não usa banco), não dado do slide
 ('<div class="sl-output"><span class="out-tag">o que fica</span><span class="out-msg">Apesar da situação péssima do crédito, o crescimento da renda gerou a demanda que permitiu à Cyrela expandir os lançamentos de médio e alto padrão.</span><span class="out-sub">Renda real +14% e massa +28% desde 2014, contra preço real do imóvel −18%: o comprador ficou mais rico e o imóvel, mais barato — o crédito é que não acompanhou.</span></div>',
  _obox18("O crédito piorou e o MAP lançou 3x: a demanda veio do topo da renda e do investidor, não da renda média.", "Renda média real +14% em 12 anos não explica lançamentos de R$ 4,0 bi para 13,2 bi; quem compra acima de R$ 1,5 mi quase não usa banco (slide 18) e o investidor segue comprando, com retorno abaixo do CDI (slide 22).", px=17)),   # 17px: a 18px sobrava "média." na 2ª linha
]
for _o, _n in _REPL_TXT:
    _k = [k for k, s in enumerate(final) if _o in s]; assert len(_k) == 1, _o[:40]
    final[_k[0]] = final[_k[0]].replace(_o, _n)
# só no slide do SBPE (o mesmo rótulo existe no svg de outro slide da base): "chaves · mês 60" ancorado à esquerda da linha do mês 60, fora do salto da curva tracejada (21/09/26)
_k = next(k for k, s in enumerate(final) if "O risco do SBPE" in _h2(s))
_o = '<text x="782.5" y="32" class="axq" text-anchor="middle" fill="var(--s1)">chaves · mês 60</text>'; assert _o in final[_k], "sbpe chaves"
final[_k] = final[_k].replace(_o, '<text x="776" y="32" class="axq" text-anchor="end" fill="var(--s1)">chaves · mês 60</text>', 1)
# slide do DuPont (vem pronto da base): sem o cartão "leitura contrária"; os dois gráficos empilhados e maiores (pedido de 18/09/26)
for k, s in enumerate(final):
    if "a DuPont diz de onde veio" in _h2(s):
        s2 = re.sub(r'<div class="c3"><span class="c3n">leitura contrária</span>.*?</div>', '', s, count=1, flags=re.S)
        s2 = re.sub(r'<div class="cards3" style="margin-top:6px;grid-template-columns:1fr 1fr">', '<div class="cards3" style="margin-top:6px;grid-template-columns:1fr">', s2, count=1)
        # cartão "sem as participações" em duas linhas: título corrido (run-in) e menos padding; tabela e nota azul mais justas (18/09/26)
        s2 = re.sub(r'<div class="c3"><span class="c3n">sem as participações</span>', '<div class="c3" style="padding:8px 14px"><span class="c3n" style="display:inline;font-size:15px;margin:0 6px 0 0">sem as participações ·</span>', s2, count=1)
        s2 = re.sub(r'(<table class="tl".*?</table>)', lambda m: m.group(1).replace('padding:3px 8px', 'padding:2px 8px').replace('padding:3px 6px', 'padding:2px 6px'), s2, count=1, flags=re.S)
        s2 = s2.replace('<p class="sl-nota" style="margin:3px 2px 0;color:var(--s2)">', '<p class="sl-nota" style="margin:2px 2px 0;color:var(--s2)">', 1)
        s2 = s2.replace('<div class="cards3" style="margin-top:6px;grid-template-columns:1fr">', '<div class="cards3" style="margin-top:4px;grid-template-columns:1fr">', 1)
        s2 = s2.replace('<div class="viz" style="margin-top:8px"><table class="tl"', '<div class="viz" style="margin-top:5px"><table class="tl"', 1)
        s2 = s2.replace('<div class="sl-output"><span class="out-tag">o que fica</span><span class="out-msg">ROE de 17%', '<div class="sl-output" style="margin-top:6px"><span class="out-tag">o que fica</span><span class="out-msg">ROE de 17%', 1)
        _vz = re.findall(r'<div class="viz"[^>]*>\s*<svg.*?</svg>\s*</div>', s2, re.S)
        if len(_vz) >= 2:
            _grid = re.search(r'<div class="fwgrid"[^>]*>\s*' + re.escape(_vz[0]) + r'\s*' + re.escape(_vz[1]) + r'\s*</div>', s2, re.S)
            if _grid:
                s2 = s2[:_grid.start()] + ''.join('<div class="viz" style="max-width:660px;margin:2px auto 0">' + re.search(r'<svg.*?</svg>', v, re.S).group(0) + '</div>' for v in _vz[:2]) + s2[_grid.end():]
        assert s2 != s, "dupont"; final[k] = s2; break
def _append_card(title_sub, c3n, html):
    for k, s in enumerate(final):
        if title_sub in _h2(s):
            s2 = re.sub(r'(<div class="c3"><span class="c3n">' + re.escape(c3n) + r'</span>.*?)(</div>)', lambda m: m.group(1) + html + m.group(2), s, count=1, flags=re.S)
            assert s2 != s, (title_sub, c3n); final[k] = s2; return
    raise KeyError(title_sub)
_append_card("Perspectivas do MCMV", "Caixa", ' <span style="color:#c5003e;font-weight:600">E a Caixa está em greve desde 10/09: impactos ainda incertos no repasse, no fluxo financeiro e na medição de obras.</span>')
# --- anexo · follow-up: Tecnisa, último slide (19/09/26); dados e svg de grafico_tecnisa.py (_tecnisa_frag.json)
TF = J("_tecnisa_frag.json")
_tb = '<div class="viz" style="margin-top:2px">' + TF["svg"] + '</div><ol class="ev3">' + "".join(f"<li>{e}</li>" for e in TF["ev"]) + "</ol>"
_tb += _obox36("R$ 94,9 mi de equity em 2016-17, ~R$ 75 mi de volta até 2026: perda nominal de R$ 16-21 mi.", "Contra o CDI, mais de R$ 70 mi; sem dividendo; o CRI da Tecnisa nas notas (R$ 5,2 mi) zerou em 2021. Follow-up: desde o follow-on de 2019 a Cyrela virou espectadora (3,3%; 5.155 ações no 1T26); o Jardim das Perdizes ficou na Tecnisa, que vendeu 26,09% ao BTG por R$ 260,9 mi em jun/26.")   # 21/09/26: caixa no padrão dos slides novos (mensagem numa linha a 19px, apoio em 2 linhas); antes a mensagem de 192 caracteres abria 2 linhas a 18px
_ts = sl("anexo · follow-up · Tecnisa", "Tecnisa: R$ 95 mi de equity, ~R$ 75 mi de volta, e o que sobrou.", _tb, cls="anexo", nota="Fontes: B3 COTAHIST (fechamento mensal, sem ajuste; o grupamento de 05/05/20 aparece como salto em jun/20); Tecnisa: FR 2026 item 1.1 (capitalizações de out/16, mai/17 e jul/19), fato relevante de 28/08/26 (grupamento 10:1), DFP 2021 nota 10 (debêntures: R$ 70 mi, 140% do CDI, jul/17-jul/21), fatos relevantes do Jardim das Perdizes (fev-jun/26); Cyrela: FR 2026 item 1.1, releases 3T16-2T20, notas de investimentos dos ITR/DFP 2018-2T26, notas de títulos das DFP 2018-21 (CRI sênior da Tecnisa a 140% do CDI: R$ 5,2 mi, 2,2 mi, 0,9 mi, zero), ITR 3T17 e DFP 2017 (9,47% e 7,91%). Vendas de 2017 a fechamentos mensais (preço não divulgado); perda a CDI com SGS 12; ações antes de out/16 derivadas (273,5 mi − 100 mi).")   # 21/09/26: nota encurtada de 6 para 4 linhas
_ts = _ts.replace('<div class="sl-in">', '<div class="wm-anexo" aria-hidden="true">ANEXO · FOLLOW-UP</div><div class="sl-in">', 1)
_ts = _ts.replace('<h2 class="head-xl">Tecnisa:', '<h2 class="head-xl" style="font-size:36px;margin-bottom:4px">Tecnisa:', 1)   # título em uma linha (a 46px quebrava em duas: +50px; a 38px " sobrou." ainda caía na 2ª linha, ~1045px > 1020)
final.append(_ts)
# --- mercado agregado × Cyrela: dois slides (MAP; MCMV), depois do slide operacional de lançamentos (19/09/26); svgs de grafico_mercado_map.py
MF = J("_mercado_frag.json"); _n = MF["num"]
def _mslide(seg, title, card_n, card_txt, out_msg, out_sub, h2px):
    body = ('<div class="viz" style="margin-top:0">' + MF[seg]["svg"] + '</div>'
            '<div class="fwgrid" style="grid-template-columns:1fr 1.15fr;gap:14px;margin-top:4px;align-items:center"><div class="viz" style="margin-top:0">' + MF[seg]["secovi"] + '</div>'   # 19/09/26: coluna do svg Secovi 1.1fr → 1fr (a altura da linha era o svg, 161px; a 468px de largura fica em ~143px) e o cartão ganha largura
            f'<div class="c3 tight2" style="font-size:11.5px"><span class="c3n">{card_n}</span>{card_txt}</div></div>'
            + output(out_msg, out_sub).replace('<div class="sl-output">', '<div class="sl-output" style="row-gap:3px;margin-top:6px">', 1)   # 19/09/26: mensagem numa linha ao lado da tag, follow-up numa linha inteira embaixo (padrão dos slides 38/45); sem o row-gap a caixa herdava o gap de 16px entre linhas
            .replace('<span class="out-msg">', '<span class="out-msg" style="flex:1 1 600px;line-height:1.2;font-size:19px">', 1).replace('<span class="out-sub">', '<span class="out-sub" style="flex:1 1 100%;line-height:1.35">', 1))   # 19/09/26: mensagem a 19px (a 20px as duas mensagens mediam 866/869px numa caixa de 872px e abriam 2 linhas, +24px)
    return sl("parte 5 · atualização operacional · mercado", title, body, nota="Fontes: ABRAINC-FIPE, Indicadores do Mercado Imobiliário (unidades e VGV nominal de lançamentos e vendas líquidas de distratos por segmento, 12 meses, abr/26); MCid, base MCMV financiado FGTS/FS por UF (unidades e valor financiado nominal por mês de assinatura, ref. 24/07/26); Secovi-SP, PMI jun/26 (cidade de São Paulo, empresas associadas; MCMV = Faixas 1-3 pelos limites de abr/26; VGV a INCC de jun/26); Cyrela, planilha de dados operacionais do RI (VGV lançado 100%, 12 meses; lista de empreendimentos, praça São Paulo = capital e região metropolitana, unidades MCMV 100%). Rio de Janeiro: a Ademi-RJ/Brain publica só o agregado (2025: R$ 17,6 bi lançados, +37%; 1S26: 13,3 mil unidades lançadas, +2%), sem abertura por padrão."
              ).replace('<h2 class="head-xl">', f'<h2 class="head-xl" style="font-size:{h2px}px;margin-bottom:4px">', 1)   # 19/09/26: h2 por slide (46px abria 2 linhas de 98px nos dois)
_pl, _pv = _n["map_lanc_pico"], _n["map_vend_pico"]
# 22/09/26: share de 2026 rotulado como parcial (jan-mai/26) no subtítulo do painel; a Cyrela no MAP: VGV lançado 100% 12m (alto + médio + Prime, lista do RI) de 2T25 para 2T26
_o31 = 'Geoimóvel, residencial vertical lançado por ano; Cyrela + Living + Vivaz; 2026 = jan-mai</text>'; assert MF["map"]["svg"].count(_o31) == 1, "share 2026"
MF["map"]["svg"] = MF["map"]["svg"].replace(_o31, 'Geoimóvel, vertical lançado por ano; Cyrela + Living + Vivaz; 2026 = jan-mai/26, parcial</text>', 1)   # "residencial" sai para o subtítulo não clipar à direita (+7 un. medidas pelo layout_enxuta.py)
_cy_map_2T25 = sum((LR[k].get(q) or 0) for k in ("vgv_alto", "vgv_medio", "vgv_prime") for q in ("3T24", "4T24", "1T25", "2T25")) / 1e6
_cy_map_var = 100 * (1 - _n["cy_map_ult"][1] / _cy_map_2T25)
_sm = _mslide("map", "Médio e alto padrão: o mercado desacelera, e a Cyrela vai junto.",
    f'{fmt(_n["geo_ult"][1], 1)}% · {fmt(_n["geo_ult"][2], 1)}%',
    f'<b>Share em São Paulo capital</b> (Geoimóvel, VGV · unidades): {fmt(_n["geo_2019"][0], 1)}% · {fmt(_n["geo_2019"][1], 1)}% em 2019, {fmt(_n["geo_2025"][0], 1)}% · {fmt(_n["geo_2025"][1], 1)}% em 2025, {fmt(_n["geo_ult"][1], 1)}% · {fmt(_n["geo_ult"][2], 1)}% em jan-mai/26 (parcial): a Cyrela ganha fatia num mercado que encolhe. <b>SP fora do MCMV</b>: vendas −21% em unidades e −11% em VGV em 12 meses. <b>Brasil</b> (ABRAINC): lançamentos −{fmt(100 * (1 - _n["map_lanc_ult"][1] / _n["map_lanc_pico"][1]))}% e vendas −{fmt(100 * (1 - _n["map_vend_ult"] / _n["map_vend_pico"][1]))}% desde o pico.',   # 19/09/26: cartão enxuto (mesmos números, menos palavras: o painel já mostra a série do share)
    f"SP ex-MCMV vende −21% em unidades; a Cyrela lança −{fmt(_cy_map_var, 0)}% e vende mais devagar (VSO 11%); o share de 2026 é parcial.", "Rio: sem série pública por padrão; o agregado (Ademi/Brain) ainda crescia no 1S26.", h2px=36)   # 22/09/26: mensagem no formato do autor; 19/09/26: 40px abria 2 linhas (1097px > 1020); 36px = 987px, uma linha
_sm = _sm.replace('<div class="sl-output" style="row-gap:3px;margin-top:6px">', '<div class="sl-output" style="row-gap:3px;margin-top:6px;align-items:flex-start;padding:7px 16px">', 1).replace('<span class="out-tag">', '<span class="out-tag" style="margin-top:3px">', 1).replace('line-height:1.2;font-size:19px', 'line-height:1.2;font-size:18px', 1)   # 22/09/26: mensagem de ~115 caracteres a 18px, tag alinhada à 1ª linha
_sc = _mslide("mcmv", "MCMV: o mercado segue no recorde, com funding próprio.",
    f'{fmt(_n["sh_vz_ult"][1], 1)}% · {fmt(_n["sh_cu_ult"], 1)}%',
    f'<b>Share no MCMV de SP + RJ</b> (12 meses): Vivaz {fmt(_n["sh_vz_ult"][1], 1)}% e Cury {fmt(_n["sh_cu_ult"], 1)}% no 2T26; a Vivaz veio de {fmt(_n["sh_vz_4T22"], 1)}% em 2022, a Cury de 2% em 2017. <b>SP + RJ</b>: {fmt(_n["sprj_ult"][1])} mil unidades financiadas em 12 meses (+{fmt(100 * (_n["sprj_ult"][1] / _n["sprj_2a"] - 1))}% em dois anos), R$ {fmt(_n["sprj_fin_ult"])} bi. <b>São Paulo capital</b>: 81% do lançado e 75% do vendido (jun/26).',
    "O MCMV não desacelera em SP e RJ, e a Vivaz recupera fatia: FGTS e orçamento decidem o volume.", "É o segmento que segura o lançado da Cyrela em 2026, com a margem exposta ao INCC e à Caixa.", h2px=37)
_io = next(i for i, s in enumerate(final) if "Operacional: lançamentos e velocidade de venda" in _h2(s))
final.insert(_io + 1, _sm); final.insert(_io + 2, _sc)
# --- bancos: funding e carteira habitacional por banco + market share PF ex-FGTS e PJ (19/09/26); svgs de grafico_bancos_slide.py
BF = J("_bancos_frag.json"); _bn = BF["num"]; _pf = _bn["sh_pf"]; _pj = _bn["sh_pj"]
def _obox(msg, sub):   # 20/09/26: caixa verde no padrão dos slides 30/31: mensagem numa linha (19px) ao lado da tag, follow-up numa linha inteira embaixo (a mensagem única media 1240/1257px a 20px e abria 2 linhas: caixa de 103px)
    return (output(msg, sub).replace('<div class="sl-output">', '<div class="sl-output" style="row-gap:3px;margin-top:6px">', 1)
            .replace('<span class="out-msg">', '<span class="out-msg" style="flex:1 1 600px;line-height:1.2;font-size:19px">', 1).replace('<span class="out-sub">', '<span class="out-sub" style="flex:1 1 100%;line-height:1.35">', 1))
_sb = sl("parte 3 · a operação hoje · demanda", "Banco a banco: a Caixa carrega o FGTS e a LCI.",
    '<div class="viz" style="margin-top:0">' + BF["svgA"] + '</div>'
    + _obox(f'A Caixa foi de R$ {fmt(_bn["caixa_jun22"])} bi para R$ {fmt(_bn["caixa_lci"])} bi de LCI desde jun/22, {fmt(100 * (_bn["caixa_lci"] - _bn["caixa_jun22"]) / (_bn["tot_lci"] - _bn["tot_jun22"]))}% do crescimento do sistema.',   # 20/09/26: 794px a 19px (cabe em 876)
            'Nos privados a LCI repôs a poupança que saiu.'),
    nota="Fontes: BCB, IF.data (API Olinda), conglomerados financeiros (prudenciais de 2025), trimestral: relatório Passivo desde mar/00 (Depósitos de Poupança, inclui rural; Letras de Crédito Imobiliário, criadas em 2004; Obrigações por Empréstimos e Repasses, que na Caixa são o FGTS: R$ 652 bi contra R$ 629 bi de carteira FGTS no BCB) e carteira de crédito por modalidade desde jun/14 (Habitação PF; Habitacional PJ = plano empresário; degrau de consolidação em dez/24). Degraus de fusão: Santander + Banespa (2001) e + Real (2009); Itaú + Unibanco (2009).")
_sb2 = sl("parte 3 · a operação hoje · demanda", "Share no crédito habitacional sem FGTS: a Caixa perde no PF e ganha no plano empresário.",
    '<div class="viz" style="margin-top:0">' + BF["svgB"] + '</div>'
    + _obox(f'PF sem FGTS: Caixa de {fmt(_pf["Caixa"][0])}% para {fmt(_pf["Caixa"][2])}% desde 2014; plano empresário: Caixa {fmt(_pj["Caixa"][0])}% → {fmt(_pj["Caixa"][2])}%.',   # 20/09/26: 757px a 19px (cabe em 876); Itaú/Bradesco foram para a linha de baixo, mesmos números
            f'No PF sem FGTS, Itaú {fmt(_pf["Itaú"][0])}% → {fmt(_pf["Itaú"][2])}% e Bradesco {fmt(_pf["Bradesco"][0])}% → {fmt(_pf["Bradesco"][2])}% no mesmo período.'),
    nota="Fontes: BCB, IF.data, carteira de crédito ativa por modalidade (Habitação PF; Habitacional PJ), desde jun/14 (primeiro trimestre publicado), conglomerados prudenciais (financeiros até dez/24). Share PF ex-FGTS = carteira PF do banco ÷ sistema, ambos sem os repasses do FGTS da Caixa; o FGTS operado por outros agentes (pequeno) fica no PF deles. Santander PJ habitacional zera em 2026 por reclassificação de modalidade. Outros = sistema menos os cinco.")
_isb = next(i for i, s in enumerate(final) if "SBPE: a poupança só sai" in _h2(s))
final.insert(_isb + 1, _sb); final.insert(_isb + 2, _sb2)
final[_isb] = re.sub(r'\s*<span class="pill-teoria"[^>]*>to-do · entender para onde corre o estoque de LCI[^<]*</span>', '', final[_isb], count=1)   # o to-do virou slide
# --- estouro de obra: orçamento +10%, 0% × 100% vendido, com e sem INCC; MAP e MCMV (20/09/26); svgs de grafico_estouro.py
EF = J("_estouro_frag.json")
def _eslide(seg, title, msg, sub, nota=None):
    body = ('<div class="fwgrid" style="grid-template-columns:1.7fr 1fr;gap:18px;margin-top:2px;align-items:start"><div class="viz" style="margin-top:0">' + EF[seg]["table"] + '</div>'
            '<div class="viz" style="margin-top:0">' + EF[seg]["svg"] + '</div></div>' + _obox(msg, sub))   # 20/09/26: tabela didática por componente (pedido do usuário: "não existe cenário sem INCC"; cenários = inflação com INCC, inflação sem venda, erro de orçamento) + barras da margem; mensagem numa linha (19px), follow-up embaixo
    return sl("parte 5 · atualização operacional · margem", title, body, nota=nota or "Modelo por R$ 100 de VGV, revisão de orçamento no meio da obra (50% do custo de construção incorrido); PoC = custo incorrido ÷ custo total orçado (CPC 47); receita acumulada = PoC × preço vendido. Premissas do slide do caixa por segmento (MAP: terreno 18%, margem 33%, 15% do preço recebido até a revisão e o saldo devedor corrigido pelo INCC; MCMV: terreno 10%, margem 32%, preço travado na assinatura com a Caixa). INCC tratado como índice perfeito da inflação de custo; erro de orçamento = mais quantidade ou menos produtividade, sem inflação. Sem juros capitalizados nem distratos.")   # 20/09/26: nota encurtada de 4 para 2 linhas (agente de formatação)
_m, _c = EF["map"]["num"], EF["mcmv"]["num"]
_es1 = _eslide("map", "Estouro no MAP: INCC repassa inflação, não erro.",   # 20/09/26: agente de formatação: h2 em 2 linhas → ≤ 60 chars a 38px
    f'Custo +10% com INCC: margem de {fmt(_m["A"]["mg"], 0)}% vai a {fmt(_m["B"]["mg"], 1)}%; custo +10% por erro de quantidade: cai a {fmt(_m["D"]["mg"], 1)}%.',
    f'Com o INCC a receita não estorna (R$ {fmt(_m["B"]["rec0"], 1)} → {fmt(_m["B"]["rec1"], 1)} por R$ 100 de VGV); sem índice, estorna R$ {fmt(abs(_m["D"]["est"]), 1)} no trimestre da revisão.')
_es2 = _eslide("mcmv", "Estouro no MCMV: inflação e erro custam o mesmo.",
    f'Preço travado: custo +10% leva a margem de {fmt(_c["A"]["mg"], 0)}% a {fmt(_c["B"]["mg"], 1)}%, por inflação ou por erro.',
    f'Estorno de R$ {fmt(abs(_c["B"]["est"]), 1)} por R$ 100 de VGV vendido. Só o estoque não vendido remarca, e o teto limita: a defesa é obra curta e venda rápida.',
    nota="Mesmas premissas do slide anterior; MCMV: terreno 10% do VGV, margem 32%, preço travado na assinatura com a Caixa, obra paga por medição, sem INCC para o comprador.")
for _s_ in ("_es1", "_es2"): globals()[_s_] = globals()[_s_].replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
_im = next(i for i, s in enumerate(final) if "quem tem o INCC a favor" in _h2(s))
final.insert(_im + 1, _es1); final.insert(_im + 2, _es2)
# --- Cury × Vivaz: velocidade de venda (Geoimóvel), VSO 12m e ticket (20/09/26); svg de grafico_cury_vivaz.py
CV = J("_cury_vivaz_frag.json"); _cv = CV["num"]
_scv = sl("parte 5 · atualização operacional · MCMV", "Cury × Vivaz: a Cury vende mais rápido, com ticket maior.",
    '<div class="fwgrid" style="grid-template-columns:1fr 1.75fr;gap:16px;margin-top:2px;align-items:start"><div class="viz" style="margin-top:0"><div class="gtit" style="font-size:13px;font-weight:600">Safras em São Paulo capital: % vendido em mai/26</div><div class="gsub" style="margin-bottom:4px">Geoimóvel; mesma idade, mesma foto; econ. SP = econômico sem Vivaz e Cury</div>' + CV["table"] + '</div>'
    '<div class="viz" style="margin-top:0">' + CV["svg"] + '</div></div>'
    + _obox(f'Cury vende mais na mesma idade: {_cv["saf8"]} aos {_cv["idade8"]} meses, {fmt(_cv["cury8"], 0)}% contra {fmt(_cv["vivaz8"], 0)}%; VSO {fmt(_cv["vso_cury"], 0)}% contra {fmt(_cv["vso_vivaz"], 0)}% (2T26).',
            f'A Vivaz vende como o mercado econômico de SP ({fmt(_cv["econ8"], 0)}% na mesma safra) e lançou {fmt(_cv["un_vivaz_2s25"] / 1000, 1)} mil unidades no {_cv["saf8"]}; o ticket não explica: R$ {fmt(_cv["ticket_cury"])} mil contra R$ {fmt(_cv["ticket_vivaz"])} mil.'),   # 20/09/26: painel de curva por idade trocado pela tabela de safras (pedido do usuário)
    nota=f"Fontes: Geoimóvel, Mercado Completo, cidade de São Paulo, residencial vertical, foto de mai/26 (unidades lançadas e vendidas por empreendimento, agrupadas pelo semestre de lançamento; Cury {_cv['n_cury']} empreendimentos e Vivaz {_cv['n_vivaz']} desde 2S22; econômico = padrão Econômico da base sem Vivaz e Cury). A base não tem histórico mensal: só a comparação na mesma idade é válida, e as safras antigas estão esgotadas por tempo, não por velocidade; Cury, planilha Fundamentos do RI (VSO líquida do trimestre; preço médio lançado por ano); Cyrela, planilha operacional do RI (Vivaz = MCMV Faixas 1-3; VSO bruta do trimestre = vendas ÷ estoque no fim do trimestre anterior + lançamentos; ticket anual = VGV ÷ unidades lançadas).").replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)   # 20/09/26: nota encurtada (agente de formatação); h2 a 38px para caber em uma linha
_ic = next(i for i, s in enumerate(final) if "MCMV: o mercado segue no recorde" in _h2(s))
final.insert(_ic + 1, _scv)
# --- slide 'Os parâmetros do MCMV' (vem pronto da base): quatro gráficos regenerados com a série alongada para antes de 2009 (grafico_param_mcmv.py)
_PM = J("_param_mcmv_frag.json")
for _k, _s in enumerate(final):
    if "Os parâmetros do MCMV" in _h2(_s):
        _svgs = re.findall(r'<svg viewBox="0 0 900 \d+">.*?</svg>', _s, re.S)
        assert len(_svgs) == 4, len(_svgs)
        for _old, _new in zip(_svgs, _PM["svgs"]): _s = _s.replace(_old, _new, 1)
        _s = _s.replace("Fontes:", "Fontes: Res. CCFGTS 289/1998, 460/2004 e alterações (parâmetros do FGTS antes do MCMV, fontes/verificacao/ccfgts_pre2009);", 1) if _PM.get("n_pre") else _s
        # 20/09/26: caixa verde em uma linha + follow-up numa linha (agente de formatação: as duas abriam 2 linhas)
        _s = _s.replace("Cada revisão alarga o programa para cima: mais renda, mais teto, mais gente — por portaria, paga pelo cotista.", "Cada revisão alarga o programa para cima, por portaria, paga pelo cotista do FGTS.", 1)
        _s = _s.replace("Dois subsídios empilhados: juro abaixo do mercado em todas as faixas e desconto de até R$ 55 mil (Faixas 1-2). Mesmo assim a entrada não fecha sem a incorporadora: o pró-soluto é a terceira perna do crédito, e a única sem garantia.", "Juro subsidiado e desconto de até R$ 55 mil; ainda assim a entrada só fecha com o pró-soluto da incorporadora, a única perna sem garantia.", 1)
        final[_k] = _s; break
# --- slide 37: receita por trimestre por componente, logo depois de 'De onde vem a receita' (20/09/26)
final.insert(next(i for i, s in enumerate(final) if "De onde vem a receita" in _h2(s)) + 1, _s37)
# --- mapa de SP: onde Cury e Vivaz lançam, por período (20/09/26); svg e tabela de grafico_mapa_sp.py (Geoimóvel + malha GeoSampa)
MP = J("_mapa_sp_frag.json"); _ms = MP["num"]["share"]
_cO = (_ms["Cury"]["2019-21"]["Oeste"], _ms["Cury"]["2025-26"]["Oeste"]); _vNL = (_ms["Vivaz"]["2019-21"]["Norte"] + _ms["Vivaz"]["2019-21"]["Leste"], _ms["Vivaz"]["2025-26"]["Norte"] + _ms["Vivaz"]["2025-26"]["Leste"])
_vNL22 = _ms["Vivaz"]["2022-24"]["Norte"] + _ms["Vivaz"]["2022-24"]["Leste"]; _vSO = _ms["Vivaz"]["2025-26"]["Sul"] + _ms["Vivaz"]["2025-26"]["Oeste"]
_smp = sl("parte 5 · atualização operacional · MCMV", "SP no mapa: Cury vai para o Oeste, Vivaz deixa a periferia.",
    '<div class="viz" style="margin-top:2px">' + MP["svg"] + '</div><div class="viz" style="margin-top:4px">' + MP["table"] + '</div>'
    + _obox(f'Cury: Oeste de {fmt(_cO[0], 0)}% para {fmt(_cO[1], 0)}% das unidades; Vivaz: Norte e Leste de {fmt(_vNL22, 0)}% para {fmt(_vNL[1], 0)}% desde 2022-24.',
            f'A Cury sobe de praça (Lapa, Jaguaré, Barra Funda, Santo Amaro) e de ticket; a Vivaz deixa a borda para o Sul e o Oeste ({fmt(_vSO, 0)}%), com unidade menor.'),
    nota="Fontes: Geoimóvel, Mercado Completo, cidade de São Paulo, residencial vertical, foto de mai/26 (unidades lançadas por empreendimento, distrito e data de lançamento; Cury e Vivaz pelo grupo incorporador); Prefeitura de São Paulo, GeoSampa (malha de distritos e regiões, WFS, EPSG:31983), polígonos simplificados. Bolha no centroide do distrito, área proporcional às unidades lançadas no período; 2025-26 vai até mai/26. Só a capital: a Cury lança também no Rio e na Grande SP, e a Vivaz na Grande SP e no Rio, fora deste mapa.").replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
final.insert(next(i for i, s in enumerate(final) if "Cury × Vivaz" in _h2(s)) + 1, _smp)
def _obox47(msg, sub):   # mesma caixa de _obox (definida mais abaixo)
    return (output(msg, sub).replace('<div class="sl-output">', '<div class="sl-output" style="row-gap:3px;margin-top:6px">', 1).replace('<span class="out-msg">', '<span class="out-msg" style="flex:1 1 600px;line-height:1.2;font-size:19px">', 1).replace('<span class="out-sub">', '<span class="out-sub" style="flex:1 1 100%;line-height:1.35">', 1))
# --- slide novo 47 (20/09/26): retorno por vertical, com a nota de segmentos dos ITR (_segmentos_full.json: receita, lucro bruto, despesas, lucro operacional, ativo, passivo e PL por segmento, trimestral desde 1T20; _roe_seg_serie.json: lucro operacional LTM ÷ PL médio do segmento)
SGF = J("_segmentos_full.json"); _sq = sorted(SGF, key=ord_); _SEG = [("cyrela", "alto padrão", S3), ("living", "Living (médio)", S2), ("mcmv", "Vivaz (MCMV)", S1)]
_rq = sorted(set(q for v in RSG.values() for q in v), key=ord_); _rq = [q for q in _rq if ord_(q) >= (14, 1)]
CD = J("_cury_dre.json")["serie"]; _cqs = sorted(CD, key=ord_)   # Cury (benchmark MCMV): DRE e balanço trimestrais da planilha Fundamentos do RI
def _cret(q):
    if q not in CD: return None
    i = _cqs.index(q)
    if i < 4: return None
    lop = sum(CD[x]["lop"] for x in _cqs[i - 3:i + 1]); pl = sum(CD[x]["pl_total"] for x in _cqs[i - 4:i + 1]) / 5; return 100 * lop / pl if pl else None
def _cltm(f): return sum(CD[x][f] for x in _cqs[-4:]) / 1e6
CU47 = {"rec": _cltm("rec"), "lb": _cltm("lb"), "desp": _cltm("desp"), "lop": _cltm("lop"), "ativo": CD[_cqs[-1]]["ativo"] / 1e6, "pl": CD[_cqs[-1]]["pl_total"] / 1e6, "ret": _cret(_cqs[-1])}
# Plano & Plano (2º benchmark do MCMV, 21/09/26): DRE e balanço consolidados da CVM (dados_cvm_lavvi_pp.py); lucro operacional = 3.05 (antes do financeiro)
PPV = J("_cvm_lavvi_pp.json")["pp"]; _pqs = sorted(PPV, key=ord_)
def _pret(q):
    if q not in PPV: return None
    i = _pqs.index(q)
    if i < 4: return None
    ebit = sum(PPV[x]["ebit_tri"] for x in _pqs[i - 3:i + 1]); pl = sum(PPV[x]["pl_total"] for x in _pqs[i - 4:i + 1]) / 5; return 100 * ebit / pl if pl else None
def _pltm(f): return sum(PPV[x][f + "_tri"] for x in _pqs[-4:]) / 1000
PP47 = {"rec": _pltm("rec"), "lb": _pltm("lb"), "lop": _pltm("ebit"), "desp": _pltm("lb") - _pltm("ebit"), "ativo": None, "pl": PPV[_pqs[-1]]["pl_total"] / 1000, "ret": _pret(_pqs[-1]), "ret_max": max(v for v in (_pret(q) for q in _pqs) if v), "mb": 100 * _pltm("lb") / _pltm("rec")}
PP47["q_max"] = next(q for q in _pqs if _pret(q) == PP47["ret_max"])
c = Chart(60, 430, 46, 190, 0, 90, len(_rq)); c.grid([0, 30, 60, 90], lambda t: f"{t:g}%"); c.xlabels(_rq, 8, 3, lambda l: "20" + l[2:])
for k, lab, col in _SEG: c.line([RSG[k].get(q) for q in _rq], col, w=2.6 if k == "mcmv" else 2.2, lab=lab.split(" (")[0], labval=lambda v: fmt(v, 0) + "%")
c.line([_cret(q) for q in _rq], "#2e7d32", w=2.2, dash="5 3", lab="Cury", labval=lambda v: fmt(v, 0) + "%")
c.line([_pret(q) for q in _rq], "#6b4e9b", w=2.0, dash="2 3", lab="P&amp;P", labval=lambda v: fmt(v, 0) + "%")
c.g.append('<text x="60" y="18" class="gtit">Retorno operacional s/ capital por segmento, LTM</text><text x="60" y="34" class="gsub">lucro operacional 12m ÷ PL médio, antes de juros e IR; Cury e P&amp;P: RI/CVM</text>')
_plmax = 0.5 * (int(max(SGF[q][k]["pl"] for q in _sq for k, _, _ in _SEG) / 500) + 1)
c2 = Chart(560, 850, 46, 190, 0, _plmax, len(_sq)); c2.grid([i * 1.0 for i in range(int(_plmax) + 1)], lambda t: fmt(t, 0)); c2.xlabels(_sq, 4, 3, lambda l: "20" + l[2:])
for k, lab, col in _SEG: c2.line([SGF[q][k]["pl"] / 1000 for q in _sq], col, w=2.6 if k == "mcmv" else 2.2, lab=lab, labval=lambda v: fmt(v, 1))
c2.g.append('<text x="560" y="18" class="gtit">PL atribuído por segmento, R$ bi</text><text x="560" y="34" class="gsub">ativo menos passivo do segmento, nota do ITR</text>')
body = svg(980, 212, c.flush(15) + c2.flush(15))
_L4 = _sq[-4:]; _u = _sq[-1]
def _qf(k, f, q):   # fluxos da nota vêm acumulados no ano: trimestre = acumulado − acumulado do trimestre anterior
    t_ = int(q[0]); return SGF[q][k][f] if t_ == 1 else SGF[q][k][f] - SGF[f"{t_ - 1}T{q[2:]}"][k][f]
def _ltm(k, f): return sum(_qf(k, f, q) for q in _L4) / 1000
_cols = _SEG + [("demais", "demais / holding", MU)]
_tot = {f: sum(_ltm(k, f) for k, _, _ in _cols) for f in ("rec", "lb", "desp", "lop")}; _tot["pl"] = sum(SGF[_u][k]["pl"] for k, _, _ in _cols) / 1000; _tot["ativo"] = sum(SGF[_u][k]["ativo"] for k, _, _ in _cols) / 1000
def _row(lab, f, pct=False, cls="", cury=None, pp=None):
    cells = ""
    for k, _, _ in _cols:
        v = f(k); cells += f'<td style="text-align:right">{(fmt(v, 1) + "%" if pct else fmt(v, 1)) if v is not None else "—"}</td>'
    cells += f'<td style="text-align:right;border-left:1px solid var(--grid);color:#2e7d32">{(fmt(cury, 1) + "%" if pct else fmt(cury, 1)) if cury is not None else "—"}</td>'
    cells += f'<td style="text-align:right;color:#6b4e9b">{(fmt(pp, 1) + "%" if pct else fmt(pp, 1)) if pp is not None else "—"}</td>'
    return f'<tr class="{cls}"><td>{lab}</td>{cells}</tr>'
_th = "".join(f'<th style="text-align:right;color:{col}">{lab}</th>' for _, lab, col in _cols) + '<th style="text-align:right;border-left:1px solid var(--grid);color:#2e7d32">Cury (benchmark)</th><th style="text-align:right;color:#6b4e9b">P&amp;P (benchmark)</th>'
_tbl = (f'<table class="tl compact" style="width:100%;margin-top:0"><thead><tr><th style="text-align:left">LTM {_u}, R$ bi</th>{_th}</tr></thead><tbody>'
        + _row("receita líquida", lambda k: _ltm(k, "rec"), cury=CU47["rec"], pp=PP47["rec"]) + _row("lucro bruto", lambda k: _ltm(k, "lb"), cury=CU47["lb"], pp=PP47["lb"]) + _row("margem bruta", lambda k: 100 * _ltm(k, "lb") / _ltm(k, "rec") if k != "demais" and _ltm(k, "rec") else None, pct=True, cury=100 * CU47["lb"] / CU47["rec"], pp=PP47["mb"])
        + _row("despesas do segmento", lambda k: _ltm(k, "desp"), cury=CU47["desp"], pp=PP47["desp"]) + _row("lucro operacional", lambda k: _ltm(k, "lop"), cls="total", cury=CU47["lop"], pp=PP47["lop"])
        + _row(f"ativo ({_u})", lambda k: SGF[_u][k]["ativo"] / 1000, cury=CU47["ativo"], pp=PP47["ativo"]) + _row(f"PL atribuído ({_u})", lambda k: SGF[_u][k]["pl"] / 1000, cls="total", cury=CU47["pl"], pp=PP47["pl"]) + _row("% do PL dos segmentos", lambda k: 100 * SGF[_u][k]["pl"] / 1000 / _tot["pl"], pct=True)
        + _row("retorno operacional s/ capital, LTM", lambda k: RSG[k][_u] if k in RSG else None, pct=True, cls="total", cury=CU47["ret"], pp=PP47["ret"])
        + '</tbody></table>')
body += '<div class="viz" style="margin-top:6px">' + _tbl + '</div>'
_r = {k: RSG[k][_u] for k, _, _ in _SEG}; _plsh = {k: 100 * SGF[_u][k]["pl"] / 1000 / _tot["pl"] for k, _, _ in _cols}
body += _obox47(f'Vivaz rende {fmt(_r["mcmv"], 0)}% sobre o capital com {fmt(_plsh["mcmv"], 0)}% do PL; alto padrão, {fmt(_r["cyrela"], 0)}% com {fmt(_plsh["cyrela"], 0)}%; a Cury, {fmt(CU47["ret"], 0)}%.',
              f'O capital está no alto padrão e o retorno marginal na Vivaz; a Cury, no mesmo MCMV, faz {fmt(100 * CU47["lb"] / CU47["rec"], 0)}% de margem bruta e o dobro do retorno: o teto do modelo. A P&P mostra o piso: de {fmt(PP47["ret_max"], 0)}% ({PP47["q_max"]}) para {fmt(PP47["ret"], 0)}%, com a margem bruta de 34% para {fmt(PP47["mb"], 0)}% (programa público e custo).')
_s47 = sl("parte 4 · onde estamos no ciclo", "Retorno por vertical: a Vivaz rende mais com menos capital.", body,
    nota="Fontes: nota explicativa de informações por segmento dos ITR/DFP (Cyrela = alto padrão; Living = médio; MCMV = Vivaz; demais = loteamento, serviços e corporativo), R$ mi, trimestral desde 1T20 (fluxos por diferença dos acumulados; balanço 2T22 da Vivaz corrigido pela nota) e anual antes. Retorno operacional sobre o capital = lucro operacional do segmento em 12 meses (antes de resultado financeiro, equivalência e IR) ÷ PL médio atribuído ao segmento (ativo menos passivo, 5 balanços); as JVs ficam fora dos segmentos. Cury: DRE e balanço trimestrais da planilha Fundamentos do RI (lucro antes do resultado financeiro LTM ÷ PL total médio de 5 pontas; ativo e PL de 2T26), consolidado, 100%. Plano & Plano: ITR/DFP consolidados na CVM (mesma conta; despesas = lucro bruto − lucro operacional; sem ativo); a queda de 2025-26 vem do programa municipal Pode Entrar (margem de 8% a 13%) e do custo absorvido (release 2T26). Cury e P&P são benchmarks, não segmentos.").replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
# --- slide 47: retorno por vertical, logo depois de 'Terreno a prazo, obra e recebível' (antes do slide de lucro/caixa/dívida, que vira 48)
final.insert(next(i for i, s in enumerate(final) if "Terreno a prazo, obra e recebível" in _h2(s)) + 1, _s47)
# --- slide 48 (20/09/26): Cury × Vivaz, alavancagem e valor; de grafico_cury_valor.py
CV2 = J("_cury_valor_frag.json"); _n2 = CV2["num"]
_s48 = sl("parte 4 · onde estamos no ciclo", f"Cury: {fmt(_n2['pb_cury'], 1)}x book com ROE de {fmt(_n2['roe_cury'], 0)}%; a Vivaz, por analogia, ~{fmt(_n2['pb_viv'], 1)}x.".replace("ROE de", "ROE"),   # 22/09/26: o teto sai do título e da caixa verde; fica na tabela como cenário ("ROE 75%": com "de" o "~2,5x." caía na 2ª linha a 38px)
    '<div class="viz" style="margin-top:2px">' + CV2["svg"] + '</div>'
    '<div class="fwgrid" style="grid-template-columns:1fr 1.25fr;gap:16px;margin-top:6px;align-items:start"><div class="viz" style="margin-top:0">' + CV2["t1"] + '</div><div class="viz" style="margin-top:0">' + CV2["t2"] + '</div></div>'
    + _obox18(f'Cury a {fmt(_n2["pb_cury"], 1)}x book com ROE {fmt(_n2["roe_cury"], 0)}%; a Vivaz, por analogia (Ke {fmt(_n2["mkt"]["ke"], 0)}%, g {fmt(_n2["mkt"]["g"], 0)}%), ~{fmt(_n2["pb_viv"], 1)}x: R$ {fmt(_n2["val_viv"], 1)} bi, {fmt(100 * _n2["val_viv"] / _n2["mc_cyre"], 0)}% da Cyrela.',
              f'Cury: caixa líquido e terreno a prazo = {fmt(_n2["cred_pl"], 0)}% do PL. Vivaz: vendido não reconhecido {fmt(_n2["vr_viv"], 1)}x a receita; o cenário de {fmt(_n2["pb_viv_top"], 1)}x (R$ {fmt(_n2["val_viv_top"], 1)} bi) fica na tabela, não na conta.'),
    nota=f"Fontes: Cury, planilha Fundamentos do RI (DRE e balanço trimestrais, consolidado): retorno operacional = lucro antes do resultado financeiro LTM ÷ PL total médio de 5 pontas; ROE = lucro atribuído aos controladores LTM ÷ PL da controladora médio; dívida líquida = empréstimos e financiamentos − caixa − títulos; terreno a prazo = credores por imóveis compromissados. B3, preços e ações em {_n2['mkt']['data']}. Vivaz: nota de segmentos do ITR (2T26), sem juros, IR e minoritários alocados; ROE estimado = retorno operacional × {fmt(_n2['fator_ll'], 2)} (razão ROE ÷ retorno operacional da Cury). P/B implícito = (ROE − g) ÷ (Ke − g), Ke 17% e g 4%, premissas do slide do P/B; a Cury a mercado ({fmt(_n2['pb_cury'], 1)}x) confirma a régua. Cenário da tabela = dois estágios: lucro cresce {fmt(100 * _n2['g1'])}% a.a. por {_n2['n1']} anos reinvestindo (payout = 1 − g ÷ ROE), depois perpetuidade a g 4% com o mesmo ROE; {fmt(100 * _n2['g1'])}% a.a. é o lucro da Vivaz no cenário em que ela alcança o lançado da Cury (R$ 8,1 bi) em dois anos, com a curva de reconhecimento da Cury. Vendas ÷ receita: Cury, vendas parte Cury ÷ receita; Vivaz, vendas × perímetro consolidado ({fmt(100 * _n2['cons'])}%, %consol do lançado de MCMV, lista do RI) ÷ receita do segmento; a 100% seria {fmt(_n2['vr_viv100'], 1)}x. Não é preço-alvo.").replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
final.insert(next(i for i, s in enumerate(final) if "Retorno por vertical" in _h2(s)) + 1, _s48)
# --- slide 49 (20/09/26): MAP × Vivaz por dentro; de grafico_map_vivaz.py
MV = J("_map_vivaz_frag.json"); _m9, _v9 = MV["num"]["MAP"], MV["num"]["Vivaz"]
_s49 = sl("parte 4 · onde estamos no ciclo", "MAP × Vivaz por dentro: onde está o capital de cada uma.",
    '<div class="fwgrid" style="grid-template-columns:1.15fr 1fr;gap:16px;margin-top:2px;align-items:start"><div class="viz" style="margin-top:0">' + MV["table"] + '</div><div class="viz" style="margin-top:0">' + MV["svg"] + '</div></div>'
    + _obox(f'MAP carrega R$ {fmt(_m9["cr"], 1)} bi de recebível e R$ {fmt(_m9["c_terr"], 1)} bi de terreno sobre PL de {fmt(_m9["pl"], 1)}; a Vivaz, R$ {fmt(_v9["cr"], 1)} bi sobre {fmt(_v9["pl"], 1)}.',
            f'A Vivaz lança {fmt(100 * _v9["lanc_cons"] / _v9["lanc"], 0)}% consolidado com {fmt(100 * _v9["lanc_cbr"] / _v9["lanc"], 0)}% de participação (JVs por equivalência); o MAP consolida {fmt(100 * _m9["lanc_cons"] / _m9["lanc"], 0)}% com {fmt(100 * _m9["lanc_cbr"] / _m9["lanc"], 0)}%, carregando R$ {fmt(_m9["lanc_min"], 1)} bi de sócios no balanço.'),
    nota=f"Fontes: lista de empreendimentos do RI (VGV lançado 100%, %Cyrela e % consolidado, 12 meses até 2T26; minoritários consolidados = consolidado − parte Cyrela); planilha operacional do RI (vendas e estoque a valor de mercado por segmento, 100%; %CBR só no total: vendas 74%, estoque 75%); nota de segmentos do ITR (ativo, passivo e PL de cada segmento; MAP = Cyrela + Living); nota de estoques e balanço consolidado (obra em andamento R$ {fmt(MV['num']['MAP']['c_obra'] + MV['num']['Vivaz']['c_obra'], 1)} bi, concluídos, terrenos e adiantamentos, contas a receber de clientes R$ {fmt(MV['num']['cr_total'], 1)} bi). Alocação por segmento é estimativa: obra e concluídos pelo estoque a valor de mercado de cada segmento, terrenos pelo VGV lançado × peso do terreno (18% MAP, 10% MCMV), contas a receber = resíduo do ativo do segmento, escalado ao consolidado (fator {fmt(MV['num']['k_cr'], 2)}). O recebível da Vivaz é pequeno porque o repasse à Caixa acontece na venda; o do MAP é grande porque 70% do preço vem nas chaves.").replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
final.insert(next(i for i, s in enumerate(final) if "x book com ROE" in _h2(s)) + 1, _s49)
# --- slide novo (20/09/26): Cury, VSO ex-venda direta; de grafico_cury_vd.py (carteira gerencial dos releases 1T23-2T26, dados_cury_carteira.py)
CVD = J("_cury_vd_frag.json"); _d = CVD["num"]
_svd = sl("parte 5 · atualização operacional · MCMV", f"Cury: VSO de {fmt(_d['vso'], 0)}% com venda direta; sem ela, {fmt(_d['vsox2'], 0)}% ou {fmt(_d['vsox'], 0)}%.",
    '<div class="viz" style="margin-top:2px">' + CVD["svg"] + '</div><div class="viz" style="margin-top:6px">' + CVD["table"] + '</div>'
    + _obox(f'Sem a venda direta ({fmt(_d["d"], 0)}% das vendas, est.), a VSO da Cury cai de {fmt(_d["vso"], 0)}% para {fmt(_d["vsox2"], 0)}% ou {fmt(_d["vsox"], 0)}%, perto da Vivaz ({fmt(_d["vz"], 0)}%).',
            f'Duas leituras no 2T26: só tirando a venda direta do vendido, {fmt(_d["vsox2"], 0)}%; devolvendo a carteira ao estoque, {fmt(_d["vsox"], 0)}% (médias de 4 tri: {fmt(_d["vso_m4"], 0)}% → {fmt(_d["vsox2_m4"], 0)}% ou {fmt(_d["vsox_m4"], 0)}%). A velocidade extra é crédito da própria Cury: carteira de venda direta de R$ {fmt(_d["vd0"], 1)} bi para {fmt(_d["vd"], 1)} bi desde {_d["x0"]} ({fmt(_d["d0"], 0)}% para {fmt(_d["d"], 0)}% das vendas), mais R$ {fmt(_d["ps"], 1)} bi de pró-soluto.'),
    nota=f"Fontes: releases trimestrais da Cury, seção 'Carteira e contas a receber' (carteira gerencial = recebíveis fora das instituições financeiras: pró-soluto, a parcela não financiável pelo banco, e venda direta, unidade vendida sem agente financeiro, paga à Cury; 2T23, 4T23 e 3T24 pela coluna comparativa do release seguinte); planilha Fundamentos do RI (vendas líquidas, lançamentos, estoque a valor de mercado, VSO líquida). A Cury não divulga o fluxo de venda direta: fatia estimada = carteira ÷ ({_d['nq']} trimestres × {fmt(100 * (1 - _d['pago']), 0)}% a receber; o cliente da tabela direta paga 60% na obra, call 2T26) ÷ vendas médias; com 20% ou 40% pagos, {fmt(_d['d'] * 0.7 / 0.8, 0)}% a {fmt(_d['d'] * 0.7 / 0.6, 0)}%. VSO ex-venda direta, duas curvas: (a) sobre o estoque reportado = vendas × (1 − fatia) ÷ (estoque do trimestre anterior + lançamentos), a unidade de venda direta sai do estoque como vendida; (b) carteira devolvida ao estoque = mesmo numerador ÷ (estoque anterior + carteira de venda direta + lançamentos), o caso extremo em que essa unidade nunca é vendida. Vivaz: vendas 100% ÷ (estoque inicial + lançamentos), bruta.").replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
final.insert(next(i for i, s in enumerate(final) if "Cury × Vivaz" in _h2(s)) + 1, _svd)
# --- anexo · follow-up: Lei do Distrato, último slide (20/09/26); dados de grafico_distrato.py
DF = J("_distrato_frag.json"); _dn = DF["num"]
_cards = ('<div class="cards3" style="margin-top:6px;gap:12px">'
    '<div class="c3 tight2" style="font-size:11.5px"><span class="c3n" style="font-size:20px">antes · 2015-18</span><b>Jurisprudência, não lei.</b> Súmula 543 do STJ (2015): desistiu, recebe de volta, e já; retenção arbitrada pelo juiz, em regra 10% a 25% do pago. Corretagem ao comprador se informada (Tema 938). Sem tolerância em lei para atraso de obra. Na Cyrela, o distrato só entrava na conta quando acontecia: a provisão era um item de "provisões para riscos", R$ 21 mi (2015), 23 mi (2016) e 17 mi (2017).</div>'
    '<div class="c3 tight2" style="font-size:11.5px"><span class="c3n" style="font-size:20px">a lei · 13.786/2018</span><b>O que mudou.</b> Quadro-resumo no contrato (art. 35-A). Desistência: pena de até 25% do pago, <b>até 50% com patrimônio de afetação</b>, mais corretagem; devolução 30 dias após o habite-se (afetação) ou 180 dias após o desfazimento (art. 67-A); 7 dias de arrependimento no estande. Atraso: 180 dias de tolerância; depois, devolução integral em 60 dias ou 1% do pago por mês (art. 43-A).</div>'
    '<div class="c3 tight2" style="font-size:11.5px"><span class="c3n" style="font-size:20px">testada? · em parte</span><b>O STJ não fechou o teto.</b> 4ª Turma (REsp 2.159.971, 15/06/26, unânime): 50% com afetação é lícito se pactuado; reafirmado em set/26. 3ª Turma reduz judicialmente (CDC, art. 413 do CC). A 2ª Seção afetou sete recursos como repetitivos (Temas 1.464 a 1.466), sem data. Contratos pré-dez/18 seguem a súmula. Na contabilidade, o CPC 47 passou a provisionar o distrato esperado: R$ 697 mi na abertura de 2018, 26% do recebível; é o que o gráfico mede.</div></div>')
_db = ('<div class="viz" style="margin-top:6px">' + DF["svg"] + '</div>' + _cards
    + _obox(f'O pior ficou antes da lei: {fmt(_dn["pct_0118"], 0)}% do recebível provisionado na abertura de 2018, {fmt(_dn["pct_now"], 0)}% hoje.',
            f'Saldo de R$ {fmt(_dn["cy_saldo_0118"], 0)} mi (jan/18) para {fmt(_dn["cy_saldo"], 0)} mi ({_dn["q"]}) com a venda dobrando; hoje o saldo gira: R$ {fmt(_dn["cy_adic_ltm"], 0)} mi de adições e {fmt(-_dn["cy_rev_ltm"], 0)} mi de reversões em 12 meses. Follow-up: Temas 1.464-1.466 (teto de 50% com afetação; a Vivaz tem afetação em todo MCMV).'))
_dsl = sl("anexo · follow-up · Lei do Distrato", "Lei do Distrato: antes, a lei e o que o STJ já testou.", _db, cls="anexo",
    nota="Fontes: Lei 13.786/2018 (arts. 35-A, 43-A e 67-A da Lei 4.591/1964); STJ, Súmula 543 (2015) e Tema 938 (2016); REsp 2.159.971/SP (4ª Turma, 15/06/2026) e REsp 2.221.464/SP (4ª Turma, set/2026); 2ª Seção, Temas repetitivos 1.464 a 1.466 (afetados, sem mérito). Cyrela: DFP 2015-17 (provisões para riscos, 'distratos de clientes'); DFP 2018-19, ITR 1T19-3T19 e ITR 1T20-2T26 (contas a receber: provisão para distrato do CPC 47/Ofício CVM 02/2018, abertura em 01/01/2018, adições e reversões). Provisão ÷ contas a receber de vendas apropriado (consolidado). A companhia não divulga distratos em VGV, só vendas líquidas; de 1T18 a 3T18 a provisão não existia nessa forma (tracejado). Não há lei nova em 2025-26: a de 2018 está sendo interpretada."   # 21/09/26: nota encurtada de 5 para 4 linhas
    ).replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
_dsl = _dsl.replace('<div class="sl-in">', '<div class="wm-anexo" aria-hidden="true">ANEXO · FOLLOW-UP</div><div class="sl-in">', 1)
final.append(_dsl)
# --- anexo · follow-up: retomadas em SP (ITBI, resolução da alienação fiduciária), 20/09/26; dados de grafico_retomadas_itbi.py
RT = J("_retomadas_frag.json"); _rn = RT["num"]; _ra = {r["ano"][:4]: r for r in _rn["ano"]}
CX = J("_caixa_bndu_frag.json"); _cx = CX["num"]
_rb = ('<div class="viz" style="margin-top:6px">' + RT["svg"] + '</div>' + RT["table"] + '<div class="viz" style="margin-top:8px">' + CX["svg"] + '</div>'
    + _obox(f'Retomada em SP: de {fmt(_ra["2020"]["shr"], 1)}% para {fmt(_ra["2025"]["shr"], 1)}% das compras residenciais, e {fmt(_ra["2025"]["p350"], 0)}% delas até R$ 350 mil.',
            f'Média 12m: de {fmt(_rn["ret12_min"], 0)} retomadas por mês (mar/21) para {fmt(_rn["ret12"], 0)} (jul/26); leilões sobem menos ({fmt(_rn["arr12"], 0)}/mês), o estoque fica no banco: na Caixa, imóveis retomados de R$ {fmt(_cx["rec_min"] / 1000, 1)} bi (jun/22) a {fmt(_cx["rec_now"] / 1000, 1)} bi (jun/26), R$ {fmt(_cx["desp_2025"] / 1000, 1)} bi de despesa em 2025. É default do crédito bancário na baixa renda; o pró-soluto (sem alienação fiduciária) não aparece aqui, mas é o mesmo cliente.'))   # 21/09/26: apoio encurtado de 3 para 2 linhas
_rsl = sl("anexo · follow-up · retomadas em SP", "Retomadas em SP: 4x desde 2019, e cada vez mais baratas.", _rb, cls="anexo",
    nota=f"Fonte: Prefeitura de São Paulo (Fazenda), guias de ITBI pagas (dados abertos), jan/19 a jul/26, pelo mês da guia. Retomada = natureza '17. Resolução da alienação fiduciária por inadimplemento' (Lei 9.514/1997, art. 26); leilão = natureza '4. Arrematação em leilão ou hasta pública' (inclui judiciais). Residencial = usos IPTU 10 e 20. Faixa e valor médio pela base de cálculo (valor venal de referência: na retomada não há preço); razão sobre compras e vendas residenciais com 100% transmitido; só o município. Caixa: demonstrações semestrais (RI): 'ativos não financeiros mantidos para venda, recebidos' (bruto, dez/20+); jun/18 a jun/20, 'imóveis adjudicados/arrematados' da nota antiga (pontilhado; pico de R$ 9,0 bi em dez/18); provisão para desvalorização e despesa com imóveis adjudicados (1S22-1S26)."   # 21/09/26: nota encurtada de 5 para 4 linhas
    ).replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
_rsl = _rsl.replace('<div class="sl-in">', '<div class="wm-anexo" aria-hidden="true">ANEXO · FOLLOW-UP</div><div class="sl-in">', 1)
final.append(_rsl)
# --- risco de ciclo no MAP: estoque de hoje × custo a incorrer × VSO (21/09/26); dados de grafico_risco_ciclo.py
RC = J("_risco_ciclo_frag.json"); _rc = RC["num"]
_rcb = ('<div class="viz" style="margin-top:6px">' + RC["svg"] + '</div>' + RC["table"]
    + _obox(f'A obra se paga; o que trava é o pronto: R$ 1,8 a {fmt(_rc["pronto_fim_2016"] / 1000, 1)} bi sem vender em 3 anos, conforme a VSO.',
            f'O estoque MAP (R$ {fmt(_rc["e_map"] / 1000, 1)} bi a mercado, 100%) tem R$ {fmt(_rc["custo_map"] / 1000, 1)} bi de obra a pagar; com {fmt(_rc["vso_atual"], 0)}%/tri de VSO de estoque, o que vende cobre a obra (30% na obra, 70% nas chaves), mas R$ {fmt(_rc["novo_pronto_atual"] / 1000, 1)} bi chegam prontos sem dono e um quarto do que está em obra segue sem vender no ano 3. Estoque consolidado a custo, todos os segmentos: R$ {fmt(_rc["custo_investido"] / 1000, 1)} bi.'))
_rcs = sl("parte 4 · riscos · ciclo do MAP", "Risco de ciclo: com a VSO parada, o capital trava no pronto.", _rcb,
    nota=f"Fontes: Cyrela, release 2T26 (estoque a valor de mercado por segmento, em obra e pronto, 100%; cronograma do custo a incorrer das unidades em estoque, consolidado) e ITR 2T26 (estoque a custo: imóveis em construção e concluídos). Modelo: só o estoque de hoje, sem lançamentos novos; parte Cyrela = %CBR do estoque ({fmt(100 * _rc['cbr'], 0)}%); custo a incorrer do MAP = cronograma × fatia do MAP no estoque em obra ({fmt(100 * _rc['sh_ob'], 0)}%); VSO de estoque = vendas de estoque ÷ estoque inicial, todos os segmentos (média de 4 trimestres, média de 2016 e média de 2019-21); VSO anual = 1 − (1 − VSO trimestral)^4; cliente paga {fmt(100 * _rc['pago_obra'], 0)}% na obra e 70% nas chaves; entregas do estoque em obra em 30/40/30% nos anos 1-3; custo do pronto = {fmt(100 * _rc['custo_vgv'], 0)}% do VGV. Lançamentos novos e a venda direta (pró-soluto) ficam fora: os dois pioram a conta."
    ).replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
final.insert(next(i for i, s in enumerate(final) if "O risco do SBPE" in _h2(s)) + 1, _rcs)
# --- dividendos: quanto, de onde saiu o caixa e payout ajustado (21/09/26); dados de grafico_dividendos.py
DV = J("_dividendos_frag.json"); _dv = DV["num"]
_dvb = ('<div class="viz" style="margin-top:6px">' + DV["svg"] + '</div>' + DV["table"]
    + _obox(f'De 2019 a 2025, payout de {fmt(_dv["pay_tot"], 0)}%: um terço do dividendo veio de vender Cury, P&P e Lavvi.',
            f'R$ {fmt(_dv["div_tot"] / 1000, 1)} bi pagos sobre R$ {fmt(_dv["ll_tot"] / 1000, 1)} bi de lucro; R$ {fmt(_dv["part_tot"] / 1000, 1)} bi vieram das participações e R$ {fmt(_dv["oper_tot"] / 1000, 1)} bi do caixa operacional de 2020-25, o resto é dívida. Sem os ganhos com as sócias o payout é {fmt(_dv["pay_exg_tot"], 0)}%; líquido do caixa delas, {fmt(_dv["pay_liq_tot"], 0)}%. Yield de 12 meses {fmt(_dv["dy12"], 1)}%, todo do extraordinário de dez/25; o ordinário de 2025 rende ~3,5%.'))
_dvs = sl("parte 4 · lucro, caixa e payout", "Dividendo: um terço veio da venda das sócias, não do caixa.", _dvb,
    nota=f"Fontes: B3 (proventos por ação com data ex × ações ex-tesouraria: DFs e CYREMod até 2019, ITR desde 2020), por ano da data ex, conferido com '(+) dividendos' da geração de caixa dos releases (pago no trimestre); lucro atribuível aos controladores (DFs do RI); releases, geração de caixa: '(+) aquisição/venda de participação societária' (2020 IPOs de Cury, P&P e Lavvi; 2022, 2024 e 2025 ações da Cury) e 'caixa operacional' (exclui recompra e participações; desde 2020). Ganho contábil: 2020 R$ 1.335 mi (perda de controle + secundária), 2022 R$ 139 mi (3T22), 2024 ~R$ 135 mi (estimado), 2025 R$ 240 mi (3T25). 2017-18: prejuízo, sem payout. 12m = jul/25 a jun/26; yield sobre R$ {fmt(_dv['preco'], 2)} ({_dv['preco_dt'][8:]}/{_dv['preco_dt'][5:7]}/{_dv['preco_dt'][2:4]}), ajustado pela bonificação de jan/26."   # 21/09/26: nota encurtada de 5 para 4 linhas
    ).replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
final.insert(next(i for i, s in enumerate(final) if "Lucro, caixa, dívida e payout" in _h2(s)) + 1, _dvs)
# --- sócias no book: goodwill de 2020, book × mercado (21/09/26); dados de grafico_socias.py
SB = J("_socias_frag.json"); _sb_ = SB["num"]
_sbb = ('<div class="viz" style="margin-top:6px">' + SB["svg"] + '</div>' + SB["table"]
    + _obox(f'Goodwill de 2020 é R$ {fmt(_sb_["gw_tot"] / 1000, 1)} bi do PL; a fatia na P&P: R$ {fmt(_sb_["pp_book"])} mi no book, R$ {fmt(_sb_["pp_mkt"])} mi em bolsa.',
            f'Na perda de controle a Cyrela remensurou P&P e Lavvi a valor justo (R$ {fmt(_sb_["gw_2020"])} mi de goodwill em 2020, R$ {fmt(_sb_["gw_tot"])} mi hoje; sem amortização, só teste de valor em uso). A equivalência é a fatia do lucro contábil: {fmt(_sb_["roe_pp"], 0)}% de ROE na P&P viram {fmt(_sb_["ret_pp"], 0)}% sobre o book da Cyrela; na Lavvi, {fmt(_sb_["roe_lv"], 0)}% viram {fmt(_sb_["ret_lv"], 0)}%. Sem o goodwill o ROE da Cyrela sobe de {fmt(_sb_["roe_cy"], 1)}% para {fmt(_sb_["roe_ex_gw"], 1)}%; o risco é o inverso: impairment.'))
_sbs = sl("parte 4 · onde o PL está aplicado", "P&P vale em bolsa metade do book: é o goodwill de 2020.", _sbb,
    nota=f"Fontes: Cyrela, ITR 2T26, nota de investimentos (saldo por investida; goodwill de R$ 528 mi na P&P e R$ 175 mi na Lavvi, R$ 756 mi na DFP 2020, testado por valor em uso em 2025, 5 anos sem crescimento) e fatias (Cury 15,08%, Lavvi 28,36%, P&P 33,60%); CVM, ITR/DFP consolidados de Lavvi e Plano & Plano (PL dos controladores, lucro 12 meses, ações = lucro ÷ LPA); Cury: planilha Fundamentos do RI e B3 (308,0 mi de ações); B3 COTAHIST (fechamento mensal desde set/2020; valor em bolsa da fatia no último pregão disponível). Vendas de ações da Cury pela Cyrela: caixa da linha de participações dos releases (3T22, 2T24, 3T24, 3T25). Book ÷ mercado acima de 1 não obriga baixa contábil (o teste usa valor em uso), mas é o sinal que a queda de lucro da P&P em 2026 põe à prova."
    ).replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
final.insert(next(i for i, s in enumerate(final) if "Terreno a prazo, obra e recebível" in _h2(s)) + 1, _sbs)
# --- anexo · sell-side (21/09/26): modelos do Itaú BBA para Cyrela (1Q26) e Cury (2Q26); dados de grafico_sellside.py; nada entra nas séries primárias
SS = J("_sellside_frag.json"); _ss = SS["num"]
_ssb = ('<div class="viz" style="margin-top:6px">' + SS["svg"] + '</div>' + SS["table"]
    + _obox(f'Para R$ {_ss["tp"]}, os dois bancos precisam do estoque girando mais: IBBA {fmt(_ss["vso_est_30"], 0)}%, BTG {fmt(_ss["btg_vso_30"], 0)}% ao ano; hoje 38%.',
            f'Lançamento cai ({fmt(-_ss["lanc_var"], 0)}% no IBBA, {fmt(-_ss["btg_lanc_var"], 0)}% no BTG), dividendo de 2026 vai a zero ou R$ {fmt(_ss["btg_div_26"], 1)} bi, e o BTG deixa o recebível ir de R$ {fmt(_ss["btg_cr_25"], 1)} para {fmt(_ss["btg_cr_30"], 1)} bi com FCFE negativo em 2027 e ROE ex-sócias de {fmt(_ss["btg_roe_exjv"], 0)}%. Na Cury (alvos R$ {_ss["tp_cu"]} e {_ss["tp_bu"]}) ninguém modela a venda direta; o BTG põe o estoque pronto de R$ 0,06 para {fmt(_ss["bu_pronto_30"], 1)} bi em 2030.'))
_sss = sl("anexo · sell-side · Itaú BBA e BTG", "Sell-side: o que Itaú BBA e BTG assumem para Cyrela e Cury.", _ssb, cls="anexo",
    nota="Fontes: modelos distribuídos a clientes, transcritos sem ajuste (fontes/sellside/): Itaú BBA, CYRE_Model_1Q26 (25/05/26, TP R$ 35) e CURY_Model_2Q26 (TP R$ 44), abas Operating, IS, BS & FCF, Valuation e SOTP; BTG Pactual, Cyrela_Model_2Q26 (TP R$ 35; Ke 16,1%, g 4,3% no DCF e 5% no alvo por P/TBV; 'FCF build up' com LTV 50% e VSO anual 45%) e Cury_Model_2Q26_v2 (TP R$ 48; mesmo template, atribuído ao BTG pelo envio), abas Forecasts, Income Statement, Balance Sheet, Cash Flow, TP Calculation e DCF; consenso Bloomberg da Cury (telas de 21/09/26). VSO de estoque = vendas brutas de estoque ÷ estoque inicial (definição das casas). Coluna 'este deck' = slides citados, fontes primárias. Barras claras = estimativa. Este anexo existe para confronto e pode ser retirado sem afetar o resto do deck."
    ).replace('<h2 class="head-xl">', '<h2 class="head-xl" style="font-size:38px;margin-bottom:4px">', 1)
_sss = _sss.replace('<div class="sl-in">', '<div class="wm-anexo" aria-hidden="true">ANEXO · SELL-SIDE</div><div class="sl-in">', 1)
final.append(_sss)
# tag "Slide Novo" (estrela, caixa amarela, extremo direito do kick) nos slides criados em 18-19/09/26
_NOVOS = ("Lucro, caixa, dívida e payout", "Tecnisa: R$ 95 mi de equity", "Médio e alto padrão: o mercado desacelera", "MCMV: o mercado segue no recorde", "Banco a banco: a Caixa carrega", "Share no crédito habitacional sem FGTS", "Estouro no MAP", "Estouro no MCMV", "Cury × Vivaz", "tem venda direta dentro", "Receita por trimestre", "SP no mapa", "Retorno por vertical", "x book com ROE", "MAP × Vivaz por dentro", "Lei do Distrato: antes", "Retomadas em SP", "Risco de ciclo", "Dividendo: um terço", "metade do book", "Sell-side: o que Ita")
for _k, _s in enumerate(final):
    if any(n in _h2(_s) for n in _NOVOS):
        final[_k] = _s.replace('<p class="kick">', '<p class="kick"><span class="tag-novo" title="slide novo">★ Slide Novo</span>', 1)
slides = final

EXTRA_CSS = """
<style>
  .slide.teoria { background: rgba(46,125,50,.06); box-shadow: inset 0 0 0 3px rgba(46,125,50,.55); }
  .pill-teoria { display:inline-block; background:#2e7d32; color:#fff; padding:2px 10px; border-radius:999px; font-size:10.5px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; vertical-align:middle; margin-left:6px; }
  .slide.teoria .kick { color:#2e7d32; }
  .slide.destaque { background: rgba(160,125,28,.07); box-shadow: inset 0 0 0 4px #a07d1c; }
  .slide.destaque .kick { color:#a07d1c; }
  a.chip { text-decoration:none; }
  /* versão enxuta: cards um pouco mais densos para caber em 768px */
  .deck .head-xl { font-size: clamp(28px, 3.7vw, 46px); }
  .deck .fwcard dd { font-size:12.4px; line-height:1.34; }
  .deck .fwcard dt { margin-top:7px; }
  .deck .fwcard dl { padding: 4px 16px 10px; }
  .deck .fwcard header { padding: 7px 16px 6px; }
  .deck .sl-nota { font-size:11px; margin-top:5px; }
  .deck .c3 { padding: 13px 15px; font-size:12.4px; line-height:1.38; }
  .deck .c3n { font-size:23px; margin-bottom:5px; }
  .deck .cards3, .deck .fwgrid { gap: 12px; }
  .deck .head-xl { margin-bottom: 8px; }
  .deck .sl-callout p { font-size:13px; line-height:1.45; }
  .deck table.tl th, .deck table.tl td { text-align:left; }
  .deck table.tl tr.total td { font-weight:650; color:var(--ink-1); border-top:1.5px solid var(--baseline); }
  /* variantes densas (slide de teoria da receita): tabela a 10px/1.0 e cartões com menos respiro, sem tirar linha */
  .deck table.tl.compact { margin-top:0; }
  .deck table.tl.compact th, .deck table.tl.compact td { font-size:10px; line-height:1.0; padding:2px 8px; }
  .deck .fwgrid.compact .fwcard header { padding:5px 16px 4px; }
  .deck .fwgrid.compact .fwcard dl { padding:2px 16px 7px; }
  .deck .fwgrid.compact .fwcard dt { margin-top:5px; }
  .deck .fwgrid.compact .fwcard dd { line-height:1.3; }
  .deck .fwgrid.dense .fwcard dd { font-size:12px; line-height:1.3; }   /* slide 'MCMV por dentro' (19/09/26): cartões um pouco mais densos, sem tirar linha */
  .deck .cards3.tight .c3 { font-size:12px; line-height:1.32; padding:11px 13px; }   /* slide do terreno/capital de giro: três cartões densos em 4 linhas */
  .deck .cards3.tight .c3n { margin-bottom:4px; }
  .deck .slide.anexo { overflow:hidden; background:linear-gradient(180deg, rgba(197,0,62,.035), transparent 38%); }   /* anexo · follow-up: marca d'água em todo o slide */
  .deck .slide.anexo .wm-anexo { position:absolute; left:0; right:0; top:50%; transform:translateY(-50%) rotate(-24deg); text-align:center; font-family:"Fraunces", Georgia, serif; font-weight:800; font-size:100px; letter-spacing:.06em; color:rgba(197,0,62,.055); white-space:nowrap; pointer-events:none; z-index:0; }   /* 19/09/26: 150px/-16° cortava em "ANEXO · FOLLOW"; a 100px/-24° o texto inteiro atravessa o slide (~1150px na diagonal de ~1240×740) */
  .deck .slide.anexo .sl-in { position:relative; z-index:1; }
  .deck .ev3 { columns:4; column-gap:14px; font-size:10px; line-height:1.22; margin:4px 0 0; padding-left:15px; color:var(--ink-2); }   /* 19/09/26: 3 col/10,8px → 4 col/10,3px (slide 45 a 953px); textos mais longos → 10px/1,22 (slide a 774px) */
  .deck .ev3 li { break-inside:avoid; margin-bottom:2px; }
  .dots a.novo { background:#ffd54f; border-color:#d9a400; }
  .dots a.novo.on { background:var(--s1); border-color:var(--s1); }
  .deck .kick .tag-novo { float:right; background:#ffd54f; color:#2b2a26; padding:3px 10px; border-radius:6px; font-size:10.5px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; margin-left:12px; box-shadow:0 1px 2px rgba(0,0,0,.12); }
  .deck .cards3.tight2r .c3 { font-size:11.6px; line-height:1.3; padding:9px 12px; }   /* 2ª linha do slide do terreno: dois cartões dentro da altura do gráfico */
  .deck .cards3.tight2r .c3n { font-size:19px; margin-bottom:2px; }
  /* slide de teoria do caixa MAP × MCMV: premissas em texto corrido (uma linha por cartão) e cartão do retorno ao lado do gráfico */
  .deck .fwgrid.compact .fwcard p { margin:0; padding:4px 14px 7px; font-size:11.8px; line-height:1.32; color:var(--ink-1); }
  .deck .c3.tight2 { font-size:11.8px; line-height:1.32; padding:10px 13px; }
  .deck .c3.tight2 .c3n { font-size:20px; margin-bottom:3px; }
  .sl-output { display:flex; align-items:center; gap:16px; flex-wrap:wrap; margin:9px 2px 0; padding:8px 16px;
    background:rgba(46,125,50,.08); border:1px solid rgba(46,125,50,.45); border-left:5px solid #2e7d32; border-radius:12px; }
  .sl-output .out-tag { font-size:10.5px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; color:#fff; background:#2e7d32; padding:3px 10px; border-radius:999px; }
  .sl-output .out-msg { font-family:"Fraunces", Georgia, serif; font-size:20px; font-weight:650; color:#1b5e20; letter-spacing:-.005em; }
  .sl-output .out-sub { font-size:13px; color:var(--ink-2); flex:1 1 260px; }
</style>"""
out = ['<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Cyrela (CYRE3) — Versão enxuta</title>\n',
       H[H.index('<link rel="preconnect"'):H.index("<style>")], CSS, EXTRA_CSS, "\n</head>\n<body>\n<div class=\"wrap\">\n  <header class=\"top\">\n    <h1>Cyrela (CYRE3) — Versão enxuta</h1>\n",
       f'    <span class="chip">{VERSAO} · dados até 2T26 · {len(slides)} slides</span>\n    <a class="chip" href="index.html">análise completa (54 slides) →</a>\n  </header>\n\n<div class="deck" id="deck">\n\n']
_lp = os.path.join(here, "_layout_enxuta.json"); _LO = json.load(io.open(_lp, encoding="utf-8")) if os.path.exists(_lp) else {}
def _widen(m):
    svg = m.group(0); tit = re.search(r'class="gtit">([^<]*)</text>', svg); key = (tit.group(1).strip() if tit else ""); extra = _LO.get(key, 0)
    if not extra: return svg
    vb = re.search(r'viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"', svg)
    if not vb: return svg
    x0, y0, w, h_ = vb.groups(); return svg.replace(vb.group(0), f'viewBox="{x0} {y0} {float(w) + extra + 6:g} {h_}"', 1)
def _so(s):   # 19/09/26: um slide vindo de index.html trazia markup do <nav> das abas antes do <section>, e um </div> ali fechava o .deck cedo (os últimos slides caíam fora do deck)
    i = s.find('<section class="slide'); j = s.rfind('</section>')
    return s[i:j + len('</section>')] + "\n" if i >= 0 and j >= 0 else s
out += ["  " + _so(re.sub(r'<svg viewBox="[^"]+">.*?</svg>', _widen, s, flags=re.S) if id(s) in GEN_SET else s) + "\n" for s in slides]
ALIGN_JS = """
  // slides mais altos que a janela: alinhar pelo topo (o título aparece; o resto rola dentro do slide)
  (function () {
    function ajusta() {
      var deck = document.getElementById('deck'); if (!deck) return;
      deck.querySelectorAll('.slide').forEach(function (s) {
        var inn = s.querySelector('.sl-in'); if (!inn) return;
        s.style.alignItems = (inn.scrollHeight + 44 > deck.clientHeight) ? 'flex-start' : 'center';
      });
    }
    window.addEventListener('load', ajusta); window.addEventListener('resize', ajusta); setTimeout(ajusta, 900);
  })();
  // capa (21/09/26): os chips numerados viram botões que levam ao primeiro slide de cada parte (casado pelo kick "parte N")
  (function () {
    var deck = document.getElementById('deck'); if (!deck) return;
    var slides = Array.prototype.slice.call(deck.querySelectorAll('.slide'));
    function alvo(n) {
      var rx = new RegExp('^\\\\s*parte\\\\s*' + n + '\\\\b', 'i');
      for (var i = 0; i < slides.length; i++) { var k = slides[i].querySelector('.kick'); if (k && rx.test(k.textContent)) return slides[i]; }
      return null;
    }
    document.querySelectorAll('#sl0 .chip2').forEach(function (c) {
      var b = c.querySelector('b'); var n = b ? parseInt(b.textContent, 10) : NaN; var s = isNaN(n) ? null : alvo(n);
      if (!s) return;
      c.setAttribute('role', 'button'); c.setAttribute('tabindex', '0'); c.title = 'ir para a parte ' + n;
      c.addEventListener('click', function () { s.scrollIntoView({ behavior: 'smooth' }); });
      c.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); s.scrollIntoView({ behavior: 'smooth' }); } });
    });
  })();
"""
CHIP_CSS = "<style>#sl0 .chip2[role=button]{cursor:pointer;transition:background .15s,border-color .15s,transform .15s}#sl0 .chip2[role=button]:hover,#sl0 .chip2[role=button]:focus-visible{background:var(--surface-1);border-color:var(--s1);color:var(--ink-1);transform:translateY(-1px);outline:none}#sl0 .chip2[role=button]:hover b{color:var(--s1)}</style>\n"
out.append('</div>\n<div class="dots" id="dots"></div>\n' + CHIP_CSS + '<script>\n' + JS + ALIGN_JS + '</script>\n</body>\n</html>\n')
html = "".join(out)
# layout: alarga o viewBox dos svgs cujo texto saiu do quadro (medido por layout_enxuta.py em _layout_enxuta.json) — só nos slides gerados
_lp = os.path.join(here, "_layout_enxuta.json")
if os.path.exists(_lp) and False:
    _LO = json.load(io.open(_lp, encoding="utf-8"))
    def _widen(m):
        svg = m.group(0); tit = re.search(r'class="gtit">([^<]*)</text>', svg)
        key = (tit.group(1).strip() if tit else "")
        extra = _LO.get(key, 0)
        if not extra: return svg
        vb = re.search(r'viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"', svg)
        if not vb: return svg
        x0, y0, w, h_ = vb.groups()
        return svg.replace(vb.group(0), f'viewBox="{x0} {y0} {float(w) + extra + 6:g} {h_}"', 1)
    # regra do usuário (17/09/26): nenhum callout amarelo — o que sobrou dos slides reaproveitados vira caixa verde
def _to_green(m):
    tag = re.sub(r"<[^>]+>", "", m.group(1)).strip(); txt = m.group(2).strip()
    return f'<div class="sl-output"><span class="out-tag">{tag}</span><span class="out-sub">{txt}</span></div>'
html = re.sub(r'<div class="sl-callout"[^>]*>\s*<span class="ct-tag"[^>]*>(.*?)</span>\s*<p>(.*?)</p>\s*</div>', _to_green, html, flags=re.S)
io.open(os.path.join(here, "enxuta.html"), "w", encoding="utf-8").write(html)
print("enxuta.html:", len(html) // 1000, "k;", len(slides), "slides")
