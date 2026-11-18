"""One-shot, private hosted preflight. Never prints the API service key.

Run with PAGECHECK_PRIVATE_API_KEY set only in the current PowerShell session.
Do not run this until stage43-api is Live, but keep public auditing disabled.
"""
from __future__ import annotations

import argparse
import os
import sys
import getpass

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, help="Deployed FastAPI HTTPS origin")
    parser.add_argument("--audit", action="store_true", help="Run one authenticated public test audit after enabling API flags")
    args = parser.parse_args()
    key = os.environ.get("PAGECHECK_PRIVATE_API_KEY", "") or getpass.getpass("Page Check private API key (hidden): ")
    if len(key) < 32:
        print("ERROR: PAGECHECK_PRIVATE_API_KEY is missing in this terminal", file=sys.stderr)
        return 2
    origin = args.api.rstrip("/")
    if not origin.startswith("https://"):
        print("ERROR: Only HTTPS origins are accepted", file=sys.stderr)
        return 2
    try:
        response = httpx.post(origin + "/v1/audits/isolation-check",
                              headers={"X-PageCheck-Service-Key": key}, timeout=45)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        print(f"HOSTED_WORKER_PREFLIGHT_FAILED: {type(exc).__name__}")
        return 1
    required = (data.get("status") == "ok"
                and data.get("worker_ipv4_blocked") is True
                and data.get("worker_ipv6_blocked") is True
                and data.get("broker_required") is True
                and data.get("container_wide_egress_firewall") is False)
    if not required:
        print("HOSTED_WORKER_PREFLIGHT_FAILED: unexpected security response")
        return 1
    print("STAGE43_RENDER_WORKER_OS_SOCKET_BLOCK_PASSED")
    print("STAGE43_PUBLIC_FETCH_BROKER_CONFIGURED")
    print("NO_HOST_WIDE_FIREWALL_CLAIM")
    if args.audit:
        try:
            scan = httpx.post(origin + "/v1/audits/page", json={
                "url": "https://example.com/", "niche": "Technology",
                "objective": "leads", "language": "en", "keywords": ["example"],
            }, headers={"X-PageCheck-Service-Key": key}, timeout=140)
            scan.raise_for_status()
            report = scan.json()
        except (httpx.HTTPError, ValueError) as exc:
            print("STAGE43_HOSTED_PUBLIC_AUDIT_FAILED: " + type(exc).__name__)
            return 1
        states = report.get("source_states", {})
        screenshots = report.get("screenshots", {})
        if states.get("seo") != "completed" or states.get("conversion") != "completed":
            print("STAGE43_HOSTED_PUBLIC_AUDIT_INCOMPLETE")
            return 1
        if not all(bool(screenshots.get(v)) for v in ("desktop", "mobile")):
            print("STAGE43_HOSTED_SCREENSHOTS_INCOMPLETE")
            return 1
        print("STAGE43_HOSTED_PUBLIC_AUDIT_SUCCEEDED")
        print("STAGE43_HOSTED_DESKTOP_MOBILE_EVIDENCE_PRESENT")
    else:
        print("PUBLIC_AUDITS_NOT_ENABLED_BY_THIS_TEST")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
