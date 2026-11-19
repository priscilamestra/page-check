"""Compact, prioritized findings for a non-technical reader.

The underlying findings, severity and evidence remain unchanged. The screen
shows actionable items first and explains recorded evidence in readable labels.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

import streamlit as st

from pagecheck.reporting.english_copy import check_copy, team_name
from pagecheck.ui.components.issues_explorer import (
    filter_findings,
    finding_evidence_summary,
    finding_rows,
    finding_summary,
)

_PRIORITY_COLORS = {
    "critical": "red", "high": "red", "medium": "orange", "low": "gray", "info": "gray",
}


def _small_note(value: str, limit: int = 165) -> str:
    """Bound long automated explanations without modifying the source report."""
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def render_issues(report: dict[str, Any]) -> None:
    st.markdown("#### Issues & recommendations")
    rows = finding_rows(report, describe=check_copy, team_label=team_name)
    summary = finding_summary(rows)

    a, b, c = st.columns(3)
    a.metric("Confirmed issues", summary["issues"])
    b.metric("Needs review", summary["reviews"])
    c.metric("Areas affected", summary["areas_affected"])

    if not rows:
        st.info("No findings were reported by completed checks.")
        return

    # Offer only populated areas/results. Searching partial free-text and empty
    # filter combinations made the audit harder to understand.
    area_counts = Counter(row["area"] for row in rows)
    areas = ["All"] + sorted(area_counts)
    left, right = st.columns(2)
    with left:
        area = st.selectbox(
            "Area", areas, key="issues_area_simple_v3",
            format_func=lambda value: (
                f"All areas ({len(rows)})" if value == "All"
                else f"{value.replace('_', ' ').title()} ({area_counts[value]})"
            ),
        )
    scoped_rows = [r for r in rows if area == "All" or r["area"] == area]
    status_counts = Counter(r["status"] for r in scoped_rows)
    attention_count = status_counts["failed"] + status_counts["warning"]
    status_options = ["All"]
    if attention_count:
        status_options.insert(0, "Needs attention")
    for raw, label in (("failed", "Issue"), ("warning", "Needs review"),
                       ("passed", "Passed"), ("not_verified", "Not verified"),
                       ("not_applicable", "Not applicable")):
        if status_counts[raw]:
            status_options.append(label)
    label_for_status = {
        "failed": "Issue", "warning": "Needs review", "passed": "Passed",
        "not_verified": "Not verified", "not_applicable": "Not applicable",
    }
    count_for_label = {label: status_counts[raw] for raw, label in label_for_status.items()}
    with right:
        result = st.selectbox(
            "Result", status_options,
            key=f"issues_result_simple_v3_{area}",
            format_func=lambda value: (
                f"All results ({len(scoped_rows)})" if value == "All"
                else (f"Needs attention ({attention_count})" if value == "Needs attention"
                      else f"{value} ({count_for_label[value]})")
            ),
        )
    visible = filter_findings(rows, area=area, result=result, priority="All", search="")
    if not visible:
        st.info("No findings match these filters.")
        return

    # Pagination keeps the page short without hiding any matching finding.
    shown = visible[:10]
    if len(visible) > 10:
        page_count = (len(visible) + 9) // 10
        page = st.selectbox("Page", range(1, page_count + 1), key="issues_page_ux")
        start = (page - 1) * 10
        shown = visible[start:start + 10]
        st.caption(f"Showing {start + 1}–{start + len(shown)} of {len(visible)} findings")

    for row in shown:
        with st.container(border=True):
            body, status_col = st.columns([5, 1.5], vertical_alignment="top")
            with body:
                st.markdown(f"**{row['title']}**")
                st.caption(row["area"].replace("_", " ").title())
            with status_col:
                st.badge(
                    f"{row['severity_label']} · {row['result']}",
                    color=(_PRIORITY_COLORS[row["severity"]] if row["status"] == "failed"
                           else ("gray" if row["severity"] in {"low", "info"} else "orange")),
                )
            if row["status"] == "passed":
                st.caption("Check passed · no change needed")
            elif row["status"] == "not_verified":
                st.caption("Not verified · the scan did not establish a result")
            elif row["status"] == "not_applicable":
                st.caption("Not applicable to this page")

            evidence = finding_evidence_summary(row["evidence"])
            with st.expander("What was found and where"):
                st.markdown("**Problem**")
                st.write(row["description"] or row["title"])
                if evidence:
                    for label, value in evidence:
                        st.markdown(f"**{label}**")
                        if label in {"Element HTML", "HTML excerpt"}:
                            st.code(value, language="html")
                        elif label in {"Element selector", "Selector hint", "DOM location",
                                       "Element location", "Affected selectors"}:
                            st.code(value, language="css")
                        else:
                            st.text(value)
                else:
                    st.caption(
                        "The audit did not provide a usable element location or observed "
                        "value for this finding, so it cannot yet point to the exact "
                        "place to make the change."
                    )
                if row["status"] in {"failed", "warning"}:
                    st.markdown("**Correction**" if row["status"] == "failed" else
                                "**Recommended review**")
                    st.write(row["recommendation"] or
                             "Review this finding against the recorded evidence.")
                if row["check_id"]:
                    st.caption(f"Check: {row['check_id']}")
                if row["source"] and row["source"] != "Unknown":
                    st.caption(f"Evidence source: {row['source']}")
                st.json(row["evidence"], expanded=False)
