"""Local audit-history repository.

SQLite holds a searchable index; report JSON and screenshots are stored as files.
No network access, browser automation or Streamlit dependencies.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "audit-report-1.0"
MAX_REPORT_BYTES = 5 * 1024 * 1024
MAX_SCREENSHOT_BYTES = 20 * 1024 * 1024
ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
SCREENSHOT_KEYS = ("initial", "after_scroll", "annotated")
VIEWPORTS = ("desktop", "mobile")


class InvalidHistoryReport(ValueError):
    """Report does not satisfy the minimum persistence contract."""


class AuditNotFound(LookupError):
    """An audit record does not exist in the local history."""


def _validate_report(report: object) -> Mapping[str, Any]:
    if not isinstance(report, dict) or report.get("schema_version") != SCHEMA_VERSION:
        raise InvalidHistoryReport("Expected a Page Check audit-report-1.0 object.")
    if report.get("status") not in {"completed", "partial"}:
        raise InvalidHistoryReport("Only completed or partial reports can be saved.")
    for key in ("requested_url", "final_url", "niche", "objective"):
        if not isinstance(report.get(key), str) or not report[key].strip():
            raise InvalidHistoryReport(f"Invalid or missing report field: {key}.")
    for key in ("scores", "summary", "source_states"):
        if not isinstance(report.get(key), dict):
            raise InvalidHistoryReport(f"Invalid or missing report section: {key}.")
    for key in ("checks", "findings", "actions_by_team"):
        if not isinstance(report.get(key), list) or any(
            not isinstance(item, dict) for item in report[key]
        ):
            raise InvalidHistoryReport(f"Invalid or missing report collection: {key}.")
    return report


def _serialize(report: Mapping[str, Any]) -> bytes:
    try:
        raw = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidHistoryReport("Report must contain serializable JSON values.") from exc
    if len(raw) > MAX_REPORT_BYTES:
        raise InvalidHistoryReport("Report exceeds the 5 MB storage limit.")
    return raw


def _safe_screenshot(value: object, root: Path) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    allowed = (root / "artifacts").resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    if not candidate.is_relative_to(allowed) or candidate.suffix.lower() != ".png":
        return None
    try:
        if not candidate.is_file() or not 0 < candidate.stat().st_size <= MAX_SCREENSHOT_BYTES:
            return None
    except OSError:
        return None
    return candidate


class AuditHistory:
    """Small, local-only history store; not a multi-user account database."""

    def __init__(self, project_root: Path):
        self.root = Path(project_root).resolve()
        self.database = self.root / "data" / "local" / "pagecheck_history.sqlite3"
        self.reports_dir = self.root / "data" / "local" / "history"
        self.screenshot_dir = self.root / "artifacts" / "history"
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    requested_url TEXT NOT NULL,
                    final_url TEXT NOT NULL,
                    niche TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    seo_score REAL,
                    issue_count INTEGER NOT NULL,
                    has_screenshots INTEGER NOT NULL,
                    report_relpath TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audits_created ON audits(created_at DESC, id DESC)")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def _valid_id(audit_id: str) -> str:
        if not isinstance(audit_id, str) or not ID_PATTERN.fullmatch(audit_id):
            raise AuditNotFound("Audit was not found.")
        return audit_id

    def _copy_screenshots(self, report: dict[str, Any], audit_id: str) -> None:
        incoming = report.get("screenshots")
        if not isinstance(incoming, dict):
            report["screenshots"] = {}
            return
        persistent: dict[str, dict[str, str]] = {}
        for viewport in VIEWPORTS:
            sources = incoming.get(viewport)
            if not isinstance(sources, dict):
                continue
            copied: dict[str, str] = {}
            for kind in SCREENSHOT_KEYS:
                source = _safe_screenshot(sources.get(kind), self.root)
                if source is None:
                    continue
                dest_rel = Path("artifacts") / "history" / audit_id / f"{viewport}_{kind}.png"
                dest = self.root / dest_rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
                copied[kind] = dest_rel.as_posix()
            if copied:
                persistent[viewport] = copied
        report["screenshots"] = persistent

    def save(self, report: dict[str, Any]) -> dict[str, Any]:
        """Persist a snapshot, creating a new ID even when the source has a demo ID."""
        _validate_report(report)
        # JSON round-trip prevents mutating live Streamlit state or caller references.
        copy = json.loads(_serialize(report))
        audit_id = uuid.uuid4().hex
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        copy["audit_id"] = audit_id
        copy["saved_at"] = timestamp
        report_folder = self.reports_dir / audit_id
        report_folder.mkdir(parents=True, exist_ok=False)
        try:
            self._copy_screenshots(copy, audit_id)
            raw = _serialize(copy)
            report_file = report_folder / "report.json"
            with tempfile.NamedTemporaryFile(dir=report_folder, prefix=".report-", suffix=".tmp", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = Path(tmp.name)
            try:
                os.replace(tmp_path, report_file)
            finally:
                tmp_path.unlink(missing_ok=True)
            score_data = ((copy.get("scores") or {}).get("internal") or {}).get("seo")
            score = score_data.get("score") if isinstance(score_data, dict) else None
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                score = None
            counts = ((copy.get("summary") or {}).get("counts") or {})
            issues = counts.get("failed", 0) if isinstance(counts, dict) else 0
            issues = int(issues) if isinstance(issues, int) and not isinstance(issues, bool) else 0
            with self._connect() as conn:
                conn.execute("""INSERT INTO audits
                    (id,created_at,requested_url,final_url,niche,objective,status,seo_score,
                     issue_count,has_screenshots,report_relpath)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (
                        audit_id, timestamp, copy["requested_url"], copy["final_url"],
                        copy["niche"], copy["objective"], copy["status"], score, issues,
                        int(bool(copy["screenshots"])),
                        f"data/local/history/{audit_id}/report.json",
                    ))
        except Exception:
            shutil.rmtree(report_folder, ignore_errors=True)
            shutil.rmtree(self.screenshot_dir / audit_id, ignore_errors=True)
            raise
        return {"audit_id": audit_id, "created_at": timestamp, "status": copy["status"],
                "has_screenshots": bool(copy["screenshots"])}

    def list(self, *, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        if not 1 <= limit <= 100 or offset < 0:
            raise ValueError("Invalid history pagination.")
        with self._connect() as conn:
            rows = conn.execute("""SELECT id,created_at,requested_url,niche,objective,status,
                                 seo_score,issue_count,has_screenshots FROM audits
                                 ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?""",
                                (limit, offset)).fetchall()
        return [dict(row) for row in rows]

    def load(self, audit_id: str) -> dict[str, Any]:
        audit_id = self._valid_id(audit_id)
        with self._connect() as conn:
            present = conn.execute("SELECT 1 FROM audits WHERE id=?", (audit_id,)).fetchone()
        if present is None:
            raise AuditNotFound("Audit was not found.")
        report_file = self.reports_dir / audit_id / "report.json"
        try:
            if report_file.stat().st_size > MAX_REPORT_BYTES:
                raise InvalidHistoryReport("Stored report exceeds size limit.")
            payload = json.loads(report_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InvalidHistoryReport("Stored report could not be read.") from exc
        _validate_report(payload)
        return payload

    def delete(self, audit_id: str) -> bool:
        """Delete a single local audit and its copied evidence, without touching other runs."""
        audit_id = self._valid_id(audit_id)
        with self._connect() as conn:
            result = conn.execute("DELETE FROM audits WHERE id=?", (audit_id,))
        if result.rowcount == 0:
            return False
        shutil.rmtree(self.reports_dir / audit_id, ignore_errors=True)
        shutil.rmtree(self.screenshot_dir / audit_id, ignore_errors=True)
        return True
