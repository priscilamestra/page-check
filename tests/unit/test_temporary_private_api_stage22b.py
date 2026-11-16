"""Offline route security checks; no live PostgreSQL/Neon credentials required."""
from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pagecheck.api.routes import temporary as route
from pagecheck.persistence.postgres.temporary import TemporaryAuditNotFound, new_recovery_token


class FakeStore:
    def __init__(self):
        self.items = {}
        self.images = {}

    def save(self, report, *, previous_token=None):
        if previous_token:
            self.items.pop(previous_token, None)
        token = new_recovery_token()
        self.items[token] = report
        return {"recovery_token": token, "expires_at": "2026-11-16T00:00:00+00:00", "stored_screenshots": 0}

    def load(self, token):
        if token not in self.items:
            raise TemporaryAuditNotFound()
        return self.items[token]

    def load_image(self, token, viewport, kind):
        if token not in self.items:
            raise TemporaryAuditNotFound()
        return b"\x89PNG\r\n\x1a\n" + b"X" * 20

    def delete(self, token):
        return self.items.pop(token, None) is not None


def test_private_api_is_local_only_by_default(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "development")
    monkeypatch.delenv("PAGECHECK_PRIVATE_API_KEY", raising=False)
    from pagecheck.common.security.private_api import require_private_service
    from starlette.requests import Request
    from fastapi import HTTPException
    request = Request({"type": "http", "headers": [], "client": ("192.0.2.20", 9000), "method":"POST", "path":"/"})
    import pytest
    with pytest.raises(HTTPException) as exc:
        require_private_service(request)
    assert exc.value.status_code == 403


def test_private_api_requires_secret_in_production(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.delenv("PAGECHECK_PRIVATE_API_KEY", raising=False)
    from pagecheck.common.security.private_api import require_private_service
    from starlette.requests import Request
    from fastapi import HTTPException
    request = Request({"type": "http", "headers": [], "client": ("127.0.0.1", 9000), "method":"POST", "path":"/"})
    import pytest
    with pytest.raises(HTTPException) as exc:
        require_private_service(request)
    assert exc.value.status_code == 403


def test_private_auth_rejects_short_key(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.setenv("PAGECHECK_PRIVATE_API_KEY", "too-short")
    app = FastAPI()
    app.include_router(route.router)
    client = TestClient(app, client=("127.0.0.1", 1234))
    assert client.post("/v1/temporary/restore", json={"token": new_recovery_token()},
                       headers={"x-pagecheck-service-key": "too-short"}).status_code == 403


def test_private_routes_save_restore_revoke(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    secret = "a" * 40
    monkeypatch.setenv("PAGECHECK_PRIVATE_API_KEY", secret)
    store = FakeStore()
    monkeypatch.setattr(route, "_store", lambda: store)
    app = FastAPI()
    app.include_router(route.router)
    client = TestClient(app, client=("192.0.2.20", 9000))
    header = {"x-pagecheck-service-key": secret}
    report = {"schema_version": "audit-report-1.0", "requested_url": "https://example.org"}
    assert client.get("/v1/temporary/save").status_code == 405
    assert client.post("/v1/temporary/save", json={"report": report}).status_code == 403
    saved = client.post("/v1/temporary/save", json={"report": report}, headers=header)
    assert saved.status_code == 201
    assert saved.headers["cache-control"] == "no-store"
    token = saved.json()["recovery_token"]
    assert "token" not in report
    # The real PostgreSQL repository hashes tokens (Stage 22A tests);
    # this memory-only fake intentionally uses them as dictionary keys.
    assert client.post("/v1/temporary/restore", json={"token": token}, headers=header).json() == report
    assert client.post("/v1/temporary/restore", json={"token": new_recovery_token()}, headers=header).status_code == 404
    image = client.post("/v1/temporary/image", json={"token": token, "viewport": "desktop", "kind": "initial"}, headers=header)
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert client.post("/v1/temporary/revoke", json={"token": token}, headers=header).status_code == 204
    assert client.post("/v1/temporary/restore", json={"token": token}, headers=header).status_code == 404


def test_private_api_declines_large_body(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "development")
    monkeypatch.delenv("PAGECHECK_PRIVATE_API_KEY", raising=False)
    app = FastAPI()
    app.include_router(route.router)
    client = TestClient(app, client=("127.0.0.1", 1234))
    response = client.post("/v1/temporary/save", json={"report": {}}, headers={"content-length": str(7*1024*1024)})
    assert response.status_code == 413
