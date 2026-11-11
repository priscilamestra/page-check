"""Testes de contrato HTTP sem acesso à internet."""

from fastapi.testclient import TestClient

from pagecheck.acquisition.http.fetcher import FetchError
from pagecheck.acquisition.http.safe_transport import UnsafeDestination
from pagecheck.api.app import app
import pagecheck.api.routes.pages as pages_route


client = TestClient(app)


def sample_response(url: str) -> dict:
    return {
        "requested_url": url,
        "final_url": url,
        "status_code": 200,
        "redirects": [],
        "title": "Exemplo",
        "meta_description": None,
        "meta_robots": None,
        "canonical": None,
        "headings_count": 0,
        "headings": [],
        "links_count": 0,
        "links_preview": [],
        "images_count": 0,
        "images_preview": [],
        "previews_truncated": {"headings": False, "links": False, "images": False},
        "audit_scored": False,
    }


def test_disabled_without_explicit_flag(monkeypatch):
    monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_FETCH", raising=False)
    response = client.post("/v1/pages/inspect", json={"url": "https://example.com"})
    assert response.status_code == 503


def test_rejects_invalid_input(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    response = client.post("/v1/pages/inspect", json={"url": "http://localhost"})
    assert response.status_code == 422


def test_returns_extracted_response(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.setattr(pages_route, "inspect_page", sample_response)
    response = client.post("/v1/pages/inspect", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert response.json()["title"] == "Exemplo"
    assert response.json()["audit_scored"] is False


def test_blocks_network_destination(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    def unsafe(_: str) -> dict:
        raise UnsafeDestination("forbidden")
    monkeypatch.setattr(pages_route, "inspect_page", unsafe)
    response = client.post("/v1/pages/inspect", json={"url": "https://example.com"})
    assert response.status_code == 403


def test_translates_fetch_failures(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    def failed(_: str) -> dict:
        raise FetchError("Falha ao consultar a página")
    monkeypatch.setattr(pages_route, "inspect_page", failed)
    response = client.post("/v1/pages/inspect", json={"url": "https://example.com"})
    assert response.status_code == 502


def test_health_still_works():
    assert client.get("/health").status_code == 200
