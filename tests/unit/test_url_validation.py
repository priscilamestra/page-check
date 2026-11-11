
import pytest

from pagecheck.common.security.url_validation import (
    URLValidationError,
    validate_public_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/campanha?utm_source=linkedin",
        "http://example.org",
        "https://www.exemplo.com.br/landing-page",
    ],
)
def test_valid_urls(url):
    assert validate_public_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "example.com",
        "ftp://example.com",
        "http://localhost",
        "http://127.0.0.1",
        "http://[::1]",
        "http://192.168.1.1",
        "http://site.local",
        "http://site.test",
        "http://example.com:8080",
        "http://user:pass@example.com",
        "http://2130706433",
        "http://0177.0.0.1",
        "https://example.com/hello world",
    ],
)
def test_invalid_urls(url):
    with pytest.raises(URLValidationError):
        validate_public_url(url)
