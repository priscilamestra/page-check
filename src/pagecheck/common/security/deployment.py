"""Fail-closed deployment policy for the local-only MVP.

This is not authentication or a full production scanner. Enabling public
URL fetch requires an independent sandbox/security review in a future stage.
"""
from __future__ import annotations

import os

LOCAL_MODES = frozenset({"local", "dev", "development", "test"})


def is_local_development() -> bool:
    return os.environ.get("PAGECHECK_ENV", "local").strip().lower() in LOCAL_MODES


def live_fetch_enabled() -> bool:
    return is_local_development() and os.environ.get("PAGECHECK_ALLOW_LIVE_FETCH") == "1"
