"""A long page must never trigger a giant full-page screenshot."""
from types import SimpleNamespace

from pagecheck.application.use_cases.collect_public_visuals import capture_with_browser


class LongPage:
    def __init__(self):
        self.screenshot_args = []
    def goto(self, *_args, **_kwargs):
        return SimpleNamespace(ok=True)
    def evaluate(self, _code):
        return 9000
    def screenshot(self, *, path, **kwargs):
        from pathlib import Path
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\nsmall-test")
        self.screenshot_args.append(kwargs)


class Context:
    def __init__(self, page):
        self.page = page
    def route(self, *_args):
        pass
    def route_web_socket(self, *_args):
        pass
    def new_page(self):
        return self.page
    def close(self):
        pass


class Browser:
    def __init__(self):
        self.pages = [LongPage(), LongPage()]
        self.index = 0
        self.options = []
    def new_context(self, **kwargs):
        self.options.append(kwargs)
        page = self.pages[self.index]
        self.index += 1
        return Context(page)


def test_long_page_captures_only_safe_initial_viewports(monkeypatch, tmp_path):
    from pagecheck.application.use_cases import collect_public_visuals as collector
    monkeypatch.setattr(collector, "audit_visual_viewport",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            AssertionError("full-page audit must not run")))
    browser = Browser()
    observed = capture_with_browser(browser, url="https://example.com/long", output_dir=tmp_path,
                                    fetch_resource=lambda *_args, **_kwargs: None)
    assert observed["status"] == "partial"
    assert not observed["errors"]
    assert set(observed["visuals"]) == {"desktop", "mobile"}
    for viewport, page in zip(("desktop", "mobile"), browser.pages):
        entry = observed["visuals"][viewport]
        assert entry["findings"] == []
        assert "initial" in entry["screenshots"]
        assert (tmp_path / viewport / "initial_viewport.png").is_file()
        assert "without annotations" in entry["limitations"][0]
        assert page.screenshot_args[0]["full_page"] is False
    assert all(opts["java_script_enabled"] for opts in browser.options)


def test_fallback_does_not_mark_visual_checks_completed(monkeypatch, tmp_path):
    from pagecheck.application.use_cases import collect_public_visuals as collector
    browser = Browser()
    result = capture_with_browser(browser, url="https://example.com/long", output_dir=tmp_path)
    from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
    report = consolidate_audit(
        requested_url="https://example.com/long", final_url="https://example.com/long",
        niche="Software", objective="leads", visuals=result["visuals"])
    assert report["source_states"]["visuals"] == {"desktop": "partial", "mobile": "partial"}
    assert report["screenshots"]["desktop"].get("annotated") is None
