"""Compact team task presentation: summary -> filter -> one selected action."""
from __future__ import annotations

from typing import Any

import streamlit as st

from pagecheck.reporting.english_copy import check_copy, team_name
from pagecheck.ui.components.teams_explorer import filter_team_tasks, team_summary, team_tasks


def render_teams(report: dict[str, Any]) -> None:
    st.markdown("#### Actions by team")
    st.caption("Find the responsible team and its suggested next steps. "
               "This is a routing suggestion, not a task tracker.")
    rows = team_tasks(report, team_label=team_name, describe=check_copy)
    if not rows:
        st.info("No team actions were reported by the completed checks.")
        return
    summary = team_summary(rows)
    a, b = st.columns(2)
    a.metric("Suggested actions", len(rows))
    b.metric("Teams", len(summary))
    st.dataframe(summary, hide_index=True, use_container_width=True,
                 height=min(260, 52 + 36 * len(summary)))
    left, right = st.columns([1, 2])
    with left:
        team = st.selectbox("Team", ["All"] + [row["Team"] for row in summary],
                            key="teams_filter_19d")
    with right:
        search = st.text_input("Search actions", key="teams_search_19d")
    selected_rows = filter_team_tasks(rows, team=team, search=search)
    st.caption(f"Showing {len(selected_rows)} of {len(rows)} suggested actions.")
    if not selected_rows:
        st.info("No actions match the selected team or search.")
        return
    st.dataframe([{"Team": r["team"], "Priority": r["priority"].title(),
                   "Task": r["title"][:110], "Next step": r["recommendation"][:140]}
                  for r in selected_rows],
                 hide_index=True, use_container_width=True,
                 height=min(380, 60 + len(selected_rows) * 37))
    lookup = {r["index"]: r for r in selected_rows}
    chosen = st.selectbox("Inspect action", [None] + list(lookup),
                          format_func=lambda i: "Choose an action" if i is None
                          else f"{lookup[i]['team']} · {lookup[i]['title'][:90]}",
                          key="teams_selected_19d")
    if chosen is not None:
        task = lookup[chosen]
        with st.container(border=True):
            st.markdown(f"**{task['title']}**")
            st.caption(f"{task['team']} · {task['priority'].title()} priority")
            st.write(task["recommendation"] or "Review the related finding and evidence.")
            with st.expander("Technical details (advanced)"):
                st.caption(f"Source finding: {task['finding_id'] or 'Not recorded'}")
                st.json(task["evidence"], expanded=False)
