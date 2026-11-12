"""Prova de integração local: desktop/mobile, qualidade visual, imagens e screenshot."""
from pathlib import Path
import os

from PIL import Image
from playwright.sync_api import sync_playwright

from pagecheck.application.use_cases.audit_visual_viewport import audit_visual_viewport

FIXTURE = Path(__file__).parents[1] / "fixtures/pages/responsive_visual.html"


def test_desktop_mobile_evidence_without_network(tmp_path):
    with sync_playwright() as pw:
        options = {"headless": True}
        if os.environ.get("PAGECHECK_CHROMIUM_EXECUTABLE"):
            options["executable_path"] = os.environ["PAGECHECK_CHROMIUM_EXECUTABLE"]
        browser = pw.chromium.launch(**options)
        reports = {}
        try:
            for name, width in (("desktop", 1280), ("mobile", 390)):
                context = browser.new_context(
                    viewport={"width": width, "height": 720},
                    device_scale_factor=1, service_workers="block",
                )
                context.route("**/*", lambda route: route.abort())
                try:
                    page = context.new_page()
                    page.set_content(FIXTURE.read_text(encoding="utf-8"), wait_until="load")
                    reports[name] = audit_visual_viewport(page, output_dir=tmp_path / name)
                finally:
                    context.close()
        finally:
            browser.close()

    desk_ids = {f["id"] for f in reports["desktop"]["findings"]}
    mobile_ids = {f["id"] for f in reports["mobile"]["findings"]}
    assert "layout-horizontal-overflow" not in desk_ids
    assert "layout-horizontal-overflow" in mobile_ids
    assert any(item.startswith("layout-overlap") for item in mobile_ids)
    assert not any(item.startswith("layout-overlap") for item in desk_ids)
    assert any(item.startswith("image-upscaled") for item in desk_ids)
    assert any(item.startswith("image-broken") for item in mobile_ids)
    for report in reports.values():
        assert report["annotated_count"] > 0
        assert Path(report["manifest"]).is_file()
        assert report["scroll_complete"] is True
        assert report["geometry"]["truncated"] is False
        with Image.open(report["screenshots"]["annotated"]) as im:
            assert im.height > 1000
