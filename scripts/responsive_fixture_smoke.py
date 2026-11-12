"""Gera duas auditorias visuais (desktop e mobile), usando HTML local.

Nunca navega para URLs públicas. Todos os requests de rede são abortados.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from pagecheck.application.use_cases.audit_visual_viewport import audit_visual_viewport

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/pages/responsive_visual.html"
OUTPUT = ROOT / "artifacts/browser_stage12"


def main() -> None:
    reports = {}
    with sync_playwright() as driver:
        options = {"headless": True}
        if os.environ.get("PAGECHECK_CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["PAGECHECK_CHROMIUM_EXECUTABLE"]
        browser = driver.chromium.launch(**options)
        try:
            for key, width in (("desktop", 1280), ("mobile", 390)):
                context = browser.new_context(
                    viewport={"width": width, "height": 720},
                    device_scale_factor=1, service_workers="block",
                )
                context.route("**/*", lambda route: route.abort())
                try:
                    page = context.new_page()
                    page.set_content(FIXTURE.read_text(encoding="utf-8"), wait_until="load")
                    result = audit_visual_viewport(page, output_dir=OUTPUT / key)
                    reports[key] = {
                        "viewport": result["viewport"],
                        "document_width": result["geometry"]["document_width"],
                        "findings": [item["id"] for item in result["findings"]],
                        "annotated_image": result["screenshots"]["annotated"],
                    }
                finally:
                    context.close()
        finally:
            browser.close()
    print(json.dumps(reports, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
