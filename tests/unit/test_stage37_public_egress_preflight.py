"""Offline regression checks for the Stage37 deployment preflight."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/stage37_public_egress_preflight.py"


def _invoke(*, enabled: bool = False) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PAGECHECK_ENV"] = "production"
    env["PAGECHECK_PUBLIC_AUDITS_ENABLED"] = "1" if enabled else "0"
    env["PAGECHECK_EGRESS_ISOLATED"] = "0"
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=ROOT, env=env,
        text=True, capture_output=True, timeout=15, check=False,
    )


def test_preflight_passes_without_network_and_never_claims_render_isolation():
    result = _invoke()
    assert result.returncode == 0, result.stderr
    assert "STAGE37_APPLICATION_EGRESS_PRECHECK_PASSED" in result.stdout
    assert "HOSTED_OS_EGRESS_ISOLATION_NOT_VERIFIED" in result.stdout
    assert "PUBLIC_AUDITS_MUST_REMAIN_DISABLED" in result.stdout
    assert "RENDER_EGRESS_ISOLATED" not in result.stdout


def test_preflight_fails_closed_if_operator_prematurely_enables_public_audits():
    result = _invoke(enabled=True)
    assert result.returncode != 0
    assert "STAGE37_PRECHECK_FAILED" in result.stderr


def test_preflight_contains_no_live_socket_or_external_service_dependency():
    script = SCRIPT.read_text(encoding="utf-8")
    assert 'patch("socket.getaddrinfo"' in script
    assert 'patch.object(backend._backend, "connect_tcp"' in script
    assert "docker run" not in script
