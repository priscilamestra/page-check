"""Testes de contrato HTTP SEO. Não abrem sites externos."""

from fastapi.testclient import TestClient

from pagecheck.acquisition.http.fetcher import FetchError
from pagecheck.acquisition.http.safe_transport import UnsafeDestination
from pagecheck.api.app import app
import pagecheck.api.routes.seo as seo_route

client = TestClient(app)
VALID = {"url": "https://example.com", "niche": "SaaS B2B", "objective": "leads"}


def sample_result(url: str, *, niche: str, objective: str) -> dict:
    return {
        "requested_url": url, "final_url": url, "status_code": 200, "redirects": [],
        "niche": niche, "module": "seo", "ruleset_version": "seo-1.0.0",
        "objective": objective, "score": 100.0, "coverage": 1.0,
        "partial_score": False, "checks_executed": 1, "checks_applicable": 1,
        "checks": [{
            "check_id": "SEO_TITLE", "module": "seo", "status": "passed",
            "severity": "info", "title": "Title presente", "weight": 3,
            "target_url": url, "team": "SEO / Conteúdo",
            "evidence": {"source": "beautifulsoup", "observed_value": "OK"},
            "recommendation": "",
        }], "findings": [],
    }


def test_endpoint_disabled_by_default(monkeypatch):
    monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_FETCH", raising=False)
    assert client.post("/v1/audits/seo", json=VALID).status_code == 503


def test_returns_seo_score_and_evidence(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.setattr(seo_route, "audit_seo_page", sample_result)
    response = client.post("/v1/audits/seo", json=VALID)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["score"] == 100.0
    assert result["checks"][0]["evidence"]["source"] == "beautifulsoup"
    assert result["niche"] == "SaaS B2B"
    assert result["module"] == "seo"


def test_rejects_local_url(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    assert client.post("/v1/audits/seo", json={**VALID, "url": "http://127.0.0.1"}).status_code == 422


def test_rejects_invalid_objective(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    assert client.post("/v1/audits/seo", json={**VALID, "objective": "rank_google"}).status_code == 422


def test_returns_blocked_destination(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")

    def blocked(url, *, niche, objective):
        raise UnsafeDestination("Blocked")

    monkeypatch.setattr(seo_route, "audit_seo_page", blocked)
    assert client.post("/v1/audits/seo", json=VALID).status_code == 403


def test_returns_fetch_error(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")

    def failed(url, *, niche, objective):
        raise FetchError("Consulta falhou")

    monkeypatch.setattr(seo_route, "audit_seo_page", failed)
    assert client.post("/v1/audits/seo", json=VALID).status_code == 502


def test_existing_endpoints_stay_registered():
    assert client.get("/health").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert "/v1/pages/inspect" in paths
    assert "/v1/audits/seo" in paths
