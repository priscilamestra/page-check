"""Regressions: show evidence without treating a restricted capture as a live defect."""
from pathlib import Path

from PIL import Image

from pagecheck.acquisition.browser.visual_hierarchy import assess_heading_hierarchy
from pagecheck.application.use_cases.collect_public_visuals import capture_with_browser
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.reporting.annotations.findings import build_capture_image_warnings
from pagecheck.reporting.annotations.overlay import annotate_screenshot
from pagecheck.ui.components.visual_explorer import visual_observations


def heading(level, font_px, y):
    return {"level": level, "font_px": font_px, "text": f"Heading {level}",
            "box": {"x": 20, "y": y, "width": 180, "height": 30}}


def test_design_hierarchy_reports_real_heading_scale_mismatch():
    result = assess_heading_hierarchy({"headings": [heading(1, 18, 10), heading(2, 35, 70)]})
    assert result["status"] == "needs_review"
    assert result["findings"][0]["id"] == "design-heading-size"
    assert result["findings"][0]["box"]["y"] == 70


def test_design_hierarchy_positive_status_requires_multiple_levels():
    assert assess_heading_hierarchy({"headings": [heading(1, 32, 10)]})["status"] == "limited"
    assert assess_heading_hierarchy({"headings": [heading(1, 36, 10), heading(2, 22, 60)]})["status"] == "no_measured_findings"
    assert assess_heading_hierarchy({"headings": []})["status"] == "not_verified"


def test_unverified_image_becomes_capture_only_warning():
    images = [{"index": 1, "src": "https://example.org/image.png", "alt": "Product", "rendered": True,
               "complete": True, "natural_width": 0, "status": "not_verified",
               "box": {"x": 10, "y": 20, "width": 60, "height": 40}}]
    findings = build_capture_image_warnings({"images": images})
    assert len(findings) == 1
    assert findings[0]["status"] == "warning"
    assert findings[0]["evidence"]["capture_only"] is True
    pending = build_capture_image_warnings({"images": [{**images[0], "complete": False}]})
    assert len(pending) == 1
    assert pending[0]["status"] == "warning"
    assert pending[0]["evidence"]["finished_loading"] is False


def test_annotation_warning_uses_box_and_preserves_original(tmp_path):
    original, annotated = tmp_path / "original.png", tmp_path / "annotated.png"
    Image.new("RGB", (390, 720), "white").save(original)
    finding = build_capture_image_warnings({"images": [{"index": 0, "rendered": True,
        "status": "not_verified", "complete": True, "natural_width": 0,
        "box": {"x": 20, "y": 40, "width": 100, "height": 60}}]})[0]
    result = annotate_screenshot(screenshot_path=original, output_path=annotated,
                                 findings=[finding], viewport_width=390, page_height=720)
    assert result["annotated_count"] == 1
    assert original.read_bytes() != annotated.read_bytes()


def test_design_review_preserved_in_report():
    report = consolidate_audit(requested_url="https://example.org", final_url="https://example.org",
        niche="Tech", objective="leads", visuals={"desktop": {"findings": [], "screenshots": {},
            "design_review": {"status": "limited", "headings_checked": 1, "scope": "first viewport"},
            "scroll_complete": False}})
    assert report["design_reviews"]["desktop"]["status"] == "limited"


def test_real_collector_option_marks_blocked_visible_image_without_claiming_live_failure(tmp_path):
    from unittest.mock import patch
    from pagecheck.acquisition.browser.public_navigation import NavigationReport

    class Response:
        ok = True

    class Page:
        viewport_size = {"width": 390, "height": 720}
        def goto(self, *_args, **_kwargs):
            return Response()
        def evaluate(self, script):
            if "Math.max(document.body.scrollHeight" in script:
                return 9001
            if "document.images" in script:
                return [{"index": 0, "src": "https://example.org/logo.png", "alt": "Logo",
                    "complete": True, "natural_width": 0, "rendered": True,
                    "box": {"x": 12, "y": 15, "width": 80, "height": 40}}]
            return {"headings": [heading(1, 31, 90), heading(2, 24, 140)]}
        def screenshot(self, *, path, **_kwargs):
            Image.new("RGB", (390, 720), "white").save(path)

    class Context:
        def route(self, *_a, **_kw):
            return None
        def route_web_socket(self, *_a, **_kw):
            return None
        def new_page(self):
            return Page()
        def close(self):
            return None

    class Browser:
        def new_context(self, **_kwargs):
            return Context()

    report = NavigationReport(blocked=[{"url": "https://example.org/logo.png", "reason": "safe policy"}])
    with patch("pagecheck.application.use_cases.collect_public_visuals.install_guarded_routes",
               return_value=report):
        data = capture_with_browser(Browser(), url="https://example.org", output_dir=tmp_path,
                                    include_rendering_hints=True)
    for visual in data["visuals"].values():
        assert visual["findings"][0]["status"] == "warning"
        assert visual["findings"][0]["evidence"]["capture_only"] is True
        assert "annotated" in visual["screenshots"]
        assert Path(visual["screenshots"]["annotated"]).is_file()
        assert visual["design_review"]["status"] == "no_measured_findings"
