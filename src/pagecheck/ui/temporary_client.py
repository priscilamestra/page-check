"""Trusted Streamlit-to-FastAPI transport for 24h PostgreSQL recovery.

The bearer token never enters a URL or JSON report and is not logged. The
browser stores only one token in its origin-scoped localStorage bridge.
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any

import httpx

from pagecheck.persistence.postgres.temporary import (
    IMAGE_KINDS, MAX_IMAGE_BYTES, PNG_SIGNATURE, VIEWPORTS, decode_recovery_token,
)

CACHE_RELATIVE = Path("artifacts") / "temporary_restore"


class TemporaryRecoveryUnavailable(RuntimeError):
    pass


def _headers() -> dict[str, str]:
    key = os.environ.get("PAGECHECK_PRIVATE_API_KEY", "")
    return {"X-PageCheck-Service-Key": key} if key else {}


def _request(api_url: str, operation: str, payload: dict[str, Any], *, timeout: float = 15) -> httpx.Response:
    try:
        result = httpx.post(f"{api_url.rstrip('/')}/v1/temporary/{operation}",
                            json=payload, headers=_headers(), timeout=timeout)
        result.raise_for_status()
        return result
    except httpx.HTTPError as exc:
        # Never echo response body or URL, which might contain private info.
        raise TemporaryRecoveryUnavailable("Temporary report storage is unavailable.") from exc


def save_temporary(api_url: str, report: dict[str, Any], previous_token: str | None = None) -> str:
    payload = {"report": report, "previous_token": previous_token}
    try:
        response = _request(api_url, "save", payload, timeout=30).json()
        token = response["recovery_token"]
        decode_recovery_token(token)
        return token
    except (KeyError, ValueError, TypeError) as exc:
        raise TemporaryRecoveryUnavailable("Temporary report storage returned an invalid response.") from exc


def revoke_temporary(api_url: str, token: str) -> None:
    decode_recovery_token(token)
    _request(api_url, "revoke", {"token": token})


def restore_temporary(api_url: str, token: str, root: Path) -> dict[str, Any]:
    """Restore JSON + scoped PNG files into Streamlit's own artifacts tree.

    Render's API and Streamlit containers may have entirely separate disks.
    The PNGs are streamed from PostgreSQL and restored under Streamlit's disk
    only for the duration of that server process. The DB remains authoritative.
    """
    decode_recovery_token(token)
    raw = _request(api_url, "restore", {"token": token}).json()
    if not isinstance(raw, dict):
        raise TemporaryRecoveryUnavailable("Temporary report is malformed.")
    # Deep-copy screenshot paths via the storage-provided placeholders, not
    # paths supplied by a user or left over from a different server.
    shots = raw.get("screenshots")
    if not isinstance(shots, dict):
        shots = {}
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()[:32]
    root = Path(root).resolve()
    base = root / CACHE_RELATIVE / digest
    bounded: dict[str, dict[str, str]] = {}
    for viewport in VIEWPORTS:
        item = shots.get(viewport)
        if not isinstance(item, dict):
            continue
        for kind in IMAGE_KINDS:
            if item.get(kind) != f"temporary-image://{viewport}/{kind}":
                continue
            try:
                response = _request(api_url, "image", {
                    "token": token, "viewport": viewport, "kind": kind,
                })
            except TemporaryRecoveryUnavailable:
                continue
            png = response.content
            if not png.startswith(PNG_SIGNATURE) or not 0 < len(png) <= MAX_IMAGE_BYTES:
                continue
            path = base / viewport / f"{kind}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(png)
            bounded.setdefault(viewport, {})[kind] = str(path)
    raw["screenshots"] = bounded
    cleanup_stale_screenshots(root)
    return raw


def cleanup_stale_screenshots(root: Path, *, now: float | None = None, max_remove: int = 8) -> int:
    """Bounded best-effort removal of local PNG cache after 24 hours.

    This is NOT the authoritative PostgreSQL expiration job. A restarted
    container naturally loses the local screenshots and they can be restored.
    """
    import shutil
    cache = Path(root).resolve() / CACHE_RELATIVE
    if not cache.exists() or cache.is_symlink():
        return 0
    current = time.time() if now is None else now
    count = 0
    for folder in cache.iterdir():
        if count >= max_remove:
            break
        if not folder.is_dir() or folder.is_symlink():
            continue
        try:
            last = max((p.stat().st_mtime for p in folder.rglob("*.png")), default=folder.stat().st_mtime)
            if current - last > 24 * 3600:
                shutil.rmtree(folder)
                count += 1
        except OSError:
            continue
    return count
