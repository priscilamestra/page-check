"""Casos de referência SEO: HTML completo -> parser -> regras -> API.

Não há acesso à internet. Os arquivos não são modelos de qualidade editorial,
apenas fixtures para verificar as regras determinísticas atuais.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.application.use_cases.audit_seo_page import audit_seo_page
from pagecheck.api.app import app
import pagecheck.api.routes.seo as seo_route

PAGES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "pages"
BASE_URL = "https://example.com"
GOOD_URL = f"{BASE_URL}/landing-ok"
BAD_URL = f"{BASE_URL}/landing-problems"


def fixture_fetch(url: str) -> FetchedPage:
    mapping = {
        GOOD_URL: "seo_ok.html",
        BAD_URL: "seo_problems.html",
    }
    if url not in mapping:
        raise AssertionError(f"Nenhuma fixture para esta URL: {url}")
    html = (PAGES_DIR / mapping[url]).read_text(encoding="utf-8")
    return FetchedPage(
        original_url=url,
        final_url=url,
        status_code=200,
        html=html,
        redirects=(),
    )


def analyze(url: str, objective: str = "organic_traffic") -> dict:
    return audit_seo_page(
        url, niche="Tecnologia B2B", objective=objective, fetch=fixture_fetch
    )


def check_by_id(result: dict) -> dict:
    return {check["check_id"]: check for check in result["checks"]}


def test_reference_page_without_known_problems():
    result = analyze(GOOD_URL)
    assert result["score"] == 100.0
    assert result["coverage"] == 1.0
    assert result["findings"] == []
    assert result["status_code"] == 200
    assert result["ruleset_version"] == "seo-1.0.0"


def test_problem_page_exposes_known_findings():
    result = analyze(BAD_URL)
    checks = check_by_id(result)
    expected = {
        "SEO_TITLE": "failed",
        "SEO_DESCRIPTION": "failed",
        "SEO_H1": "failed",
        "SEO_CANONICAL": "warning",
        "SEO_NOINDEX": "failed",
        "SEO_IMAGE_ALT": "warning",
    }
    for check_id, status in expected.items():
        assert checks[check_id]["status"] == status, check_id
    assert result["coverage"] == 1.0
    assert len(result["findings"]) == 6
    assert 0 <= result["score"] < 50


def test_evidence_and_recommendations_point_to_known_html():
    result = analyze(BAD_URL)
    checks = check_by_id(result)
    assert checks["SEO_IMAGE_ALT"]["evidence"]["observed_value"][
        "missing_alt_sources"
    ] == [f"{BASE_URL}/assets/banner-sem-alt.png"]
    assert checks["SEO_NOINDEX"]["evidence"]["observed_value"] == "noindex, follow"
    assert all(item["recommendation"] for item in result["findings"])
    assert all(item["target_url"] == BAD_URL for item in result["findings"])


def test_scores_reflect_difference_between_pages():
    healthy = analyze(GOOD_URL)
    problematic = analyze(BAD_URL)
    assert healthy["score"] > problematic["score"]
    assert healthy["checks_executed"] == problematic["checks_executed"]


def test_noindex_is_scoped_to_organic_objective():
    organic = check_by_id(analyze(BAD_URL, "organic_traffic"))
    leads = check_by_id(analyze(BAD_URL, "leads"))
    assert organic["SEO_NOINDEX"]["status"] == "failed"
    assert leads["SEO_NOINDEX"]["status"] == "not_applicable"


def _patch_route_to_use_fixtures(monkeypatch):
    """Substitui apenas a aquisição externa; mantém parser, regras e rota reais."""
    def inspect(url: str, *, niche: str, objective: str):
        return audit_seo_page(
            url, niche=niche, objective=objective, fetch=fixture_fetch
        )

    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.setattr(seo_route, "audit_seo_page", inspect)


def test_http_route_returns_complete_good_page_result(monkeypatch):
    _patch_route_to_use_fixtures(monkeypatch)
    response = TestClient(app).post(
        "/v1/audits/seo",
        json={"url": GOOD_URL, "niche": "Tecnologia B2B", "objective": "organic_traffic"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["score"] == 100.0
    assert body["findings"] == []
    assert body["requested_url"] == GOOD_URL
    assert body["checks_applicable"] >= 6


def test_http_route_returns_problem_details_and_coverage(monkeypatch):
    _patch_route_to_use_fixtures(monkeypatch)
    response = TestClient(app).post(
        "/v1/audits/seo",
        json={"url": BAD_URL, "niche": "Tecnologia B2B", "objective": "organic_traffic"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["score"] < 50
    assert body["coverage"] == 1.0
    assert len(body["findings"]) == 6
    assert {x["check_id"] for x in body["findings"]} >= {
        "SEO_TITLE", "SEO_DESCRIPTION", "SEO_H1", "SEO_NOINDEX"
    }
