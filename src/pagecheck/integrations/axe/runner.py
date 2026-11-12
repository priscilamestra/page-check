"""Executa axe-core somente em uma página Playwright já aberta."""
from __future__ import annotations

from pathlib import Path

from pagecheck.integrations.axe.adapter import normalize_axe
from pagecheck.integrations.engine_result import unavailable


def run_axe_on_page(page, *, project_root: Path) -> dict:
    js_path = project_root.resolve() / "node_modules" / "axe-core" / "axe.min.js"
    if not js_path.is_file():
        return unavailable("axe", "Instale axe-core localmente com npm install.")
    try:
        page.add_script_tag(path=str(js_path))
        raw = page.evaluate("async () => await window.axe.run(document)")
        return normalize_axe(raw)
    except Exception as exc:
        # O modo offline é um diagnóstico: um engine que falha nunca vira aprovado.
        return unavailable("axe", f"Não foi possível executar axe: {type(exc).__name__}")
