"""Stage 28: the screenshot report explains measured findings and marker colors."""
from pathlib import Path

from PIL import Image

from pagecheck.acquisition.browser.visual_hierarchy import assess_heading_hierarchy
from pagecheck.reporting.annotations.marker_style import CATEGORY_COLORS
from pagecheck.reporting.annotations.overlay import annotate_screenshot, link_marker_numbers
from pagecheck.reporting.consolidation.normalize import normalize_check
from pagecheck.ui.components.overview_dashboard import OVERVIEW_STYLES, metric_cards_html
from pagecheck.ui.components.visual_explorer import visual_observations
from pagecheck.ui.components.visual_issue_details import (
    design_chips_html, detailed_observations_html,
)


def test_overview_three_compact_cards_one_wide_coverage():
    assert "minmax(0,1.35fr)" in OVERVIEW_STYLES
    result = metric_cards_html(seo_score=90, seo_partial=False, issues=0, reviews=2,
                               completed=2, partial=2, not_verified=3)
    assert 'class="pc-kpi-label">Technical SEO</div>' in result
    assert 'pc-kpi-seo' in result
    assert 'Eligible SEO rules' not in result
    assert 'not a site-wide score' not in result
    assert 'pc-kpi-inline' in result
    assert "2/7" in result
    assert "Reported by executed checks" not in result


def test_category_chips_use_distinct_semantic_colors():
    review = {"criteria": {
        "headings": {"status": "no_issues"},
        "contrast": {"status": "needs_review", "detail": "7"},
        "cta": {"status": "needs_review", "detail": "5"},
        "layout": {"status": "needs_review"},
    }}
    rendered = design_chips_html(review)
    for category in ("titles", "contrast", "buttons", "layout"):
        assert CATEGORY_COLORS[category] in rendered
    assert "Contrast:</strong> 7 to review" in rendered
    assert "Buttons:</strong> 5 to review" in rendered


def test_specific_ratios_controls_and_image_sources_remain_in_report():
    samples = {
        "headings": [],
        "targets": [{"text": "Get a demo", "selector": "button:nth-of-type(1)",
                     "box": {"x": 30, "y": 40, "width": 16, "height": 18}}],
        "contrast": [
            {"text": "Customer support", "ratio": 2.2, "threshold": 4.5,
             "foreground": "rgb(153, 153, 153)", "background": "rgb(255,255,255)",
             "selector": "p:nth-of-type(2)",
             "box": {"x": 10, "y": 20, "width": 90, "height": 30}},
            {"text": "Pricing", "ratio": 2.8, "threshold": 4.5,
             "selector": "a:nth-of-type(3)",
             "box": {"x": 160, "y": 40, "width": 70, "height": 30}},
        ],
    }
    findings = assess_heading_hierarchy(samples)["findings"]
    checks = [normalize_check(f, source="playwright", viewport="desktop",
                              page_url="https://example.com", default_module="visual")
              for f in findings]
    checks[0]["evidence"]["marker_number"] = 2
    observations = visual_observations({"findings": checks}, "desktop")
    assert len(observations) == 3
    rendered = detailed_observations_html(observations)
    assert "Customer support" in rendered
    assert "Pricing" in rendered
    assert "Get a demo" in rendered
    assert "2.2:1" in rendered and "4.5:1" in rendered
    assert "16 × 18px" in rendered and "24 × 24px" in rendered
    assert "#2" in rendered and "p:nth-of-type(2)" in rendered
    assert rendered.count("Text may have insufficient contrast") == 0


def test_markup_escapes_untrusted_capture_text():
    html = detailed_observations_html([{
        "check_id": "design-text-contrast-0", "status": "warning",
        "evidence": {"text": "<script>alert(1)</script>",
                     "contrast_ratio": 1.2, "minimum_ratio": 4.5},
    }])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_marker_colors_and_numbers_share_the_same_report_record(tmp_path: Path):
    path = tmp_path / "initial.png"
    Image.new("RGB", (390, 720), "white").save(path)
    findings = [
        {"id": "design-text-contrast-0", "status": "warning",
         "category": "layout", "evidence": {"text": "Pricing"},
         "box": {"x": 30, "y": 80, "width": 60, "height": 26}},
        {"id": "design-small-target-0", "status": "warning",
         "category": "layout", "evidence": {"label": "Demo"},
         "box": {"x": 150, "y": 80, "width": 16, "height": 18}},
        {"id": "capture-image-missing-0", "status": "warning",
         "category": "images", "evidence": {"capture_only": True},
         "box": {"x": 250, "y": 80, "width": 40, "height": 45}},
    ]
    rendered = annotate_screenshot(screenshot_path=path,
                                  output_path=tmp_path / "annotated.png",
                                  findings=findings, viewport_width=390,
                                  page_height=720)
    assert [m["color"] for m in rendered["markers"]] == [
        CATEGORY_COLORS["contrast"], CATEGORY_COLORS["buttons"],
        CATEGORY_COLORS["images"],
    ]
    link_marker_numbers(findings, rendered)
    assert [f["evidence"]["marker_number"] for f in findings] == [1, 2, 3]
    assert findings[0]["evidence"]["marker_color"] == CATEGORY_COLORS["contrast"]
    Image.open(tmp_path / "annotated.png").verify()


def test_confirmed_failure_remains_red_and_unmarked_findings_do_not_claim_number(tmp_path):
    path = tmp_path / "initial.png"
    Image.new("RGB", (390, 720), "white").save(path)
    findings = [
        {"id": "image-broken-0", "status": "failed", "category": "images",
         "box": {"x": 10, "y": 30, "width": 30, "height": 40}},
        {"id": "design-text-contrast-1", "status": "warning", "category": "layout",
         "box": {"x": 10, "y": 2000, "width": 30, "height": 40}},
    ]
    rendered = annotate_screenshot(screenshot_path=path, output_path=tmp_path / "out.png",
                                  findings=findings, viewport_width=390, page_height=720)
    link_marker_numbers(findings, rendered)
    assert rendered["annotated_count"] == 1
    assert rendered["markers"][0]["color"] == "#E46A70"
    assert findings[0]["evidence"]["marker_number"] == 1
    assert "evidence" not in findings[1]
