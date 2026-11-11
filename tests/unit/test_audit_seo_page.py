"""Testes do caso de uso SEO sem requisições externas."""

import pytest

from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.application.use_cases.audit_seo_page import audit_seo_page
from pagecheck.common.security.url_validation import URLValidationError


URL = "https://example.com/landing"


def test_seo_receives_full_html_and_final_url():
    html = ("<title>Landing</title><meta name='description' content='Teste'>"
            "<link rel='canonical' href='/final'><h1>Serviço</h1>"
            + "<img src='/image.png'>" * 26)

    def fetch(url: str) -> FetchedPage:
        assert url == URL
        return FetchedPage(url, "https://example.com/final", 200, html, ("https://example.com/final",))

    result = audit_seo_page(URL, niche="SaaS B2B", objective="organic_traffic", fetch=fetch)
    image_check = next(x for x in result["checks"] if x["check_id"] == "SEO_IMAGE_ALT")
    assert image_check["status"] == "warning"
    assert image_check["evidence"]["observed_value"]["count"] == 26
    assert result["final_url"] == "https://example.com/final"
    assert result["requested_url"] == URL
    assert result["redirects"] == ["https://example.com/final"]
    assert result["niche"] == "SaaS B2B"
    assert result["ruleset_version"] == "seo-1.0.0"
    assert result["score"] is not None


def test_noindex_depends_on_objective():
    html = "<meta name='robots' content='noindex'><h1>Olá</h1>"

    def fetch(url):
        return FetchedPage(url, url, 200, html, ())

    organic = audit_seo_page(URL, niche="Educação", objective="organic_traffic", fetch=fetch)
    leads = audit_seo_page(URL, niche="Educação", objective="leads", fetch=fetch)
    by_id = lambda result: next(c for c in result["checks"] if c["check_id"] == "SEO_NOINDEX")
    assert by_id(organic)["status"] == "failed"
    assert by_id(leads)["status"] == "not_applicable"


def test_validates_url_before_fetch():
    def should_not_fetch(url):
        raise AssertionError("Fetcher não deve ser chamado")

    with pytest.raises(URLValidationError):
        audit_seo_page("http://localhost", niche="SaaS", objective="leads", fetch=should_not_fetch)


def test_niche_does_not_change_score():
    def fetch(url):
        return FetchedPage(url, url, 200, "<h1>Teste</h1>", ())

    a = audit_seo_page(URL, niche="Tecnologia", objective="leads", fetch=fetch)
    b = audit_seo_page(URL, niche="Nutrição", objective="leads", fetch=fetch)
    assert a["score"] == b["score"]
