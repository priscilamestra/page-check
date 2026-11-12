from pagecheck.audits.layout.rules import build_layout_findings


def layout(width=390, document=390, controls=None):
    return {"viewport_width": width, "document_width": document,
            "measured_elements": controls or []}


def control(i, x, y, width, height):
    return {"index": i, "tag": "button", "kind": "control",
            "box": {"x": x, "y": y, "width": width, "height": height}}


def test_without_overflow_or_overlap_is_clear():
    assert build_layout_findings(layout(390, 390, [control(0, 4, 20, 110, 32)])) == []


def test_horizontal_overflow_has_observed_width_and_box():
    items = build_layout_findings(layout(390, 820, [control(0, 450, 20, 120, 40)]))
    ids = {item["id"] for item in items}
    assert "layout-horizontal-overflow" in ids
    assert "layout-control-offscreen-0" in ids
    assert any("820" in f["description"] for f in items)


def test_overlap_returns_warning_not_failure():
    items = build_layout_findings(layout(390, 390, [
        control(0, 10, 20, 120, 40), control(1, 50, 20, 120, 40),
    ]))
    overlaps = [f for f in items if f["id"].startswith("layout-overlap")]
    assert len(overlaps) == 1 and overlaps[0]["status"] == "warning"


def test_adjacent_controls_are_not_overlaps():
    items = build_layout_findings(layout(390, 390, [
        control(0, 10, 20, 120, 40), control(1, 140, 20, 120, 40),
    ]))
    assert not any(f["id"].startswith("layout-overlap") for f in items)


def test_invalid_or_missing_geometry_is_ignored():
    items = build_layout_findings(layout(390, 390, [{"kind": "control", "box": {"x": float("nan")}}]))
    assert items == []


def test_overflow_is_detected_even_without_culprit():
    items = build_layout_findings(layout(390, 900))
    assert items[0]["id"] == "layout-horizontal-overflow"
    assert items[0]["box"] is None


def test_overflow_structural_element_is_annotatable():
    report = layout(390, 810)
    report["overflow_candidates"] = [{"tag": "div", "box": {
        "x": 12, "y": 120, "width": 810, "height": 40,
    }}]
    issues = build_layout_findings(report)
    assert issues[0]["box"]["width"] == 810
