"""Offline regression tests for first-viewport image evidence and DOM locations."""
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from PIL import Image

from pagecheck.acquisition.browser.public_navigation import NavigationReport
from pagecheck.acquisition.browser.visual_probe import inspect_visible_images
from pagecheck.application.use_cases.collect_public_visuals import capture_with_browser
from pagecheck.audits.navigation.rules import inspect_navigation
from pagecheck.reporting.consolidation.normalize import normalize_check


class FakeResponse:
    ok = True


class FakePage:
    viewport_size = {"width": 390, "height": 720}

    def __init__(self, image_state="broken"):
        self.image_state = image_state

    def goto(self, *_args, **_kwargs):
        return FakeResponse()

    def evaluate(self, script):
        if "Math.max(document.body.scrollHeight" in script:
            return 9001
        return [
            {"index": 0, "src": "https://example.org/missing.png", "data_src": None,
             "alt": "Company logo", "loading": None,
             "complete": self.image_state != "pending",
             "natural_width": 0, "rendered": True,
             "box": {"x": 20, "y": 40, "width": 100, "height": 60}},
            {"index": 1, "src": "https://example.org/outside.png", "data_src": None,
             "alt": "Outside", "loading": None, "complete": True,
             "natural_width": 0, "rendered": True,
             "box": {"x": 20, "y": 1400, "width": 100, "height": 60}},
        ]

    def wait_for_timeout(self, _ms):
        return None

    def screenshot(self, *, path, **_kwargs):
        Image.new("RGB", (self.viewport_size["width"], self.viewport_size["height"]), "white").save(path)


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False

    def new_page(self):
        return self.page

    def route(self, *_args, **_kwargs):
        return None

    def route_web_socket(self, *_args, **_kwargs):
        return None

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, page):
        self.page = page
        self.contexts = []

    def new_context(self, **kwargs):
        self.page.viewport_size = kwargs["viewport"]
        context = FakeContext(self.page)
        self.contexts.append(context)
        return context


def test_visible_images_excludes_offscreen_and_pending():
    assert len(inspect_visible_images(FakePage())) == 1
    assert inspect_visible_images(FakePage("pending"))[0]["status"] == "not_verified"


def test_oversized_page_marks_confirmed_broken_image_with_source(tmp_path: Path):
    browser = FakeBrowser(FakePage())
    result = capture_with_browser(browser, url="https://example.org", output_dir=tmp_path)
    for name in ("desktop", "mobile"):
        item = result["visuals"][name]
        assert item["scroll_complete"] is False
        assert item["images"]["total"] == 1
        assert item["images"]["broken"] == 1
        assert len(item["findings"]) == 1
        finding = item["findings"][0]
        assert finding["evidence"]["src"] == "https://example.org/missing.png"
        assert finding["evidence"]["alt"] == "Company logo"
        assert finding["status"] == "failed"
        assert Path(item["screenshots"]["annotated"]).is_file()
        normalized = normalize_check(finding, source="playwright", page_url="https://example.org",
                                     default_module="visual", viewport=name)
        assert normalized["status"] == "failed"
        assert normalized["evidence"]["src"].endswith("missing.png")
    assert all(ctx.closed for ctx in browser.contexts)


def test_blocked_and_pending_assets_not_reported_as_site_defects(tmp_path: Path):
    for state, blocked in (("broken", True), ("pending", False)):
        browser = FakeBrowser(FakePage(state))
        report = NavigationReport(blocked=[{"url": "https://example.org/missing.png",
                                             "reason": "blockedbyclient"}] if blocked else [])
        with patch("pagecheck.application.use_cases.collect_public_visuals.install_guarded_routes",
                   return_value=report):
            result = capture_with_browser(browser, url="https://example.org",
                                          output_dir=tmp_path / ("blocked" if blocked else "pending"))
        for item in result["visuals"].values():
            assert not item["findings"]
            assert "annotated" not in item["screenshots"]
            assert item["images"]["not_verified"] == 1


def test_navigation_evidence_identifies_correct_html_element():
    html = '<html><body><nav><a href="#">Contact</a><a href="/about">About</a></nav></body></html>'
    rows = inspect_navigation(html, "https://example.org/")
    warning = next(row for row in rows if row["status"] == "warning")
    selector = warning["evidence"]["selector"]
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one(selector).get_text(strip=True) == "Contact"
    assert "[document]" not in selector
