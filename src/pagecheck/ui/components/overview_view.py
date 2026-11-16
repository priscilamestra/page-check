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
from pagecheck.reporting.exports import zip_export
from pagecheck.ui.components.coverage_composition import source_composition_html
from pagecheck.ui.components.coverage_details import source_rows
from pagecheck.ui.components.overview_dashboard import (
    OVERVIEW_STYLES, area_chart_html, findings_html, metric_cards_html,
)
from pagecheck.ui.components.overview_insights import (
    actionable_rows, missing_evidence_rows, prioritized_findings, source_counts,
)
from pagecheck.ui.components.report_data import issue_counts


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def render_overview(report: dict[str, Any], *, root: Path, zip_data: bytes | None = None) -> None:
    """Single-page summary; heavy evidence stays in Issues/Screenshots/Data."""
    st.markdown(OVERVIEW_STYLES, unsafe_allow_html=True)
    heading, download = st.columns([5, 2], vertical_alignment="center")
    with heading:
        st.markdown("#### Audit overview")
    with download:
        st.download_button(
            "Download report (ZIP)", zip_data if zip_data is not None else zip_export(report, root),
            file_name="pagecheck_report.zip", mime="application/zip",
            use_container_width=True,
        )
    # Visual evidence remains in the dedicated Screenshots tab.

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
    priorities = prioritized_findings(report, limit=4)
    if priorities:
        prepared = []
        for item in priorities:
            title, recommendation = check_copy(item)
            prepared.append({
                "title": title, "recommendation": recommendation,
                "status": item.get("status"), "severity": item.get("severity"),
                "area": item.get("module"),
            })
        st.markdown(findings_html(prepared), unsafe_allow_html=True)
        st.caption("Open **Issues** to inspect all findings, evidence and full recommendations.")
    else:
        st.caption("No issues or review items were reported by the checks that ran. "
                   "Unchecked areas are not assumed to pass.")

    left, right = st.columns([1.35, 1], gap="medium")
    with left:
        st.markdown("#### Findings by area")
        by_area = actionable_rows(report)
        if by_area:
            st.markdown(area_chart_html(by_area), unsafe_allow_html=True)
            if len(by_area) > 6:
                st.caption(f"Showing the 6 busiest of {len(by_area)} areas; see **Issues** for all findings.")
        else:
            st.caption("No actionable findings in the checks that ran.")
    with right:
        st.markdown("#### Audit coverage")
        st.markdown(source_composition_html(coverage), unsafe_allow_html=True)
        st.caption("Completed, limited and unavailable sources are kept separate. "
                   "This is not a score for the entire website.")

    with st.expander("What was checked? · coverage details"):
        st.dataframe(
            [{"Source": row["title"], "Result": row["status_label"],
              "Limitation": row["reason"] or "—"}
             for row in source_rows(report)],
            hide_index=True, use_container_width=True, height=292,
        )
        missing = missing_evidence_rows(report)
        if missing:
            total = sum(row["total"] for row in missing)
            st.caption(f"{total} individual checks were not verified. "
                       "These are missing evidence, not confirmed defects.")
        score_coverage = seo.get("coverage")
        if (isinstance(score_coverage, (int, float))
                and not isinstance(score_coverage, bool) and 0 <= score_coverage <= 1):
            st.caption(f"Technical SEO score covers {score_coverage:.0%} of eligible SEO "
                       "scoring rules—not the entire website, accessibility or visual quality.")
        if seo.get("partial_score") is True:
            st.caption("The technical SEO score is partial because not all eligible rules were verified.")
