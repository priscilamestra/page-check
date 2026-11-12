"""Auditoria HTML combinada. Execução remota somente em ambiente local opt-in."""
import os
from fastapi import APIRouter, HTTPException

from pagecheck.acquisition.http.fetcher import FetchError
from pagecheck.acquisition.http.safe_transport import UnsafeDestination
from pagecheck.api.schemas.audit import PageAuditRequest
from pagecheck.application.use_cases.audit_page_html import audit_page_html
from pagecheck.common.security.url_validation import URLValidationError, validate_public_url

router = APIRouter(prefix="/v1/audits", tags=["audit"])

@router.post("/page")
def audit_page(payload: PageAuditRequest) -> dict:
    if os.getenv("PAGECHECK_ALLOW_LIVE_FETCH") != "1":
        raise HTTPException(503, "Live URL fetching is disabled. Enable it only for local development.")
    try:
        url = validate_public_url(payload.url)
        kwargs = {"niche": payload.niche, "objective": payload.objective}
        # Preserve the original call shape for legacy consumers and patched tests.
        if payload.language != "en" or payload.keywords:
            kwargs.update(language=payload.language, keywords=payload.keywords)
        return audit_page_html(url, **kwargs)
    except (UnsafeDestination, URLValidationError) as exc:
        raise HTTPException(403, "This network destination is not permitted.") from exc
    except FetchError as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
