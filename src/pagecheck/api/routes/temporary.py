"""Private, token-protected 24h recovery; no history listing or public GET route.

All sensitive values are sent in POST JSON, never a URL/query parameter. The
Streamlit server calls these routes; ordinary browsers should not call them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from pagecheck.common.security.private_api import require_private_service
from pagecheck.persistence.postgres.temporary import (
    TemporaryAuditNotFound, TemporaryAuditStore, TemporaryAuditTooLarge,
)
from pagecheck.persistence.sqlite.history import InvalidHistoryReport

router = APIRouter(prefix="/v1/temporary", tags=["temporary"])
ROOT = Path(__file__).resolve().parents[4]
NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}
MAX_REQUEST_BYTES = 6 * 1024 * 1024


class SaveRequest(BaseModel):
    report: dict[str, Any]
    previous_token: str | None = Field(default=None, max_length=43)


class TokenRequest(BaseModel):
    token: str = Field(min_length=43, max_length=43)


class ImageRequest(TokenRequest):
    viewport: Literal["desktop", "mobile"]
    kind: Literal["initial", "after_scroll", "annotated"]


def _store() -> TemporaryAuditStore:
    return TemporaryAuditStore(ROOT)


def _guard_size(request: Request) -> None:
    size = request.headers.get("content-length")
    if size:
        try:
            if int(size) > MAX_REQUEST_BYTES:
                raise HTTPException(413, "Audit payload is too large.")
        except ValueError:
            raise HTTPException(400, "Invalid request length.") from None


@router.post("/save", status_code=201, dependencies=[Depends(require_private_service), Depends(_guard_size)])
def save_temporary(payload: SaveRequest) -> Response:
    try:
        result = _store().save(payload.report, previous_token=payload.previous_token)
    except (InvalidHistoryReport, TemporaryAuditTooLarge, ValueError) as exc:
        raise HTTPException(422, "Report could not be stored.") from exc
    except TemporaryAuditNotFound as exc:
        raise HTTPException(404, "Audit not found or expired.") from exc
    return Response(content=json.dumps(result), media_type="application/json", headers=NO_STORE, status_code=201)


@router.post("/restore", dependencies=[Depends(require_private_service)])
def restore_temporary(payload: TokenRequest) -> Response:
    try:
        report = _store().load(payload.token)
    except TemporaryAuditNotFound as exc:
        raise HTTPException(404, "Audit not found or expired.") from exc
    return Response(content=json.dumps(report, ensure_ascii=False),
                    media_type="application/json", headers=NO_STORE)


@router.post("/image", dependencies=[Depends(require_private_service)])
def image_temporary(payload: ImageRequest) -> Response:
    try:
        png = _store().load_image(payload.token, payload.viewport, payload.kind)
    except TemporaryAuditNotFound as exc:
        raise HTTPException(404, "Screenshot not found or expired.") from exc
    return Response(png, media_type="image/png", headers=NO_STORE)


@router.post("/revoke", status_code=204, dependencies=[Depends(require_private_service)])
def revoke_temporary(payload: TokenRequest) -> Response:
    try:
        _store().delete(payload.token)
    except TemporaryAuditNotFound:
        pass
    return Response(status_code=204, headers=NO_STORE)
