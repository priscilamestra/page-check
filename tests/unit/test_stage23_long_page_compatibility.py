"""Long-page compatibility: a screenshot must survive unavailable image inspection."""
from pathlib import Path
from PIL import Image
from pagecheck.application.use_cases.collect_public_visuals import capture_with_browser
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit


class Response:
    ok = True


class LimitedPage:
    """Old-style controlled page: can render, but no optional image probe API."""
    def goto(self, *_args, **_kwargs):
        return Response()

    def evaluate(self, _script):
        return 9001

    def screenshot(self, *, path, **_kwargs):
        Image.new("RGB", (1280, 720), "white").save(path)


class Context:
    def route(self, *_args):
        return None
    def route_web_socket(self, *_args):
        return None
    def new_page(self):
        return LimitedPage()
    def close(self):
        return None


class Browser:
    def new_context(self, **_kwargs):
        return Context()


def test_long_page_preserves_partial_viewport_when_image_probe_unavailable(tmp_path: Path):
    result = capture_with_browser(Browser(), url="https://example.org/long", output_dir=tmp_path)
    assert not result["errors"]
    assert set(result["visuals"]) == {"desktop", "mobile"}
    assert all(Path(v["screenshots"]["initial"]).is_file() for v in result["visuals"].values())
    assert all(v["scroll_complete"] is False for v in result["visuals"].values())
    assert all("not verified" in " ".join(v["limitations"]).lower() for v in result["visuals"].values())
    report = consolidate_audit(requested_url="https://example.org/long", final_url="https://example.org/long", niche="Software", objective="leads", visuals=result["visuals"])
    assert report["source_states"]["visuals"] == {"desktop":"partial", "mobile":"partial"}
