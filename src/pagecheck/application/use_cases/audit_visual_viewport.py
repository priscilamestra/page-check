"""Coordena auditoria visual de uma Page PREPARADA pelo chamador.

Não abre URLs e não altera políticas de rede. A coleta segura do navegador
é responsabilidade de acquisition/browser e da camada de execução.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from PIL import Image
from playwright.sync_api import Page

from pagecheck.acquisition.browser.visual_probe import inspect_rendered_page
from pagecheck.acquisition.browser.visual_hierarchy import inspect_heading_hierarchy
from pagecheck.acquisition.browser.layout_probe import collect_layout_observations
from pagecheck.audits.images.visual_rules import build_image_quality_findings
from pagecheck.audits.layout.rules import build_layout_findings
from pagecheck.reporting.annotations.findings import (build_image_findings,
    build_capture_image_warnings)
from pagecheck.reporting.annotations.overlay import annotate_screenshot, write_annotation_manifest


def audit_visual_viewport(
    page: Page, *, output_dir: Path | str,
    blocked_urls: Callable[[], set[str]] | None = None,
    include_rendering_hints: bool = False,
) -> dict[str, Any]:
    """Produz screenshot, evidências geométricas e marcadores por viewport.

    Para capturas full-page com overflow horizontal, o PNG pode ser mais
    largo que a viewport. As coordenadas de referência usam a largura real
    da imagem (DPR=1) para que as caixas sejam posicionadas corretamente.
    """
    directory = Path(output_dir)
    visual = inspect_rendered_page(page, screenshot_dir=directory)
    # Routes denied by our browser policy are not evidence that the origin site
    # serves a broken image. Downgrade those images BEFORE making annotations.
    blocked = blocked_urls() if blocked_urls is not None else set()
    for image in visual["images"]:
        if image.get("src") in blocked:
            image["status"] = "not_verified"
            image["loaded_after_scroll"] = False
    visual["broken_image_count"] = sum(i["status"] == "broken" for i in visual["images"])
    visual["not_verified_image_count"] = sum(
        i["status"] == "not_verified" for i in visual["images"]
    )
    layout = collect_layout_observations(page)
    # The scanner has scrolled to the bottom. Inspect the first visible screen
    # so heading boxes match document coordinates in the full-page screenshot.
    try:
        page.evaluate("() => window.scrollTo(0, 0)")
    except (TypeError, ValueError, AttributeError):
        pass
    try:
        hierarchy = inspect_heading_hierarchy(page)
    except (TypeError, ValueError, AttributeError):
        hierarchy = {"status": "not_verified", "headings_checked": 0, "findings": []}
    layout_findings = build_layout_findings(layout)
    findings = (build_image_findings(visual) +
                (build_capture_image_warnings(visual) if include_rendering_hints else []) +
                build_image_quality_findings(layout) +
                layout_findings + hierarchy["findings"])
    design_status = "needs_review" if layout_findings or hierarchy["findings"] else hierarchy["status"]
    findings.sort(key=lambda x: (float((x.get("box") or {}).get("y", 1e10)), x["id"]))

    screenshot = visual["screenshots"]["after_scroll"]
    with Image.open(screenshot) as image:
        screenshot_width = image.width
    target = directory / "after_scroll_annotated.png"
    # Um elemento pode ter dois alertas (resolução e proporção). Evita
    # desenhar etiquetas sobrepostas no mesmo retângulo, preservando
    # todos os achados no manifesto para consulta posterior.
    by_region: dict[tuple[float, float, float, float], list[dict[str, Any]]] = {}
    for item in findings:
        box = item.get("box")
        if not isinstance(box, dict):
            continue
        key = tuple(round(float(box[k]), 1) for k in ("x", "y", "width", "height"))
        by_region.setdefault(key, []).append(item)
    representatives = [group[0] for group in by_region.values()]
    annotation = annotate_screenshot(
        screenshot_path=screenshot, output_path=target, findings=representatives,
        viewport_width=screenshot_width, page_height=visual["page_height"],
    )
    marker_groups = [
        {"finding_id": group[0]["id"], "related_ids": [f["id"] for f in group]}
        for group in by_region.values()
    ]
    manifest_path = directory / "annotations.json"
    write_annotation_manifest({**annotation, "marker_groups": marker_groups,
                               "findings": findings}, manifest_path)
    return {
        "viewport": visual["viewport"], "scroll_complete": visual["scroll_complete"],
        "geometry": {"document_width": layout["document_width"],
                     "document_height": layout["document_height"],
                     "truncated": layout["truncated"]},
        "images": {"total": visual["image_count"],
                   "broken": visual["broken_image_count"],
                   "not_verified": visual["not_verified_image_count"]},
        "findings": findings,
        "design_review": {"status": design_status,
                          "headings_checked": hierarchy["headings_checked"],
                          "layout_findings": len(layout_findings),
                          "scope": "visible headings + page geometry"},
        "screenshots": {**visual["screenshots"], "annotated": str(target)},
        "manifest": str(manifest_path),
        "annotated_count": annotation["annotated_count"],
    }
