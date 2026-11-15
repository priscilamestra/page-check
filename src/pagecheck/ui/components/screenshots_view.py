"""Bounded side-by-side visual evidence; original images and status are unchanged."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from pagecheck.ui.components.visual_explorer import visual_cards, visual_observations


def render_screenshots(report: dict[str, Any], *, root: Path) -> None:
    st.markdown("#### Screenshots and visual evidence")
    st.caption("These images come from a guarded static browser with JavaScript disabled. "
               "A first-viewport capture is partial evidence, not a full visual audit.")
    cards = visual_cards(report, root)
    columns = st.columns([1.5, 1])
    for column, card in zip(columns, cards):
        with column:
            with st.container(border=True):
                st.markdown(f"**{card['title']}**")
                color = ("green" if card["status"] == "completed" else
                         "orange" if card["status"] == "partial" else "gray")
                st.badge(card["status_label"], color=color)
                st.caption(card["kind"])
                if card["path"]:
                    # Tall screenshots must never expand the whole Streamlit page.
                    with st.container(height=360, border=False):
                        st.image(str(card["path"]), use_container_width=True)
                else:
                    st.info("No screenshot was captured. Visual quality was not verified.")
                if card["is_partial"]:
                    st.caption("Only limited visual evidence is available for this device.")
                if card["reason"]:
                    with st.expander("Capture limitation"):
                        st.write(card["reason"])
                observations = visual_observations(report, card["viewport"])
                if observations:
                    st.caption(f"{len(observations)} reported observations linked to this viewport. "
                               "They are not necessarily annotated in the image.")
                    with st.expander("View linked findings"):
                        for finding in observations[:20]:
                            st.write(f"{finding['severity'].title()}: {finding['title']}")
                        if len(observations) > 20:
                            st.caption("Additional findings remain in Issues and the report export.")
                elif not card["annotated"]:
                    st.caption("No confirmed visual issue markers are attached to this capture.")
    st.caption("Screenshots do not prove that forms, menus or analytics work. "
               "Blocked resources are not confirmed page defects. Original files remain "
               "in the audit history and ZIP export.")
