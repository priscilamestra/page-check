"""Check STAGE32 hosting scaffold without Docker or the Neon credential."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_render_blueprint_is_free_web_only_and_protected():
    manifest = _text("render.yaml")
    assert manifest.count("- type: web") == 2
    assert manifest.count("plan: free") == 2
    assert "type: pserv" not in manifest
    assert "type: cron" not in manifest
    assert "preDeployCommand:" not in manifest
    assert "PAGECHECK_ENV\n        value: production" in manifest
    assert 'PAGECHECK_ALLOW_LIVE_FETCH\n        value: "0"' in manifest
    assert 'PAGECHECK_ALLOW_LIVE_BROWSER\n        value: "0"' in manifest
    assert "PAGECHECK_DATABASE_URL\n        sync: false" in manifest
    assert "PAGECHECK_PRIVATE_API_KEY\n        generateValue: true" in manifest
    assert "envVarKey: RENDER_EXTERNAL_URL" in manifest
    assert "envVarKey: PAGECHECK_PRIVATE_API_KEY" in manifest
    assert "healthCheckPath: /_stcore/health" in manifest


def test_production_dockerfiles_and_shell_commands_match_entrypoints():
    api = _text("deploy/Dockerfile.api")
    ui = _text("deploy/Dockerfile.ui")
    start = _text("deploy/start_streamlit.sh")
    cron = _text("deploy/run_cleanup.sh")
    for dockerfile in (api, ui):
        assert "uv sync --locked --no-dev" in dockerfile
        assert "USER pagecheck" in dockerfile
    assert "playwright==1.57.0" in api
    assert "playwright install --with-deps chromium" in api
    assert '"--workers", "1"' in api
    assert "FastAPI URL must use HTTPS" in start
    assert "PAGECHECK_API_URL" in start
    assert "deploy/start_api_render_free.sh" in api
    assert "streamlit run streamlit_app.py" in start
    assert "scripts/postgres_temporary_cleanup.py" in cron
    for relative in ("main.py", "streamlit_app.py", "uv.lock", "migrations/0001_temporary_postgres.sql"):
        assert (ROOT / relative).is_file()


def test_prod_security_gates_still_enabled():
    # The UI must not silently run with a missing production sandbox.
    app = _text("src/pagecheck/ui/app.py")
    policy = _text("src/pagecheck/common/security/deployment.py")
    assert 'st.form_submit_button("Audit page", type="primary", disabled=scans_unavailable)' in app
    assert "production_scan_configured()" in policy
    assert "PAGECHECK_ALLOW_LIVE_FETCH" in policy


def test_docker_context_excludes_private_runtime_files():
    patterns = _text(".dockerignore")
    for pattern in (".env", ".env.*", "artifacts/", ".venv/", "tests/"):
        assert pattern in patterns
