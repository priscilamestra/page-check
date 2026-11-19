"""No network or model calls: Spanish, Portuguese, and English checks."""
import pytest
from fastapi.testclient import TestClient

from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.acquisition.http.parser import parse_html
from pagecheck.api.app import app
from pagecheck.api.routes import audit as audit_route
from pagecheck.application.use_cases.audit_page_html import audit_page_html
from pagecheck.audits.seo.content_guidance import (
    _phrase_present,
    inspect_content_guidance,
    normalize_keywords,
)
from pagecheck.reporting.english_copy import check_copy


def html_for(lang="pt-BR"):
    return f'''<html lang="{lang}"><head><title>Automação comercial</title>
       <meta name="description" content="Automação comercial para empresas"></head>
       <body><h1>Automação comercial</h1><p>Soluções para vendas</p></body></html>'''


def test_selected_portuguese_and_accent_insensitive_keyword():
    source = html_for()
    result = inspect_content_guidance(source, parse_html(source, "https://example.com"),
                                      language="pt", niche="Marketing", keywords=["automacao comercial"])
    assert result["checks"][0]["status"] == "passed"
    assert result["checks"][1]["status"] == "passed"
    assert result["checks"][1]["evidence"]["locations"]["title"] is True


def test_spanish_page_language_mismatch_is_warning():
    source = html_for("es")
    result = inspect_content_guidance(source, parse_html(source, "https://example.com"),
                                      language="en", niche="Sales", keywords=["automation"])
    assert result["checks"][0]["status"] == "warning"
    assert result["checks"][1]["status"] == "warning"


def test_body_only_keyword_is_guidance_not_a_penalty_claim():
    html = '''<html lang="es"><head><title>Servicios</title></head>
              <body><h1>Servicios</h1>Optimización de campañas</body></html>'''
    data = inspect_content_guidance(html, parse_html(html, "https://example.com"),
                                    language="es", niche="Marketing", keywords=["campañas"])
    check = data["checks"][1]
    assert check["status"] == "warning"
    assert check["evidence"]["locations"]["visible_copy"] is True
    assert check["evidence"]["locations"]["title"] is False


def test_prominent_terms_outside_supplied_context_are_review_candidates():
    html = """<html lang='en'><head><title>Welcome to Python</title></head>
              <body><h1>Developer resources</h1><p>Python documentation.</p></body></html>"""
    data = inspect_content_guidance(
        html, parse_html(html, "https://python.example"), language="en",
        niche="Software programming", keywords=["python"],
    )
    assert [item["term"].casefold() for item in data["relevance_candidates"]] == [
        "welcome", "developer", "resources",
    ]
    assert all("outside the supplied niche" in item["reason"]
               for item in data["relevance_candidates"])


def test_supplied_target_terms_are_never_relevance_candidates():
    source = "<title>Python programming</title><h1>Python software</h1>"
    data = inspect_content_guidance(
        source, parse_html(source, "https://example.com"), language="en",
        niche="Software programming", keywords=["python"],
    )
    assert data["relevance_candidates"] == []


def test_word_boundary_avoids_false_positive():
    assert not _phrase_present("sale", "wholesale")
    assert _phrase_present("sale", "sale today")


def test_missing_html_lang_needs_review():
    html = '<html><title>Testing</title><h1>Testing</h1></html>'
    check = inspect_content_guidance(html, parse_html(html, "https://example.com"),
                                     language="en", niche="Testing")["checks"][0]
    assert check["status"] == "warning"


@pytest.mark.parametrize("value", [[" "] , ["x"], ["one"] * 9, ["abc", "ABC"]])
def test_rejects_invalid_keyword_sets(value):
    with pytest.raises(ValueError):
        normalize_keywords(value)


def test_preserves_original_technical_seo_score():
    source = html_for()
    def fake_fetch(url):
        return FetchedPage(url, url, 200, source, ())
    base = audit_page_html("https://example.com", niche="Sales", objective="sales", fetch=fake_fetch)
    guided = audit_page_html("https://example.com", niche="Sales", objective="sales",
                             language="pt", keywords=["automação comercial"], fetch=fake_fetch)
    assert base["scores"]["internal"]["seo"]["score"] == guided["scores"]["internal"]["seo"]["score"]
    assert guided["audit_context"] == {"language": "pt", "keywords": ["automação comercial"]}
    assert "relevance_candidates" in guided["seo_content_guidance"]
    assert any(c["check_id"].startswith("SEO_TARGET_KEYWORD_") for c in guided["checks"])
    assert guided["status"] == "partial"


def test_english_display_copy_for_old_portuguese_findings():
    title, action = check_copy({"check_id": "SEO_CANONICAL", "status": "warning",
                                "title": "Canonical não declarada", "recommendation": "Avaliar canonical"})
    assert title == "Canonical URL needs review"
    assert action.startswith("Check whether")


def test_api_receives_language_and_keyword_tags(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    captured = {}
    def fake_audit(url, **kwargs):
        captured.update(kwargs)
        return {"schema_version": "audit-report-1.0", "requested_url": url, "final_url": url,
                "niche": kwargs["niche"], "objective": kwargs["objective"], "status": "partial",
                "summary": {}, "scores": {}, "checks": [], "findings": [],
                "actions_by_team": [], "source_states": {}}
    monkeypatch.setattr(audit_route, "audit_page_html", fake_audit)
    response = TestClient(app).post("/v1/audits/page", json={
        "url": "https://example.com", "niche": "Comercial", "objective": "sales",
        "language": "es", "keywords": ["ventas", "gestión comercial"]})
    assert response.status_code == 200
    assert captured["language"] == "es"
    assert captured["keywords"] == ["ventas", "gestión comercial"]


def test_api_rejects_duplicate_keywords():
    response = TestClient(app).post("/v1/audits/page", json={
        "url": "https://example.com", "niche": "Marketing", "objective": "sales",
        "language": "pt", "keywords": ["análise", "ANÁLISE"]})
    assert response.status_code == 422
