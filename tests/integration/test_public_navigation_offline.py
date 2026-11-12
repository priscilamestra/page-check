"""Testes da política de roteamento, inteiramente offline.

O Chromium nesta infraestrutura bloqueia navegações HTTP/S administrativamente,
por isso testamos a interceptação com rotas simuladas e o comportamento de
captura com o Chromium em fixtures (já coberto pela Etapa 9).
"""
from dataclasses import dataclass

from pagecheck.acquisition.browser.public_navigation import (
    BrowserFetchBlocked, ResourceResponse, install_guarded_routes,
    inspect_public_page,
)


@dataclass
class FakeRequest:
    url: str
    method: str = "GET"
    resource_type: str = "document"


class FakeRoute:
    def __init__(self, url, method="GET", resource_type="document"):
        self.request = FakeRequest(url, method, resource_type)
        self.fulfilled = None
        self.aborted = False

    def fulfill(self, **kwargs):
        self.fulfilled = kwargs

    def abort(self, _reason):
        self.aborted = True


class FakeContext:
    def route(self, pattern, handler):
        self.pattern = pattern
        self.handler = handler

    def route_web_socket(self, pattern, handler):
        self.websocket_pattern = pattern
        self.websocket_handler = handler


def make_context(fetcher, *, max_requests=60, max_total_bytes=12_000_000):
    context = FakeContext()
    report = install_guarded_routes(
        context, fetch_resource=fetcher,
        max_requests=max_requests, max_total_bytes=max_total_bytes,
    )
    return context, report


def ok_fetch(url, *, max_bytes):
    return ResourceResponse(url, 200, "text/html", b"<html>ok</html>")


def test_public_document_is_fulfilled_offline():
    context, report = make_context(ok_fetch)
    route = FakeRoute("https://example.com/page")
    context.handler(route)
    assert context.pattern == "**/*"
    assert route.fulfilled["status"] == 200
    assert report.delivered == 1
    assert report.total_bytes == len(b"<html>ok</html>")


def test_internal_destination_is_blocked_before_fetcher():
    calls = []
    def fetcher(url, *, max_bytes):
        calls.append(url)
        return ok_fetch(url, max_bytes=max_bytes)
    context, report = make_context(fetcher)
    route = FakeRoute("http://127.0.0.1/admin")
    context.handler(route)
    assert route.aborted
    assert calls == []
    assert report.blocked


def test_post_and_scripts_are_blocked():
    context, report = make_context(ok_fetch)
    post = FakeRoute("https://example.com/form", method="POST")
    script = FakeRoute("https://example.com/app.js", resource_type="script")
    context.handler(post)
    context.handler(script)
    assert post.aborted and script.aborted
    assert report.delivered == 0


def test_request_count_limit():
    context, report = make_context(ok_fetch, max_requests=1)
    a = FakeRoute("https://example.com/")
    b = FakeRoute("https://example.com/style.css", resource_type="stylesheet")
    context.handler(a)
    context.handler(b)
    assert a.fulfilled is not None
    assert b.aborted
    assert report.requested == 2


def test_blocked_upstream_resource_is_reported():
    def reject(url, *, max_bytes):
        raise BrowserFetchBlocked("Falha simulada.")
    context, report = make_context(reject)
    route = FakeRoute("https://example.com/image.png", resource_type="image")
    context.handler(route)
    assert route.aborted
    assert report.blocked[0]["reason"] == "Falha simulada."


def test_reject_private_target_before_browser_start(tmp_path):
    from pagecheck.common.security.url_validation import URLValidationError
    try:
        inspect_public_page(None, url="http://127.0.0.1", output_dir=tmp_path)
    except URLValidationError:
        pass
    else:
        raise AssertionError("IP local não deve ser aceito")
