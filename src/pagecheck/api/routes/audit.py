"""Auditoria HTML combinada. Execução remota somente em ambiente local opt-in."""
import os
import ipaddress
from fastapi import APIRouter, HTTPException, Request

from pagecheck.acquisition.http.fetcher import FetchError
from pagecheck.acquisition.http.safe_transport import UnsafeDestination
from pagecheck.api.schemas.audit import PageAuditRequest
from pagecheck.application.use_cases.audit_page_html import audit_page_html
from pagecheck.application.use_cases.collect_public_visuals import collect_public_visuals
from pagecheck.common.security.url_validation import URLValidationError, validate_public_url

router = APIRouter(prefix="/v1/audits", tags=["audit"])

@router.post("/page")
def audit_page(payload: PageAuditRequest, request: Request) -> dict:
    if os.getenv("PAGECHECK_ALLOW_LIVE_FETCH") != "1":
        raise HTTPException(503, "Live URL fetching is disabled. Enable it only for local development.")
    try:
        url = validate_public_url(payload.url)
        kwargs = {"niche": payload.niche, "objective": payload.objective}
        # Preserve the original call shape for legacy consumers and patched tests.
        if payload.language != "en" or payload.keywords:
            kwargs.update(language=payload.language, keywords=payload.keywords)
        if os.getenv("PAGECHECK_ALLOW_LIVE_BROWSER") == "1":
            # An explicit local-only opt-in is required for experimental browser
            # capture. Remote callers cannot activate the Chromium runtime.
            try:
                is_local = ipaddress.ip_address(request.client.host).is_loopback
            except (ValueError, AttributeError):
                is_local = False
            if not is_local:
                raise HTTPException(403, "Visual browser mode is restricted to local requests.")
            kwargs["visual_collector"] = collect_public_visuals
        return audit_page_html(url, **kwargs)
    except (UnsafeDestination, URLValidationError) as exc:
        raise HTTPException(403, "This network destination is not permitted.") from exc
    except FetchError as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
