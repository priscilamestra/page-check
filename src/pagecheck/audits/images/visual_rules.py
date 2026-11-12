"""Alertas de qualidade técnica de imagens; sem reconhecimento visual por IA."""
from __future__ import annotations

import math
from typing import Any

from pagecheck.audits.layout.rules import _valid_box


def build_image_quality_findings(observation: dict[str, Any]) -> list[dict[str, Any]]:
    """Avisos de ampliação exagerada e proporções distorcidas.

    Sem dimensões intrínsecas ou se a imagem não carregou, não se conclui
    que há problema de apresentação (será tratada pelo detector de quebradas).
    """
    findings: list[dict[str, Any]] = []
    items = observation.get("measured_elements", [])
    if not isinstance(items, list):
        return findings
    for item in items:
        if not isinstance(item, dict) or item.get("kind") != "image":
            continue
        box = _valid_box(item.get("box"))
        if box is None or item.get("complete") is not True:
            continue
        try:
            nw, nh = int(item.get("natural_width", 0)), int(item.get("natural_height", 0))
        except (ValueError, TypeError, OverflowError):
            continue
        if nw <= 0 or nh <= 0:
            continue
        index = item.get("index")
        upscale = max(box["width"] / nw, box["height"] / nh)
        if math.isfinite(upscale) and upscale > 2.5:
            findings.append({
                "id": f"image-upscaled-{index}", "category": "images",
                "severity": "low", "status": "warning", "title": "Imagem ampliada além da resolução original",
                "description": f"Arquivo {nw}×{nh}px exibido a {box['width']:.0f}×{box['height']:.0f}px.",
                "action": "Revisar a resolução e a nitidez em dispositivos de alta densidade.",
                "owner": "Design / Frontend", "box": box,
            })
        ratio_delta = abs((box["width"] / box["height"]) / (nw / nh) - 1)
        if (item.get("object_fit") in ("fill", "") and
                math.isfinite(ratio_delta) and ratio_delta > .15):
            findings.append({
                "id": f"image-aspect-{index}", "category": "images",
                "severity": "medium", "status": "warning", "title": "Possível distorção de proporção da imagem",
                "description": "Proporção renderizada difere mais de 15% da proporção intrínseca.",
                "action": "Verificar width/height e object-fit; cortes intencionais não são erro.",
                "owner": "Design / Frontend", "box": box,
            })
    return findings
