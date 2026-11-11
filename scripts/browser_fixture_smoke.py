"""Demonstra o motor Playwright usando apenas HTML local, sem navegação web."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from pagecheck.acquisition.browser.visual_probe import inspect_rendered_page


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    fixture = ROOT / "tests/fixtures/pages/visual_scroll.html"
    out_dir = ROOT / "artifacts/browser_stage9"
    with sync_playwright() as p:
        options = {"headless": True}
        if os.getenv("PAGECHECK_CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["PAGECHECK_CHROMIUM_EXECUTABLE"]
        browser = p.chromium.launch(**options)
        try:
            context = browser.new_context(viewport={"width": 960, "height": 600}, service_workers="block")
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(fixture.read_text(encoding="utf-8"), wait_until="load")
            result = inspect_rendered_page(page, screenshot_dir=out_dir, settle_ms=100)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
