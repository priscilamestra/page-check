import json

import pytest
from PIL import Image

from pagecheck.reporting.annotations.findings import build_image_findings
from pagecheck.reporting.annotations.overlay import (
    AnnotationError,
    annotate_screenshot,
    write_annotation_manifest,
)


def sample_image(*, index=0, status="broken", rendered=True, x=8, y=10, width=20, height=30):
    return {"index": index, "status": status, "rendered": rendered,
            "box": {"x": x, "y": y, "width": width, "height": height}}


def make_png(path):
    Image.new("RGB", (100, 100), (255, 255, 255)).save(path)


def test_only_broken_image_creates_finding():
    findings = build_image_findings({"images": [sample_image()]})
    assert [f["id"] for f in findings] == ["image-broken-0"]
    assert findings[0]["owner"] == "Frontend"


def test_pending_and_loaded_are_not_falsely_reported():
    data = {"images": [sample_image(status="loaded"), sample_image(index=1, status="not_verified")]}
    assert build_image_findings(data) == []


def test_hidden_image_not_marked_on_screenshot():
    assert build_image_findings({"images": [sample_image(rendered=False)]}) == []


def test_invalid_or_non_finite_geometry_is_ignored():
    imgs = [sample_image(width=0), sample_image(index=1, x=float("nan")),
            {"index": 2, "status": "broken", "rendered": True, "box": None}]
    assert build_image_findings({"images": imgs}) == []


def test_findings_sorted_by_document_position():
    data = {"images": [sample_image(index=3, y=60), sample_image(index=2, y=20)]}
    assert [f["id"] for f in build_image_findings(data)] == ["image-broken-2", "image-broken-3"]


def test_annotation_creates_visible_marker_and_preserves_original(tmp_path):
    source = tmp_path / "source.png"
    target = tmp_path / "annotated.png"
    make_png(source)
    finding = build_image_findings({"images": [sample_image()]})
    summary = annotate_screenshot(screenshot_path=source, output_path=target,
                                  findings=finding, viewport_width=100, page_height=100)
    assert summary["annotated_count"] == 1
    assert summary["markers"][0]["finding_id"] == "image-broken-0"
    with Image.open(source) as before, Image.open(target) as after:
        assert before.getpixel((8, 10)) == (255, 255, 255)
        assert after.getpixel((8, 10)) != (255, 255, 255)


def test_refuse_to_overwrite_original_capture(tmp_path):
    source = tmp_path / "source.png"
    make_png(source)
    with pytest.raises(AnnotationError):
        annotate_screenshot(screenshot_path=source, output_path=source,
                            findings=[], viewport_width=100, page_height=100)


def test_out_of_bounds_finding_is_not_drawn(tmp_path):
    source, target = tmp_path / "source.png", tmp_path / "annotated.png"
    make_png(source)
    finding = build_image_findings({"images": [sample_image(x=500, y=500)]})
    summary = annotate_screenshot(screenshot_path=source, output_path=target,
                                  findings=finding, viewport_width=100, page_height=100)
    assert summary["annotated_count"] == 0


def test_manifest_exports_json_with_accents(tmp_path):
    path = tmp_path / "annotations.json"
    write_annotation_manifest({"markers": [{"title": "Imagem não carregou"}]}, path)
    assert json.loads(path.read_text(encoding="utf-8"))["markers"][0]["title"] == "Imagem não carregou"
