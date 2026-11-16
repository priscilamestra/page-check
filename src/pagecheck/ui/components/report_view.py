"""Readable English reporting UI, with automatic severity and no severity selector."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from pagecheck.reporting.english_copy import check_copy
from pagecheck.reporting.exports import findings_csv, zip_export
from pagecheck.ui.components.report_data import export_report_json
from pagecheck.ui.components.overview_view import render_overview
from pagecheck.ui.components.issues_view import render_issues
from pagecheck.ui.components.screenshots_view import render_screenshots
from pagecheck.ui.components.teams_view import render_teams
from pagecheck.ui.components.table_sizing import compact_table_height
from pagecheck.ui.components.url_explorer import (
    campaign_parameters, check_rows, area_summary, filter_rows,
)

def render_report(report: dict[str, Any], *, root: Path) -> None:
    st.subheader("Audit results")
    context = report.get("audit_context") or {}
    language = context.get("language")
    labels = {"en": "English", "pt": "Portuguese", "es": "Spanish"}
    keywords = context.get("keywords") or []
    st.caption(f"{report['final_url']} · {report['niche']} · {report['objective']}")
    if language:
        st.caption(f"Content language: {labels.get(language, language)}"
                   + (" · Target keywords: " + ", ".join(map(str, keywords)) if keywords else ""))

    # The report archive is shared by Overview and Data rather than assembled twice.
    report_zip = zip_export(report, root)
    tab_summary, tab_journey, tab_issues, tab_visual, tab_teams, tab_data = st.tabs(
        ["Overview", "URLs & parameters", "Issues", "Screenshots", "Teams", "Data"]
    )
    with tab_summary:
        render_overview(report, root=root, zip_data=report_zip)

    with tab_journey:
        st.markdown("#### URL & campaign parameters")
        st.caption("Quick summary first. Tracking and links are inspected without submitting "
                   "forms, executing JavaScript, or confirming analytics delivery.")
        params = campaign_parameters(report)
        rows = check_rows(report, describe=check_copy)
        pcols = st.columns(3)
        pcols[0].metric("Query parameters", params["total"])
        pcols[1].metric("UTM parameters", params["utm"])
        pcols[2].metric("Check records", len(rows))
        if params["total"]:
            with st.expander(f"View {params['total']} URL parameter(s)"):
                st.dataframe(params["parameters"], hide_index=True,
                             use_container_width=True, height=min(280, 55 + 36 * params["total"]))
        else:
            st.caption("No query parameters in the requested URL. This is not automatically a defect.")

        st.markdown("#### What the checks found")
        if not rows:
            st.info("No tracking, navigation, or form checks are available for this report.")
        else:
            st.dataframe(area_summary(rows), hide_index=True,
                         use_container_width=True, height=145)
            counts = {status: sum(r["status"] == status for r in rows)
                      for status in ("failed", "warning", "not_verified")}
            if counts["not_verified"]:
                st.caption(f"{counts['not_verified']} checks were Not verified. "
                           "These are missing evidence, not confirmed broken links or defects. "
                           "Repeated page elements may produce multiple checks.")

            st.markdown("#### Explore individual checks")
            st.caption("The table stays within a fixed-height area. Filter to find an item; "
                       "technical evidence appears only when you select a check.")
            a, b = st.columns(2)
            with a:
                area = st.selectbox("Area", ["All", "Tracking", "Navigation", "Forms"],
                                    key="url_checks_area")
            with b:
                status = st.selectbox("Result", ["Needs attention", "All", "Issue", "Needs review",
                                                  "Not verified", "Passed", "Not applicable"],
                                      key="url_checks_status")
            query = st.text_input("Search by check or recommendation", key="url_checks_search")
            filtered = filter_rows(rows, area=area, status=status, search=query)
            st.caption(f"Showing {len(filtered)} of {len(rows)} checks. "
                       "All checks remain available through the filters and exported report.")
            if filtered:
                table = [{"Area": r["area"].title(), "Check": r["title"][:100],
                          "Result": r["label"], "Suggested action": r["recommendation"][:140]}
                         for r in filtered]
                st.dataframe(table, hide_index=True, use_container_width=True,
                             height=compact_table_height(len(table), max_height=350))
                options = {f"{r['index'] + 1} · {r['area'].title()} · {r['title'][:85]}": r
                           for r in filtered}
                selected = st.selectbox("Inspect a check", ["Select a check..."] + list(options),
                                        key="url_checks_detail")
                if selected in options:
                    detail = options[selected]
                    st.markdown(f"**{detail['title']}** · {detail['label']}")
                    if detail["recommendation"]:
                        st.write("**Suggested action:** " + detail["recommendation"])
                    with st.expander("Technical evidence (advanced)"):
                        st.caption("Source: " + (detail["source"] or "Not specified"))
                        st.json(detail["evidence"], expanded=False)
            else:
                st.info("No checks match these filters. Choose another result or clear the search.")

    with tab_issues:
        render_issues(report)

    with tab_visual:
        render_screenshots(report, root=root)

    with tab_teams:
        render_teams(report)

    with tab_data:
        st.download_button(
            "Download JSON report", export_report_json(report),
            file_name="pagecheck_audit.json", mime="application/json",
        )
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download findings CSV", findings_csv(report),
                file_name="pagecheck_findings.csv", mime="text/csv",
            )
        with col2:
            st.download_button(
                "Download HTML report + screenshots (ZIP)", report_zip,
                file_name="pagecheck_report.zip", mime="application/zip",
            )
        st.caption("Reports can contain URLs and data supplied during the audit. "
                   "Files stay local unless you choose to share them.")
        with st.expander("Raw consolidated JSON"):
            st.json(report, expanded=False)
