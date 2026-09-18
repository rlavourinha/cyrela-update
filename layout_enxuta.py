# -*- coding: utf-8 -*-
"""Checagem de layout da versão enxuta (Playwright/Chromium headless): para cada <svg> de cada
slide, mede os <text> que saem do retângulo do svg (clipados à direita/esquerda) e grava
_layout_enxuta.json = {gtit_do_svg: folga_em_unidades_de_viewBox}. O build_enxuta.py lê esse
arquivo e alarga o viewBox dos svgs listados (o conteúdo encolhe um pouco e o rótulo cabe).
Uso: python layout_enxuta.py  (roda contra enxuta.html já gerado; imprime o relatório)."""
import io, json, os, functools, threading, socketserver, http.server
from playwright.sync_api import sync_playwright
here = os.path.dirname(os.path.abspath(__file__)); PORT = 8798
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=here)
class Q(socketserver.TCPServer): allow_reuse_address = True
srv = Q(("127.0.0.1", PORT), Handler); threading.Thread(target=srv.serve_forever, daemon=True).start()
JS = r"""
() => {
  const out = [];
  document.querySelectorAll('.deck .slide').forEach((sec, si) => {
    sec.classList.add('vis');
    sec.querySelectorAll('svg').forEach((svg, k) => {
      const sr = svg.getBoundingClientRect(); if (sr.width === 0) return;
      const vb = (svg.getAttribute('viewBox') || '0 0 0 0').split(/\s+/).map(Number); const scale = vb[2] / sr.width;
      const tit = (svg.querySelector('.gtit') || {}).textContent || '';
      let right = 0, left = 0, ex = [];
      svg.querySelectorAll('text').forEach(t => {
        const r = t.getBoundingClientRect(); if (r.width === 0) return;
        const dr = r.right - sr.right, dl = sr.left - r.left;
        if (dr > 1) { right = Math.max(right, dr); ex.push(t.textContent.trim().slice(0, 40)); }
        if (dl > 1) { left = Math.max(left, dl); ex.push('<' + t.textContent.trim().slice(0, 40)); }
      });
      if (right > 0 || left > 0) out.push({slide: si + 1, svg: k, gtit: tit.trim(), right_units: Math.ceil(right * scale), left_units: Math.ceil(left * scale), vb: vb, textos: ex.slice(0, 6)});
    });
  });
  const tall = [];
  document.querySelectorAll('.deck .slide').forEach((sec, si) => { const inn = sec.querySelector('.sl-in'); if (inn && inn.scrollHeight + 42 > 682) tall.push((si + 1) + ':' + (inn.scrollHeight + 42)); });
  out.push({tall: tall});
  return out;
}"""
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1280, "height": 768})
    pg.goto(f"http://127.0.0.1:{PORT}/enxuta.html"); pg.wait_for_timeout(1500)
    rep = pg.evaluate(JS); b.close()
srv.shutdown()
prev = {}
pj = os.path.join(here, "_layout_enxuta.json")
if os.path.exists(pj): prev = json.load(io.open(pj, encoding="utf-8"))
tall = [r for r in rep if "tall" in r]; rep = [r for r in rep if "tall" not in r]
if tall: print("slides acima de 682px (rolam dentro do slide):", tall[0]["tall"])
for r in rep:
    key = r["gtit"] or f"slide{r['slide']}svg{r['svg']}"
    prev[key] = max(prev.get(key, 0), r["right_units"] + r["left_units"])
    print(f"slide {r['slide']:2d} svg {r['svg']} | {r['gtit'][:50]!r} | direita +{r['right_units']} esquerda +{r['left_units']} | {r['textos']}")
json.dump(prev, io.open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("svgs com texto clipado:", len(rep), "| acumulado em _layout_enxuta.json:", len(prev))
