"""Desktop/mobile evidence with direct downloads and truthful capture scope."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from pagecheck.ui.components.visual_explorer import visual_cards, visual_observations


def render_screenshots(report: dict[str, Any], *, root: Path) -> None:
    st.markdown("#### Page screenshots")
    cards = visual_cards(report, root)
    columns = st.columns(2, gap="medium")
    for column, card in zip(columns, cards):
        with column:
            with st.container(border=True):
                header, status = st.columns([2, 1], vertical_alignment="center")
                header.markdown(f"**{card['title']}**")
                status.badge(card["status_label"], color=(
                    "green" if card["status"] == "completed" else
                    "orange" if card["status"] == "partial" else "gray"
                ))
                image_path = card["path"]
                if image_path:
                    # Only allow paths already vetted by visual_cards/safe_screenshot_path.
                    with st.container(height=400, border=False):
                        st.image(str(image_path), use_container_width=True)
                    try:
                        png = image_path.read_bytes()
                    except OSError:
                        st.warning("Screenshot unavailable for download.")
                    else:
                        st.download_button(
                            f"Download {card['title'].lower()} screenshot (PNG)", png,
                            file_name=f"pagecheck_{card['viewport']}.png", mime="image/png",
                            use_container_width=True,
                        )
                    if card["annotated"]:
                        st.caption("This capture includes the annotations available in the report.")
                else:
                    st.info("No screenshot available for this device.")

                observations = visual_observations(report, card["viewport"])
                if observations:
                    with st.expander(f"Related observations ({len(observations)})"):
                        for finding in observations[:20]:
                            st.write(f"{finding['severity'].title()}: {finding['title']}")
                        if len(observations) > 20:
                            st.caption("Additional findings are available in Issues.")
                if card["reason"]:
                    with st.expander("Capture details"):
                        st.write(card["reason"])
                elif card["is_partial"]:
                    st.caption("Partial screenshot — not a full-page visual audit.")

    st.caption("Only confirmed annotations included in the report are displayed. "
               "An unmarked screenshot does not mean the page has no issues.")
