"""Gera captura anotada de uma fixture local, sem abrir URLs externas."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from pagecheck.acquisition.browser.visual_probe import inspect_rendered_page
from pagecheck.reporting.annotations.findings import build_image_findings
from pagecheck.reporting.annotations.overlay import (
    annotate_screenshot,
    write_annotation_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    page_fixture = ROOT / "tests/fixtures/pages/visual_scroll.html"
    out_dir = ROOT / "artifacts/browser_stage10"
    with sync_playwright() as driver:
        options = {"headless": True}
        if os.getenv("PAGECHECK_CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["PAGECHECK_CHROMIUM_EXECUTABLE"]
        browser = driver.chromium.launch(**options)
        try:
            context = browser.new_context(viewport={"width": 960, "height": 600}, service_workers="block")
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(page_fixture.read_text(encoding="utf-8"), wait_until="load")
            probe = inspect_rendered_page(page, screenshot_dir=out_dir, settle_ms=100)
        finally:
            browser.close()
    findings = build_image_findings(probe)
    manifest = annotate_screenshot(
        screenshot_path=probe["screenshots"]["after_scroll"],
        output_path=out_dir / "after_scroll_annotated.png",
        findings=findings,
        viewport_width=probe["viewport"]["width"],
        page_height=probe["page_height"],
    )
    write_annotation_manifest(manifest, out_dir / "annotations.json")
    print(json.dumps({"broken_images": probe["broken_image_count"],
                      "markers": manifest["annotated_count"],
                      "annotated_image": manifest["image"]},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
