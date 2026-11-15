"""19C: prevent full-page image flood and false visual certainty."""
from pathlib import Path

from pagecheck.ui.components.visual_explorer import visual_cards, visual_observations


def report():
    return {"source_states": {"seo": "completed", "conversion": "completed",
                               "visuals": {"desktop": "partial", "mobile": "not_verified"},
                               "engines": {}},
            "visual_capture": {"errors": {"desktop": "Too tall for full-page capture"}},
            "screenshots": {}, "findings": []}


def test_both_viewports_are_present_even_without_images(tmp_path):
    cards = visual_cards(report(), tmp_path)
    assert len(cards) == 2
    assert [c["viewport"] for c in cards] == ["desktop", "mobile"]
    assert cards[0]["status"] == "partial"
    assert all(c["path"] is None for c in cards)


def test_first_viewport_stays_partial(tmp_path):
    root = tmp_path / "artifacts" / "screenshots"
    root.mkdir(parents=True)
    (root / "first.png").write_bytes(b"test")
    rep = report()
    rep["screenshots"] = {"desktop": {"initial": str(root / "first.png")}}
    cards = visual_cards(rep, tmp_path)
    assert cards[0]["path"] == (root / "first.png").resolve()
    assert cards[0]["is_partial"] is True
    assert cards[0]["annotated"] is False
    assert "Initial viewport" in cards[0]["kind"]


def test_annotated_evidence_does_not_change_source_status(tmp_path):
    folder = tmp_path / "artifacts"
    folder.mkdir()
    (folder / "annotated.png").write_bytes(b"test")
    rep = report()
    rep["screenshots"] = {"mobile": {"annotated": "artifacts/annotated.png"}}
    card = visual_cards(rep, tmp_path)[1]
    assert card["annotated"] is True
    assert card["status"] == "not_verified"  # stored status always authoritative


def test_no_outside_image_can_be_loaded(tmp_path):
    outside = tmp_path / "private.png"
    outside.write_bytes(b"private")
    rep = report()
    rep["screenshots"] = {"desktop": {"initial": str(outside)}}
    assert visual_cards(rep, tmp_path)[0]["path"] is None


def test_unavailable_annotated_path_falls_back_to_safe_initial(tmp_path):
    folder = tmp_path / "artifacts"
    folder.mkdir()
    (folder / "first.png").write_bytes(b"image")
    rep = report()
    rep["screenshots"] = {"desktop": {"initial": "artifacts/first.png",
                                      "annotated": "../../private.png"}}
    card = visual_cards(rep, tmp_path)[0]
    assert card["path"] == (folder / "first.png").resolve()
    assert card["annotated"] is False


def test_only_explicit_viewport_findings_are_linked():
    rep = report()
    rep["findings"] = [
        {"title": "Overflow", "status": "failed", "severity": "high",
         "evidence": {"viewport": "mobile"}},
        {"title": "Other", "status": "failed", "evidence": {"viewport": "desktop"}},
        {"title": "Unknown device", "status": "failed"},
        {"title": "No defect", "status": "not_verified", "viewport": "mobile"},
    ]
    assert [r["title"] for r in visual_observations(rep, "mobile")] == ["Overflow"]
    assert [r["title"] for r in visual_observations(rep, "desktop")] == ["Other"]


def test_visual_observations_ignore_malformed_input():
    assert visual_observations({"findings": "bad"}, "desktop") == []
    assert visual_observations({"findings": [None, "bad"]}, "desktop") == []
