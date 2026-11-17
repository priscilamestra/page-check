"""Stage 27: report integrity and concise, non-duplicated overview."""
from pagecheck.acquisition.browser.visual_hierarchy import assess_heading_hierarchy, make_design_review
from pagecheck.application.use_cases.consolidate_audit import consolidate_audit
from pagecheck.ui.components.overview_insights import prioritized_unique_findings
from pagecheck.ui.components.overview_dashboard import findings_html
from pagecheck.ui.components.hierarchy_indicator import design_analysis_available


def _issue(number, *, title=None, module="images", severity="low"):
    return {
        "id": f"test-{number}", "title": title or f"Finding {number}",
        "recommendation": "Inspect the element and fix its source.",
        "module": module, "severity": severity, "status": "warning",
    }


def test_up_to_ten_distinct_findings_not_four():
    rows = [_issue(i) for i in range(14)]
    report = {"findings": rows}
    result = prioritized_unique_findings(report, limit=10)
    assert len(result) == 10
    assert len({r["title"] for r in result}) == 10


def test_overview_aggregates_repeated_image_symptoms_without_deleting_details():
    rows = [_issue(i, title="Image missing in audit screenshot") for i in range(3)]
    rows.append(_issue(4, title="Link has no destination", module="navigation", severity="medium"))
    result = prioritized_unique_findings({"findings": rows}, limit=10)
    assert len(result) == 2
    image = next(r for r in result if r["module"] == "images")
    assert image["occurrences"] == 3
    rendered = findings_html([{
        "title": r["title"], "recommendation": r["recommendation"],
        "status": r["status"], "severity": r["severity"],
        "area": r["module"], "occurrences": r["occurrences"],
    } for r in result])
    assert "3 occurrences" in rendered
    assert rendered.count("Image missing in audit screenshot") == 1
    assert len(rows) == 4  # backend audit evidence remains intact


def test_design_review_is_retained_by_report_consolidation():
    observation = {
        "headings": [
            {"level": 1, "font_px": 20, "text": "H1", "box": {"x": 0, "y": 0, "width": 200, "height": 24}},
            {"level": 2, "font_px": 36, "text": "H2", "box": {"x": 0, "y": 2200, "width": 200, "height": 45}},
        ],
        "contrast": [{"text": "Tiny", "ratio": 2, "threshold": 4.5}],
        "targets": [{"text": "Buy", "box": {"x": 0, "y": 100, "width": 14, "height": 14}}],
    }
    design = make_design_review(assess_heading_hierarchy(observation), geometry_checked=True)
    report = consolidate_audit(
        requested_url="https://example.com/test", final_url="https://example.com/test",
        niche="SaaS", objective="organic_traffic", visuals={
            "desktop": {"findings": [], "design_review": design, "screenshots": {}, "scroll_complete": False}
        }
    )
    assert report["design_reviews"]["desktop"]["criteria"]["headings"]["status"] == "needs_review"
    assert report["design_reviews"]["desktop"]["criteria"]["contrast"]["status"] == "needs_review"
    assert report["design_reviews"]["desktop"]["criteria"]["cta"]["status"] == "needs_review"


def test_old_report_without_design_results_is_not_presented_as_four_assessments():
    assert not design_analysis_available(None)
    assert not design_analysis_available({"criteria": {"headings": {"status": "not_assessed"}}})
    assert design_analysis_available({"criteria": {"headings": {"status": "needs_review"}}})
