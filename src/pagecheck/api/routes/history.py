"""Local-only history API (no account login or public multi-user access)."""
from __future__ import annotations

import ipaddress
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from pagecheck.common.security.deployment import is_local_development

from pagecheck.persistence.sqlite.history import (
    AuditHistory, AuditNotFound, InvalidHistoryReport,
)
from pagecheck.reporting.exports import findings_csv, json_export, zip_export

router = APIRouter(prefix="/v1/history", tags=["history"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _local_only(request: Request) -> None:
    """Prevent exposing unprotected local reports on a public interface."""
    if not is_local_development():
        raise HTTPException(503, "Local history is disabled outside development.")
    try:
        if request.client is not None and ipaddress.ip_address(request.client.host).is_loopback:
            return
    except ValueError:
        pass
    raise HTTPException(403, "Audit history is available only from this computer.")


def _store() -> AuditHistory:
    root = Path(os.environ.get("PAGECHECK_HISTORY_ROOT") or PROJECT_ROOT)
    return AuditHistory(root)


@router.post("", dependencies=[Depends(_local_only)], status_code=201)
def save_history(report: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return _store().save(report)
    except InvalidHistoryReport as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("", dependencies=[Depends(_local_only)])
def list_history(limit: int = Query(20, ge=1, le=100),
                 offset: int = Query(0, ge=0)) -> dict[str, Any]:
    return {"items": _store().list(limit=limit, offset=offset)}


@router.get("/{audit_id}", dependencies=[Depends(_local_only)])
def get_history(audit_id: str) -> dict[str, Any]:
    try:
        return _store().load(audit_id)
    except AuditNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidHistoryReport as exc:
        raise HTTPException(500, "Saved audit is invalid or unavailable.") from exc


@router.get("/{audit_id}/export", dependencies=[Depends(_local_only)])
def export_history(audit_id: str, format: Literal["json", "csv", "html_zip"] = "html_zip") -> Response:
    store = _store()
    try:
        report = store.load(audit_id)
    except AuditNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except InvalidHistoryReport as exc:
        raise HTTPException(500, "Saved audit is invalid or unavailable.") from exc
    if format == "json":
        payload, mime, extension = json_export(report), "application/json", "json"
    elif format == "csv":
        payload, mime, extension = findings_csv(report), "text/csv; charset=utf-8", "csv"
    else:
        payload, mime, extension = zip_export(report, store.root), "application/zip", "zip"
    return Response(payload, media_type=mime, headers={
        "Content-Disposition": f'attachment; filename="pagecheck_{audit_id}.{extension}"'
    })


@router.delete("/{audit_id}", dependencies=[Depends(_local_only)], status_code=204)
def delete_history(audit_id: str) -> Response:
    try:
        deleted = _store().delete(audit_id)
    except AuditNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    if not deleted:
        raise HTTPException(404, "Audit was not found.")
    return Response(status_code=204)
