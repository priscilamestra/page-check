"""Read-only, fail-closed smoke test to run inside the deployed private API.

Command: python -m pagecheck.ops.release_smoke

No audit is run, no browser is started, and no user records are written.
Never print Neon URLs, authentication tokens, or HTTP response bodies.
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API_BASE = "http://127.0.0.1:10000"
TEST_TOKEN = "A" * 43  # Syntactically valid, deliberately nonexistent recovery token.


class ReleaseSmokeError(RuntimeError):
    """The hosted release gate has not passed."""


def _require_staging_policy(env: Mapping[str, str]) -> None:
    if env.get("PAGECHECK_ENV", "").strip().lower() != "production":
        raise ReleaseSmokeError("Production mode is not configured")
    for key in (
        "PAGECHECK_PUBLIC_AUDITS_ENABLED",
        "PAGECHECK_EGRESS_ISOLATED",
        "PAGECHECK_ALLOW_LIVE_FETCH",
        "PAGECHECK_ALLOW_LIVE_BROWSER",
    ):
        if env.get(key) != "0":
            raise ReleaseSmokeError(f"Unsafe or unspecified staging flag: {key}")
    if len(env.get("PAGECHECK_PRIVATE_API_KEY", "")) < 32:
        raise ReleaseSmokeError("Private API key is not configured")
    if not env.get("PAGECHECK_DATABASE_URL", "").strip():
        raise ReleaseSmokeError("Neon database URL is not configured")


def _http_status(path: str, *, headers: Mapping[str, str] | None = None,
                 body: bytes | None = None) -> tuple[int, bytes]:
    request = Request(
        API_BASE + path,
        data=body,
        method="POST" if body is not None else "GET",
        headers=dict(headers or {}),
    )
    try:
        with urlopen(request, timeout=8) as response:
            return response.status, response.read(1024)
    except HTTPError as exc:
        # Don't read or print error responses: they might contain sensitive data.
        return exc.code, b""


def _database_schema_ok() -> bool:
    # psycopg is an existing production dependency. Use a read-only statement.
    import psycopg

    with psycopg.connect(os.environ["PAGECHECK_DATABASE_URL"], connect_timeout=8) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT to_regclass('public.pagecheck_temporary_audits'), "
                "to_regclass('public.pagecheck_temporary_screenshots')"
            )
            return all(name is not None for name in cursor.fetchone())


def run_smoke(env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    current = os.environ if env is None else env
    _require_staging_policy(current)

    status, body = _http_status("/health")
    if status != 200:
        raise ReleaseSmokeError("Private API health check failed")
    try:
        healthy = json.loads(body)
    except (ValueError, TypeError) as exc:
        raise ReleaseSmokeError("Health check returned invalid JSON") from exc
    if healthy.get("status") != "ok" or healthy.get("service") != "pagecheck-api":
        raise ReleaseSmokeError("Health check returned the wrong service")

    payload = json.dumps({"token": TEST_TOKEN}).encode("utf-8")
    content_header = {"Content-Type": "application/json"}
    denied, _ = _http_status("/v1/temporary/restore", headers=content_header, body=payload)
    if denied != 403:
        raise ReleaseSmokeError("Unauthenticated private request was not denied")
    authorized, _ = _http_status(
        "/v1/temporary/restore",
        headers={**content_header, "X-PageCheck-Service-Key": current["PAGECHECK_PRIVATE_API_KEY"]},
        body=payload,
    )
    if authorized not in (404, 422):
        raise ReleaseSmokeError("Authenticated private request failed the isolation check")

    if not _database_schema_ok():
        raise ReleaseSmokeError("Expected Neon temporary tables were not found")

    return (
        "STAGE38_API_HEALTH_OK",
        "STAGE38_PRIVATE_AUTH_OK",
        "STAGE38_NEON_SCHEMA_OK",
        "STAGE38_PUBLIC_AUDITS_DISABLED_OK",
        "STAGE38_HOSTED_STAGING_SMOKE_PASSED",
    )


def main() -> int:
    try:
        for line in run_smoke():
            print(line)
    except Exception as exc:
        # Only an exception class is revealed; never leak credentials or URLs.
        print(f"STAGE38_HOSTED_STAGING_SMOKE_FAILED ({type(exc).__name__})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
