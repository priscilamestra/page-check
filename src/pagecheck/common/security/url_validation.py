
"""Filtro inicial de URLs para auditorias públicas, sem fazer requisições."""

import ipaddress
import re
from urllib.parse import urlsplit


class URLValidationError(ValueError):
    """Indica uma URL que não atende às regras de entrada."""


def validate_public_url(raw_url: str) -> str:
    """Valida a entrada antes de qualquer tentativa de conexão."""
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise URLValidationError("Informe uma URL.")

    url = raw_url.strip()

    if "\\" in url or any(ch.isspace() or ord(ch) < 32 for ch in url):
        raise URLValidationError("A URL contém caracteres inválidos.")

    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise URLValidationError("A URL está malformada.") from exc

    if parts.scheme.lower() not in {"http", "https"}:
        raise URLValidationError("Use somente HTTP ou HTTPS.")

    if not hostname:
        raise URLValidationError("Informe um domínio válido.")

    if parts.username is not None or parts.password is not None:
        raise URLValidationError("URLs com credenciais não são permitidas.")

    if port not in (None, 80, 443):
        raise URLValidationError("A auditoria aceita somente as portas 80 e 443.")

    hostname = hostname.rstrip(".").lower()

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise URLValidationError(
            "Informe um domínio público, não um endereço IP."
        )

    if hostname == "localhost" or hostname.endswith(
        (".localhost", ".local", ".internal", ".test", ".invalid", ".onion")
    ):
        raise URLValidationError("Domínio local ou reservado não permitido.")

    try:
        ascii_host = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise URLValidationError("Domínio inválido.") from exc

    labels = ascii_host.split(".")

    if (
        len(labels) < 2
        or len(ascii_host) > 253
        or not all(
            1 <= len(label) <= 63
            and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
            for label in labels
        )
        or labels[-1].isdigit()
    ):
        raise URLValidationError("Informe um domínio público válido.")

    return url
