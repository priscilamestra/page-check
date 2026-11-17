"""Desenha marcações numeradas em uma captura real, sem alterar o original."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from pagecheck.reporting.annotations.marker_style import marker_color, finding_category


class AnnotationError(ValueError):
    """A evidência não pode ser representada nas dimensões fornecidas."""


def annotate_screenshot(
    *,
    screenshot_path: str | Path,
    output_path: str | Path,
    findings: list[dict[str, Any]],
    viewport_width: int,
    page_height: int,
) -> dict[str, Any]:
    """Desenha caixas em coordenadas de documento (CSS pixels).

    A escala é inferida das dimensões capturadas e validadas; não confunde
    posição na viewport com posição absoluta depois do scroll.
    """
    source = Path(screenshot_path)
    target = Path(output_path)
    if source.resolve() == target.resolve():
        raise AnnotationError("A captura original deve ser preservada.")
    if viewport_width < 1 or page_height < 1:
        raise AnnotationError("Dimensões de referência inválidas.")

    with Image.open(source) as opened:
        image = opened.convert("RGB")
    width, height = image.size
    scale_x = width / viewport_width
    scale_y = height / page_height
    if not (0.9 <= scale_x <= 3.1 and 0.9 <= scale_y <= 3.1):
        raise AnnotationError("Escala da captura incompatível com o documento.")
    if abs(scale_x - scale_y) > 0.08:
        raise AnnotationError("Captura com escalas divergentes; marcações não confiáveis.")

    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    marks: list[dict[str, Any]] = []
    for item in findings:
        box = item.get("box") or {}
        try:
            x = float(box["x"]) * scale_x
            y = float(box["y"]) * scale_y
            w = float(box["width"]) * scale_x
            h = float(box["height"]) * scale_y
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
        if not all(math.isfinite(v) for v in (x, y, w, h)) or w <= 0 or h <= 0:
            continue
        x1 = max(0, int(round(x)))
        y1 = max(0, int(round(y)))
        x2 = min(width - 1, int(round(x + w)))
        y2 = min(height - 1, int(round(y + h)))
        if x2 <= x1 or y2 <= y1:
            continue
        number = len(marks) + 1
        # Stable category colors match the category labels in Screenshots.
        # Red remains reserved for confirmed failures.
        hex_color = marker_color(item)
        mark_color = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
        draw.rectangle((x1, y1, x2, y2), outline=mark_color, width=3)
        label = str(number)
        text_box = draw.textbbox((0, 0), label, font=font)
        text_w, text_h = text_box[2] - text_box[0], text_box[3] - text_box[1]
        badge_w, badge_h = max(23, text_w + 12), max(23, text_h + 10)
        left = min(max(0, x1), max(0, width - badge_w))
        top = max(0, y1 - badge_h - 2)
        draw.rounded_rectangle((left, top, left + badge_w - 1, top + badge_h - 1),
                               radius=5, fill=mark_color)
        draw.text((left + (badge_w - text_w) // 2, top + (badge_h - text_h) // 2 - text_box[1]),
                  label, font=font, fill=(255, 255, 255))
        marks.append({"number": number, "finding_id": item["id"],
                      "title": item.get("title", "Problema visual"),
                      "severity": item.get("severity", "warning"),
                      "owner": item.get("owner", "Revisão"),
                      "category": finding_category(item), "color": hex_color,
                      "box_pixels": {"x": x1, "y": y1, "width": x2-x1, "height": y2-y1}})

    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, format="PNG")
    return {"image": str(target), "width": width, "height": height,
            "annotated_count": len(marks), "markers": marks}


def write_annotation_manifest(manifest: dict[str, Any], destination: str | Path) -> None:
    """Exporta marcadores em JSON para o relatório Streamlit posterior."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def link_marker_numbers(findings: list[dict[str, Any]], annotation: dict[str, Any],
                        groups: list[list[dict[str, Any]]] | None = None) -> None:
    """Attach actual screenshot marker IDs to their findings for API/report consumers.

    Findings whose boxes are outside the captured image receive no number.
    A single marker may describe multiple findings at the same location.
    """
    marker_by_id = {mark["finding_id"]: mark for mark in annotation.get("markers", [])}
    number_by_id = {key: mark["number"] for key, mark in marker_by_id.items()}
    color_by_id = {key: mark.get("color") for key, mark in marker_by_id.items()}
    if groups:
        for group in groups:
            if group and group[0].get("id") in number_by_id:
                for finding in group:
                    number_by_id[finding["id"]] = number_by_id[group[0]["id"]]
                    color_by_id[finding["id"]] = color_by_id[group[0]["id"]]
    for finding in findings:
        number = number_by_id.get(finding.get("id"))
        if number is None:
            continue
        evidence = finding.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}
            finding["evidence"] = evidence
        evidence["marker_number"] = number
        if color_by_id.get(finding.get("id")):
            evidence["marker_color"] = color_by_id[finding["id"]]
