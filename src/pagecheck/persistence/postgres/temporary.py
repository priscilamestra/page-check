"""Opt-in PostgreSQL repository for a single recoverable audit per browser.

No public HTTP routes are registered here. The bearer recovery token is returned
once to the trusted caller; PostgreSQL only receives its SHA-256 digest.
The runtime/HTTP security checks are intentionally left to the deployment stage.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, ContextManager

from pagecheck.persistence.sqlite.history import InvalidHistoryReport, _serialize, _validate_report

RETENTION = timedelta(hours=24)
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGES_TOTAL = 4 * 1024 * 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
VIEWPORTS = ("desktop", "mobile")
IMAGE_KINDS = ("initial", "after_scroll", "annotated")
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")


class TemporaryAuditNotFound(LookupError):
    """An audit is absent, expired or the recovery token is invalid."""


class TemporaryAuditTooLarge(ValueError):
    """The visual evidence exceeds the bounded temporary storage allowance."""


def new_recovery_token() -> str:
    """Generate 256 unpredictable bits, encoded as a URL-safe opaque token."""
    return secrets.token_urlsafe(32)


def decode_recovery_token(token: object) -> bytes:
    """Reject malformed and noncanonical tokens before querying the database."""
    if not isinstance(token, str) or not TOKEN_PATTERN.fullmatch(token):
        raise TemporaryAuditNotFound("Audit not found or expired.")
    try:
        raw = base64.urlsafe_b64decode(token + "=")
    except (ValueError, base64.binascii.Error) as exc:
        raise TemporaryAuditNotFound("Audit not found or expired.") from exc
    if len(raw) != 32 or base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != token:
        raise TemporaryAuditNotFound("Audit not found or expired.")
    return raw


def _digest(token: str) -> bytes:
    return hashlib.sha256(decode_recovery_token(token)).digest()


def _connect_from_env():
    """Import psycopg lazily: existing SQLite tests do not require a live DB."""
    url = os.environ.get("PAGECHECK_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("PAGECHECK_DATABASE_URL is not configured for PostgreSQL.")
    if not (url.startswith("postgresql://") or url.startswith("postgres://")):
        raise RuntimeError("PAGECHECK_DATABASE_URL must be a PostgreSQL connection URL.")
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("Install the PostgreSQL driver: uv sync (psycopg[binary]).") from exc
    return psycopg.connect(url, connect_timeout=5)


def _allowed_png(path_value: object, root: Path) -> bytes | None:
    """Accept only bounded PNG evidence produced within the application's artifacts/."""
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        candidate = candidate.resolve(strict=True)
        if not candidate.is_relative_to((root / "artifacts").resolve()):
            return None
        if candidate.suffix.lower() != ".png" or not candidate.is_file():
            return None
        size = candidate.stat().st_size
        if size <= 0:
            return None
        if size > MAX_IMAGE_BYTES:
            raise TemporaryAuditTooLarge("A PNG screenshot exceeds the 2 MB limit.")
        raw = candidate.read_bytes()
    except (OSError, RuntimeError):
        return None
    if not raw.startswith(PNG_SIGNATURE):
        return None
    return raw


def _copy_for_storage(report: dict[str, Any], root: Path) -> tuple[dict[str, Any], list[tuple[str, str, bytes]]]:
    """Copy the input; never persist the scanner's local screenshot paths."""
    _validate_report(report)
    copy: dict[str, Any] = json.loads(_serialize(report))
    originals = copy.get("screenshots") or {}
    if not isinstance(originals, dict):
        originals = {}
    stored: dict[str, dict[str, str]] = {}
    image_rows: list[tuple[str, str, bytes]] = []
    total = 0
    for viewport in VIEWPORTS:
        kinds = originals.get(viewport)
        if not isinstance(kinds, dict):
            continue
        for kind in IMAGE_KINDS:
            png = _allowed_png(kinds.get(kind), root)
            if png is None:
                continue
            total += len(png)
            if total > MAX_IMAGES_TOTAL:
                raise TemporaryAuditTooLarge("Screenshots exceed the 4 MB total limit per audit.")
            stored.setdefault(viewport, {})[kind] = f"temporary-image://{viewport}/{kind}"
            image_rows.append((viewport, kind, png))
    copy["screenshots"] = stored
    copy["temporary_storage"] = {
        "recoverable_for_hours": 24,
        "stored_screenshot_count": len(image_rows),
        "image_content_not_in_report_json": True,
    }
    _serialize(copy)
    return copy, image_rows


class TemporaryAuditStore:
    """PostgreSQL JSONB + BYTEA evidence, with no permanent audit history API.

    The caller must already have run the migration. A private server process
    should construct this class, never browser code. An optional connector is
    accepted for tests; the default uses PAGECHECK_DATABASE_URL.
    """

    def __init__(self, project_root: Path, *, connect: Callable[[], ContextManager[Any]] | None = None):
        self.root = Path(project_root).resolve()
        self._connect = connect or _connect_from_env

    def save(self, report: dict[str, Any], *, previous_token: str | None = None) -> dict[str, Any]:
        prepared, images = _copy_for_storage(report, self.root)
        # Validate before executing any write; old audit is deleted only after insert succeeds.
        previous_digest = _digest(previous_token) if previous_token is not None else None
        token = new_recovery_token()
        token_digest = _digest(token)
        expiry = datetime.now(timezone.utc) + RETENTION
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO pagecheck_temporary_audits "
                    "(token_digest, expires_at, report) VALUES (%s, %s, %s::jsonb)",
                    (token_digest, expiry, json.dumps(prepared, ensure_ascii=False)),
                )
                for viewport, kind, png in images:
                    cur.execute(
                        "INSERT INTO pagecheck_temporary_screenshots "
                        "(token_digest, viewport, kind, png) VALUES (%s, %s, %s, %s)",
                        (token_digest, viewport, kind, png),
                    )
                if previous_digest is not None:
                    cur.execute(
                        "DELETE FROM pagecheck_temporary_audits WHERE token_digest = %s",
                        (previous_digest,),
                    )
                # Clean expired rows on use, in addition to a scheduled cleanup job.
                cur.execute("DELETE FROM pagecheck_temporary_audits WHERE expires_at <= now()")
        return {
            "recovery_token": token,
            "expires_at": expiry.isoformat(timespec="seconds"),
            "stored_screenshots": len(images),
        }

    def load(self, token: str) -> dict[str, Any]:
        digest = _digest(token)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT report FROM pagecheck_temporary_audits "
                    "WHERE token_digest = %s AND expires_at > now()",
                    (digest,),
                )
                row = cur.fetchone()
        if row is None:
            raise TemporaryAuditNotFound("Audit not found or expired.")
        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload)
        _validate_report(payload)
        return payload

    def load_image(self, token: str, viewport: str, kind: str) -> bytes:
        if viewport not in VIEWPORTS or kind not in IMAGE_KINDS:
            raise TemporaryAuditNotFound("Screenshot not found or expired.")
        digest = _digest(token)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT s.png FROM pagecheck_temporary_screenshots AS s "
                    "JOIN pagecheck_temporary_audits AS a USING (token_digest) "
                    "WHERE s.token_digest = %s AND a.expires_at > now() "
                    "AND s.viewport = %s AND s.kind = %s",
                    (digest, viewport, kind),
                )
                row = cur.fetchone()
        if row is None:
            raise TemporaryAuditNotFound("Screenshot not found or expired.")
        return bytes(row[0])

    def delete(self, token: str) -> bool:
        digest = _digest(token)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pagecheck_temporary_audits WHERE token_digest = %s", (digest,))
                deleted = cur.rowcount
        return deleted > 0

    def purge_expired(self) -> int:
        """Run periodically in production; request-triggered cleanup alone is insufficient."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pagecheck_temporary_audits WHERE expires_at <= now()")
                count = cur.rowcount
        return count
