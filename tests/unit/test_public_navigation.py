import httpx
import pytest

from pagecheck.acquisition.browser.public_navigation import (
    BrowserFetchBlocked, ResourceResponse, fetch_public_resource,
    install_guarded_routes,
)


def test_fetch_resource_offline():
    def respond(req):
        assert req.url.host == "example.com"
        return httpx.Response(200, text="<h1>Hello</h1>", headers={"content-type": "text/html"})
    out = fetch_public_resource("https://example.com/", transport=httpx.MockTransport(respond))
    assert out.content == b"<h1>Hello</h1>"


def test_redirect_to_private_ip_is_blocked():
    def respond(req):
        return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})
    with pytest.raises(BrowserFetchBlocked):
        fetch_public_resource("https://example.com/", transport=httpx.MockTransport(respond))


def test_redirect_to_localhost_is_blocked():
    def respond(req):
        return httpx.Response(302, headers={"location": "http://localhost/private"})
    with pytest.raises(BrowserFetchBlocked):
        fetch_public_resource("https://example.com/", transport=httpx.MockTransport(respond))


def test_resource_byte_limit():
    def respond(req):
        return httpx.Response(200, content=b"x" * 100, headers={"content-type": "text/css"})
    with pytest.raises(BrowserFetchBlocked):
        fetch_public_resource("https://example.com/style.css", transport=httpx.MockTransport(respond), max_bytes=20)


def test_unsupported_mime():
    def respond(req):
        return httpx.Response(200, content=b"data", headers={"content-type": "application/zip"})
    with pytest.raises(BrowserFetchBlocked):
        fetch_public_resource("https://example.com/api", transport=httpx.MockTransport(respond))


def test_json_is_allowed_for_guarded_javascript_fetches():
    def respond(req):
        return httpx.Response(200, json={"ok": True}, headers={"content-type": "application/json"})
    out = fetch_public_resource("https://example.com/api", transport=httpx.MockTransport(respond))
    assert out.content_type == "application/json"


def test_illegal_port():
    with pytest.raises((ValueError, BrowserFetchBlocked)):
        fetch_public_resource("http://example.com:8080")


def test_guard_requires_low_limits():
    with pytest.raises(ValueError):
        install_guarded_routes(None, max_requests=100000)


class _Request:
    def __init__(self, *, method="GET", resource_type="script"):
        self.method = method
        self.resource_type = resource_type
        self.url = "https://example.com/app.js"


class _Route:
    def __init__(self, request):
        self.request = request
        self.fulfilled = None
        self.aborted = None

    def fulfill(self, **kwargs):
        self.fulfilled = kwargs

    def abort(self, reason):
        self.aborted = reason


class _Context:
    def route(self, _pattern, handler):
        self.handler = handler

    def route_web_socket(self, _pattern, handler):
        self.websocket_handler = handler


def test_guarded_routes_allow_bounded_javascript_gets():
    context = _Context()
    report = install_guarded_routes(
        context,
        fetch_resource=lambda url, max_bytes: ResourceResponse(
            url, 200, "application/javascript", b"document.body.dataset.ready='1'"
        ),
    )
    route = _Route(_Request())
    context.handler(route)
    assert route.aborted is None
    assert route.fulfilled["headers"]["content-type"] == "application/javascript"
    assert report.delivered == 1


def test_guarded_routes_still_block_script_posts():
    context = _Context()
    report = install_guarded_routes(context, fetch_resource=lambda *_args, **_kwargs: None)
    route = _Route(_Request(method="POST"))
    context.handler(route)
    assert route.fulfilled is None
    assert route.aborted == "blockedbyclient"
    assert report.blocked[0]["reason"] == "Somente GET é permitido."
