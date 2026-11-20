"""Private audit endpoint with guarded production admission and optional visuals."""
from __future__ import annotations

import ipaddress
import os

from fastapi import APIRouter, HTTPException, Request

from pagecheck.acquisition.http.fetcher import FetchError
from pagecheck.acquisition.http.safe_transport import UnsafeDestination
from pagecheck.api.schemas.audit import PageAuditRequest
from pagecheck.application.use_cases.audit_page_html import audit_page_html
from pagecheck.application.use_cases.collect_public_visuals import collect_public_visuals
from pagecheck.application.use_cases.collect_static_engines import collect_static_engines
from pagecheck.application.use_cases.crawl_public_site import crawl_public_site
from pagecheck.common.security.admission import AuditAdmissionError, production_audit_admission
from pagecheck.common.security.deployment import (
    is_local_development,
    live_browser_enabled,
    live_fetch_enabled,
)
from pagecheck.common.security.isolated_audit import (
    AuditIsolationUnavailable,
    run_isolated_audit,
    verify_worker_python_exec,
)
from pagecheck.common.security.private_api import require_private_service
from pagecheck.common.security.url_validation import URLValidationError, validate_public_url

router = APIRouter(prefix="/v1/audits", tags=["audit"])


def _execute_audit(payload: PageAuditRequest, request: Request) -> dict:
    # Private service authorization is mandatory in production even though the
    # API is also on Render's private network. Never reveal the key to browsers.
    if not is_local_development():
        require_private_service(request)
    url = validate_public_url(payload.url)
    kwargs = {"niche": payload.niche, "objective": payload.objective,
              "crawler": crawl_public_site}
    if payload.language != "en" or payload.keywords:
        kwargs.update(language=payload.language, keywords=payload.keywords)
    wants_browser = live_browser_enabled()
    wants_engines = (is_local_development() and
                     os.getenv("PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES") == "1")
    if wants_browser or wants_engines:
        if is_local_development():
            # Preserve the local-only opt-in of previous stages.
            try:
                is_local = ipaddress.ip_address(request.client.host).is_loopback
            except (ValueError, AttributeError):
                is_local = False
            if not is_local:
                raise HTTPException(403, "Visual browser mode is restricted to local requests.")
        if wants_browser:
            kwargs["visual_collector"] = collect_public_visuals
        if wants_engines:
            kwargs["external_collector"] = collect_static_engines
    return audit_page_html(url, **kwargs)


@router.post("/page")
def audit_page(payload: PageAuditRequest, request: Request) -> dict:
    if not live_fetch_enabled():
        raise HTTPException(503, "Live URL auditing is disabled by deployment policy.")
    if not is_local_development():
        require_private_service(request)  # Reject unauthorized callers before consuming a quota slot.
    try:
        if is_local_development():
            return _execute_audit(payload, request)
        # A single Uvicorn worker is required by the Stage33 deployment policy.
        with production_audit_admission.enter():
            if os.environ.get("PAGECHECK_AUDIT_WORKER_ISOLATED") == "1":
                validate_public_url(payload.url)
                return run_isolated_audit(payload)
            return _execute_audit(payload, request)
    except AuditIsolationUnavailable as exc:
        raise HTTPException(503, "Isolated public auditor is not available.") from exc
    except AuditAdmissionError as exc:
        raise HTTPException(429, str(exc), headers={"Retry-After": "60"}) from exc
    except (UnsafeDestination, URLValidationError) as exc:
        raise HTTPException(403, "This network destination is not permitted.") from exc
    except FetchError as exc:
        raise HTTPException(502, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/isolation-check")
def check_worker_isolation(request: Request) -> dict:
    """Authenticated hosted check: verify seccomp in both C and execve'd Python."""
    if is_local_development():
        raise HTTPException(404, "Production-only validation")
    require_private_service(request)
    launcher = os.environ.get("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", "")
    try:
        verify_worker_python_exec(launcher)
    except AuditIsolationUnavailable as exc:
        raise HTTPException(503, "Kernel worker isolation verification failed") from exc
    return {
        "status": "ok",
        "worker_ipv4_blocked": True,
        "worker_ipv6_blocked": True,
        "broker_required": True,
        "container_wide_egress_firewall": False,
    }
