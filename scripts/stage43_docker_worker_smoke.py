"""Smoke within stage43-api Docker container (no database key or UI needed)."""
from __future__ import annotations

import os
from pathlib import Path

from pagecheck.api.schemas.audit import PageAuditRequest
from pagecheck.common.security.isolated_audit import (
    verify_worker_python_exec, run_isolated_audit,
)


def main():
    launcher = os.environ.get("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", "")
    verify_worker_python_exec(launcher)
    print("STAGE43_LINUX_PYTHON_SOCKET_GUARD_PASSED", flush=True)
    report = run_isolated_audit(PageAuditRequest(
        url="https://example.com/", niche="Technology", objective="leads",
        language="en", keywords=["example"],
    ))
    states = report.get("source_states", {})
    if states.get("seo") != "completed" or states.get("conversion") != "completed":
        raise AssertionError("Incomplete source states for HTML analysis")
    print("STAGE43_ISOLATED_HTML_AUDIT_PASSED", flush=True)
    paths = report.get("screenshots", {})
    if not all(any(Path(p).is_file() for p in paths.get(v, {}).values())
               for v in ("desktop", "mobile")):
        raise AssertionError("Desktop and mobile screenshot files were not produced")
    print("STAGE43_ISOLATED_BROWSER_SCREENSHOTS_PASSED", flush=True)
    print("STAGE43_WORKER_BROKER_512MB_SMOKE_PASSED", flush=True)


if __name__ == "__main__":
    main()
