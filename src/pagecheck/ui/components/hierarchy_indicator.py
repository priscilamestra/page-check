"""Pure view labels for measured visual hierarchy results."""
from __future__ import annotations

from collections.abc import Mapping

def hierarchy_indicator(review: object) -> tuple[str, str, str]:
    """Compact, honest design summary for one viewport, including old reports."""
    review = review if isinstance(review, Mapping) else {}
    labels = {
        "needs_review": ("Hierarchy: Needs review", "orange"),
        "no_measured_findings": ("Hierarchy: Measured checks clear", "green"),
        "limited": ("Hierarchy: Limited", "orange"),
        "not_verified": ("Hierarchy: Not assessed", "gray"),
    }
    label, color = labels.get(review.get("status"), ("Hierarchy: Not assessed", "gray"))
    details = []
    headings = review.get("headings_checked")
    layout_issues = review.get("layout_findings")
    if isinstance(headings, int) and headings > 0:
        details.append(f"{headings} visible heading(s) checked")
    if isinstance(layout_issues, int) and layout_issues > 0:
        details.append(f"{layout_issues} geometry finding(s)")
    return label, color, " · ".join(details)


def design_analysis_available(review: object) -> bool:
    """Whether a report has at least one measured design criterion.

    Reports recovered from an earlier backend release can have screenshots but
    no design metadata. They must not display four misleading status pills.
    """
    if not isinstance(review, Mapping):
        return False
    criteria = review.get("criteria")
    return isinstance(criteria, Mapping) and any(
        isinstance(value, Mapping) and value.get("status") not in
        (None, "not_assessed", "not_verified")
        for value in criteria.values()
    )


def design_category_badges(review: object) -> list[tuple[str, str]]:
    """Actionable, criterion-specific labels; never duplicate screenshot status."""
    details = review if isinstance(review, Mapping) else {}
    criteria = details.get("criteria")
    criteria = criteria if isinstance(criteria, Mapping) else {}
    labels = (("headings", "Titles"), ("contrast", "Contrast"),
              ("cta", "Buttons"), ("layout", "Layout"))
    badges: list[tuple[str, str]] = []
    capped = details.get("truncated") is True
    for name, label in labels:
        item = criteria.get(name)
        item = item if isinstance(item, Mapping) else {}
        state = item.get("status", "not_assessed")
        count = item.get("detail")
        try:
            count = int(count) if count not in (None, "") else 0
        except (TypeError, ValueError):
            count = 0
        if state == "needs_review":
            text, color = f"{count} to review" if count > 0 else "Needs review", "orange"
        elif state == "no_issues":
            text, color = ("Sample without alerts", "orange") if capped else ("No measured issues", "green")
        elif state == "limited" and name == "headings":
            text, color = "Single heading level", "gray"
        elif state == "limited":
            text, color = "Partial sample", "orange"
        else:
            text, color = "Not assessed", "gray"
        badges.append((f"{label}: {text}", color))
    return badges
