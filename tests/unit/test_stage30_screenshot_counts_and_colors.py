"""Screenshot UX: honest marker counts and stable category styling."""
from pagecheck.reporting.annotations.marker_style import CATEGORY_COLORS
from pagecheck.ui.components.visual_issue_details import (
    ISSUE_ACCORDION_STYLES,
    grouped_observations,
    marker_numbers,
    marker_summary,
    screenshot_findings_label,
    detailed_observations_html,
)


def finding(category, idx, marker=None):
    check = {
        "contrast": "design-text-contrast", "buttons": "design-small-target",
        "layout": "layout-overflow", "images": "capture-image-missing",
    }[category]
    evidence = {"text": f"Item {idx}", "selector": f"#item-{idx}"}
    if marker is not None:
        evidence["marker_number"] = marker
    return {"check_id": f"{check}-{idx}", "status": "warning",
            "title": f"Issue {idx}", "evidence": evidence}


def test_count_findings_separately_from_unique_drawn_markers():
    # Seven contrast warnings but only four marks: two warnings share #1,
    # and three more are outside the annotated screenshot.
    observations = ([finding("contrast", i, m) for i, m in enumerate([1,1,2,3,4,None,None])]
                    + [finding("buttons", i+10, m) for i, m in enumerate([5,6,7,8,9])]
                    + [finding("layout", 20, 10)]
                    + [finding("images", 30, 11), finding("images", 31, None)])
    assert marker_summary(observations) == {"findings": 15, "markers": 11}
    assert screenshot_findings_label(observations) == "What to fix · 15 findings"
    groups = grouped_observations(observations)
    assert [(g["category"], g["count"], marker_summary(g["findings"])["markers"])
            for g in groups] == [("contrast", 7, 4), ("buttons", 5, 5),
                                 ("layout", 1, 1), ("images", 2, 1)]
    assert screenshot_findings_label(groups[0]["findings"], name="Contrast") == "Contrast · 7 findings"
    assert set(marker_numbers(observations)) == set(range(1, 12))


def test_not_annotated_never_claims_visible_markers():
    findings = [finding("images", 1, 1), finding("images", 2, None)]
    assert marker_summary(findings, annotated=False) == {"findings": 2, "markers": 0}
    assert screenshot_findings_label(findings, annotated=False) == "What to fix · 2 findings"
    assert screenshot_findings_label(findings, annotated=True, name="Images") == "Images · 2 findings"
    assert marker_numbers([{"evidence": {"marker_number": True}},
                           {"evidence": {"marker_number": -1}}]) == set()


def test_category_styles_match_the_kpis_and_are_scoped():
    for category in ("contrast", "buttons", "layout", "images", "titles"):
        assert CATEGORY_COLORS[category] in ISSUE_ACCORDION_STYLES
        assert f"st-key-pc_fix_desktop_{category}" in ISSUE_ACCORDION_STYLES
        assert f"st-key-pc_fix_mobile_{category}" in ISSUE_ACCORDION_STYLES
    assert '[data-testid="stExpander"] details > summary' in ISSUE_ACCORDION_STYLES
    assert 'focus-visible' in ISSUE_ACCORDION_STYLES
    assert "forced-colors" in ISSUE_ACCORDION_STYLES


def test_old_screenshot_evidence_preserved_and_escaped():
    findings = [finding("contrast", 1, 1), finding("contrast", 2, 1),
                finding("contrast", 3, None)]
    rendered = detailed_observations_html(findings)
    assert rendered.count('aria-label="Screenshot marker 1"') == 2
    assert "#item-3" in rendered
    assert marker_summary(findings) == {"findings": 3, "markers": 1}


def test_ui_findings_label_never_exposes_marker_count():
    samples = [finding("contrast", 1, None), finding("contrast", 2, 7)]
    for annotated in (True, False):
        label = screenshot_findings_label(samples, annotated=annotated, name="Contrast")
        assert label == "Contrast · 2 findings"
        assert "marker" not in label.lower()
