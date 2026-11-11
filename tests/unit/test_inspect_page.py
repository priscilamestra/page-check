"""Testes de orquestração, com transporte falso e sem rede."""

import pytest

from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.application.use_cases.inspect_page import inspect_page
from pagecheck.common.security.url_validation import URLValidationError


def fake_page(url: str) -> FetchedPage:
    assert url == "https://example.com/landing"
    return FetchedPage(
        original_url=url,
        final_url="https://example.com/final",
        status_code=200,
        html='''<title>Page Check</title><meta name="description" content="Resumo">
              <h1>Hero</h1><a href="/demo">Agendar</a>
              <img src="/banner.png" alt="Banner" loading="lazy">''',
        redirects=("https://example.com/final",),
    )


def test_inspection_joins_fetch_and_parser():
    result = inspect_page("https://example.com/landing", fetch=fake_page)
    assert result["title"] == "Page Check"
    assert result["meta_description"] == "Resumo"
    assert result["final_url"] == "https://example.com/final"
    assert result["links_preview"][0]["resolved_url"] == "https://example.com/demo"
    assert result["images_preview"][0]["loading"] == "lazy"
    assert result["headings_count"] == 1
    assert result["audit_scored"] is False


def test_previews_are_limited_but_totals_remain_accurate():
    html = "".join(f'<a href="/p{i}">Post</a>' for i in range(50))
    def many_links(url: str) -> FetchedPage:
        return FetchedPage(url, url, 200, html, ())
    result = inspect_page("https://example.com", fetch=many_links)
    assert result["links_count"] == 50
    assert len(result["links_preview"]) == 25
    assert result["previews_truncated"]["links"] is True


def test_invalid_url_fails_before_fetch():
    def forbidden_fetch(url: str) -> FetchedPage:
        raise AssertionError("Network access must not occur")
    with pytest.raises(URLValidationError):
        inspect_page("http://127.0.0.1", fetch=forbidden_fetch)
