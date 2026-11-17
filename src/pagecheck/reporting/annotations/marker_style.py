"""Stable category palette shared by screenshot markers and audit explanation UI.

Colors identify *which check* raised a finding, not whether an unverified
capture is a confirmed defect. A confirmed failure is always red.
"""
from __future__ import annotations

from collections.abc import Mapping

CATEGORY_COLORS = {
    "titles": "#6495ED",      # blue
    "contrast": "#B58BE4",    # violet
    "buttons": "#E7AD4C",     # gold
    "layout": "#42B7A2",      # teal
    "images": "#EA8A55",      # orange
    "other": "#92A0AF",       # gray
}
CONFIRMED_FAILURE_COLOR = "#E46A70"
CATEGORY_LABELS = {
    "titles": "Titles", "contrast": "Contrast", "buttons": "Buttons",
    "layout": "Layout", "images": "Images", "other": "Other",
}
CATEGORY_ORDER = ("titles", "contrast", "buttons", "layout", "images", "other")


def finding_category(finding: Mapping) -> str:
    """Classify by stable rule identifier rather than localized display text."""
    code = str(finding.get("check_id") or finding.get("id") or "")
    if "design-text-contrast-" in code:
        return "contrast"
    if "design-small-target-" in code:
        return "buttons"
    if "design-heading-" in code:
        return "titles"
    if "layout-" in code:
        return "layout"
    if "image-" in code or str(finding.get("module") or finding.get("category")) == "images":
        return "images"
    return "other"


def marker_color(finding: Mapping) -> str:
    if finding.get("status") == "failed":
        return CONFIRMED_FAILURE_COLOR
    return CATEGORY_COLORS[finding_category(finding)]
