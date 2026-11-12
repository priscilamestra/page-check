"""Testes da preparação de dados do dashboard, sem iniciar Streamlit ou rede."""
import json
from pathlib import Path

import pytest

from pagecheck.ui.components.report_data import (
    export_report_json,
    issue_counts,
    local_demo_report,
    module_rows,
    parse_uploaded_report,
    report_from_seo_response,
    safe_screenshot_path,
    screenshot_entries,
    validate_report,
)


def report():
    return {
        "schema_version": "audit-report-1.0", "audit_id": "demo",
        "requested_url": "https://example.com", "final_url": "https://example.com",
        "niche": "Tecnologia", "objective": "leads", "status": "partial",
        "summary": {"counts": {"passed": 2, "failed": 1},
                    "by_module": {"seo": {"passed": 2, "failed": 1}}},
        "scores": {"overall": None, "internal": {"seo": {"score": 80}}},
        "checks": [{"status": "passed"}], "findings": [{"status": "failed"}],
        "actions_by_team": [{"team": "SEO", "actions": []}],
        "source_states": {"seo": "completed", "conversion": "not_verified"},
    }


def test_valid_report_preserves_data():
    data = report()
    assert validate_report(data) is data


def test_missing_report_fields_rejected():
    data = report()
    del data["final_url"]
    with pytest.raises(ValueError, match="final_url"):
        validate_report(data)


def test_wrong_schema_rejected():
    data = report()
    data["schema_version"] = "other"
    with pytest.raises(ValueError, match="audit-report"):
        validate_report(data)


def test_invalid_collections_rejected():
    data = report()
    data["findings"] = [{"ok": True}, "broken"]
    with pytest.raises(ValueError, match="findings"):
        validate_report(data)


def test_parse_json_keeps_utf8_text():
    parsed = parse_uploaded_report(json.dumps(report(), ensure_ascii=False).encode("utf-8"))
    assert parsed["niche"] == "Tecnologia"


def test_parse_invalid_json_rejected():
    with pytest.raises(ValueError, match="UTF-8"):
        parse_uploaded_report(b"invalid-json")


def test_oversized_upload_rejected():
    with pytest.raises(ValueError, match="5 MB"):
        parse_uploaded_report(b"x" * (5 * 1024 * 1024 + 1))


def test_seo_report_remains_partial():
    seo = {"requested_url": "https://example.com", "final_url": "https://example.com",
           "niche": "Tecnologia", "objective": "leads", "score": 80.0,
           "coverage": 1.0, "partial_score": False, "ruleset_version": "seo-1.0.0",
           "checks": [{"check_id": "SEO_TITLE", "module": "seo", "status": "passed",
                       "severity": "info", "title": "Título", "target_url": "https://example.com",
                       "team": "SEO", "evidence": {}, "recommendation": ""}],
           "findings": []}
    result = report_from_seo_response(seo)
    assert result["status"] == "partial"
    assert result["scores"]["internal"]["seo"]["score"] == 80.0
    assert result["source_states"]["conversion"] == "not_verified"


def test_local_demo_missing_has_actionable_message(tmp_path):
    with pytest.raises(FileNotFoundError, match="consolidation_fixture_smoke"):
        local_demo_report(tmp_path)


def test_local_demo_reads_fixture(tmp_path):
    target = tmp_path / "artifacts" / "consolidation_stage15" / "consolidated_audit.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(report()), encoding="utf-8")
    assert local_demo_report(tmp_path)["audit_id"] == "demo"


def test_safe_screenshot_must_be_under_artifacts(tmp_path):
    safe = tmp_path / "artifacts" / "browser" / "shot.png"
    safe.parent.mkdir(parents=True)
    safe.write_bytes(b"fake-png")
    outside = tmp_path / "private.png"
    outside.write_bytes(b"fake-png")
    assert safe_screenshot_path(safe, tmp_path) == safe.resolve()
    assert safe_screenshot_path(outside, tmp_path) is None
    assert safe_screenshot_path("../../private.png", tmp_path) is None


def test_screenshot_rejects_other_extension_and_missing(tmp_path):
    other = tmp_path / "artifacts" / "shot.txt"
    other.parent.mkdir(parents=True)
    other.write_text("test")
    assert safe_screenshot_path(other, tmp_path) is None
    assert safe_screenshot_path("artifacts/missing.png", tmp_path) is None


def test_screenshot_entries_prioritize_annotated(tmp_path):
    shots = tmp_path / "artifacts" / "mobile"
    shots.mkdir(parents=True)
    (shots / "annotated.png").write_bytes(b"annotated")
    (shots / "plain.png").write_bytes(b"plain")
    data = report()
    data["screenshots"] = {
        "mobile": {"annotated": str(shots / "annotated.png"),
                   "after_scroll": str(shots / "plain.png")}}
    assert screenshot_entries(data, tmp_path) == [("mobile", (shots / "annotated.png").resolve())]


def test_issue_counts_and_module_rows():
    assert issue_counts(report())["not_verified"] == 0
    assert issue_counts(report())["failed"] == 1
    assert module_rows(report()) == [{"Módulo": "seo", "Problemas": 1,
                                     "Atenção": 0, "Aprovados": 2}]


def test_export_preserves_accents():
    assert "Tecnologia" in export_report_json(report())
