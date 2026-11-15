"""Stage 19A executive Overview. Presentation-only, no audit mutations or IO.

Visual reports remain truthful about limited screenshots, missing engines,
and the difference between a scored SEO subset and unverified checks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from pagecheck.reporting.english_copy import check_copy, team_name
from pagecheck.ui.components.coverage_details import screenshot_kind, source_rows
from pagecheck.ui.components.overview_insights import (
    actionable_rows, count_label, missing_evidence_rows, prioritized_findings, source_counts,
)
from pagecheck.ui.components.coverage_composition import source_composition_html
from pagecheck.ui.components.report_data import SEVERITY_LABELS, screenshot_entries

_SEVERITY_COLOR = {"critical": "red", "high": "red", "medium": "orange",
                   "low": "yellow", "info": "gray"}


def _why_it_matters(item: dict[str, Any]) -> str:
    """Cautious general impact, not claims of measured conversion/ranking losses."""
    area = str(item.get("module") or "").lower()
    if area in {"accessibility", "axe"}:
        return "May make a page control harder to use with assistive technology."
    if area == "seo":
        return "May affect how clearly the page communicates its topic to visitors and search engines."
    if area in {"navigation", "links"}:
        return "Visitors may have trouble reaching the intended destination; confirm the live behavior."
    if area == "forms":
        return "May make a form harder to understand or submit; submissions were not tested."
    if area == "tracking":
        return "May affect attribution visibility; this audit does not verify analytics delivery."
    if area in {"images", "visual", "layout"}:
        return "May affect the page experience on the inspected viewport."
    return "Review this observation before making changes; the audit reports only available evidence."


def _action_card(item: dict[str, Any], index: int) -> None:
    title, recommendation = check_copy(item)
    priority = str(item.get("severity") or "info").lower()
    status = item.get("status")
    with st.container(border=True):
        col_number, col_label = st.columns([1, 9], vertical_alignment="center")
        col_number.markdown(f"**{index}.**")
        with col_label:
            st.badge(
                f"{SEVERITY_LABELS.get(priority, 'Review')} · "
                f"{'Issue' if status == 'failed' else 'Needs review'}",
                color=_SEVERITY_COLOR.get(priority, "gray"),
            )
        st.markdown(f"**{title}**")
        st.caption(f"{str(item.get('module') or 'Other').replace('_', ' ').title()}"
                   f" · {team_name(item.get('team'))}")
        st.write("**Why it matters**")
        st.caption(_why_it_matters(item))
        st.write("**What to do**")
        st.write(recommendation or "Review the technical evidence and confirm the page behavior.")
        st.caption("Static evidence only · Open the Issues tab for source and technical details.")


def _visual_preview(report: dict[str, Any], root: Path) -> None:
    st.markdown("#### Visual evidence")
    st.caption("Only screenshots captured by the guarded browser are displayed. "
               "An initial viewport is partial evidence, not a full-page visual audit.")
    files = dict(screenshot_entries(report, root))
    sources = {item["id"]: item for item in source_rows(report)}
    columns = st.columns(2)
    for index, viewport in enumerate(("desktop", "mobile")):
        source = sources[viewport]
        with columns[index]:
            with st.container(border=True):
                st.markdown(f"**{viewport.capitalize()}**")
                st.badge(source["status_label"], color=(
                    "green" if source["status"] == "completed" else
                    "orange" if source["status"] == "partial" else "gray"))
                path = files.get(viewport)
                if path:
                    kind = screenshot_kind(report, viewport)
                    if kind.startswith("Initial"):
                        st.caption("Partial visual evidence · first viewport only")
                    else:
                        st.caption(kind)
                    # Limit full-page screenshots in the executive summary;
                    # the Screenshots tab preserves the full evidence display.
                    with st.container(height=260, border=False):
                        st.image(str(path), use_container_width=True)
                else:
                    st.caption("No screenshot available. Not a visual pass.")
                if source["reason"]:
                    with st.expander("Capture scope / reason"):
                        st.caption(source["reason"])
    st.caption("Open Screenshots for the full saved images and their limitations.")


def _source_cards(report: dict[str, Any]) -> None:
    st.markdown("#### What was actually inspected?")
    counts = source_counts(report)
    columns = st.columns(3)
    columns[0].metric("Completed sources", counts["completed"])
    columns[1].metric("Limited sources", counts["partial"])
    columns[2].metric("Not verified sources", counts["not_verified"])
    st.caption("A source that could not complete is not a successful check. "
               "The number of sources is different from the number of individual checks.")
    st.caption("One bar represents all audited sources. Segments show the share of "
               "sources that completed, ran with limits, or could not be verified.")
    st.markdown(source_composition_html(counts), unsafe_allow_html=True)
    cols = st.columns(2)
    for index, row in enumerate(source_rows(report)):
        with cols[index % 2]:
            with st.container(border=True):
                st.markdown(f"**{row['title']}**")
                st.badge(row["status_label"], color=(
                    "green" if row["status"] == "completed" else
                    "orange" if row["status"] == "partial" else "gray"))
                st.caption(row["description"])
                if row["reason"]:
                    with st.expander("Scope / reason"):
                        st.caption(row["reason"])


def render_overview(report: dict[str, Any], *, root: Path) -> None:
    """Summary → priorities → visuals → charts → coverage → technical details."""
    st.markdown("#### Fix these first")
    actionable = prioritized_findings(report, limit=3)
    if not actionable:
        st.info("No actionable findings were reported by the checks that ran. "
                "This does not guarantee the page has no problems.")
    else:
        cols = st.columns(3)
        for index, item in enumerate(actionable, 1):
            with cols[(index - 1) % 3]:
                _action_card(item, index)
        total = len([item for item in report.get("findings") or []
                     if isinstance(item, dict) and item.get("status") in {"failed", "warning"}])
        if total > len(actionable):
            st.caption(f"Showing {len(actionable)} of {total} findings. "
                       "Open the Issues tab to review all findings in priority order.")
        else:
            st.caption("Open the Issues tab for the full technical evidence.")

    _visual_preview(report, root)

    st.markdown("#### Findings by area")
    st.caption("Small counts are easier to read directly than as full-length bars. "
               "These are issues and review items, not overall area scores.")
    by_area = actionable_rows(report)
    if by_area:
        st.dataframe([
            {"Area": str(row["area"]).replace("_", " ").title(),
             "Issues": row["issues"], "Needs review": row["reviews"],
             "Total findings": row["total"]}
            for row in by_area
        ], hide_index=True, use_container_width=True, height=min(260, 55 + len(by_area) * 36))
    else:
        st.info("No issues or review items were reported in the inspected checks.")

    _source_cards(report)

    st.markdown("#### Checks without enough evidence")
    st.caption("Not verified does not mean a broken element. These items are separate "
               "from findings and may be repeated for similar navigation elements.")
    missing = missing_evidence_rows(report)
    if missing:
        total_missing = sum(item["total"] for item in missing)
        st.dataframe([
            {"Area": str(item["area"]).replace("_", " ").title(),
             "Not verified": item["total"],
             "Share of unverified checks": f"{item['total']/total_missing:.1%}"}
            for item in missing
        ], hide_index=True, use_container_width=True,
           height=min(240, 55 + len(missing) * 36))
        st.caption(f"{count_label(total_missing, 'unverified check')} across "
                   f"{count_label(len(missing), 'area')}. A large navigation count "
                   "does not imply the same number of independent defects.")
    else:
        st.caption("No individually unverified checks were recorded by area.")

    with st.expander("Technical coverage details"):
        st.json(report.get("source_states") or {}, expanded=False)
        st.caption("Only executed checks are covered. Scores do not predict "
                   "search rankings or conversions. Full raw data is in the Data tab.")
