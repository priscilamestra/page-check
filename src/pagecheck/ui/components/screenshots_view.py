"""Desktop/mobile evidence with direct downloads and truthful capture scope."""
from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping
from typing import Any

import streamlit as st


@st.dialog("Screenshot", width="large")
def _large_screenshot(image_path: Path, label: str) -> None:
    """Allow zooming the actual captured evidence, without reconstructing markers."""
    st.caption(label)
    st.image(str(image_path), use_container_width=True)

from pagecheck.ui.components.visual_explorer import visual_cards, visual_observations
from pagecheck.ui.components.hierarchy_indicator import design_analysis_available
from pagecheck.ui.components.visual_issue_details import (
    ISSUE_ACCORDION_STYLES, design_chips_html, detailed_observations_html,
    grouped_observations, marker_summary, screenshot_findings_label,
)


def render_screenshots(report: dict[str, Any], *, root: Path) -> None:
    st.markdown("#### Page screenshots")
    st.markdown(ISSUE_ACCORDION_STYLES, unsafe_allow_html=True)
    # A restored legacy report may predate the design-review field. Never
    # confuse missing analysis with a positive design evaluation.
    design_reviews = report.get("design_reviews") or {}
    if not isinstance(design_reviews, Mapping):
        design_reviews = {}
    cards = visual_cards(report, root)
    if not any(design_analysis_available(design_reviews.get(v)) for v in ("desktop", "mobile")):
        st.caption("This report has no design measurements. Run a new audit to obtain them.")
    columns = st.columns(2, gap="medium")
    for column, card in zip(columns, cards):
        with column:
            with st.container(border=True):
                st.markdown(f"**{card['title']}**")
                # Keep the actual measurements (not redundant 'Limited' labels)
                # directly alongside the related device screenshot.
                review = design_reviews.get(card["viewport"])
                if design_analysis_available(review):
                    st.markdown(design_chips_html(review), unsafe_allow_html=True)
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
                        dl_col, zoom_col = st.columns([3, 2])
                        with dl_col:
                            st.download_button(
                                f"Download {card['title'].lower()} (PNG)", png,
                                file_name=f"pagecheck_{card['viewport']}.png", mime="image/png",
                                use_container_width=True,
                            )
                        with zoom_col:
                            if st.button("View larger", key=f"zoom_{card['viewport']}",
                                         use_container_width=True):
                                _large_screenshot(image_path, card["title"])
                else:
                    st.info("No screenshot available for this device.")

                observations = visual_observations(report, card["viewport"])
                if observations:
                    # An audit finding and a number drawn in the screenshot are not
                    # interchangeable: some boxes are off-image or share one mark.
                    has_annotated_image = bool(card["annotated"])
                    st.markdown("**" + screenshot_findings_label(
                        observations, annotated=has_annotated_image) + "**")
                    for group in grouped_observations(observations):
                        category = group["category"]
                        label = screenshot_findings_label(
                            group["findings"], annotated=has_annotated_image,
                            name=group["label"],
                        )
                        with st.container(key=f"pc_fix_{card['viewport']}_{category}"):
                            with st.expander(label):
                                st.markdown(detailed_observations_html(group["findings"]),
                                            unsafe_allow_html=True)
                if card["reason"]:
                    with st.expander("Capture details"):
                        st.write(card["reason"])
