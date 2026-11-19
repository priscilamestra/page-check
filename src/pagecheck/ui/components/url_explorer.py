"""Stage 19A UX correction: compact, lossless URL-check exploration.

Pure presentation helpers. No audit changes, network calls, or file writes.
Full technical evidence remains on the original check for explicit inspection.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit

CHECK_AREAS = ("tracking", "navigation", "forms")
STATUS_TEXT = {
    "failed": "Issue",
    "warning": "Needs review",
    "passed": "Passed",
    "not_verified": "Not verified",
    "not_applicable": "Not applicable",
}
_STATUS_SORT = {"failed": 0, "warning": 1, "not_verified": 2, "passed": 3,
                "not_applicable": 4}
_SENSITIVE_TERMS = ("token", "secret", "api_key", "apikey", "password", "passwd",
                    "session", "auth", "credential", "signature", "jwt", "code")


def _is_sensitive(name: str) -> bool:
    low = name.lower()
    return any(term in low for term in _SENSITIVE_TERMS)


def campaign_parameters(report: Mapping[str, Any]) -> dict[str, Any]:
    """Describe query parameters, never guess analytics collection or attribution."""
    raw = report.get("requested_url") or report.get("final_url") or ""
    if not isinstance(raw, str):
        raw = ""
    try:
        pairs = parse_qsl(urlsplit(raw).query, keep_blank_values=True)
    except ValueError:
        pairs = []
    values = []
    utm_count = 0
    for name, value in pairs:
        if name.lower().startswith("utm_"):
            utm_count += 1
        values.append({"Parameter": name[:120],
                       "Value": "[hidden]" if _is_sensitive(name) else value[:120],
                       "Type": "UTM" if name.lower().startswith("utm_") else "Other"})
    return {"parameters": values, "total": len(values), "utm": utm_count,
            "has_utm": utm_count > 0}


def check_rows(report: Mapping[str, Any],
               describe: Callable[[dict[str, Any]], tuple[str, str | None]] | None = None
               ) -> list[dict[str, Any]]:
    """Keep all relevant checks, stable source indices and original evidence."""
    checks = report.get("checks") or []
    if not isinstance(checks, list):
        return []
    rows: list[dict[str, Any]] = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict) or check.get("module") not in CHECK_AREAS:
            continue
        if describe is not None:
            title, recommendation = describe(check)
        else:
            title = check.get("title") or check.get("check_id") or check.get("id") or "Check"
            recommendation = check.get("recommendation") or ""
        status = str(check.get("status") or "not_verified")
        if status not in STATUS_TEXT:
            status = "not_verified"
        evidence = check.get("evidence") or {}
        if not isinstance(evidence, Mapping):
            evidence = {}
        element = str(evidence.get("text") or evidence.get("id") or evidence.get("tag") or "")
        destination = str(evidence.get("resolved_url") or evidence.get("resolved_action")
                          or evidence.get("href") or evidence.get("action") or "")
        location = str(evidence.get("selector") or evidence.get("selector_hint")
                       or evidence.get("form_index") or "")
        rows.append({
            "index": index,
            "area": str(check.get("module")),
            "title": str(title or "Check"),
            "status": status,
            "label": STATUS_TEXT[status],
            "recommendation": str(recommendation or ""),
            "check_id": str(check.get("check_id") or check.get("id") or ""),
            "evidence": evidence,
            "source": str(check.get("source") or ""),
            "element": element,
            "destination": destination,
            "location": location,
        })
    return sorted(rows, key=lambda r: (_STATUS_SORT[r["status"]],
                                       CHECK_AREAS.index(r["area"]), r["index"]))


def group_check_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse repeated diagnoses while retaining every original check."""
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["area"], row["status"], row["title"], row["recommendation"])
        if key in grouped:
            grouped[key]["members"].append(row)
            grouped[key]["occurrences"] += 1
        else:
            grouped[key] = {**row, "members": [row], "occurrences": 1}
    return list(grouped.values())


def area_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = Counter((row["area"], row["status"]) for row in rows)
    result = []
    for area in CHECK_AREAS:
        result.append({
            "Area": area.title(),
            "Issues": summary[(area, "failed")],
            "Needs review": summary[(area, "warning")],
            "Not verified": summary[(area, "not_verified")],
            "Passed": summary[(area, "passed")],
            "Not applicable": summary[(area, "not_applicable")],
        })
    return result


def filter_rows(rows: list[dict[str, Any]], *, area: str = "All",
                status: str = "Needs attention", search: str = "") -> list[dict[str, Any]]:
    needle = search.strip().casefold()
    matches = []
    for row in rows:
        if area != "All" and row["area"] != area.lower():
            continue
        if status == "Needs attention" and row["status"] not in {"failed", "warning"}:
            continue
        if status not in {"All", "Needs attention"} and row["label"] != status:
            continue
        haystack = " ".join((row["title"], row["check_id"], row["recommendation"],
                             row.get("element", ""), row.get("destination", ""),
                             row.get("location", "")))
        if needle and needle not in haystack.casefold():
            continue
        matches.append(row)
    return matches
