"""Stage 41: legacy network routes cannot bypass the production audit policy."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from pagecheck.api.routes import pages, seo


@pytest.mark.parametrize("router,path,payload", [
    (pages.router, "/v1/pages/inspect", {"url": "https://example.org/"}),
    (seo.router, "/v1/audits/seo", {"url": "https://example.org/", "niche": "SaaS", "objective": "leads"}),
])
def test_legacy_routes_stay_disabled_in_production_even_with_release_flags(monkeypatch, router, path, payload):
    # Even a mistakenly flipped set of flags cannot expose unauthenticated
    # legacy network entrypoints on the public Render Free FastAPI URL.
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.setenv("PAGECHECK_PUBLIC_AUDITS_ENABLED", "1")
    monkeypatch.setenv("PAGECHECK_EGRESS_ISOLATED", "1")
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_BROWSER", "1")
    monkeypatch.setenv("PAGECHECK_PRIVATE_API_KEY", "x" * 40)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.post(path, json=payload)
    assert response.status_code == 503
    assert "local-only" in response.json()["detail"]


def test_legacy_inspect_local_mode_preserves_existing_fetch_gate(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "local")
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "0")
    app = FastAPI()
    app.include_router(pages.router)
    client = TestClient(app)
    assert client.post("/v1/pages/inspect", json={"url": "https://example.org/"}).status_code == 503


def test_legacy_seo_local_mode_preserves_existing_fetch_gate(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "local")
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "0")
    app = FastAPI()
    app.include_router(seo.router)
    client = TestClient(app)
    response = client.post("/v1/audits/seo", json={"url": "https://example.org/"})
    assert response.status_code != 200
