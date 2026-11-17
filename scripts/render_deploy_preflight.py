"""Offline, no-network check of Render Free deployment policy (no secrets)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "render.yaml", ".dockerignore", "uv.lock", "deploy/Dockerfile.api",
    "deploy/Dockerfile.ui", "deploy/start_api_render_free.sh", "deploy/start_streamlit.sh",
    "src/pagecheck/ui/idle_guard.py", "scripts/postgres_temporary_cleanup.py",
    "migrations/0001_temporary_postgres.sql",
)


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit("Missing Render Free files: " + ", ".join(missing))
    text = (ROOT / "render.yaml").read_text(encoding="utf-8")
    if text.count("- type: web") != 2 or text.count("plan: free") != 2:
        raise SystemExit("Exactly two free Web Services are required.")
    for forbidden in ("type: pserv", "type: cron", "preDeployCommand:", "1c-2g"):
        if forbidden in text:
            raise SystemExit("Render Blueprint contains paid deployment resources.")
    for flag in ("PAGECHECK_PUBLIC_AUDITS_ENABLED", "PAGECHECK_EGRESS_ISOLATED",
                 "PAGECHECK_ALLOW_LIVE_FETCH", "PAGECHECK_ALLOW_LIVE_BROWSER"):
        if text.count(f'{flag}\n        value: "0"') != 2:
            raise SystemExit(f"The public auditing admission gate must remain closed: {flag}")
    if "envVarKey: RENDER_EXTERNAL_URL" not in text:
        raise SystemExit("UI must connect to FastAPI using HTTPS service URL.")
    if 'PAGECHECK_UI_IDLE_GUARD\n        value: "1"' not in text:
        raise SystemExit("The inactivity guard must be enabled.")
    print("RENDER_FREE_TWO_WEB_SERVICES_OK")
    print("PAID_PRIVATE_CRON_PREDEPLOY_REMOVED_OK")
    print("BROWSER_IDLE_PAUSE_CONFIGURED_OK")
    print("PUBLIC_AUDITS_DISABLED_PENDING_HOSTED_SECURITY_AND_MEMORY_TESTS")
    print("NO_NETWORK_CONNECTION_OR_DEPLOYMENT_WAS_ATTEMPTED")


if __name__ == "__main__":
    main()
