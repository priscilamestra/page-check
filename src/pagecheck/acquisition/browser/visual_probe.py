"""Inspeção VISUAL de uma Page já aberta; não navega nem faz requisições.

Etapa 9: usar APENAS páginas locais controladas. Navegação de URLs públicas
fica bloqueada até existir política de rede isolada para Chromium.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from playwright.sync_api import Page


def scroll_positions(page_height: int, viewport_height: int, step_px: int) -> list[int]:
    """Retorna offsets progressivos, incluindo o fim da página."""
    if page_height < 0 or viewport_height < 1 or step_px < 1:
        raise ValueError("Dimensões e passo de scroll devem ser positivos.")
    last = max(0, page_height - viewport_height)
    if last == 0:
        return [0]
    positions = list(range(0, last + 1, step_px))
    if positions[-1] != last:
        positions.append(last)
    return positions


def image_status(*, has_source: bool, complete: bool, natural_width: int) -> str:
    """Não confunde falha comprovada com recurso ainda pendente."""
    if not has_source:
        return "not_verified"
    if complete and natural_width > 0:
        return "loaded"
    if complete and natural_width == 0:
        return "broken"
    return "not_verified"


_IMAGE_SCRIPT = """() => Array.from(document.images).map((img, index) => {
    const rect = img.getBoundingClientRect();
    const style = getComputedStyle(img);
    return {
        index,
        src: img.currentSrc || img.src || null,
        data_src: img.getAttribute('data-src'),
        alt: img.getAttribute('alt'),
        loading: img.getAttribute('loading'),
        complete: img.complete,
        natural_width: img.naturalWidth,
        rendered: style.display !== 'none' && style.visibility !== 'hidden'
            && rect.width > 0 && rect.height > 0,
        box: {x: Math.round(rect.x + window.scrollX),
              y: Math.round(rect.y + window.scrollY),
              width: Math.round(rect.width), height: Math.round(rect.height)}
    };
})"""


def inspect_visible_images(page: Page) -> list[dict[str, Any]]:
    """Inspect only images intersecting the currently visible browser viewport.

    Useful when a full-page capture is too large to process safely. It does not
    scroll or claim coverage of elements outside the initial viewport.
    """
    vp = getattr(page, "viewport_size", None) or {"width": 1280, "height": 720}
    width, height = int(vp["width"]), int(vp["height"])
    records = page.evaluate(_IMAGE_SCRIPT)
    if not isinstance(records, list):
        raise TypeError("The document did not return image inspection records.")
    visible: list[dict[str, Any]] = []
    for image in records:
        if not isinstance(image, dict) or not image.get("rendered"):
            continue
        box = image.get("box")
        if not isinstance(box, dict):
            continue
        try:
            x, y = float(box["x"]), float(box["y"])
            w, h = float(box["width"]), float(box["height"])
            index = int(image["index"])
        except (TypeError, ValueError, KeyError, OverflowError):
            continue
        if not (w > 0 and h > 0 and x < width and y < height and x + w > 0 and y + h > 0):
            continue
        # Document coordinates are screenshot coordinates at scrollY=0, but
        # only the intersection with the initial viewport may be annotated.
        left, top = max(0.0, x), max(0.0, y)
        right, bottom = min(float(width), x + w), min(float(height), y + h)
        status = image_status(
            has_source=bool(image.get("src")),
            complete=bool(image.get("complete")),
            natural_width=int(image.get("natural_width") or 0),
        )
        visible.append({
            "index": index, "src": image.get("src"),
            "data_src": image.get("data_src"), "alt": image.get("alt"),
            "complete": bool(image.get("complete")),
            "natural_width": int(image.get("natural_width") or 0),
            "status": status, "rendered": True,
            "box": {"x": left, "y": top, "width": right - left,
                    "height": bottom - top},
        })
    return visible


def inspect_rendered_page(
    page: Page,
    *,
    screenshot_dir: Path | str,
    step_px: int = 450,
    max_scroll_steps: int = 40,
    settle_ms: int = 100,
) -> dict[str, Any]:
    """Captura viewport inicial, rola a página e registra imagem inteira e observações.

    Recebe uma Page PREPARADA pelo chamador; não abre URLs, não clica nem
    submete formulários. Etapa 9 deve ser usada apenas com fixtures locais.
    """
    if max_scroll_steps < 1 or max_scroll_steps > 100 or settle_ms < 0 or settle_ms > 2000:
        raise ValueError("Limites de scroll/espera inválidos.")
    out_dir = Path(screenshot_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    initial_path = out_dir / "initial_viewport.png"
    final_path = out_dir / "after_scroll_full.png"

    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(settle_ms)
    before = page.evaluate(_IMAGE_SCRIPT)
    page.screenshot(path=str(initial_path), full_page=False)

    vp = page.viewport_size or {"width": 1280, "height": 720}
    page_height = int(page.evaluate("() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"))
    planned = scroll_positions(page_height, int(vp["height"]), step_px)
    positions = planned[:max_scroll_steps]
    for y in positions:
        page.evaluate("y => window.scrollTo(0, y)", y)
        page.wait_for_timeout(settle_ms)

    after = page.evaluate(_IMAGE_SCRIPT)
    page.screenshot(path=str(final_path), full_page=True)
    images = []
    for img in after:
        initial = before[img["index"]] if img["index"] < len(before) else None
        status = image_status(
            has_source=bool(img["src"]),
            complete=bool(img["complete"]),
            natural_width=int(img["natural_width"]),
        )
        images.append(
            {
                "index": img["index"],
                "src": img["src"],
                "data_src": img["data_src"],
                "alt": img["alt"],
                "declared_lazy": img["loading"] == "lazy",
                "loaded_before_scroll": bool(initial and initial["complete"] and initial["natural_width"] > 0),
                "loaded_after_scroll": status == "loaded",
                "status": status,
                "complete": bool(img["complete"]),
                "natural_width": int(img["natural_width"]),
                "rendered": img["rendered"],
                "box": img["box"],
            }
        )

    return {
        "viewport": {"width": int(vp["width"]), "height": int(vp["height"])},
        "page_height": page_height,
        "scroll_steps": len(positions),
        "scroll_complete": len(positions) == len(planned),
        "screenshots": {"initial": str(initial_path), "after_scroll": str(final_path)},
        "image_count": len(images),
        "broken_image_count": sum(item["status"] == "broken" for item in images),
        "not_verified_image_count": sum(item["status"] == "not_verified" for item in images),
        "images": images,
    }
