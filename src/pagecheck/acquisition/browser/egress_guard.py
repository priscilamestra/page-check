"""Additional outbound network guard for the untrusted Chromium process.

Native browser networking is pointed at a deliberately unreachable loopback
proxy. Document assets are supplied through existing Playwright route.fulfill()
handlers and the Python IP-pinned public HTTP transport.

IMPORTANT: This is a browser-level safeguard, NOT an OS/network egress sandbox.
The API still requires independently verified outbound network isolation in
its hosting environment before arbitrary public audits are enabled.
"""
from __future__ import annotations

from typing import Any

# Never listen on this address within the container. The smoke test checks
# that direct browser requests fail even when the container can reach localhost.
_BLOCKED_PROXY = "http://127.0.0.1:9"


def launch_guarded_chromium(chromium: Any) -> Any:
    """Launch headless Chromium with native network access denied via proxy.

    All requested HTTP(S) page assets must be fulfilled by installed guarded
    Playwright routes. This does not constrain host-network processes or DNS
    lookups independently of Chromium; it is defense in depth only.
    """
    return chromium.launch(
        headless=True,
        proxy={"server": _BLOCKED_PROXY},
        args=["--disable-background-networking"],
    )
