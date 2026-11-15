"""Streamlit presentation of Stage 19B's bounded issue explorer."""
from __future__ import annotations

from typing import Any

import streamlit as st

from pagecheck.reporting.english_copy import check_copy, team_name
from pagecheck.ui.components.table_sizing import compact_table_height
from pagecheck.ui.components.issues_explorer import (
    filter_findings, finding_rows, finding_summary, findings_table,
)


def render_issues(report: dict[str, Any]) -> None:
    st.markdown("#### Findings and recommended fixes")
    st.caption("Start with actionable items. Filter or search for details; the full report "
               "and original evidence are retained for export.")
    rows = finding_rows(report, describe=check_copy, team_label=team_name)
    summary = finding_summary(rows)
    cols = st.columns(4)
    cols[0].metric("Issues detected", summary["issues"])
    cols[1].metric("Needs review", summary["reviews"])
    cols[2].metric("Critical issues", summary["critical_issues"])
    cols[3].metric("Areas affected", summary["areas_affected"])
    if not rows:
        st.info("No findings were reported by completed checks. "
                "This does not guarantee the page has no problems.")
        return

    areas = ["All"] + [area.title() for area in sorted({row["area"] for row in rows})]
    first, second, third = st.columns([1.3, 1.5, 1])
    with first:
        area = st.selectbox("Area", areas, key="issues_area_19b")
    with second:
        result = st.selectbox(
            "Result", ["Needs attention", "All", "Issue", "Needs review",
                       "Not verified", "Passed", "Not applicable"],
            key="issues_result_19b",
        )
    with third:
        priority = st.selectbox(
            "Priority", ["All", "Critical", "High", "Medium", "Low", "Info"],
            key="issues_priority_19b",
        )
    query = st.text_input("Find a problem or recommendation", placeholder="Search findings...",
                          key="issues_search_19b")
    visible = filter_findings(rows, area=area, result=result, priority=priority, search=query)
    st.caption(f"Showing {len(visible)} of {summary['total']} findings. "
               "Needs review does not mean a confirmed failure.")
    if not visible:
        st.info("No findings match these filters. Change the filters or clear the search.")
        return
    st.dataframe(findings_table(visible), hide_index=True,
                 use_container_width=True, height=compact_table_height(len(visible), max_height=400))
    options = {item["index"]: item for item in visible}
    selected = st.selectbox(
        "Inspect a finding", [None] + list(options),
        format_func=lambda value: "Select a finding for guidance and evidence" if value is None
        else f"{options[value]['severity_label']} · {options[value]['title'][:95]}",
        key="issues_selected_19b",
    )
    if selected is None:
        st.caption("Select a finding above to see why it matters and what to do. "
                   "Source JSON stays closed unless requested.")
        return
    row = options[selected]
    with st.container(border=True):
        st.markdown(f"**{row['title']}**")
        st.caption(f"{row['area'].replace('_',' ').title()} · {row['team']} · "
                   f"{row['severity_label']} priority · {row['result']}")
        st.markdown("**Suggested next step**")
        st.write(row["recommendation"] or "Review this observation and verify the live page behavior.")
        if row["status"] == "warning":
            st.caption("This item requires human review and is not a confirmed page defect.")
        with st.expander("Technical evidence (advanced)"):
            st.caption(f"Source: {row['source']} · Rule: {row['check_id'] or 'Not recorded'}")
            st.json(row["evidence"], expanded=False)
