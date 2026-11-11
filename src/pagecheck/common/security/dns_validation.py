
"""Validação de endereços IP retornados pelo DNS."""

import ipaddress
import socket
from urllib.parse import urlsplit

from pagecheck.common.security.url_validation import (
    URLValidationError,
    validate_public_url,
)


def validate_resolved_ips(addresses: list[str]) -> tuple[str, ...]:
    """Rejeita resultados DNS vazios ou com endereços não públicos."""
    if not addresses:
        raise URLValidationError("O domínio não retornou endereços IP.")

    validated = set()

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise URLValidationError(
                "O DNS retornou um endereço IP inválido."
            ) from exc

        if not ip.is_global or getattr(ip, "scope_id", None):
            raise URLValidationError(
                "O domínio aponta para um endereço não público."
            )

        validated.add(str(ip))

    return tuple(sorted(validated))


def resolve_public_ips(raw_url: str) -> tuple[str, ...]:
    """Consulta o DNS e verifica todos os endereços retornados."""
    url = validate_public_url(raw_url)
    hostname = urlsplit(url).hostname

    if not hostname:
        raise URLValidationError("Domínio não encontrado.")

    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")

        results = socket.getaddrinfo(
            ascii_hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except (OSError, UnicodeError) as exc:
        raise URLValidationError(
            "Não foi possível resolver o DNS do domínio."
        ) from exc

    addresses = [result[4][0] for result in results]

    return validate_resolved_ips(addresses)
