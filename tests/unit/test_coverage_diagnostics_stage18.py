"""Stage 18: honest status explanations and safe limited evidence export."""
import io
import zipfile
from types import SimpleNamespace

from pagecheck.integrations.cli_runner import run_local_json_command
from pagecheck.reporting.exports.bundle import zip_export
from pagecheck.ui.components.coverage_details import (
    not_verified_by_area,
    screenshot_kind,
    source_rows,
)
from pagecheck.ui.components.report_data import screenshot_entries


def minimal_report():
    return {
        "schema_version": "audit-report-1.0",
        "status": "partial", "requested_url": "https://example.com",
        "final_url": "https://example.com", "niche": "B2B", "objective": "leads",
        "scores": {"internal": {"seo": {"score": 100}}},
        "summary": {"counts": {"not_verified": 246}, "by_module": {
            "navigation": {"not_verified": 244}, "tracking": {"not_verified": 2},
        }},
        "checks": [], "findings": [], "actions_by_team": [],
        "source_states": {"seo": "completed", "conversion": "completed",
                          "visuals": {"desktop": "not_verified", "mobile": "not_verified"},
                          "engines": {"axe": "completed", "impeccable": "not_verified"}},
        "visual_capture": {"status": "partial", "errors": {
            "desktop": "The guarded navigation timed out.",
            "mobile": "The page exceeded safe document height.",
        }},
        "engine_limitations": {
            "axe": ["Old source note", "Static HTML only; no runtime behavior."],
            "impeccable": ["Local detector exited with code 1."],
        },
        "screenshots": {},
    }


def test_hubspot_like_sources_are_labelled_without_inventing_success():
    rows = {row["id"]: row for row in source_rows(minimal_report())}
    assert rows["seo"]["status_label"] == "Completed"
    assert rows["axe"]["status_label"] == "Completed"
    assert rows["impeccable"]["status_label"] == "Not verified"
    assert "exited with code 1" in rows["impeccable"]["reason"]


def test_visual_unavailable_shows_real_recorded_reasons():
    rows = {row["id"]: row for row in source_rows(minimal_report())}
    assert "timed out" in rows["desktop"]["reason"]
    assert "height" in rows["mobile"]["reason"]


def test_successful_axe_uses_scope_note_not_failure():
    rows = {row["id"]: row for row in source_rows(minimal_report())}
    assert rows["axe"]["reason"] == "Static HTML only; no runtime behavior."


def test_no_browser_request_is_not_misreported_as_failure():
    report = minimal_report()
    report.pop("visual_capture")
    rows = {row["id"]: row for row in source_rows(report)}
    assert "not requested" in rows["desktop"]["reason"]


def test_old_report_without_reasons_still_renders():
    report = minimal_report()
    report.pop("engine_limitations")
    report.pop("visual_capture")
    rows = source_rows(report)
    assert len(rows) == 6
    assert any("did not produce a confirmed result" in x["reason"] for x in rows)


def test_unverified_check_breakdown_is_not_called_a_defect():
    assert not_verified_by_area(minimal_report()) == [("navigation", 244), ("tracking", 2)]


def test_malformed_missing_counts_are_ignored():
    report = minimal_report()
    report["summary"]["by_module"] = {"foo": {"not_verified": True}, "bar": {"not_verified": -4}}
    assert not_verified_by_area(report) == []


def test_initial_screenshot_has_honest_caption():
    report = minimal_report()
    report["screenshots"] = {"desktop": {"initial": "artifacts/test/first.png"}}
    assert "no annotations" in screenshot_kind(report, "desktop")
    assert screenshot_kind(report, "mobile") == "No screenshot"
    report["screenshots"]["desktop"]["annotated"] = "artifacts/test/annotated.png"
    assert screenshot_kind(report, "desktop") == "Annotated screenshot"


def test_initial_screenshot_is_resolved_inside_artifacts(tmp_path):
    shot = tmp_path / "artifacts" / "test" / "first.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(b"\x89PNG\r\n\x1a\nsmall-test")
    report = minimal_report()
    report["screenshots"] = {"desktop": {"initial": str(shot)}}
    assert screenshot_entries(report, tmp_path) == [("desktop", shot.resolve())]


def test_export_includes_initial_viewport_without_claiming_full_audit(tmp_path):
    shot = tmp_path / "artifacts" / "test" / "first.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(b"\x89PNG\r\n\x1a\nsmall-test")
    report = minimal_report()
    report["screenshots"] = {"desktop": {"initial": str(shot)}}
    with zipfile.ZipFile(io.BytesIO(zip_export(report, tmp_path))) as bundle:
        assert bundle.read("screenshots/desktop.png") == shot.read_bytes()
        assert b"screenshots/desktop.png" in bundle.read("report.html")


def test_cli_nonzero_exit_has_safe_readable_reason(tmp_path):
    def fake(_command, **_kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="SECRET output")
    response = run_local_json_command("impeccable", ["local", "detect"], root=tmp_path, run=fake)
    assert response["status"] == "not_verified"
    assert "code 1" in response["limitations"][0]
    assert "SECRET" not in str(response)


def test_cli_timeout_has_friendly_reason(tmp_path):
    import subprocess
    def fake(_command, **_kwargs):
        raise subprocess.TimeoutExpired("detector", 3)
    response = run_local_json_command("impeccable", ["local", "detect"],
                                      root=tmp_path, timeout=3, run=fake)
    assert response["status"] == "not_verified"
    assert "3 seconds" in response["limitations"][0]
