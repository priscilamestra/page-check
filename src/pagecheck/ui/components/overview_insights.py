"""Stage 19A: presentation-only summaries for Page Check's executive Overview.

No IO, scoring, network, or source-state inference. In particular, unverified
checks are not page defects and are never mixed into the actionable chart.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from html import escape
from typing import Any

from pagecheck.ui.components.coverage_details import not_verified_by_area, source_rows

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _count(value: object) -> int:
    """Never turn booleans, malformed values or negative counts into chart data."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(value, 0)
    return 0


def actionable_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Counts of checks needing action, separated from passed/unverified checks.

    Reports keep summary.by_module as their authoritative check counts. Fall
    back to individual findings for older imported reports without that index.
    """
    modules = _mapping(_mapping(report.get("summary")).get("by_module"))
    results: list[dict[str, Any]] = []
    if modules:
        for area, values in modules.items():
            if not isinstance(area, str) or not area.strip():
                continue
            counts = _mapping(values)
            issues = _count(counts.get("failed"))
            reviews = _count(counts.get("warning"))
            if issues or reviews:
                results.append({"area": area, "issues": issues, "reviews": reviews,
                                "total": issues + reviews})
    else:
        grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"issues": 0, "reviews": 0})
        for item in report.get("findings") or []:
            if not isinstance(item, Mapping):
                continue
            status = item.get("status")
            if status not in {"failed", "warning"}:
                continue
            area = str(item.get("module") or "other")
            grouped[area]["issues" if status == "failed" else "reviews"] += 1
        for area, values in grouped.items():
            results.append({"area": area, **values,
                            "total": values["issues"] + values["reviews"]})
    return sorted(results, key=lambda row: (-row["total"], -row["issues"], row["area"].lower()))


def prioritized_findings(report: Mapping[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    """Display top actionable records only; preserve original source data."""
    findings = [dict(row) for row in report.get("findings") or []
                if isinstance(row, Mapping) and row.get("status") in {"failed", "warning"}]
    findings.sort(key=lambda row: (
        SEVERITY_ORDER.get(str(row.get("severity") or "info"), 5),
        0 if row.get("status") == "failed" else 1,
        str(row.get("id") or row.get("check_id") or ""),
    ))
    return findings[:max(0, limit)]



def prioritized_unique_findings(report: Mapping[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    """Prioritize up to ``limit`` distinct actionable problems.

    Repeated checks about the same issue (for example, the same image symptom
    observed on desktop and mobile) are summarized, but every underlying
    finding remains available in the Issues tab and exported report.
    """
    ordered = prioritized_findings(report, limit=len(report.get("findings") or []))
    grouped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in ordered:
        key = (
            str(row.get("module") or ""),
            str(row.get("title") or ""),
            str(row.get("recommendation") or ""),
            str(row.get("severity") or ""),
            str(row.get("status") or ""),
        )
        if key in grouped:
            grouped[key]["occurrences"] += 1
            continue
        grouped[key] = {**row, "occurrences": 1}
    return list(grouped.values())[:max(0, limit)]


def missing_evidence_rows(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [{"area": area, "total": count} for area, count in not_verified_by_area(report)]


def source_counts(report: Mapping[str, Any]) -> dict[str, int]:
    """Counts source states, not individual checks. 'Not verified' may mean failed."""
    result = {"completed": 0, "partial": 0, "not_verified": 0}
    for source in source_rows(report):
        result[source["status"]] += 1
    return result


def count_label(value: int, singular: str, plural: str | None = None) -> str:
    return f"{value} {singular if value == 1 else (plural or singular + 's')}"


def area_bars_html(rows: list[dict[str, Any]], *, missing: bool = False) -> str:
    """Accessible, single-measure labeled bar chart, with no hover dependency.

    HTML labels are escaped; bar widths come only from validated non-negative
    integers. Never stacks Passed + Reviews + Issues into an ambiguous bar.
    """
    safe_rows = [row for row in rows if _count(row.get("total")) > 0]
    if not safe_rows:
        return ""
    max_value = max(_count(row.get("total")) for row in safe_rows)
    html = ['<div role="img" aria-label="' + (
        'Not verified checks grouped by area' if missing
        else 'Actionable issues and reviews grouped by area') + '">']
    for row in safe_rows:
        total = _count(row.get("total"))
        label = escape(str(row.get("area") or "Other").replace("_", " ").title())
        if missing:
            breakdown = count_label(total, "unverified check")
            color = "#718096"
        else:
            issues = _count(row.get("issues"))
            reviews = _count(row.get("reviews"))
            breakdown = (f"{count_label(issues, 'issue')} · "
                         f"{count_label(reviews, 'review')}")
            color = "#D45B68" if issues else "#C58A41"
        width = round(100 * total / max_value, 4)
        aria = escape(f"{label}: {breakdown}", quote=True)
        html.append(
            '<div style="margin:0 0 14px 0" aria-label="' + aria + '">'
            '<div style="display:flex;justify-content:space-between;gap:10px;'
            'align-items:baseline;flex-wrap:wrap;margin-bottom:6px">'
            '<span style="font-weight:600">' + label + '</span>'
            '<span style="font-size:.88rem;opacity:.82">' + escape(breakdown) + '</span>'
            '</div>'
            '<div style="height:12px;border-radius:6px;background:rgba(128,128,128,.18);'
            'overflow:hidden">'
            f'<div style="height:100%;width:{width}%;background:{color};'
            'border-radius:6px"></div>'
            '</div></div>'
        )
    html.append('</div>')
    return "".join(html)


def coverage_bars_html(counts: Mapping[str, int]) -> str:
    """Three independent status bars, each relative to the same source total."""
    total = sum(_count(counts.get(key)) for key in ("completed", "partial", "not_verified"))
    if not total:
        return ""
    entries = (("completed", "Completed", "#23856F"),
               ("partial", "Limited", "#C58A41"),
               ("not_verified", "Not verified", "#718096"))
    parts = ['<div role="img" aria-label="Audit coverage by source status">']
    for key, label, color in entries:
        count = _count(counts.get(key))
        width = round(100 * count / total, 4)
        parts.append(
            '<div style="margin:0 0 11px 0">'
            '<div style="display:flex;justify-content:space-between;gap:10px;'
            'margin-bottom:5px">'
            f'<span style="font-weight:600">{label}</span>'
            f'<span style="opacity:.82">{count} / {total} sources</span></div>'
            '<div style="height:11px;border-radius:6px;background:rgba(128,128,128,.18);'
            'overflow:hidden">'
            f'<div style="height:100%;width:{width}%;background:{color};'
            'border-radius:6px"></div></div></div>'
        )
    parts.append('</div>')
    return "".join(parts)
