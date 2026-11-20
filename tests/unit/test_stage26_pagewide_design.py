"""Stage 26: page-wide measurable design, truthful coverage and compact labels."""

from pagecheck.acquisition.browser.visual_hierarchy import (
    assess_heading_hierarchy,
    inspect_heading_hierarchy,
    make_design_review,
)
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.ui.components.hierarchy_indicator import design_category_badges


def _heading(level: int, y: float, size: float):
    return {"level": level, "font_px": size, "text": f"Title {level}",
            "box": {"x": 20, "y": y, "width": 250, "height": 40}}


def test_pagewide_design_catches_heading_below_screenshot():
    result = assess_heading_hierarchy({"headings": [
        _heading(1, 80, 18), _heading(2, 12900, 36)],
        "targets": [], "contrast": []})
    assert result["status"] == "needs_review"
    finding = result["findings"][0]
    assert finding["id"] == "design-heading-size"
    assert finding["box"]["y"] == 12900
    assert result["scope"] == "rendered_dom"


def test_dom_script_does_not_restrict_heading_to_first_viewport():
    captured = {}
    class Page:
        def evaluate(self, script):
            captured["script"] = script
            return {"headings": [_heading(1, 25, 32), _heading(2, 4000, 24)],
                    "contrast": [], "targets": []}
    result = inspect_heading_hierarchy(Page())
    assert result["headings_checked"] == 2
    assert "rect.top >= vp.height" not in captured["script"]
    assert "rect.left + window.scrollX" in captured["script"]


def test_buttons_and_text_contrast_generate_concrete_recommendations():
    box = {"x": 10, "y": 1500, "width": 16, "height": 16}
    result = assess_heading_hierarchy({
        "headings": [_heading(1, 10, 28)],
        "targets": [{"text": "Buy now", "box": box}],
        "contrast": [{"text": "Offer", "ratio": 1.6, "threshold": 4.5, "box": box}],
    })
    ids = {finding["id"] for finding in result["findings"]}
    assert "design-small-target-0" in ids
    assert "design-text-contrast-0" in ids
    assert all(finding.get("action") and finding.get("box") for finding in result["findings"])
    assert result["criteria"]["cta"]["status"] == "needs_review"
    assert result["criteria"]["contrast"]["detail"] == "1"


def test_device_badges_have_separate_criteria_no_duplicate_limited():
    result = assess_heading_hierarchy({"headings": [_heading(1, 10, 24),
        _heading(2, 2500, 16)], "targets": [], "contrast": []})
    review = make_design_review(result, geometry_checked=True,
                                screenshot_scope="initial_viewport")
    labels = design_category_badges(review)
    assert len(labels) == 4
    assert [v.split(':')[0] for v, _ in labels] == ["Titles", "Contrast", "Buttons", "Layout"]
    assert not any(label.startswith("Hierarchy:") or "visible heading" in label for label, _ in labels)
    assert labels[0][1] == "green"
    assert labels[1][1] == "gray"
    assert labels[3][1] == "green"


def test_legacy_reports_are_not_misrepresented_as_good_design():
    assert all("Not assessed" in text for text, _color in design_category_badges(None))


def test_optional_engine_reasons_explain_why_not_executed():
    report = consolidate_audit(requested_url="https://example.com",
                               final_url="https://example.com",
                               niche="Software", objective="leads")
    reasons = report["engine_limitations"]
    assert "PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES" in reasons["axe"][0]
    assert "sanitized HTML" in reasons["impeccable"][0]
    assert set(reasons) == {"axe", "impeccable"}
