"""Restore an explicitly opened local history report after a Streamlit browser refresh.

Only the opaque audit ID is persisted in the URL. Report data stays in the
local-only history API, not in query parameters or browser storage.
"""
from __future__ import annotations

import re
from collections.abc import Callable, MutableMapping
from typing import Any

_AUDIT_ID = re.compile(r"[0-9a-f]{32}\Z")
_PARAM = "audit"
_SESSION_ID = "pagecheck_active_history_id"


def valid_audit_id(value: object) -> str | None:
    return value if isinstance(value, str) and _AUDIT_ID.fullmatch(value) else None


def clear_active_audit(session: MutableMapping[str, Any], query: MutableMapping[str, Any]) -> None:
    """Detach the current URL from an old history entry without deleting its data."""
    session.pop(_SESSION_ID, None)
    if _PARAM in query:
        del query[_PARAM]


def remember_active_audit(
    session: MutableMapping[str, Any], query: MutableMapping[str, Any], audit_id: str,
) -> None:
    """Keep a saved audit's ID in the URL so the browser can restore it on F5."""
    key = valid_audit_id(audit_id)
    if key is None:
        raise ValueError("Invalid saved audit ID")
    session[_SESSION_ID] = key
    if query.get(_PARAM) != key:
        query[_PARAM] = key


def resume_active_audit(
    session: MutableMapping[str, Any], query: MutableMapping[str, Any],
    load: Callable[[str], dict[str, Any]],
) -> bool:
    """Load the last opened saved report if the browser's session was reset.

    This function never executes the audit engines. The provided callable must
    load an existing report from the local history API.
    """
    raw_id = query.get(_PARAM)
    if raw_id is None:
        return False
    audit_id = valid_audit_id(raw_id)
    if audit_id is None:
        clear_active_audit(session, query)
        return False
    if (session.get(_SESSION_ID) == audit_id
            and isinstance(session.get("pagecheck_report"), dict)):
        return False
    report = load(audit_id)  # Load before touching session state on failure.
    session["pagecheck_report"] = report
    session["pagecheck_origin"] = "Saved audit · local history"
    session[_SESSION_ID] = audit_id
    session.pop("pagecheck_history_notice", None)
    return True
