"""Busca HTML público sem execução de JavaScript."""
from dataclasses import dataclass
from urllib.parse import urljoin

import httpcore
import httpx

from pagecheck.acquisition.http.safe_transport import PublicHTTPTransport
from pagecheck.common.security.url_validation import validate_public_url

MAX_BODY_BYTES = 2_000_000
MAX_REDIRECTS = 3


class FetchError(RuntimeError):
    """A página não pôde ser obtida segundo as regras do Page Check."""


@dataclass(frozen=True)
class FetchedPage:
    original_url: str
    final_url: str
    status_code: int
    html: str
    redirects: tuple[str, ...]


def fetch_html(url: str, *, transport: httpx.BaseTransport | None = None) -> FetchedPage:
    """Faz GET com IP validado no connect; transporte injetável nos testes."""
    current = url
    redirects = []
    try:
        with httpx.Client(
            transport=transport if transport is not None else PublicHTTPTransport(),
            follow_redirects=False,
            timeout=httpx.Timeout(8.0),
            trust_env=False,
            headers={"User-Agent": "PageCheck/0.1 (landing page audit)"},
        ) as client:
            for hop in range(MAX_REDIRECTS + 1):
                current = validate_public_url(current)
                with client.stream("GET", current) as response:
                    if 300 <= response.status_code < 400:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("Resposta de redirecionamento sem Location.")
                        if hop >= MAX_REDIRECTS:
                            raise FetchError("Limite de redirecionamentos excedido.")
                        current = urljoin(str(response.url), location)
                        redirects.append(current)
                        continue
                    response.raise_for_status()
                    mime_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if mime_type not in ("text/html", "application/xhtml+xml"):
                        raise FetchError("O destino não retornou uma página HTML.")
                    length = response.headers.get("content-length")
                    if length and length.isdecimal() and int(length) > MAX_BODY_BYTES:
                        raise FetchError("Página maior que o limite permitido.")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BODY_BYTES:
                            raise FetchError("Página maior que o limite permitido.")
                    html = body.decode(response.encoding or "utf-8", errors="replace")
                    return FetchedPage(url, str(response.url), response.status_code, html, tuple(redirects))
    except (httpx.HTTPError, httpcore.NetworkError, httpcore.TimeoutException, httpcore.ProtocolError) as exc:
        raise FetchError(f"Falha ao consultar a página: {type(exc).__name__}") from exc
    raise FetchError("A consulta não pôde ser concluída.")
