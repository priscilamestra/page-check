"""Honest deployment readiness checklist for Page Check's current architecture.

This is intentionally a *blocking* gate, not a Vercel configuration generator.
Changing environment variables cannot make the current local-only scanner safe.
"""
from __future__ import annotations

from typing import Any


def vercel_readiness(*, websocket_ui_replaced: bool = False,
                     durable_storage_or_stateless_exports: bool = False,
                     isolated_public_scanner: bool = False,
                     abuse_limits_and_privacy: bool = False,
                     integration_tests_passed: bool = False) -> dict[str, Any]:
    checks = [
        ("websocket_ui", "A Vercel-compatible UI replaces Streamlit's persistent WebSocket server.",
         websocket_ui_replaced),
        ("history", "No shared SQLite on ephemeral function storage; use durable storage or client-only exports.",
         durable_storage_or_stateless_exports),
        ("scanner", "Public URL scanning runs with verified DNS/redirect protections and isolated browser egress.",
         isolated_public_scanner),
        ("abuse_and_privacy", "Rate/concurrency limits, data deletion/retention, and report access are enforced.",
         abuse_limits_and_privacy),
        ("test", "Full production-like end-to-end and security checks were executed successfully.",
         integration_tests_passed),
    ]
    return {
        "target": "vercel",
        "deploy_ready": all(ok for _, _, ok in checks),
        "checks": [{"id": name, "required": description, "passed": ok}
                   for name, description, ok in checks],
        "blocked_by": [name for name, _, ok in checks if not ok],
        "note": "No deployment performed; no user account/login is assumed.",
    }
