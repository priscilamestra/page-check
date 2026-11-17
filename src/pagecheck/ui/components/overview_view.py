"""Compact Sitebulb-inspired audit Overview (presentation only).

Shows a truthful audit snapshot, priorities and compact charts. Long explanations,
per-source limitations and check counts remain available on demand, without
changing report data, scoring, the audit engine or the other result tabs.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import streamlit as st

from pagecheck.reporting.english_copy import check_copy
from pagecheck.ui.components.coverage_details import source_rows
from pagecheck.ui.components.overview_dashboard import (
    OVERVIEW_STYLES, findings_html, metric_cards_html,
)
from pagecheck.ui.components.overview_insights import (
    prioritized_unique_findings, source_counts,
)
from pagecheck.ui.components.report_data import issue_counts


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def render_overview(report: dict[str, Any], *, root: Path, zip_data: bytes | None = None) -> None:
    """Single-page summary; heavy evidence stays in Issues/Screenshots/Data."""
    st.markdown(OVERVIEW_STYLES, unsafe_allow_html=True)
    st.markdown("#### Audit overview")

    summary = issue_counts(report)
    coverage = source_counts(report)
    seo = _mapping(_mapping(_mapping(report.get("scores")).get("internal")).get("seo"))
    st.markdown(metric_cards_html(
        seo_score=seo.get("score"),
        seo_partial=seo.get("partial_score") is True,
        issues=summary["failed"], reviews=summary["warning"],
        completed=coverage["completed"], partial=coverage["partial"],
        not_verified=coverage["not_verified"],
    ), unsafe_allow_html=True)

    st.markdown("#### Fix these first")
    priorities = prioritized_unique_findings(report, limit=10)
    if priorities:
        prepared = []
        for item in priorities:
            title, recommendation = check_copy(item)
            prepared.append({
                "title": title, "recommendation": recommendation,
                "status": item.get("status"), "severity": item.get("severity"),
                "area": item.get("module"), "occurrences": item.get("occurrences", 1),
            })
        st.markdown(findings_html(prepared), unsafe_allow_html=True)
    else:
        st.caption("No issues or review items were reported by the checks that ran. "
                   "Unchecked areas are not assumed to pass.")

    with st.expander("What was checked? · coverage details"):
        st.dataframe(
            [{"Source": row["title"], "Result": row["status_label"],
              "Limitation": row["reason"] or "—"}
             for row in source_rows(report)],
            hide_index=True, use_container_width=True, height=292,
        )
