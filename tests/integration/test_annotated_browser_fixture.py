"""Valida imagem anotada com dados reais de uma página fixture local."""
import os
from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import sync_playwright

from pagecheck.acquisition.browser.visual_probe import inspect_rendered_page
from pagecheck.reporting.annotations.findings import build_image_findings
from pagecheck.reporting.annotations.overlay import annotate_screenshot

FIXTURE = Path(__file__).parents[1] / "fixtures/pages/visual_scroll.html"


def test_annotations_come_from_real_browser_image_positions(tmp_path):
    with sync_playwright() as driver:
        args = {"headless": True}
        if os.environ.get("PAGECHECK_CHROMIUM_EXECUTABLE"):
            args["executable_path"] = os.environ["PAGECHECK_CHROMIUM_EXECUTABLE"]
        try:
            browser = driver.chromium.launch(**args)
        except Exception as exc:
            pytest.fail(f"Chromium indisponível: execute uv run playwright install chromium. {exc}")
        try:
            context = browser.new_context(viewport={"width": 960, "height": 600}, service_workers="block")
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(FIXTURE.read_text(encoding="utf-8"), wait_until="load")
            probe = inspect_rendered_page(page, screenshot_dir=tmp_path, settle_ms=100)
        finally:
            browser.close()
    findings = build_image_findings(probe)
    assert len(findings) == 1
    assert findings[0]["element_index"] == 2
    annotated = tmp_path / "annotated.png"
    summary = annotate_screenshot(screenshot_path=probe["screenshots"]["after_scroll"],
                                  output_path=annotated, findings=findings,
                                  viewport_width=probe["viewport"]["width"],
                                  page_height=probe["page_height"])
    assert summary["annotated_count"] == 1
    with Image.open(annotated) as screenshot:
        assert screenshot.width == 960
        assert screenshot.height >= 1600
