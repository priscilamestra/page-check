"""Coleta geometria de um DOM já carregado, sem navegar ou alterar a página.

Não testa estética subjetiva. A página deve ser criada por uma rotina de
navegação isolada e segura ou por fixtures locais.
"""
from __future__ import annotations

from typing import Any

from playwright.sync_api import Page


_LAYOUT_SCRIPT = r"""(limit) => {
  const de = document.documentElement;
  const body = document.body;
  const viewportWidth = window.innerWidth;
  const documentWidth = Math.max(de.scrollWidth, body ? body.scrollWidth : 0);
  const nodes = Array.from(document.querySelectorAll('a, button, input, select, textarea, [role="button"], img'));
  const output = [];
  let visibleCount = 0;
  for (let index = 0; index < nodes.length; index++) {
    const el = nodes[index];
    const box = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' ||
        box.width <= 0 || box.height <= 0) continue;
    visibleCount++;
    if (output.length >= limit) continue;
    const tag = el.tagName.toLowerCase();
    const isImage = tag === 'img';
    const kind = isImage ? 'image' : 'control';
    const item = {
      index, tag, kind, role: el.getAttribute('role'),
      label: isImage ? (el.getAttribute('alt') || '').slice(0, 80) :
        (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 80),
      box: {x: box.x + window.scrollX, y: box.y + window.scrollY,
            width: box.width, height: box.height},
    };
    if (isImage) {
      item.natural_width = el.naturalWidth;
      item.natural_height = el.naturalHeight;
      item.complete = el.complete;
      item.has_source = !!(el.currentSrc || el.getAttribute('src'));
      item.object_fit = style.objectFit;
    }
    output.push(item);
  }
  // Procura fontes de overflow mesmo que não sejam imagens/controles.
  // Um <div> com largura fixa pode criar o defeito sem conter um CTA.
  const overflowCandidates = [];
  for (const el of document.querySelectorAll('body *')) {
    if (overflowCandidates.length >= 30) break;
    const box = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden' ||
        box.width < 1 || box.height < 1) continue;
    if (box.left >= -2 && box.right <= viewportWidth + 2) continue;
    overflowCandidates.push({
      tag: el.tagName.toLowerCase(),
      box: {x: box.x + window.scrollX, y: box.y + window.scrollY,
            width: box.width, height: box.height}
    });
  }
  return {
    viewport_width: viewportWidth,
    document_width: documentWidth,
    document_height: Math.max(de.scrollHeight, body ? body.scrollHeight : 0),
    measured_elements: output,
    overflow_candidates: overflowCandidates,
    visible_elements: visibleCount,
    truncated: visibleCount > limit,
  };
}"""


def collect_layout_observations(page: Page, *, max_elements: int = 200) -> dict[str, Any]:
    """Inspeciona caixas de controles e imagens após o scroll.

    Evita coletar valores de campos de formulário e conteúdo completo da página.
    Se atingir o limite, o resultado sinaliza cobertura parcial.
    """
    if not 1 <= max_elements <= 500:
        raise ValueError("max_elements fora do limite de 1 a 500")
    return page.evaluate(_LAYOUT_SCRIPT, max_elements)
