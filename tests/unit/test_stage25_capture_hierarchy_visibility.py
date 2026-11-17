"""UI contract and capture-only evidence for the screenshots stage."""
from pagecheck.reporting.annotations.findings import build_capture_image_warnings
from pagecheck.ui.components.hierarchy_indicator import hierarchy_indicator


def test_screenshot_hierarchy_is_always_labeled_without_inventing_a_score():
    assert hierarchy_indicator(None) == ("Hierarchy: Not assessed", "gray", "")
    status, color, detail = hierarchy_indicator({"status": "limited", "headings_checked": 1})
    assert status == "Hierarchy: Limited"
    assert color == "orange"
    assert "1 visible heading" in detail
    assert hierarchy_indicator({"status": "no_measured_findings"})[:2] == (
        "Hierarchy: Measured checks clear", "green")


def test_visible_pending_image_is_marked_only_as_capture_warning():
    image = {"index": 2, "src": "https://example.org/icon.svg", "status": "not_verified",
             "rendered": True, "complete": False, "natural_width": 0,
             "box": {"x": 12, "y": 40, "width": 45, "height": 35}}
    warning = build_capture_image_warnings({"images": [image]})[0]
    assert warning["status"] == "warning"
    assert warning["evidence"]["capture_only"] is True
    assert warning["box"]["x"] == 12
    assert build_capture_image_warnings({"images": [{**image, "natural_width": 30}]}) == []
