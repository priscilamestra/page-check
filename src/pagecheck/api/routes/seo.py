"""Rota SEO independente da prévia /v1/pages/inspect."""

from fastapi import APIRouter, HTTPException

from pagecheck.common.security.deployment import is_local_development, live_fetch_enabled

from pagecheck.acquisition.http.fetcher import FetchError
from pagecheck.acquisition.http.safe_transport import UnsafeDestination
from pagecheck.api.schemas.seo import SeoAuditRequest, SeoAuditResponse
from pagecheck.application.use_cases.audit_seo_page import audit_seo_page
from pagecheck.common.security.url_validation import URLValidationError, validate_public_url

router = APIRouter(prefix="/v1/audits/seo", tags=["seo"])


@router.post("", response_model=SeoAuditResponse)
def audit_public_page_seo(payload: SeoAuditRequest) -> dict:
    """Auditoria SEO local por regras determinísticas, sem LLM."""
    # Production audits must use the authenticated, rate-limited /v1/audits/page.
    # Do not allow this older endpoint to bypass production admission controls.
    if not is_local_development():
        raise HTTPException(503, "This legacy SEO endpoint is local-only.")
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
        return audit_seo_page(
            validated,
            niche=payload.niche,
            objective=payload.objective,
        )
    except (UnsafeDestination, URLValidationError) as exc:
        raise HTTPException(status_code=403, detail="Destino de rede não permitido.") from exc
    except FetchError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
