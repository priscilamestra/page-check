"""STAGE37: offline pre-deploy checks for Page Check's public URL transport.

This deliberately DOES NOT certify Render egress isolation. It tests the
application-level DNS/IP boundary without contacting the network, and refuses
an accidental switch-on of public audit flags before infrastructure review.

Run from the repo root: uv run python scripts/stage37_public_egress_preflight.py
Or mount into the stage36 API container and run with its venv Python.
"""
from __future__ import annotations

import os
import socket
import sys
from unittest.mock import Mock, patch

import httpx
from pagecheck.acquisition.http.fetcher import fetch_html
from pagecheck.acquisition.browser.public_navigation import (
    BrowserFetchBlocked, fetch_public_resource,
)
from pagecheck.acquisition.http.safe_transport import PublicNetworkBackend, UnsafeDestination
from pagecheck.common.security.deployment import production_scan_configured
from pagecheck.common.security.url_validation import URLValidationError, validate_public_url


# Reserved addresses, private subnets, link-local metadata, CGNAT and ULA.
# The resolver is mocked in each case: no actual DNS lookup or TCP connection.
DENIED_IPS = (
    "127.0.0.1", "10.23.1.1", "172.16.0.20", "192.168.1.10",
    "169.254.169.254", "100.64.0.3", "0.0.0.0", "::1", "fc00::20",
    "fe80::1",
)
DENIED_URLS = (
    "http://127.0.0.1/", "http://169.254.169.254/latest/meta-data/",
    "http://localhost/", "http://service.internal/", "http://example.com:8080/",
    "file:///etc/passwd", "https://user:pass@example.com/",
)


def _dns_record(ip: str, port: int = 443) -> tuple:
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    sockaddr = (ip, port, 0, 0) if family == socket.AF_INET6 else (ip, port)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


def test_local_url_policy() -> None:
    for url in DENIED_URLS:
        try:
            validate_public_url(url)
        except URLValidationError:
            continue
        raise AssertionError(f"Unsafe URL accepted: {url!r}")
    assert validate_public_url("https://www.example.org/landing")


def _assert_no_connect(answers: list[str]) -> None:
    backend = PublicNetworkBackend()
    connector = Mock()
    records = [_dns_record(ip) for ip in answers]
    with patch("socket.getaddrinfo", return_value=records), patch.object(
        backend._backend, "connect_tcp", connector
    ):
        try:
            backend.connect_tcp("www.example.org", 443)
        except (URLValidationError, UnsafeDestination):
            pass
        else:
            raise AssertionError(f"Unsafe DNS answer accepted: {answers!r}")
    connector.assert_not_called()


def test_dns_rebinding_boundary() -> None:
    for address in DENIED_IPS:
        _assert_no_connect([address])
        # A public + private response MUST be denied, not filtered down to public.
        _assert_no_connect(["93.184.216.34", address])

    backend = PublicNetworkBackend()
    connector = Mock(return_value=object())
    with patch("socket.getaddrinfo", return_value=[_dns_record("93.184.216.34")]), patch.object(
        backend._backend, "connect_tcp", connector
    ):
        backend.connect_tcp("www.example.org", 443)
    assert connector.call_args.args[:2] == ("93.184.216.34", 443)

    backend = PublicNetworkBackend()
    connector = Mock()
    with patch.object(backend._backend, "connect_tcp", connector):
        try:
            backend.connect_tcp("www.example.org", 8080)
        except UnsafeDestination:
            pass
        else:
            raise AssertionError("Non-HTTP(S) TCP port was accepted")
    connector.assert_not_called()


def test_redirects_cannot_bypass_url_guard() -> None:
    requests = []

    def redirect(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"})

    transport = httpx.MockTransport(redirect)
    try:
        fetch_html("https://www.example.org/", transport=transport)
    except URLValidationError:
        pass
    else:
        raise AssertionError("HTML redirect to cloud metadata was followed")
    assert len(requests) == 1

    requests.clear()
    try:
        fetch_public_resource("https://www.example.org/a.css", transport=transport)
    except BrowserFetchBlocked:
        pass
    else:
        raise AssertionError("Browser resource redirect to cloud metadata was followed")
    assert len(requests) == 1


def test_production_flags_are_closed() -> None:
    dangerous = ("PAGECHECK_PUBLIC_AUDITS_ENABLED", "PAGECHECK_EGRESS_ISOLATED")
    for key in dangerous:
        if os.environ.get(key) == "1":
            raise AssertionError(f"{key} is enabled before hosted egress approval")

    with patch.dict(os.environ, {"PAGECHECK_ENV": "production",
                                "PAGECHECK_PUBLIC_AUDITS_ENABLED": "0",
                                "PAGECHECK_EGRESS_ISOLATED": "0"}):
        assert not production_scan_configured()


def main() -> int:
    checks = (
        (test_local_url_policy, "STAGE37_URL_POLICY_PASSED"),
        (test_dns_rebinding_boundary, "STAGE37_IP_PINNING_AND_SSRF_DENIAL_PASSED"),
        (test_redirects_cannot_bypass_url_guard, "STAGE37_INTERNAL_REDIRECTS_BLOCKED"),
        (test_production_flags_are_closed, "STAGE37_PRODUCTION_DISABLED_CONFIRMED"),
    )
    for check, label in checks:
        try:
            check()
        except Exception as exc:
            print(f"STAGE37_PRECHECK_FAILED: {check.__name__} ({type(exc).__name__})", file=sys.stderr)
            return 1
        print(label)
    print("STAGE37_APPLICATION_EGRESS_PRECHECK_PASSED")
    print("HOSTED_OS_EGRESS_ISOLATION_NOT_VERIFIED")
    print("PUBLIC_AUDITS_MUST_REMAIN_DISABLED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
