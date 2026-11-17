"""Aquisição visual em navegador com rede HTTP(S) intermediada por Python.

Etapa 11: modo conservador sem JavaScript para capturar HTML/CSS/imagens
públicas. Não expor como serviço público de navegação arbitrária: proteção
adicional no nível do sistema operacional (sandbox de rede) ainda é necessária.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from pathlib import Path
from urllib.parse import urljoin

import httpx
from playwright.sync_api import Browser, Route

from pagecheck.acquisition.http.safe_transport import PublicHTTPTransport
from pagecheck.common.security.url_validation import validate_public_url
from pagecheck.acquisition.browser.visual_probe import inspect_rendered_page

MAX_RESOURCE_BYTES = 2_000_000
MAX_TOTAL_BYTES = 12_000_000
MAX_REQUESTS = 60
MAX_REDIRECTS = 3
_ALLOWED_TYPES = {"document", "stylesheet", "image", "font"}
_ALLOWED_MIMES = (
    "text/html", "application/xhtml+xml", "text/css", "image/",
    "font/", "application/font-woff", "application/octet-stream",
)


class BrowserFetchBlocked(RuntimeError):
    """Recurso não carregado pela política da auditoria."""


@dataclass(frozen=True)
class ResourceResponse:
    url: str
    status_code: int
    content_type: str
    content: bytes


def fetch_public_resource(
    url: str, *, transport: httpx.BaseTransport | None = None,
    max_bytes: int = MAX_RESOURCE_BYTES,
) -> ResourceResponse:
    """Busca um único recurso via transporte com conexão TCP fixada em IP público.

    Não utiliza proxy do ambiente nem permite redirecionamento automático.
    Um transporte injetado é destinado SOMENTE aos testes offline.
    """
    if not (1 <= max_bytes <= MAX_RESOURCE_BYTES):
        raise ValueError("Limite de bytes inválido.")
    current = validate_public_url(url)
    try:
        with httpx.Client(
            transport=transport if transport is not None else PublicHTTPTransport(),
            trust_env=False,
            follow_redirects=False,
            timeout=httpx.Timeout(6.0),
            headers={"User-Agent": "PageCheck/0.1 (local visual audit)"},
        ) as client:
            for hop in range(MAX_REDIRECTS + 1):
                current = validate_public_url(current)
                with client.stream("GET", current) as response:
                    if 300 <= response.status_code < 400:
                        location = response.headers.get("location")
                        if not location or hop >= MAX_REDIRECTS:
                            raise BrowserFetchBlocked("Redirecionamento inválido ou excessivo.")
                        current = validate_public_url(urljoin(str(response.url), location))
                        continue
                    if response.status_code != 200:
                        raise BrowserFetchBlocked(f"Recurso respondeu HTTP {response.status_code}.")
                    mime = response.headers.get("content-type", "").split(";")[0].lower().strip()
                    if not any(mime == allowed or (allowed.endswith("/") and mime.startswith(allowed))
                               for allowed in _ALLOWED_MIMES):
                        raise BrowserFetchBlocked("Tipo de conteúdo não permitido.")
                    length = response.headers.get("content-length", "")
                    if length.isdecimal() and int(length) > max_bytes:
                        raise BrowserFetchBlocked("Recurso ultrapassa o limite permitido.")
                    body = bytearray()
                    for piece in response.iter_bytes():
                        body.extend(piece)
                        if len(body) > max_bytes:
                            raise BrowserFetchBlocked("Recurso ultrapassa o limite permitido.")
                    return ResourceResponse(str(response.url), response.status_code, mime, bytes(body))
    except (httpx.HTTPError, ValueError) as exc:
        raise BrowserFetchBlocked(f"Falha na consulta segura: {type(exc).__name__}") from exc
    raise BrowserFetchBlocked("Não foi possível buscar o recurso.")


@dataclass
class NavigationReport:
    """Observações de rede; recursos bloqueados não equivalem a imagens quebradas."""
    requested: int = 0
    delivered: int = 0
    total_bytes: int = 0
    blocked: list[dict[str, str]] = field(default_factory=list)


def install_guarded_routes(
    context,
    *,
    fetch_resource=fetch_public_resource,
    max_requests: int = MAX_REQUESTS,
    max_total_bytes: int = MAX_TOTAL_BYTES,
    max_elapsed_seconds: int = 65,
) -> NavigationReport:
    """Intercepta HTTP(S) e entrega somente conteúdo vindo do fetcher fixado.

    Deve ser invocado ANTES de criar qualquer página. Nunca usa route.continue_().
    """
    if not 1 <= max_requests <= MAX_REQUESTS:
        raise ValueError("Limite de requisições inválido.")
    if not 1 <= max_total_bytes <= MAX_TOTAL_BYTES:
        raise ValueError("Limite de tráfego inválido.")
    if not 5 <= max_elapsed_seconds <= 120:
        raise ValueError("Tempo limite inválido.")
    report = NavigationReport()
    started = monotonic()

    def handle(route: Route) -> None:
        request = route.request
        report.requested += 1
        try:
            if monotonic() - started > max_elapsed_seconds:
                raise BrowserFetchBlocked("Limite de duração do navegador excedido.")
            if request.method != "GET":
                raise BrowserFetchBlocked("Somente GET é permitido.")
            if request.resource_type not in _ALLOWED_TYPES:
                raise BrowserFetchBlocked("Tipo de requisição não permitido.")
            if report.requested > max_requests:
                raise BrowserFetchBlocked("Limite de requisições excedido.")
            validate_public_url(request.url)
            available = max_total_bytes - report.total_bytes
            if available < 1:
                raise BrowserFetchBlocked("Limite de tráfego excedido.")
            result = fetch_resource(request.url, max_bytes=min(MAX_RESOURCE_BYTES, available))
            report.delivered += 1
            report.total_bytes += len(result.content)
            route.fulfill(
                status=result.status_code,
                body=result.content,
                headers={"content-type": result.content_type, "cache-control": "no-store"},
            )
        except (BrowserFetchBlocked, ValueError) as exc:
            report.blocked.append({"url": request.url, "reason": str(exc)})
            route.abort("blockedbyclient")

    context.route("**/*", handle)
    # WebSocket não deve abrir conexão direta; fechar antes de qualquer handshake.
    context.route_web_socket("**/*", lambda ws: ws.close())
    return report


def inspect_public_page(
    browser: Browser,
    *,
    url: str,
    output_dir: Path | str,
    width: int = 1280,
    height: int = 720,
    fetch_resource=fetch_public_resource,
) -> dict:
    """Navega sem JavaScript; coleta evidências no modo conservador local.

    Não testa funcionalidades dependentes de JS nesta etapa. Uso com URLs de
    terceiros fica restrito ao ambiente local; não implantar em serviço público.
    """
    validate_public_url(url)
    if width < 320 or width > 1920 or height < 240 or height > 1080:
        raise ValueError("Viewport fora dos limites.")
    context = browser.new_context(
        viewport={"width": width, "height": height},
        java_script_enabled=False,
        service_workers="block",
        accept_downloads=False,
        permissions=[],
    )
    try:
        network = install_guarded_routes(context, fetch_resource=fetch_resource)
        page = context.new_page()
        navigation_status = "not_verified"
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=12000)
            if response:
                navigation_status = "loaded" if response.ok else "failed"
        except Exception:
            navigation_status = "failed"
        if navigation_status != "loaded":
            return {"navigation_status": navigation_status, "network": vars(network)}
        # Evita capturas gigantes capazes de esgotar a memória do processo.
        page_height = int(page.evaluate(
            "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
        ))
        if page_height > 8000:
            return {
                "navigation_status": "not_verified",
                "reason": "Página acima do limite de 8.000 px para captura.",
                "network": vars(network),
            }
        visual = inspect_rendered_page(
            page, screenshot_dir=Path(output_dir), step_px=450,
            max_scroll_steps=30, settle_ms=100,
        )
        # Recurso abortado pela política não é falha comprovada da landing page.
        blocked_urls = {item["url"] for item in network.blocked}
        for image in visual["images"]:
            if image["src"] in blocked_urls:
                image["status"] = "not_verified"
                image["loaded_after_scroll"] = False
        visual["broken_image_count"] = sum(
            image["status"] == "broken" for image in visual["images"]
        )
        visual["not_verified_image_count"] = sum(
            image["status"] == "not_verified" for image in visual["images"]
        )
        return {
            "navigation_status": navigation_status,
            "requested_url": url,
            "final_url": page.url,
            "javascript_disabled": True,
            "network": vars(network),
            "visual": visual,
        }
    finally:
        context.close()
