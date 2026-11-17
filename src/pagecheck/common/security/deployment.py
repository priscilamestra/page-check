"""Fail-closed deployment policy for public URL audits.

Production enablement requires separately verified egress isolation; environment
flags are approval gates, not evidence that the infrastructure is isolated.
"""
from __future__ import annotations

import os

LOCAL_MODES = frozenset({"local", "dev", "development", "test"})


def is_local_development() -> bool:
    return os.environ.get("PAGECHECK_ENV", "local").strip().lower() in LOCAL_MODES


def production_scan_configured() -> bool:
    """Admission gate only; the operator must verify network isolation first."""
    return (
        not is_local_development()
        and os.environ.get("PAGECHECK_PUBLIC_AUDITS_ENABLED") == "1"
        and os.environ.get("PAGECHECK_EGRESS_ISOLATED") == "1"
        and os.environ.get("PAGECHECK_ALLOW_LIVE_FETCH") == "1"
        and os.environ.get("PAGECHECK_ALLOW_LIVE_BROWSER") == "1"
        and len(os.environ.get("PAGECHECK_PRIVATE_API_KEY", "")) >= 32
    )


def live_fetch_enabled() -> bool:
    if is_local_development():
        return os.environ.get("PAGECHECK_ALLOW_LIVE_FETCH") == "1"
    return production_scan_configured()


def live_browser_enabled() -> bool:
    return (live_fetch_enabled() and os.environ.get("PAGECHECK_ALLOW_LIVE_BROWSER") == "1")
