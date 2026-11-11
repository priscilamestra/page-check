from pathlib import Path
import os

import pytest
from playwright.sync_api import sync_playwright

from pagecheck.acquisition.browser.visual_probe import inspect_rendered_page


FIXTURE = Path(__file__).parents[1] / "fixtures/pages/visual_scroll.html"


def test_real_browser_scroll_images_and_screenshots(tmp_path):
    with sync_playwright() as playwright:
        launch_options = {"headless": True}
        if os.environ.get("PAGECHECK_CHROMIUM_EXECUTABLE"):
            launch_options["executable_path"] = os.environ["PAGECHECK_CHROMIUM_EXECUTABLE"]
        try:
            browser = playwright.chromium.launch(**launch_options)
        except Exception as exc:
            pytest.fail(f"Chromium indisponível. Execute 'uv run playwright install chromium'. Detalhes: {exc}")
        try:
            context = browser.new_context(viewport={"width": 900, "height": 500}, service_workers="block")
            # A fixture utiliza somente data: URLs; qualquer solicitação HTTP(S) é bloqueada.
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_content(FIXTURE.read_text(encoding="utf-8"), wait_until="load")
            result = inspect_rendered_page(page, screenshot_dir=tmp_path, step_px=350, settle_ms=90)
            assert result["scroll_complete"] is True
            assert result["scroll_steps"] >= 2
            assert result["image_count"] == 3
            assert result["broken_image_count"] == 1
            assert result["images"][1]["declared_lazy"] is True
            assert result["images"][1]["loaded_after_scroll"] is True
            assert Path(result["screenshots"]["initial"]).is_file()
            assert Path(result["screenshots"]["after_scroll"]).stat().st_size > 0
        finally:
            browser.close()
