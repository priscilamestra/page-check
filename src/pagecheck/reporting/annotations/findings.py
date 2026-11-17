"""Converte observações do Playwright em problemas visuais verificáveis.

Etapa 10: somente imagens comprovadamente quebradas. A entrada deve vir de
inspect_rendered_page() da Etapa 9, em uma página local controlada.
"""
from __future__ import annotations

from typing import Any


def build_image_findings(probe: dict[str, Any]) -> list[dict[str, Any]]:
    """Não classifica estados pendentes como erros nem inventa conclusões visuais."""
    result: list[dict[str, Any]] = []
    for image in probe.get("images", []):
        if image.get("status") != "broken" or not image.get("rendered", False):
            continue
        box = image.get("box")
        if not isinstance(box, dict):
            continue
        try:
            x, y = float(box["x"]), float(box["y"])
            w, h = float(box["width"]), float(box["height"])
            index = int(image["index"])
        except (TypeError, KeyError, ValueError, OverflowError):
            continue
        import math
        if not all(math.isfinite(v) for v in (x, y, w, h)) or w <= 0 or h <= 0 or index < 0:
            continue
        result.append(
            {
                "id": f"image-broken-{index}",
                "category": "images",
                "severity": "high",
                "title": "Imagem não carregou após o scroll",
                "description": "O navegador finalizou a tentativa, mas a imagem não foi decodificada.",
                "action": "Verificar o endereço, o arquivo e o carregamento da imagem.",
                "owner": "Frontend",
                "status": "failed",
                "element_index": index,
                "evidence": {
                    "src": str(image.get("src") or ""),
                    "alt": str(image.get("alt") or ""),
                    "element_index": index,
                    "tag": "img",
                },
                "box": {"x": x, "y": y, "width": w, "height": h},
            }
        )
    return sorted(result, key=lambda item: (item["box"]["y"], item["box"]["x"], item["id"]))


def build_capture_image_warnings(probe: dict[str, Any]) -> list[dict[str, Any]]:
    """Flag an image that did not display *in the restricted screenshot*.

    A pending/lazy image is a capture limitation, not a confirmed defect of
    the target website. Only visible, sourced <img> elements with a usable box
    can be marked. A successfully decoded image is never flagged.
    """
    result: list[dict[str, Any]] = []
    for image in probe.get("images", []):
        if (not isinstance(image, dict) or image.get("status") != "not_verified"
                or not image.get("rendered")
                or int(image.get("natural_width") or 0) > 0):
            continue
        box = image.get("box")
        if not isinstance(box, dict):
            continue
        try:
            import math
            coords = {key: float(box[key]) for key in ("x", "y", "width", "height")}
            index = int(image["index"])
            if not all(math.isfinite(v) for v in coords.values()):
                continue
            if coords["width"] <= 0 or coords["height"] <= 0 or index < 0:
                continue
        except (TypeError, ValueError, KeyError, OverflowError):
            continue
        finished = image.get("complete") is True
        result.append({
            "id": f"capture-image-missing-{index}", "category": "images",
            "severity": "low", "status": "warning",
            "title": "Image missing in the audit screenshot",
            "description": (
                "The visible image was not decoded in the restricted browser capture. "
                "This does not prove the live page is broken."
            ) if finished else (
                "This visible image had not finished loading when the screenshot was taken. "
                "It may depend on lazy loading or JavaScript; this does not prove a site defect."
            ),
            "action": "Check the image in a normal browser and verify its source "
                      "and lazy-loading behavior if it remains missing.",
            "owner": "Frontend / Content", "element_index": index,
            "evidence": {"src": str(image.get("src") or ""),
                         "alt": str(image.get("alt") or ""),
                         "data_src": str(image.get("data_src") or ""),
                         "capture_only": True, "finished_loading": finished},
            "box": coords,
        })
    return result
