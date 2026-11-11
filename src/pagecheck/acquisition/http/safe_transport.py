"""Transporte HTTPX com resolução de DNS validada na conexão TCP.

Mantém hostname da URL para Host, SNI e validação de certificado TLS.
"""

import socket
from collections.abc import Iterable, Iterator

from pagecheck.common.security.dns_validation import validate_resolved_ips

import httpcore
import httpx


class UnsafeDestination(ValueError):
    """Destino bloqueado pela política de rede."""


class PublicNetworkBackend(httpcore.NetworkBackend):
    def __init__(self) -> None:
        self._backend = httpcore.SyncBackend()

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[tuple] | None = None,
    ) -> httpcore.NetworkStream:
        if port not in (80, 443):
            raise UnsafeDestination("Porta não permitida.")
        try:
            records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise UnsafeDestination("Falha ao resolver o endereço do domínio.") from exc
        if not records:
            raise UnsafeDestination("O domínio não retornou nenhum endereço IP.")
        approved_ips = validate_resolved_ips([record[4][0] for record in records])
        # Conexão usa endereço NUMÉRICO validado, sem resolver o domínio novamente.
        return self._backend.connect_tcp(
            approved_ips[0], port, timeout=timeout,
            local_address=local_address, socket_options=socket_options,
        )

    def connect_unix_socket(self, *args, **kwargs) -> httpcore.NetworkStream:
        raise UnsafeDestination("Unix sockets não são permitidos.")

    def sleep(self, seconds: float) -> None:
        self._backend.sleep(seconds)


class _ResponseStream(httpx.SyncByteStream):
    def __init__(self, source: Iterable[bytes]) -> None:
        self.source = source

    def __iter__(self) -> Iterator[bytes]:
        yield from self.source

    def close(self) -> None:
        close = getattr(self.source, "close", None)
        if close:
            close()


class PublicHTTPTransport(httpx.BaseTransport):
    """Transporte direto, sem proxy, limitado a conexões TCP públicas."""

    def __init__(self) -> None:
        self.pool = httpcore.ConnectionPool(
            network_backend=PublicNetworkBackend(),
            http1=True, http2=False, retries=0,
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        result = self.pool.handle_request(core_request)
        return httpx.Response(
            status_code=result.status,
            headers=result.headers,
            stream=_ResponseStream(result.stream),
            extensions=result.extensions,
        )

    def close(self) -> None:
        self.pool.close()
