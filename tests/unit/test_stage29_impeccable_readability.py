"""Stage 29: concise UX, category-first investigation without lost evidence."""
from pagecheck.ui.components.visual_issue_details import (
    grouped_observations, detailed_observations_html, design_chips_html,
)
from pagecheck.ui.components.overview_dashboard import metric_cards_html, OVERVIEW_STYLES


def _finding(category, index):
    name = {
        "contrast": "design-text-contrast", "buttons": "design-small-target",
        "layout": "layout-overflow", "images": "capture-image-missing",
    }[category]
    return {
        "check_id": f"{name}-{index}", "title": "Needs review", "status": "warning",
        "evidence": {"marker_number": index + 1, "selector": f"#element-{index}"},
    }


def test_categories_collapsed_at_ui_level_preserve_every_finding_and_marker():
    findings = ([_finding("contrast", i) for i in range(7)] +
                [_finding("buttons", i) for i in range(5)] +
                [_finding("layout", 0)] +
                [_finding("images", i) for i in range(2)])
    grouped = grouped_observations(findings)
    assert [(g["label"], g["count"]) for g in grouped] == [
        ("Contrast", 7), ("Buttons", 5), ("Layout", 1), ("Images", 2)]
    assert sum(g["count"] for g in grouped) == 15
    assert [x for g in grouped for x in g["findings"]] == findings
    html = detailed_observations_html(grouped[0]["findings"])
    assert "#1" in html and "#7" in html
    assert "#element-6" in html


def test_grouping_unknown_category_is_safe_and_empty_has_no_groups():
    assert grouped_observations([]) == []
    assert grouped_observations([{"check_id": "other", "title": "Other"}])[0]["label"] == "Other"


def test_seo_score_discloses_scope_inline():
    html = metric_cards_html(seo_score=100, seo_partial=False, issues=0, reviews=2,
                             completed=2, partial=2, not_verified=3)
    assert "Technical SEO · scoped" in html
    assert "not a site-wide score" in html
    assert "2/7" in html
    assert "minmax(0,1.35fr)" in OVERVIEW_STYLES


def test_category_chips_explain_status_with_text_not_just_color():
    html = design_chips_html({"criteria": {"contrast": {"status": "needs_review", "detail": "7"}}})
    assert "Contrast:</strong> 7 to review" in html
    assert "Titles:</strong> Not assessed" in html
