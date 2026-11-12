"""Readable English reporting UI, with automatic severity and no severity selector."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from pagecheck.reporting.english_copy import check_copy, team_name
from pagecheck.ui.components.report_data import (
    SEVERITY_LABELS, STATUS_LABELS, export_report_json, issue_counts, module_rows,
    screenshot_entries,
)

SEVERITY_COLORS = {
    "critical": "red", "high": "red", "medium": "orange",
    "low": "yellow", "info": "gray",
}
STATUS_COLORS = {
    "failed": "red", "warning": "orange", "passed": "green",
    "not_verified": "gray", "not_applicable": "gray",
}


def _score(value: object) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.0f}/100"
    return "Not verified"


def _state_counts(state: dict) -> tuple[int, int]:
    engine_states = state.get("engines") or {}
    visual_states = state.get("visuals") or {}
    all_states = [state.get("seo"), state.get("conversion"),
                  *(engine_states.values() if isinstance(engine_states, dict) else []),
                  *(visual_states.values() if isinstance(visual_states, dict) else [])]
    return (sum(s == "completed" for s in all_states), len(all_states))


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
    if report["status"] == "partial":
        done, total = _state_counts(report.get("source_states") or {})
        st.info(f"Limited audit coverage: {done} of {total} sources completed. "
                "Unrun checks remain **Not verified**; no missing check counts as passed.")
    else:
        st.success("All applicable audit sources in this run completed.")

    counts = issue_counts(report)
    seo = ((report.get("scores") or {}).get("internal") or {}).get("seo") or {}
    cols = st.columns(4)
    cols[0].metric("Technical SEO", _score(seo.get("score")))
    cols[1].metric("Issues", counts["failed"])
    cols[2].metric("Needs review", counts["warning"])
    cols[3].metric("Not verified", counts["not_verified"])

    tab_summary, tab_journey, tab_issues, tab_visual, tab_teams, tab_data = st.tabs(
        ["Overview", "URLs & parameters", "Issues", "Screenshots", "Teams", "Data"]
    )
    with tab_summary:
        st.caption("The Page Check technical SEO score is separate from Lighthouse scores and content guidance.")
        lh = (report.get("scores") or {}).get("lighthouse")
        if isinstance(lh, dict) and lh:
            st.markdown("**Lighthouse**")
            cols = st.columns(4)
            for col, (key, label) in zip(cols, (
                ("performance", "Performance"), ("accessibility", "Accessibility"),
                ("best-practices", "Best practices"), ("seo", "Lighthouse SEO"),
            )):
                col.metric(label, _score(lh.get(key)))
        st.markdown("**Results by area**")
        rows = module_rows(report)
        if rows:
            frame = pd.DataFrame(rows).set_index("Módulo")
            frame = frame.rename(columns={"Problemas": "Issues", "Atenção": "Needs review",
                                          "Aprovados": "Passed"})
            st.bar_chart(frame[["Issues", "Needs review", "Passed"]], horizontal=True)
        else:
            st.info("No area-level checks available.")
        with st.expander("Coverage and technical limitations"):
            st.json(report.get("source_states") or {}, expanded=False)
            st.caption("The audit covers only the engines actually executed; scores do not predict rankings or conversions.")

    with tab_journey:
        st.caption("Observable URL and HTML checks. These do not measure real conversions or analytics events.")
        related = [item for item in report.get("checks", [])
                   if item.get("module") in {"tracking", "navigation", "forms"}]
        if not related:
            st.info("No URL, link, or form checks are available.")
        else:
            for item in related:
                title, recommendation = check_copy(item)
                with st.container(border=True):
                    st.badge(STATUS_LABELS.get(item.get("status"), "Not verified"),
                             color=STATUS_COLORS.get(item.get("status"), "gray"))
                    st.markdown(f"**{title}**")
                    if recommendation:
                        st.caption(recommendation)
                    with st.expander("Technical evidence"):
                        st.json(item.get("evidence") or {}, expanded=False)

    with tab_issues:
        findings = report.get("findings") or []
        if not findings:
            st.info("No issues were reported by the executed checks. This is not a guarantee of zero issues.")
        else:
            st.caption(f"{len(findings)} findings · Automatically sorted by priority · Nothing is hidden")
            for item in findings:
                severity_code = str(item.get("severity") or "info")
                title, recommendation = check_copy(item)
                with st.container(border=True):
                    st.badge(f"{SEVERITY_LABELS.get(severity_code, 'Info')} priority",
                             color=SEVERITY_COLORS.get(severity_code, "gray"))
                    st.markdown(f"**{title}**")
                    st.caption(f"{item.get('module', 'Review')} · {team_name(item.get('team'))}")
                    if recommendation:
                        st.write(f"**Suggested fix:** {recommendation}")
                    with st.expander("Technical details"):
                        st.caption(f"Status: {STATUS_LABELS.get(item.get('status'), 'Not verified')}"
                                   f" · Source: {item.get('source', 'Unknown')}")
                        st.json(item.get("evidence") or {}, expanded=False)

    with tab_visual:
        images = screenshot_entries(report, root)
        if not images:
            st.info("No screenshots are linked to this report. The browser audit has not run in this workflow.")
        else:
            for viewport, path in images:
                st.markdown(f"**{viewport.capitalize()}**")
                st.image(str(path), caption=f"Annotated {viewport} view", use_container_width=True)
        st.caption("Screenshots appear only when an executed browser audit links local evidence files.")

    with tab_teams:
        actions = report.get("actions_by_team") or []
        if not actions:
            st.info("No team actions are available for these checks.")
        for team in actions:
            if not isinstance(team, dict):
                continue
            with st.expander(f"{team_name(team.get('team'))} · {team.get('count', 0)} actions", expanded=True):
                for task in team.get("actions") or []:
                    if not isinstance(task, dict):
                        continue
                    title, recommended = check_copy({**task, "check_id": task.get("check_id")})
                    st.markdown(f"**{title}** · "
                                f"{SEVERITY_LABELS.get(task.get('priority'), 'Review')}")
                    st.caption(recommended or "Review the associated finding and its evidence.")

    with tab_data:
        st.download_button(
            "Download JSON report", export_report_json(report),
            file_name="pagecheck_audit.json", mime="application/json",
        )
        st.caption("Raw data can include original source messages; all primary controls are in English.")
        with st.expander("Raw consolidated JSON"):
            st.json(report, expanded=False)
