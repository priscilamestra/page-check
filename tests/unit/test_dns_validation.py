
import socket

import pytest

from pagecheck.common.security.dns_validation import (
    resolve_public_ips,
    validate_resolved_ips,
)
from pagecheck.common.security.url_validation import URLValidationError


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "192.168.1.1",
        "10.0.0.1",
        "169.254.169.254",
        "0.0.0.0",
        "::1",
        "fc00::1",
        "fe80::1",
    ],
)
def test_rejects_non_public_ips(address):
    with pytest.raises(URLValidationError):
        validate_resolved_ips([address])


def test_accepts_public_ips():
    result = validate_resolved_ips(
        ["8.8.8.8", "2606:4700:4700::1111"]
    )
    assert len(result) == 2


def test_rejects_mixed_public_and_private_ips():
    with pytest.raises(URLValidationError):
        validate_resolved_ips(["8.8.8.8", "10.0.0.1"])


def test_rejects_empty_dns_result():
    with pytest.raises(URLValidationError):
        validate_resolved_ips([])


def test_resolves_public_domain(monkeypatch):
    def fake_getaddrinfo(*args, **kwargs):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("8.8.8.8", 0),
            )
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    result = resolve_public_ips("https://example.com")

    assert result == ("8.8.8.8",)
