"""Defense in depth for Chromium when rendering untrusted public pages.

All documents/assets are delivered by the IP-pinned Python fetcher through
Playwright's guarded route.fulfill. Stage35 blocks native browser networking
with an unreachable proxy. Stage36 additionally starts Chromium under a
Linux-kernel seccomp filter that denies all non-AF_UNIX socket creation.

IMPORTANT: A process-level browser guard is not a container egress firewall;
the trusted Python API still has networking. Production stays disabled until
independent environment-wide egress isolation is verified.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pagecheck.common.security.deployment import is_local_development

_BLOCKED_PROXY = "http://127.0.0.1:9"


class BrowserSandboxUnavailable(RuntimeError):
    """Refuse to launch a production browser without its kernel guard."""


def launch_guarded_chromium(chromium: Any) -> Any:
    """Launch Chromium with browser proxy and, in Docker, an OS syscall guard.

    The strict Chromium environment intentionally excludes API keys, database
    credentials, proxy configuration and other potentially sensitive secrets.
    Outside Docker, local development keeps Stage35's proxy-only behavior.
    """
    launch_options: dict[str, Any] = {
        "headless": True,
        "proxy": {"server": _BLOCKED_PROXY},
        "args": [
            "--disable-background-networking",
            "--disable-quic",
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        ],
    }
    launcher = os.environ.get("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", "").strip()
    if not launcher:
        if not is_local_development():
            raise BrowserSandboxUnavailable(
                "Production Chromium requires PAGECHECK_BROWSER_SECCOMP_LAUNCHER"
            )
        return chromium.launch(**launch_options)

    binary = Path(launcher)
    if not binary.is_absolute() or not binary.is_file() or not os.access(binary, os.X_OK):
        raise BrowserSandboxUnavailable("Chromium syscall sandbox binary is missing or not executable")
    real_chromium = getattr(chromium, "executable_path", None)
    if not isinstance(real_chromium, str) or not real_chromium.startswith("/"):
        raise BrowserSandboxUnavailable("Chromium executable path is not available")

    # Do not leak Neon credentials or the private API key to an untrusted page
    # renderer. Chromium receives only the variables it needs to start.
    launch_options["executable_path"] = str(binary)
    launch_options["env"] = {
        "PAGECHECK_BROWSER_REAL_EXECUTABLE": real_chromium,
        "HOME": "/tmp",
        "TMPDIR": "/tmp",
        "XDG_CACHE_HOME": "/tmp",
        "XDG_CONFIG_HOME": "/tmp",
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
    }
    return chromium.launch(**launch_options)
