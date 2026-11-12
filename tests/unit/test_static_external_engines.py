"""No unguarded external navigation or fabricated Lighthouse scores."""
from pagecheck.application.use_cases.collect_static_engines import (
    collect_static_engines, sanitize_static_html, MAX_HTML_BYTES,
)
from pagecheck.integrations.engine_result import result, unavailable
from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.application.use_cases.audit_page_html import audit_page_html
import pytest

HTML = """<html lang='en'><head><title>Landing</title>
<script src='https://internal.local/leak.js'>alert(1)</script>
<style>@import url(https://internal.local/leak.css)</style></head>
<body onload='alert(1)'><a href='http://127.0.0.1/secret' onclick='alert(1)'>Buy</a>
<img src='http://10.0.0.2/private' alt=''><iframe src='http://127.0.0.1'></iframe>
<h1>Product</h1></body></html>"""


def test_strips_active_content_and_urls():
    cleaned = sanitize_static_html(HTML)
    assert "alert(1)" not in cleaned
    assert "127.0.0.1" not in cleaned
    assert "internal.local" not in cleaned
    assert "10.0.0.2" not in cleaned
    assert "<script" not in cleaned
    assert "<iframe" not in cleaned
    assert 'href="#"' in cleaned
    assert 'alt=""' in cleaned


def test_rejects_oversized_html():
    with pytest.raises(ValueError):
        sanitize_static_html("a" * (MAX_HTML_BYTES + 1))


def test_static_collector_isolates_engine_exceptions(tmp_path):
    calls=[]
    def axe_runner(html, root):
        calls.append(html)
        return result("axe", findings=[{"id": "axe:test", "source":"axe", "module":"accessibility", "status":"failed", "severity":"medium", "title":"Missing label", "description":"", "evidence":{}, "owner":"Frontend"}])
    def failed(html, root):
        raise RuntimeError("broken")
    out = collect_static_engines(HTML, "https://example.com/a", root=tmp_path,
                                 axe_runner=axe_runner, impeccable_runner=failed)
    assert len(calls) == 1
    assert out["engines"]["axe"]["status"] == "completed"
    assert out["engines"]["impeccable"]["status"] == "not_verified"
    assert out["engines"]["lighthouse"]["status"] == "not_verified"
    assert out["status"] == "partial"


def test_static_collector_does_not_run_engines_for_private_target():
    called=[]
    def spy(*args, **kwargs):
        called.append(1)
        return result("axe")
    with pytest.raises(Exception):
        collect_static_engines(HTML, "http://127.0.0.1/", axe_runner=spy)
    assert not called


def test_combined_report_includes_same_page_external_findings():
    def fetch(url):
        return FetchedPage(url, url, 200, "<html lang='en'><title>A</title><body><h1>A</h1></body></html>", ())
    def engines(html, final_url):
        assert "<h1>A</h1>" in html
        assert final_url == "https://example.com/a"
        return {"engines": {"axe": result("axe", findings=[{"id": "axe:fake", "module":"accessibility", "status":"failed", "severity":"medium", "title":"Missing label", "description":"", "evidence":{"selector":"input"}, "owner":"Frontend"}]), "lighthouse": unavailable("lighthouse", "No safe Chrome"), "impeccable": unavailable("impeccable", "Not installed")}}
    report = audit_page_html("https://example.com/a", niche="Software", objective="leads",
                              fetch=fetch, external_collector=engines)
    assert report["source_states"]["engines"]["axe"] == "completed"
    assert report["source_states"]["engines"]["lighthouse"] == "not_verified"
    assert report["scores"]["lighthouse"] is None
    assert any(x.get("source") == "axe" for x in report["checks"])
    assert report["external_capture"]["mode"] == "opt_in_sanitized_static_html"


def test_engine_collector_exception_leaves_html_report_usable():
    def fetch(url):
        return FetchedPage(url, url, 200, "<html><body><h1>A</h1></body></html>", ())
    def broken(*_):
        raise RuntimeError("broken")
    report = audit_page_html("https://example.com", niche="Software", objective="leads", fetch=fetch, external_collector=broken)
    assert report["source_states"]["seo"] == "completed"
    assert report["source_states"]["engines"]["axe"] == "not_verified"


def test_missing_binaries_never_pass(tmp_path):
    out = collect_static_engines("<html><title>Demo</title></html>", "https://example.com", root=tmp_path)
    assert all(x["status"] == "not_verified" for x in out["engines"].values())


def test_nested_active_elements_are_removed():
    cleaned = sanitize_static_html("<html><body><iframe><b>secret</b></iframe><p>safe</p></body></html>")
    assert "secret" not in cleaned and "safe" in cleaned


def test_invalid_external_collector_return_does_not_break_seo():
    def fetch(url):
        return FetchedPage(url, url, 200, "<html><body><h1>A</h1></body></html>", ())
    report = audit_page_html("https://example.com", niche="Software", objective="leads", fetch=fetch,
                             external_collector=lambda *args: [])
    assert report["source_states"]["seo"] == "completed"
    assert report["source_states"]["engines"]["axe"] == "not_verified"
