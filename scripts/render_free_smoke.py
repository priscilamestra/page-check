"""Read-only hosted smoke test for two Render Free web services.

Run locally AFTER deployment; never transmits secrets or starts an audit:
  uv run python scripts/render_free_smoke.py --api https://... --ui https://...
"""
from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def _base(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("A public HTTPS URL is required.")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ValueError("Pass only the HTTPS base URL.")
    return f"https://{parsed.netloc}"


def _call(url: str, *, method: str = "GET", data: bytes | None = None) -> tuple[int, bytes]:
    headers = {"Content-Type": "application/json"} if data else {}
    request = Request(url, method=method, data=data, headers=headers)
    try:
        with urlopen(request, timeout=110) as response:
            return response.status, response.read(1024)
    except HTTPError as exc:
        return exc.code, b""
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach the service. Check its Render logs and free instance status.") from exc


def run(api: str, ui: str) -> None:
    api, ui = _base(api), _base(ui)
    status, body = _call(f"{api}/health")
    if status != 200 or json.loads(body).get("service") != "pagecheck-api":
        raise RuntimeError("FastAPI health is not ready.")
    status, _ = _call(f"{ui}/_stcore/health")
    if status != 200:
        raise RuntimeError("Streamlit health is not ready.")
    status, _ = _call(f"{api}/v1/temporary/restore", method="POST",
                      data=json.dumps({"token": "A" * 43}).encode("ascii"))
    if status != 403:
        raise RuntimeError("The FastAPI recovery endpoint did not reject an unauthenticated request.")
    print("RENDER_FREE_API_HEALTH_OK")
    print("RENDER_FREE_UI_HEALTH_OK")
    print("RENDER_FREE_PUBLIC_RECOVERY_AUTH_BLOCKED")
    print("RENDER_FREE_HOSTED_STAGING_SMOKE_PASSED")
    print("NO_AUDIT_PERFORMED__PUBLIC_URL_AUDITS_STILL_DISABLED")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Free no-secret hosted health/auth checks")
    parser.add_argument("--api", required=True, help="FastAPI public HTTPS URL")
    parser.add_argument("--ui", required=True, help="Streamlit public HTTPS URL")
    args = parser.parse_args()
    try:
        run(args.api, args.ui)
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"HOSTED_SMOKE_FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
