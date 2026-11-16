"""Offline contract tests for the private PostgreSQL temporary report repository."""
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pagecheck.persistence.postgres.temporary import (
    TemporaryAuditNotFound, TemporaryAuditStore, TemporaryAuditTooLarge,
    _allowed_png, _copy_for_storage, _digest, decode_recovery_token,
    new_recovery_token, RETENTION,
)
from pagecheck.persistence.sqlite.history import InvalidHistoryReport


class FakeDatabase:
    """Simulates the tiny SQL contract without requiring credentials/network."""

    def __init__(self):
        self.audits = {}
        self.images = {}
        self.commands = []

    def connect(self):
        return FakeConnection(self)


class FakeConnection:
    def __init__(self, db):
        self.db = db
        self.snapshot = None

    def __enter__(self):
        self.snapshot = (copy.deepcopy(self.db.audits), copy.deepcopy(self.db.images))
        return self

    def __exit__(self, typ, value, tb):
        if typ is not None:
            self.db.audits, self.db.images = self.snapshot

    def cursor(self):
        return FakeCursor(self.db)


class FakeCursor:
    rowcount = 0

    def __init__(self, db):
        self.db = db
        self.row = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, sql, params=None):
        self.db.commands.append((sql, params))
        self.rowcount = 0
        self.row = None
        now = datetime.now(timezone.utc)
        if sql.startswith("INSERT INTO pagecheck_temporary_audits"):
            digest, expiry, payload = params
            if digest in self.db.audits:
                raise ValueError("duplicate")
            self.db.audits[digest] = (expiry, json.loads(payload))
            self.rowcount = 1
        elif sql.startswith("INSERT INTO pagecheck_temporary_screenshots"):
            digest, viewport, kind, png = params
            self.db.images[(digest, viewport, kind)] = png
            self.rowcount = 1
        elif sql.startswith("DELETE FROM pagecheck_temporary_audits WHERE token_digest"):
            digest = params[0]
            self.rowcount = int(digest in self.db.audits)
            self.db.audits.pop(digest, None)
            for key in list(self.db.images):
                if key[0] == digest:
                    del self.db.images[key]
        elif sql.startswith("DELETE FROM pagecheck_temporary_audits WHERE expires_at"):
            expired = [digest for digest, (expiry, _) in self.db.audits.items() if expiry <= now]
            for digest in expired:
                del self.db.audits[digest]
                for key in list(self.db.images):
                    if key[0] == digest:
                        del self.db.images[key]
            self.rowcount = len(expired)
        elif sql.startswith("SELECT report FROM"):
            digest = params[0]
            record = self.db.audits.get(digest)
            if record and record[0] > now:
                self.row = (copy.deepcopy(record[1]),)
        elif sql.startswith("SELECT s.png FROM"):
            digest, viewport, kind = params
            record = self.db.audits.get(digest)
            if record and record[0] > now:
                png = self.db.images.get((digest, viewport, kind))
                if png is not None:
                    self.row = (png,)
        else:
            raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchone(self):
        return self.row


def sample_report():
    return {
        "schema_version": "audit-report-1.0", "requested_url": "https://example.org",
        "final_url": "https://example.org", "niche": "SaaS", "objective": "leads",
        "status": "partial", "source_states": {"seo": "completed"},
        "scores": {"internal": {"seo": {"score": 70}}},
        "summary": {"counts": {"failed": 0}},
        "checks": [], "findings": [], "actions_by_team": [], "screenshots": {},
    }


def store(tmp_path):
    db = FakeDatabase()
    return TemporaryAuditStore(tmp_path, connect=db.connect), db


def test_tokens_are_unique_and_decodable():
    first, second = new_recovery_token(), new_recovery_token()
    assert first != second
    assert len(decode_recovery_token(first)) == 32
    assert len(first) == 43


@pytest.mark.parametrize("token", [None, "", "abc", "a" * 43, "../file", "?audit=x", "á" * 43])
def test_malformed_tokens_cannot_access_records(token):
    with pytest.raises(TemporaryAuditNotFound):
        decode_recovery_token(token)


def test_token_digest_is_not_bearer_token():
    token = new_recovery_token()
    assert len(_digest(token)) == 32
    assert token.encode() not in _digest(token)


def test_save_load_roundtrip_does_not_modify_caller(tmp_path):
    target, db = store(tmp_path)
    original = sample_report()
    saved = target.save(original)
    assert original == sample_report()
    assert target.load(saved["recovery_token"])["requested_url"] == "https://example.org"
    assert "recovery_token" not in str(db.audits)
    assert len(db.audits) == 1
    assert saved["stored_screenshots"] == 0


def test_duration_is_24_hours(tmp_path):
    target, _ = store(tmp_path)
    start = datetime.now(timezone.utc)
    saved = target.save(sample_report())
    end = datetime.fromisoformat(saved["expires_at"])
    assert timedelta(hours=23, minutes=59) < end - start < timedelta(hours=24, minutes=1)
    assert RETENTION == timedelta(hours=24)


def test_replace_revokes_the_old_token_after_new_save(tmp_path):
    target, db = store(tmp_path)
    first = target.save(sample_report())["recovery_token"]
    second = target.save(sample_report(), previous_token=first)["recovery_token"]
    assert len(db.audits) == 1
    with pytest.raises(TemporaryAuditNotFound):
        target.load(first)
    assert target.load(second)["niche"] == "SaaS"


def test_invalid_previous_token_is_rejected_before_write(tmp_path):
    target, db = store(tmp_path)
    with pytest.raises(TemporaryAuditNotFound):
        target.save(sample_report(), previous_token="not a token")
    assert db.audits == {}


def test_expired_reports_are_inaccessible_and_prunable(tmp_path):
    target, db = store(tmp_path)
    token = target.save(sample_report())["recovery_token"]
    digest = _digest(token)
    _, report = db.audits[digest]
    db.audits[digest] = (datetime.now(timezone.utc) - timedelta(seconds=1), report)
    with pytest.raises(TemporaryAuditNotFound):
        target.load(token)
    assert target.purge_expired() == 1
    assert db.audits == {}


def test_invalid_report_never_writes(tmp_path):
    target, db = store(tmp_path)
    report = sample_report()
    report["status"] = "queued"
    with pytest.raises(InvalidHistoryReport):
        target.save(report)
    assert not db.audits


def test_oversized_report_never_writes(tmp_path):
    target, db = store(tmp_path)
    report = sample_report()
    report["content"] = "x" * (5 * 1024 * 1024)
    with pytest.raises(InvalidHistoryReport):
        target.save(report)
    assert not db.audits


def test_valid_image_is_persisted_as_bytes_not_local_path(tmp_path):
    target, db = store(tmp_path)
    shot = tmp_path / "artifacts" / "run" / "desktop.png"
    shot.parent.mkdir(parents=True)
    image = b"\x89PNG\r\n\x1a\n" + b"test" * 20
    shot.write_bytes(image)
    report = sample_report()
    report["screenshots"] = {"desktop": {"initial": str(shot)}}
    saved = target.save(report)
    shot.unlink()
    stored = target.load(saved["recovery_token"])
    assert stored["screenshots"]["desktop"]["initial"] == "temporary-image://desktop/initial"
    assert target.load_image(saved["recovery_token"], "desktop", "initial") == image
    assert str(shot) not in json.dumps(stored)
    assert saved["stored_screenshots"] == 1


def test_nonlocal_and_invalid_image_is_not_persisted(tmp_path):
    target, _ = store(tmp_path / "app")
    image = tmp_path / "outside.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"hi")
    report = sample_report()
    report["screenshots"] = {"desktop": {"initial": str(image)}}
    saved = target.save(report)
    assert target.load(saved["recovery_token"])["screenshots"] == {}


def test_invalid_png_content_is_not_accepted(tmp_path):
    image = tmp_path / "artifacts" / "bad.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"broken")
    assert _allowed_png(str(image), tmp_path) is None


def test_large_png_rejected_before_write(tmp_path):
    target, db = store(tmp_path)
    image = tmp_path / "artifacts" / "huge.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024))
    report = sample_report()
    report["screenshots"] = {"mobile": {"initial": str(image)}}
    with pytest.raises(TemporaryAuditTooLarge):
        target.save(report)
    assert not db.audits


def test_multiple_screenshots_enforce_collective_limit(tmp_path):
    report = sample_report()
    report["screenshots"] = {}
    for i, kind in enumerate(("initial", "after_scroll", "annotated")):
        path = tmp_path / "artifacts" / f"{i}.png"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * (1500 * 1024))
        report["screenshots"].setdefault("desktop", {})[kind] = str(path)
    with pytest.raises(TemporaryAuditTooLarge):
        _copy_for_storage(report, tmp_path)


def test_delete_revokes_token_and_images(tmp_path):
    target, db = store(tmp_path)
    token = target.save(sample_report())["recovery_token"]
    assert target.delete(token) is True
    assert target.delete(token) is False
    with pytest.raises(TemporaryAuditNotFound):
        target.load(token)
    assert not db.audits


@pytest.mark.parametrize("viewport,kind", [("admin", "initial"), ("desktop", "bad")])
def test_reject_invalid_image_coordinates(tmp_path, viewport, kind):
    target, _ = store(tmp_path)
    token = target.save(sample_report())["recovery_token"]
    with pytest.raises(TemporaryAuditNotFound):
        target.load_image(token, viewport, kind)


def test_migration_has_expiry_index_and_cascade():
    migration = (Path(__file__).parents[2] / "migrations" / "0001_temporary_postgres.sql").read_text()
    assert "expires_at TIMESTAMPTZ NOT NULL" in migration
    assert "ON DELETE CASCADE" in migration
    assert "CREATE INDEX" in migration
    assert "report JSONB NOT NULL" in migration
    assert "png BYTEA NOT NULL" in migration


def test_connection_message_is_not_redundant():
    ui = (Path(__file__).parents[2] / "src/pagecheck/ui/app.py").read_text()
    assert "Live audits require the API server." not in ui
    assert 'st.badge("FastAPI connected", color="green")' in ui
    assert 'st.badge("FastAPI disconnected", color="gray")' in ui
