"""Endpoint interno de inspeção; não é ainda a auditoria completa."""

from fastapi import APIRouter, HTTPException

from pagecheck.common.security.deployment import is_local_development, live_fetch_enabled

from pagecheck.acquisition.http.fetcher import FetchError
from pagecheck.acquisition.http.safe_transport import UnsafeDestination
from pagecheck.api.schemas.pages import PageInspectionRequest, PageInspectionResponse
from pagecheck.application.use_cases.inspect_page import inspect_page
from pagecheck.common.security.url_validation import URLValidationError, validate_public_url

router = APIRouter(prefix="/v1/pages", tags=["pages"])


@router.post("/inspect", response_model=PageInspectionResponse)
def inspect_public_page(payload: PageInspectionRequest) -> dict:
    """Inspeção síncrona local de HTML sem avaliação de SEO/UX."""
    # Legacy inspection endpoint: never expose it on an internet-facing API.
    # Production audits must use the authenticated, rate-limited /v1/audits/page.
    if not is_local_development():
        raise HTTPException(503, "This legacy inspection endpoint is local-only.")
    if not live_fetch_enabled():
        raise HTTPException(
            status_code=503,
            detail="Consulta remota desabilitada; habilite apenas no desenvolvimento local.",
        )

    try:
        validated = validate_public_url(payload.url)
    except URLValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        return inspect_page(validated)
    except (UnsafeDestination, URLValidationError) as exc:
        raise HTTPException(status_code=403, detail="Destino de rede não permitido.") from exc
    except FetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
