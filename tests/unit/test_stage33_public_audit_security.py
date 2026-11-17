"""No external network needed: production gates, admission, auth and UI wiring."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from pagecheck.api.routes import audit as audit_route
from pagecheck.common.security.admission import AuditAdmission, AuditAdmissionError
from pagecheck.common.security.deployment import live_fetch_enabled, production_scan_configured

PAYLOAD = {"url": "https://example.org/", "niche": "SaaS", "objective": "leads"}


def _prod(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.setenv("PAGECHECK_PUBLIC_AUDITS_ENABLED", "1")
    monkeypatch.setenv("PAGECHECK_EGRESS_ISOLATED", "1")
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_BROWSER", "1")
    monkeypatch.setenv("PAGECHECK_PRIVATE_API_KEY", "x" * 40)


def test_production_fails_closed_unless_every_required_gate_is_present(monkeypatch):
    _prod(monkeypatch)
    assert production_scan_configured() and live_fetch_enabled()
    for name in ("PAGECHECK_PUBLIC_AUDITS_ENABLED", "PAGECHECK_EGRESS_ISOLATED",
                 "PAGECHECK_ALLOW_LIVE_FETCH", "PAGECHECK_ALLOW_LIVE_BROWSER",
                 "PAGECHECK_PRIVATE_API_KEY"):
        with monkeypatch.context() as m:
            m.delenv(name)
            assert not production_scan_configured()
            assert not live_fetch_enabled()


def test_audit_production_requires_key_before_network(monkeypatch):
    _prod(monkeypatch)
    fake = []
    monkeypatch.setattr(audit_route, "audit_page_html", lambda *args, **kwargs: fake.append(1) or {"ok": True})
    app = FastAPI()
    app.include_router(audit_route.router)
    client = TestClient(app, client=("192.0.2.11", 9000))
    assert client.post("/v1/audits/page", json=PAYLOAD).status_code == 403
    assert fake == []
    response = client.post("/v1/audits/page", json=PAYLOAD,
                           headers={"X-PageCheck-Service-Key": "x" * 40})
    assert response.status_code == 200
    assert len(fake) == 1


def test_production_rejects_nonpublic_urls_even_when_authorized(monkeypatch):
    _prod(monkeypatch)
    app = FastAPI()
    app.include_router(audit_route.router)
    client = TestClient(app)
    response = client.post("/v1/audits/page", json={**PAYLOAD, "url": "http://127.0.0.1/admin"},
                           headers={"X-PageCheck-Service-Key": "x" * 40})
    assert response.status_code == 403


def test_rate_limit_and_concurrency_have_no_queue():
    instant = [0.0]
    gate = AuditAdmission(max_concurrent=1, max_per_minute=2, clock=lambda: instant[0])
    with gate.enter():
        with pytest.raises(AuditAdmissionError, match="capacity"):
            with gate.enter():
                pass
    with gate.enter():
        pass
    with pytest.raises(AuditAdmissionError, match="rate limit"):
        with gate.enter():
            pass
    instant[0] = 61.0
    with gate.enter():
        pass


def test_stage33_blueprint_is_disabled_by_default():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    blueprint = (root / "render.yaml").read_text(encoding="utf-8")
    assert 'PAGECHECK_PUBLIC_AUDITS_ENABLED\n        value: "0"' in blueprint
    assert 'PAGECHECK_EGRESS_ISOLATED\n        value: "0"' in blueprint
    ui = (root / "src/pagecheck/ui/app.py").read_text(encoding="utf-8")
    assert 'disabled=scans_unavailable' in ui
    assert 'X-PageCheck-Service-Key' in ui
