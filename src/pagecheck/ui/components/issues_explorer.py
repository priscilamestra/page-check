"""Stage 19B: compact, lossless, deterministic exploration of audit findings.

No Streamlit calls, network access, or mutation of report data. A finding that
needs review is not silently promoted to a confirmed page defect.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from typing import Any

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
RESULT_RANK = {"failed": 0, "warning": 1, "not_verified": 2, "passed": 3,
               "not_applicable": 4}
RESULT_LABEL = {"failed": "Issue", "warning": "Needs review",
                "not_verified": "Not verified", "passed": "Passed",
                "not_applicable": "Not applicable"}


def finding_rows(
    report: Mapping[str, Any],
    *,
    describe: Callable[[dict[str, Any]], tuple[str, str | None]] | None = None,
    team_label: Callable[[object], str] | None = None,
) -> list[dict[str, Any]]:
    """Keep every finding with a stable original index and original evidence."""
    findings = report.get("findings") or []
    if not isinstance(findings, list):
        return []
    output: list[dict[str, Any]] = []
    for index, item in enumerate(findings):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "not_verified")
        if status not in RESULT_LABEL:
            status = "not_verified"
        severity = str(item.get("severity") or "info").lower()
        if severity not in SEVERITY_RANK:
            severity = "info"
        title, action = (describe(item) if describe else
                         (item.get("title") or item.get("check_id") or "Finding",
                          item.get("recommendation") or ""))
        team = team_label(item.get("team")) if team_label else str(item.get("team") or "Other")
        output.append({
            "index": index, "title": str(title or "Finding"),
            "recommendation": str(action or ""),
            "area": str(item.get("module") or "other").lower(),
            "team": team, "status": status, "result": RESULT_LABEL[status],
            "severity": severity, "severity_label": severity.title(),
            "source": str(item.get("source") or "Unknown"),
            "check_id": str(item.get("check_id") or item.get("id") or ""),
            "evidence": item.get("evidence") or {},
        })
    return sorted(output, key=lambda row: (
        0 if row["status"] in {"failed", "warning"} else 1,
        SEVERITY_RANK[row["severity"]], RESULT_RANK[row["status"]], row["index"],
    ))


def finding_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    by_status = Counter(row["status"] for row in rows)
    return {
        "total": len(rows),
        "issues": by_status["failed"],
        "reviews": by_status["warning"],
        "critical_issues": sum(row["status"] == "failed" and row["severity"] == "critical"
                               for row in rows),
        "areas_affected": len({row["area"] for row in rows
                               if row["status"] in {"failed", "warning"}}),
    }


def filter_findings(
    rows: list[dict[str, Any]], *, area: str = "All", result: str = "Needs attention",
    priority: str = "All", search: str = "",
) -> list[dict[str, Any]]:
    needle = search.strip().casefold()
    selected: list[dict[str, Any]] = []
    for row in rows:
        if area != "All" and row["area"] != area.casefold():
            continue
        if result == "Needs attention":
            if row["status"] not in {"failed", "warning"}:
                continue
        elif result != "All" and row["result"] != result:
            continue
        if priority != "All" and row["severity"] != priority.casefold():
            continue
        haystack = " ".join((row["title"], row["area"], row["team"],
                            row["check_id"], row["recommendation"]))
        if needle and needle not in haystack.casefold():
            continue
        selected.append(row)
    return selected


def findings_table(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{
        "Priority": row["severity_label"], "Area": row["area"].replace("_", " ").title(),
        "Finding": row["title"][:120], "Result": row["result"],
        "Suggested action": row["recommendation"][:140] or "Review the evidence",
    } for row in rows]


# User-facing labels for evidence already produced by the audit. Do not infer
# selectors, statuses or failed page elements when the scan did not collect them.
_EVIDENCE_KEYS = (
    ("page_url", "Page URL"), ("url", "URL"),
    ("target_url", "Target URL"), ("href", "Link destination"),
    ("destination", "Destination"), ("src", "Image source"),
    ("image_url", "Image URL"), ("selector", "Element selector"),
    ("dom_path", "DOM location"), ("xpath", "Element location"),
    ("element_html", "Element HTML"), ("outer_html", "Element HTML"),
    ("tag_name", "HTML tag"), ("tag", "HTML tag"),
    ("text", "Element text"), ("link_text", "Link text"),
    ("attribute", "Attribute"), ("actual", "Observed value"),
    ("actual_value", "Observed value"), ("observed", "Observed value"),
    ("value", "Recorded value"), ("expected", "Expected value"),
    ("expected_value", "Expected value"),
    ("status_code", "HTTP status"), ("http_status", "HTTP status"),
    ("reason", "Reason"), ("message", "Diagnostic detail"),
    ("snippet", "HTML excerpt"),
)


def finding_evidence_summary(evidence: object, *, limit: int = 6) -> list[tuple[str, str]]:
    """Present only recorded, recognizable diagnostic evidence without guessing.

    Produces bounded, plain text for Streamlit st.text. Other raw fields still
    exist in the saved/exported report; the view never changes the source data.
    """
    if not isinstance(evidence, Mapping):
        return []
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    # Real reports may nest element details in a local dictionary. Read at
    # most one level; never flatten arbitrary data or echo unknown fields.
    sources = [evidence]
    for key in ("element", "location", "details", "response"):
        nested = evidence.get(key)
        if isinstance(nested, Mapping):
            sources.append(nested)
    for key, label in _EVIDENCE_KEYS:
        for source in sources:
            value = source.get(key)
            if value is None or isinstance(value, bool):
                continue
            if not isinstance(value, (str, int, float)):
                continue
            string_value = " ".join(str(value).split())
            if not string_value or string_value in seen:
                continue
            seen.add(string_value)
            result.append((label, string_value[:500] + ("…" if len(string_value) > 500 else "")))
            if len(result) >= limit:
                return result
    return result
