"""Network-denied worker invoked only through pagecheck-chromium-sandbox.

A worker must never be started directly in production. Its IPv4 and IPv6 socket
syscalls are denied by the inherited Linux seccomp filter before Python starts.
"""
from __future__ import annotations

import json
import os
import socket
import sys


def main() -> int:
    if not os.environ.get("PAGECHECK_PUBLIC_FETCH_BROKER_SOCKET"):
        raise RuntimeError("Network broker is required")
    # Fail closed: the seccomp block must be present *before* reading a URL.
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            connection = socket.socket(family, socket.SOCK_STREAM)
        except PermissionError:
            continue
        else:
            connection.close()
            raise RuntimeError("Worker has direct network access")

    from pagecheck.api.schemas.audit import PageAuditRequest
    from pagecheck.application.use_cases.audit_page_html import audit_page_html
    from pagecheck.application.use_cases.collect_public_visuals import collect_public_visuals
    from pagecheck.application.use_cases.collect_static_engines import collect_static_engines

    payload = PageAuditRequest.model_validate(json.load(sys.stdin))
    report = audit_page_html(payload.url, niche=payload.niche, objective=payload.objective,
                             language=payload.language, keywords=payload.keywords,
                             visual_collector=collect_public_visuals,
                             external_collector=collect_static_engines)
    json.dump(report, sys.stdout, separators=(",", ":"), ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
