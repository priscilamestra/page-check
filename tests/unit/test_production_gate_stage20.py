"""Keep the current scanner and unprotected history unavailable in public mode."""
import pytest
from fastapi.testclient import TestClient

from pagecheck.api.app import app
from pagecheck.common.security.deployment import is_local_development, live_fetch_enabled

client = TestClient(app)


@pytest.mark.parametrize("mode", ["production", "prod", "public", "staging", "unknown"])
def test_public_environment_blocks_opted_in_fetch(monkeypatch, mode):
    monkeypatch.setenv("PAGECHECK_ENV", mode)
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    assert not live_fetch_enabled()
    response = client.post("/v1/audits/page", json={
        "url": "https://example.com", "niche": "Software", "objective": "leads"
    })
    assert response.status_code == 503


def test_other_fetch_routes_are_closed_in_production(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    assert client.post("/v1/pages/inspect", json={"url": "https://example.com"}).status_code == 503
    assert client.post("/v1/audits/seo", json={
        "url": "https://example.com", "niche": "Software", "objective": "leads"
    }).status_code == 503


def test_history_closed_in_production_but_health_available(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    assert client.get("/v1/history").status_code == 503
    assert client.get("/health").status_code == 200


def test_local_environment_requires_explicit_fetch_opt_in(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "local")
    monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_FETCH", raising=False)
    assert is_local_development()
    assert not live_fetch_enabled()
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    assert live_fetch_enabled()
