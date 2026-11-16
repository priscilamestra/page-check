"""Server-to-server authentication for the temporary audit API.

The public browser must never receive PAGECHECK_PRIVATE_API_KEY. Local loopback
is permitted only in explicit development modes; production requires a secret.
This is not a public scanner security approval.
"""
from __future__ import annotations

import ipaddress
import os
import secrets

from fastapi import HTTPException, Request

from pagecheck.common.security.deployment import is_local_development


def require_private_service(request: Request) -> None:
    configured = os.getenv("PAGECHECK_PRIVATE_API_KEY", "")
    supplied = request.headers.get("x-pagecheck-service-key", "")
    # If a key was configured, demand it even for localhost: no silent bypass.
    if configured:
        if len(configured) >= 32 and secrets.compare_digest(configured, supplied):
            return
        raise HTTPException(403, "Private service authentication required.")
    if is_local_development():
        try:
            if request.client and ipaddress.ip_address(request.client.host).is_loopback:
                return
        except (ValueError, TypeError):
            pass
    raise HTTPException(403, "Private service authentication required.")
