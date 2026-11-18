"""Offline regression checks for Render Free's kernel-denied audit worker."""
from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pagecheck.common.security import deployment
from pagecheck.common.security.isolated_audit import AuditIsolationUnavailable, verify_worker_launcher
from pagecheck.common.security.public_fetch_broker import (
    PublicBrokerTransport, public_fetch_broker,
)
from pagecheck.acquisition.http.safe_transport import UnsafeDestination


def test_flag_requires_explicit_worker_isolation(monkeypatch):
    settings = {
        'PAGECHECK_ENV': 'production',
        'PAGECHECK_PUBLIC_AUDITS_ENABLED': '1',
        'PAGECHECK_EGRESS_ISOLATED': '0',
        'PAGECHECK_AUDIT_WORKER_ISOLATED': '1',
        'PAGECHECK_ALLOW_LIVE_FETCH': '1',
        'PAGECHECK_ALLOW_LIVE_BROWSER': '1',
        'PAGECHECK_PRIVATE_API_KEY': 'k' * 48,
    }
    for k, v in settings.items():
        monkeypatch.setenv(k, v)
    assert deployment.production_scan_configured()
    for flag in ('PAGECHECK_AUDIT_WORKER_ISOLATED', 'PAGECHECK_ALLOW_LIVE_FETCH',
                 'PAGECHECK_ALLOW_LIVE_BROWSER', 'PAGECHECK_PUBLIC_AUDITS_ENABLED'):
        with monkeypatch.context() as m:
            m.setenv(flag, '0')
            assert not deployment.production_scan_configured()


def test_broker_delivers_only_bounded_public_gets(monkeypatch, tmp_path):
    # STAGE43_WINDOWS_FAIL_CLOSED_TEST_V2: Windows must reject Unix-socket broker startup.
    if __import__("sys").platform == "win32":
        import pytest
        from pagecheck.common.security import public_fetch_broker as broker_module
        with pytest.raises(RuntimeError, match="isolated Unix-socket broker is unavailable"):
            broker_module._BrokerServer(str(tmp_path / "b.sock"))
        return

    from pagecheck.common.security import public_fetch_broker as broker_module
    seen = []
    def handler(req):
        seen.append(str(req.url))
        return httpx.Response(200, headers={'content-type': 'text/html'}, text='<!doctype html><title>OK</title>')
    monkeypatch.setattr(broker_module, 'PublicHTTPTransport', lambda: httpx.MockTransport(handler))
    with public_fetch_broker(tmp_path / 'b.sock'):
        with httpx.Client(transport=PublicBrokerTransport(str(tmp_path / 'b.sock'))) as client:
            response = client.get('https://example.org/a')
            assert response.status_code == 200
            assert '<title>OK' in response.text
            assert seen == ['https://example.org/a']
            with pytest.raises(ValueError):
                client.get('http://127.0.0.1/private')
            with pytest.raises(ValueError):
                client.post('https://example.org/anything')
    assert len(seen) == 1


def test_no_launcher_refuses_production_scan():
    with pytest.raises(AuditIsolationUnavailable):
        verify_worker_launcher('/not/a/real/network/sandbox')


def test_api_rejects_public_without_private_key(monkeypatch):
    from pagecheck.api.routes import audit
    monkeypatch.setenv('PAGECHECK_ENV', 'production')
    monkeypatch.setenv('PAGECHECK_PRIVATE_API_KEY', 'k' * 48)
    monkeypatch.setenv('PAGECHECK_AUDIT_WORKER_ISOLATED', '1')
    monkeypatch.setenv('PAGECHECK_PUBLIC_AUDITS_ENABLED', '1')
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_FETCH', '1')
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_BROWSER', '1')
    app = FastAPI()
    app.include_router(audit.router)
    r = TestClient(app).post('/v1/audits/page', json={
        'url': 'https://example.org/', 'niche': 'Tech', 'objective': 'leads'
    })
    assert r.status_code == 403


def test_isolated_mode_calls_only_guarded_worker(monkeypatch):
    from pagecheck.api.routes import audit
    monkeypatch.setenv('PAGECHECK_ENV', 'production')
    monkeypatch.setenv('PAGECHECK_PRIVATE_API_KEY', 'k' * 48)
    monkeypatch.setenv('PAGECHECK_AUDIT_WORKER_ISOLATED', '1')
    monkeypatch.setenv('PAGECHECK_PUBLIC_AUDITS_ENABLED', '1')
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_FETCH', '1')
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_BROWSER', '1')
    called = []
    monkeypatch.setattr(audit, '_execute_audit', lambda *_: (_ for _ in ()).throw(AssertionError('direct executor used')))
    monkeypatch.setattr(audit, 'run_isolated_audit', lambda p: called.append(p.url) or {'isolated': True})
    from pagecheck.common.security.admission import AuditAdmission
    monkeypatch.setattr(audit, 'production_audit_admission', AuditAdmission())
    app = FastAPI()
    app.include_router(audit.router)
    r = TestClient(app).post('/v1/audits/page',
        json={'url':'https://example.org/', 'niche':'Technology', 'objective':'leads'},
        headers={'X-PageCheck-Service-Key':'k' * 48})
    assert r.status_code == 200 and r.json() == {'isolated': True}
    assert called == ['https://example.org/']


def test_isolation_ready_route_is_private(monkeypatch):
    from pagecheck.api.routes import audit
    monkeypatch.setenv('PAGECHECK_ENV', 'production')
    monkeypatch.setenv('PAGECHECK_PRIVATE_API_KEY', 'k' * 48)
    app = FastAPI()
    app.include_router(audit.router)
    client = TestClient(app)
    assert client.post('/v1/audits/isolation-check').status_code == 403
    called = []
    monkeypatch.setattr(audit, 'verify_worker_python_exec', lambda launcher: called.append(launcher))
    monkeypatch.setenv('PAGECHECK_BROWSER_SECCOMP_LAUNCHER','/safe/path')
    r = client.post('/v1/audits/isolation-check', headers={'X-PageCheck-Service-Key':'k' * 48})
    assert r.status_code == 200
    assert r.json()['container_wide_egress_firewall'] is False
    assert called == ['/safe/path']
