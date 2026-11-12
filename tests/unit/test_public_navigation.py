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
        return httpx.Response(200, content=b"data", headers={"content-type": "application/json"})
    with pytest.raises(BrowserFetchBlocked):
        fetch_public_resource("https://example.com/api", transport=httpx.MockTransport(respond))


def test_illegal_port():
    with pytest.raises((ValueError, BrowserFetchBlocked)):
        fetch_public_resource("http://example.com:8080")


def test_guard_requires_low_limits():
    with pytest.raises(ValueError):
        install_guarded_routes(None, max_requests=100000)
