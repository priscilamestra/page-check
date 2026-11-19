"""Readable English reporting UI, with automatic severity and no severity selector."""
from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import streamlit as st

from pagecheck.reporting.english_copy import check_copy
from pagecheck.reporting.exports import findings_csv, zip_export
from pagecheck.ui.components.issues_view import render_issues
from pagecheck.ui.components.overview_view import render_overview
from pagecheck.ui.components.report_data import OBJECTIVE_LABELS, export_report_json
from pagecheck.ui.components.screenshots_view import render_screenshots
from pagecheck.ui.components.table_sizing import compact_table_height
from pagecheck.ui.components.url_explorer import (
    area_summary,
    campaign_parameters,
    check_rows,
    destination_inventory_count,
    filter_rows,
    group_check_rows,
)

# Small, narrowly scoped CSS: no global Streamlit/toolbar overrides.
_REPORT_PRESENTATION_CSS = """
<style>
[data-testid="stTabs"] [role="tab"] {
    font-size: 1.075rem !important;
    padding: 0.65rem 1rem !important;
}
[data-testid="stTabs"] [role="tab"] p {
    font-size: 1.075rem !important;
}
.pc-report-link {
    display: block;
    font-size: 0.975rem;
    line-height: 1.65;
    overflow-wrap: anywhere;
}
.pc-report-context {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.45rem;
    padding-top: 0.12rem;
}
.pc-report-chip {
    display: inline-flex;
    align-items: center;
    border: 1px solid transparent;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    line-height: 1.35;
    padding: 0.28rem 0.7rem;
    max-width: 100%;
    overflow-wrap: anywhere;
}
.pc-report-chip-niche {
    color: #9CD6CD;
    background: rgba(29, 142, 121, 0.16);
    border-color: rgba(47, 170, 146, 0.4);
}
.pc-report-chip-goal {
    color: #E8C397;
    background: rgba(190, 120, 53, 0.15);
    border-color: rgba(206, 137, 67, 0.38);
}
</style>
"""


def _report_context_html(report: dict[str, Any]) -> tuple[str, str]:
    """Build safe, concise HTML with user-supplied values escaped.

    Report imports have only basic schema validation, so never trust href
    schemes or interpolate unescaped niche/objective strings into HTML.
    """
    raw_url = str(report.get("final_url") or "")
    safe_url = escape(raw_url, quote=True)
    try:
        parsed = urlsplit(raw_url)
        is_web_link = parsed.scheme.lower() in {"https", "http"} and bool(parsed.hostname)
    except ValueError:
        is_web_link = False
    if is_web_link:
        url_html = f'<a class="pc-report-link" href="{safe_url}" target="_blank" rel="noopener noreferrer">{escape(raw_url)}</a>'
    else:
        url_html = f'<span class="pc-report-link">{escape(raw_url)}</span>'
    niche = escape(str(report.get("niche") or ""))
    goal_raw = str(report.get("objective") or "")
    goal = escape(OBJECTIVE_LABELS.get(goal_raw, goal_raw.replace("_", " ").title()))
    chips = (
        '<div class="pc-report-context">'
        f'<span class="pc-report-chip pc-report-chip-niche">{niche}</span>'
        f'<span class="pc-report-chip pc-report-chip-goal">{goal}</span>'
        '</div>'
    )
    return url_html, chips


def render_report(report: dict[str, Any], *, root: Path) -> None:
    st.markdown(_REPORT_PRESENTATION_CSS, unsafe_allow_html=True)
    st.subheader("Audit results")
    url_html, chips_html = _report_context_html(report)
    # The URL is immediately below the heading; selections appear beside it
    # as compact, color-coded chips instead of a low-contrast prose caption.
    url_col, chips_col = st.columns([3, 2], gap="medium", vertical_alignment="center")
    with url_col:
        st.markdown(url_html, unsafe_allow_html=True)
    with chips_col:
        st.markdown(chips_html, unsafe_allow_html=True)

    # Build the report archive once for the Export tab.
    report_zip = zip_export(report, root)
    tab_summary, tab_journey, tab_issues, tab_visual, tab_export = st.tabs(
        ["Overview", "URLs & parameters", "Issues", "Screenshots", "Export"]
    )
    with tab_summary:
        render_overview(report, root=root, zip_data=report_zip)

    with tab_journey:
        st.markdown("#### URL & campaign parameters")
        params = campaign_parameters(report)
        rows = check_rows(report, describe=check_copy)
        destination_count = destination_inventory_count(rows)
        pcols = st.columns(3)
        pcols[0].metric("Query parameters", params["total"])
        pcols[1].metric("UTM parameters", params["utm"])
        pcols[2].metric("Link destinations", destination_count)
        st.caption(
            f"{len(rows)} diagnostic check records. Unvisited destinations are kept as "
            "one inventory coverage limit, not counted as individual failures."
        )
        if params["total"]:
            with st.expander(f"View {params['total']} URL parameter(s)"):
                st.dataframe(params["parameters"], hide_index=True,
                             width="stretch", height=min(280, 55 + 36 * params["total"]),
                             alt="URL query parameters and campaign tags")

        st.markdown("#### What the checks found")
        if not rows:
            st.info("No tracking, navigation, or form checks are available for this report.")
        else:
            st.dataframe(area_summary(rows), hide_index=True,
                         width="stretch", height=145,
                         alt="URL, navigation, and form checks by result")
            st.markdown("#### Explore individual checks")
            area_counts = Counter(row["area"] for row in rows)
            areas = ["All"] + sorted(area_counts)
            a, b = st.columns(2)
            with a:
                area = st.selectbox(
                    "Area", areas, key="url_checks_area_simple_v3",
                    format_func=lambda value: (
                        f"All areas ({len(rows)})" if value == "All"
                        else f"{value.title()} ({area_counts[value]})"
                    ),
                )
            scoped_rows = [r for r in rows if area == "All" or r["area"] == area]
            status_counts = Counter(r["status"] for r in scoped_rows)
            label_for_status = {
                "failed": "Issue", "warning": "Needs review", "passed": "Passed",
                "not_verified": "Not verified", "not_applicable": "Not applicable",
            }
            attention_count = status_counts["failed"] + status_counts["warning"]
            statuses = ["All"]
            if attention_count:
                statuses.insert(0, "Needs attention")
            statuses.extend(label for raw, label in label_for_status.items() if status_counts[raw])
            count_for_label = {label: status_counts[raw]
                               for raw, label in label_for_status.items()}
            with b:
                status = st.selectbox(
                    "Result", statuses, key=f"url_checks_status_simple_v3_{area}",
                    format_func=lambda value: (
                        f"All results ({len(scoped_rows)})" if value == "All"
                        else (f"Needs attention ({attention_count})" if value == "Needs attention"
                              else f"{value} ({count_for_label[value]})")
                    ),
                )
            filtered = filter_rows(rows, area=area, status=status, search="")
            grouped = group_check_rows(filtered)
            st.caption(
                f"Showing {len(filtered)} of {len(rows)} check records in "
                f"{len(grouped)} diagnostic group(s)."
            )
            if filtered:
                table = [{"Area": r["area"].title(), "Finding": r["title"][:100],
                          "Result": r["label"], "Records": r["occurrences"],
                          "Example element": r["element"][:80] or "—",
                          "Example destination": r["destination"][:120] or "—"}
                         for r in grouped]
                st.dataframe(table, hide_index=True, width="stretch",
                             height=compact_table_height(len(table), max_height=350),
                             alt="Grouped URL, navigation, and form diagnostics")
                options = {
                    f"{index} · {r['area'].title()} · {r['title'][:75]}"
                    f" ({r['occurrences']} record{'s' if r['occurrences'] != 1 else ''})": r
                    for index, r in enumerate(grouped, 1)
                }
                selected = st.selectbox(
                    "Inspect a diagnostic group", ["Select a group..."] + list(options),
                    key="url_checks_detail_group",
                )
                if selected in options:
                    group = options[selected]
                    detail = group
                    if group["occurrences"] > 1:
                        members = {
                            f"{item['index'] + 1} · {item['element'][:55] or item['check_id']}"
                            f" · {item['destination'][:70] or 'No destination'}": item
                            for item in group["members"]
                        }
                        selected_member = st.selectbox(
                            "Element in this group", list(members), key="url_checks_detail_member"
                        )
                        detail = members[selected_member]
                    st.markdown(f"**{detail['title']}** · {detail['label']}")
                    if detail["inventory_items"]:
                        st.caption(
                            f"{detail['inventory_items']} destinations were recorded. Their availability was "
                            "not tested, so this is one coverage limitation—not "
                            f"{detail['inventory_items']} broken or failed links."
                        )
                    if detail["recommendation"]:
                        label = "Coverage limit" if detail["status"] == "not_verified" else "Next step"
                        st.write(f"**{label}:** {detail['recommendation']}")
                    with st.expander("What was found and where"):
                        if detail["element"]:
                            st.markdown("**Element**")
                            st.text(detail["element"])
                        if detail["destination"]:
                            st.markdown("**Destination**")
                            st.text(detail["destination"])
                        if detail["location"]:
                            st.markdown("**DOM location**")
                            st.code(detail["location"], language="css")
                        st.caption("Source: " + (detail["source"] or "Not specified"))
                        st.json(detail["evidence"], expanded=False)
            else:
                st.info("No checks in this category.")

    with tab_issues:
        render_issues(report)

    with tab_visual:
        render_screenshots(report, root=root)

    with tab_export:
        st.markdown("#### Export your audit")
        st.download_button(
            "Download full report (HTML + screenshots ZIP)", report_zip,
            file_name="pagecheck_report.zip", mime="application/zip",
            width="stretch",
        )
        st.caption("Includes the HTML report and desktop/mobile captures when available. "
                   "Individual PNG downloads are in Screenshots.")
        with st.expander("Other formats (advanced)"):
            a, b = st.columns(2)
            with a:
                st.download_button(
                    "Download findings (CSV)", findings_csv(report),
                    file_name="pagecheck_findings.csv", mime="text/csv",
                    width="stretch",
                )
            with b:
                st.download_button(
                    "Download data (JSON)", export_report_json(report),
                    file_name="pagecheck_audit.json", mime="application/json",
                    width="stretch",
                )
        st.caption("Reports may include page URLs and audit data. "
                   "Files are downloaded to your device.")
