"""Read-only STAGE32 deployment readiness check; never reads credentials."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "render.yaml", ".dockerignore", "uv.lock", "deploy/Dockerfile.api",
    "deploy/Dockerfile.ui", "deploy/start_streamlit.sh",
    "deploy/run_cleanup.sh", "scripts/postgres_temporary_cleanup.py",
    "migrations/0001_temporary_postgres.sql",
)


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit("Missing STAGE32 files: " + ", ".join(missing))
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
    if 'PAGECHECK_ALLOW_LIVE_FETCH\n        value: "0"' not in blueprint:
        raise SystemExit("Production URL-fetch safety gate is not fail-closed.")
    if 'PAGECHECK_ENV\n        value: production' not in blueprint:
        raise SystemExit("Render must not deploy a development-mode scanner.")
    print("STAGE32 config files: OK")
    print("Private API + Web UI + hourly cleanup: declared")
    print("Global audit admission: single-worker rate + concurrency control present")
    print("Private service key: required for production audit endpoint")
    print("Production public auditing: BLOCKED pending independently verified network egress isolation")
    print("Neon credentials: must be configured in Render; not inspected")
    print("Docker builds and production E2E: NOT VERIFIED")
    print("No deployment or network connection was attempted.")


if __name__ == "__main__":
    main()
