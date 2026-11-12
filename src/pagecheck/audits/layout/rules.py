"""Regras geométricas determinísticas; não classificam gosto estético."""
from __future__ import annotations

import math
from typing import Any


def _valid_box(box: object) -> dict[str, float] | None:
    if not isinstance(box, dict):
        return None
    try:
        values = {key: float(box[key]) for key in ("x", "y", "width", "height")}
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if not all(math.isfinite(v) for v in values.values()):
        return None
    if values["width"] <= 0 or values["height"] <= 0:
        return None
    return values


def build_layout_findings(observation: dict[str, Any]) -> list[dict[str, Any]]:
    """Detecta overflow horizontal e sobreposição significativa de controles.

    Sobreposição é um aviso para revisão: nem toda sobreposição é defeito.
    """
    try:
        viewport = float(observation["viewport_width"])
        width = float(observation["document_width"])
    except (KeyError, ValueError, TypeError):
        return []
    if not (math.isfinite(viewport) and math.isfinite(width)) or viewport < 1:
        return []

    elements = observation.get("measured_elements", [])
    if not isinstance(elements, list):
        return []
    results: list[dict[str, Any]] = []
    boxes = [(item, _valid_box(item.get("box"))) for item in elements if isinstance(item, dict)]
    offenders = [(item, box) for item, box in boxes if box is not None and
                 (box["x"] + box["width"] > viewport + 2 or box["x"] < -2)]
    if width > viewport + 2:
        chosen = max(offenders, key=lambda pair: pair[1]["x"] + pair[1]["width"], default=None)
        overflow_box = chosen[1] if chosen else None
        if overflow_box is None:
            # Elementos estruturais (p.ex. div/grid) também podem gerar overflow.
            for candidate in observation.get("overflow_candidates", []):
                if isinstance(candidate, dict):
                    candidate_box = _valid_box(candidate.get("box"))
                    if candidate_box is not None:
                        overflow_box = candidate_box
                        break
        results.append({
            "id": "layout-horizontal-overflow", "category": "layout", "severity": "medium",
            "status": "failed", "title": "Conteúdo excede a largura da tela",
            "description": f"Documento com {width:.0f}px em uma viewport de {viewport:.0f}px.",
            "action": "Revisar largura fixa, flex/grid, padding e elementos fora da viewport.",
            "owner": "Frontend", "box": overflow_box,
        })
    for item, box in offenders[:4]:
        if item.get("kind") != "control":
            continue
        results.append({
            "id": f"layout-control-offscreen-{item.get('index')}",
            "category": "layout", "severity": "medium", "status": "warning",
            "title": "Controle fora da área visível horizontal",
            "description": f"Elemento {item.get('tag', 'controle')} não cabe na viewport.",
            "action": "Revisar a posição do CTA/campo no tamanho de tela testado.",
            "owner": "Frontend", "box": box,
        })

    controls = [(item, box) for item, box in boxes if item.get("kind") == "control" and box]
    overlap_count = 0
    for idx, (first, a) in enumerate(controls):
        for second, b in controls[idx + 1:]:
            ix = min(a["x"] + a["width"], b["x"] + b["width"]) - max(a["x"], b["x"])
            iy = min(a["y"] + a["height"], b["y"] + b["height"]) - max(a["y"], b["y"])
            if ix < 10 or iy < 10:
                continue
            shared = ix * iy
            if shared < .25 * min(a["width"] * a["height"], b["width"] * b["height"]):
                continue
            results.append({
                "id": f"layout-overlap-{first.get('index')}-{second.get('index')}",
                "category": "layout", "severity": "low", "status": "warning",
                "title": "Possível sobreposição entre controles",
                "description": "Duas áreas interativas ocupam parte significativa da mesma região.",
                "action": "Revisar se a sobreposição é intencional nos tamanhos de tela afetados.",
                "owner": "Design / Frontend", "box": a,
            })
            overlap_count += 1
            if overlap_count >= 5:
                break
        if overlap_count >= 5:
            break
    return results
