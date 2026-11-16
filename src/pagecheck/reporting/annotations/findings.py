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
