"""Offline regression checks for staging release gate; no live network or Neon."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pagecheck.ops import release_smoke as smoke


def valid_env():
    return {
        "PAGECHECK_ENV": "production", "PAGECHECK_PUBLIC_AUDITS_ENABLED": "0",
        "PAGECHECK_EGRESS_ISOLATED": "0", "PAGECHECK_ALLOW_LIVE_FETCH": "0",
        "PAGECHECK_ALLOW_LIVE_BROWSER": "0", "PAGECHECK_PRIVATE_API_KEY": "x" * 40,
        "PAGECHECK_DATABASE_URL": "postgresql://REDACTED",
    }


@pytest.mark.parametrize("name", [
    "PAGECHECK_PUBLIC_AUDITS_ENABLED", "PAGECHECK_EGRESS_ISOLATED",
    "PAGECHECK_ALLOW_LIVE_FETCH", "PAGECHECK_ALLOW_LIVE_BROWSER",
])
def test_rejects_live_production_flags(name):
    env = valid_env()
    env[name] = "1"
    with pytest.raises(smoke.ReleaseSmokeError):
        smoke._require_staging_policy(env)


def test_no_secret_is_printed_on_failure(monkeypatch, capsys):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.setenv("PAGECHECK_PRIVATE_API_KEY", "x" * 40)
    monkeypatch.setenv("PAGECHECK_DATABASE_URL", "postgresql://SECRET-EXAMPLE")
    assert smoke.main() == 1
    out = capsys.readouterr().out
    assert "SECRET-EXAMPLE" not in out
    assert "x" * 40 not in out


def test_read_only_smoke_checks_health_auth_and_schema(monkeypatch):
    calls = []

    def fake_http(path, *, headers=None, body=None):
        calls.append((path, headers, body))
        if path == "/health":
            return (200, json.dumps({"status": "ok", "service": "pagecheck-api"}).encode())
        if headers.get("X-PageCheck-Service-Key"):
            return (404, b"")
        return (403, b"")

    monkeypatch.setattr(smoke, "_http_status", fake_http)
    monkeypatch.setattr(smoke, "_database_schema_ok", lambda: True)
    result = smoke.run_smoke(valid_env())
    assert result[-1] == "STAGE38_HOSTED_STAGING_SMOKE_PASSED"
    assert len(calls) == 3
    assert all(path != "/v1/audits/page" for path, _, _ in calls)


def test_auth_misconfiguration_fails(monkeypatch):
    def fake_http(path, *, headers=None, body=None):
        if path == "/health":
            return 200, b'{"status":"ok","service":"pagecheck-api"}'
        return 403, b""

    monkeypatch.setattr(smoke, "_http_status", fake_http)
    monkeypatch.setattr(smoke, "_database_schema_ok", lambda: True)
    with pytest.raises(smoke.ReleaseSmokeError, match="Authenticated private"):
        smoke.run_smoke(valid_env())


def test_render_api_migration_and_scan_flags_unchanged():
    root = Path(__file__).resolve().parents[2]
    content = (root / "render.yaml").read_text(encoding="utf-8")
    assert "preDeployCommand: /app/.venv/bin/python /app/scripts/postgres_temporary_migrate.py" in content
    assert 'PAGECHECK_PUBLIC_AUDITS_ENABLED\n        value: "0"' in content
    assert 'PAGECHECK_EGRESS_ISOLATED\n        value: "0"' in content
