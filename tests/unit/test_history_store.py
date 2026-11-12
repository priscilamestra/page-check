"""Unit tests for offline local SQLite persistence (no remote sites)."""
import copy
import json
from pathlib import Path

import pytest

from pagecheck.persistence.sqlite.history import (
    AuditHistory, AuditNotFound, InvalidHistoryReport,
)


def sample_report():
    return {
        "schema_version": "audit-report-1.0", "audit_id": "sample-id",
        "requested_url": "https://example.com/landing?utm_source=google",
        "final_url": "https://example.com/landing", "niche": "Tecnología",
        "objective": "leads", "status": "partial",
        "audit_context": {"language": "es", "keywords": ["gestión comercial"]},
        "source_states": {"seo": "completed", "conversion": "completed", "visuals": {
            "desktop": "not_verified", "mobile": "not_verified"}, "engines": {}},
        "scores": {"internal": {"seo": {"score": 75}}},
        "summary": {"counts": {"passed": 2, "failed": 1, "warning": 0, "not_verified": 1}},
        "checks": [{"check_id": "SEO_TITLE", "status": "passed"}],
        "findings": [{"title": "Missing alt", "severity": "high", "status": "failed",
                      "recommendation": "Add alt text", "team": "Frontend", "module": "images"}],
        "actions_by_team": [], "screenshots": {},
    }


def test_save_and_load_roundtrip_and_timestamp(tmp_path):
    store = AuditHistory(tmp_path)
    original = sample_report()
    saved = store.save(original)
    assert len(saved["audit_id"]) == 32
    assert original["audit_id"] == "sample-id"  # caller not modified
    loaded = store.load(saved["audit_id"])
    assert loaded["audit_id"] == saved["audit_id"]
    assert loaded["audit_context"]["keywords"] == ["gestión comercial"]
    assert loaded["saved_at"] == saved["created_at"]
    assert (tmp_path / "data/local/pagecheck_history.sqlite3").exists()
    assert (tmp_path / "data/local/history" / saved["audit_id"] / "report.json").exists()


def test_history_list_contains_metadata_and_score(tmp_path):
    store = AuditHistory(tmp_path)
    store.save(sample_report())
    entry = store.list()[0]
    assert entry["seo_score"] == 75
    assert entry["issue_count"] == 1
    assert entry["niche"] == "Tecnología"
    assert entry["has_screenshots"] == 0


def test_two_identical_reports_are_distinct_snapshots(tmp_path):
    store = AuditHistory(tmp_path)
    a = store.save(sample_report())
    b = store.save(sample_report())
    assert a["audit_id"] != b["audit_id"]
    assert len(store.list()) == 2


def test_pagination_and_bad_limits(tmp_path):
    store = AuditHistory(tmp_path)
    for _ in range(3):
        store.save(sample_report())
    assert len(store.list(limit=2)) == 2
    assert len(store.list(limit=2, offset=2)) == 1
    for limit, offset in ((0, 0), (101, 0), (1, -1)):
        with pytest.raises(ValueError):
            store.list(limit=limit, offset=offset)


def test_rejects_invalid_report_without_inserting(tmp_path):
    store = AuditHistory(tmp_path)
    bad = sample_report()
    bad["status"] = "queued"
    with pytest.raises(InvalidHistoryReport):
        store.save(bad)
    assert store.list() == []


def test_rejects_large_report(tmp_path):
    store = AuditHistory(tmp_path)
    bad = sample_report()
    bad["extra"] = "x" * (5 * 1024 * 1024)
    with pytest.raises(InvalidHistoryReport, match="5 MB"):
        store.save(bad)


def test_rejects_invalid_and_nonexistent_ids(tmp_path):
    store = AuditHistory(tmp_path)
    with pytest.raises(AuditNotFound):
        store.load("../../etc/passwd")
    with pytest.raises(AuditNotFound):
        store.load("0" * 32)
    with pytest.raises(AuditNotFound):
        store.delete("../other")


def test_copies_visual_evidence_and_survives_original_removal(tmp_path):
    store = AuditHistory(tmp_path)
    picture = tmp_path / "artifacts" / "run" / "desktop.png"
    picture.parent.mkdir(parents=True)
    picture.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 90)
    report = sample_report()
    report["screenshots"] = {"desktop": {"annotated": str(picture)}}
    saved = store.save(report)
    picture.unlink()
    loaded = store.load(saved["audit_id"])
    copied = tmp_path / loaded["screenshots"]["desktop"]["annotated"]
    assert copied.is_file()
    assert copied.read_bytes().startswith(b"\x89PNG")
    assert saved["has_screenshots"] is True


def test_rejects_nonlocal_screenshot_and_preserves_report(tmp_path):
    store = AuditHistory(tmp_path / "project")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"fake")
    report = sample_report()
    report["screenshots"] = {"mobile": {"annotated": str(outside)}}
    saved = store.save(report)
    assert store.load(saved["audit_id"])["screenshots"] == {}
    assert report["screenshots"]["mobile"]["annotated"] == str(outside)


def test_delete_only_target_record_and_copied_evidence(tmp_path):
    store = AuditHistory(tmp_path)
    shot = tmp_path / "artifacts" / "run" / "a.png"
    shot.parent.mkdir(parents=True)
    shot.write_bytes(b"PNGcontent")
    report = sample_report()
    report["screenshots"] = {"mobile": {"after_scroll": str(shot)}}
    first = store.save(report)["audit_id"]
    second = store.save(sample_report())["audit_id"]
    assert store.delete(first) is True
    assert store.delete(first) is False
    assert not (tmp_path / "artifacts/history" / first).exists()
    assert not (tmp_path / "data/local/history" / first).exists()
    assert store.load(second)["audit_id"] == second
    assert shot.exists()  # original evidence isn't deleted


def test_corrupt_report_is_not_returned_as_success(tmp_path):
    store = AuditHistory(tmp_path)
    audit_id = store.save(sample_report())["audit_id"]
    (tmp_path / "data/local/history" / audit_id / "report.json").write_text("not-json")
    with pytest.raises(InvalidHistoryReport, match="could not be read"):
        store.load(audit_id)
