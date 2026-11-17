"""Stage39 safeguards: 2 free services, secrets and client-side idle pause."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_render_free_blueprint_has_no_billable_services():
    content = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert content.count("- type: web") == 2
    assert content.count("plan: free") == 2
    assert content.count("autoDeployTrigger: 'off'") == 2
    assert "preDeployCommand:" not in content
    assert "type: cron" not in content
    assert "type: pserv" not in content
    assert "envVarKey: RENDER_EXTERNAL_URL" in content
    assert "PAGECHECK_PRIVATE_API_KEY\n        generateValue: true" in content
    assert "envVarKey: PAGECHECK_PRIVATE_API_KEY" in content
    assert 'PAGECHECK_UI_IDLE_MINUTES\n        value: "15"' in content
    assert 'PAGECHECK_UI_IDLE_GUARD\n        value: "1"' in content
    assert content.count('PAGECHECK_EGRESS_ISOLATED\n        value: "0"') == 2
    assert content.count('PAGECHECK_PUBLIC_AUDITS_ENABLED\n        value: "0"') == 2


def test_no_paid_deployment_and_no_health_ping_polling():
    start_api = (ROOT / "deploy/start_api_render_free.sh").read_text(encoding="utf-8")
    start_ui = (ROOT / "deploy/start_streamlit.sh").read_text(encoding="utf-8")
    manifest = (ROOT / "render.yaml").read_text(encoding="utf-8")
    ui = (ROOT / "src/pagecheck/ui/app.py").read_text(encoding="utf-8")
    assert "postgres_temporary_migrate.py" in start_api
    assert "postgres_temporary_cleanup.py" in start_api
    assert "--workers 1" in start_api
    assert "exec /app/.venv/bin/streamlit" in start_ui
    assert "https://" in start_ui
    assert "type: cron" not in manifest
    assert "type: pserv" not in manifest
    assert "st.fragment(run_every=" not in ui
    assert "st.autorefresh" not in ui
    assert "enable_idle_guard()" in ui


def test_inactivity_guard_is_opt_in_and_never_exposes_key():
    script = (ROOT / "src/pagecheck/ui/idle_guard.py").read_text(encoding="utf-8")
    ast.parse(script)
    assert 'env.get("PAGECHECK_ENV", "local")' in script
    assert 'env.get("PAGECHECK_UI_IDLE_GUARD") == "1"' in script
    assert "setInterval(pauseWhenIdle, 30_000)" in script
    assert "window.location.replace(idleUrl)" in script
    assert "PAGECHECK_PRIVATE_API_KEY" not in script
    assert "fetch(" not in script
    assert "st.html(idle_guard_html" in script


def test_api_startup_scripts_are_copied_into_image():
    dockerfile = (ROOT / "deploy/Dockerfile.api").read_text(encoding="utf-8")
    assert "COPY deploy/start_api_render_free.sh ./deploy/start_api_render_free.sh" in dockerfile
    assert "COPY scripts/postgres_temporary_cleanup.py ./scripts/postgres_temporary_cleanup.py" in dockerfile


def test_idle_guard_does_not_activate_for_local_development(monkeypatch):
    import sys
    import types
    source = (ROOT / "src/pagecheck/ui/idle_guard.py").read_text(encoding="utf-8")
    dummy = types.SimpleNamespace(html=lambda *args, **kwargs: None)
    monkeypatch.setitem(sys.modules, "streamlit", dummy)
    namespace = {"__name__": "pagecheck.ui.idle_guard"}
    exec(compile(source, "idle_guard.py", "exec"), namespace)
    assert namespace["idle_guard_enabled"]({"PAGECHECK_ENV": "local", "PAGECHECK_UI_IDLE_GUARD": "1"}) is False
    assert namespace["idle_guard_enabled"]({"PAGECHECK_ENV": "production"}) is False
    assert namespace["idle_guard_enabled"]({"PAGECHECK_ENV": "production", "PAGECHECK_UI_IDLE_GUARD": "1"}) is True
    assert namespace["idle_minutes"]({"PAGECHECK_UI_IDLE_MINUTES": "1"}) == 10
    assert namespace["idle_minutes"]({"PAGECHECK_UI_IDLE_MINUTES": "999"}) == 60
    assert namespace["idle_minutes"]({"PAGECHECK_UI_IDLE_MINUTES": "bad"}) == 15
    assert "const idleMs = 900000;" in namespace["idle_guard_html"](15)


def test_hosted_smoke_has_no_live_audit_and_does_not_use_secrets():
    script = (ROOT / "scripts/render_free_smoke.py").read_text(encoding="utf-8")
    ast.parse(script)
    assert '"/v1/temporary/restore"' not in script or 'temporary/restore' in script
    assert 'v1/audits/page' not in script
    assert 'PAGECHECK_PRIVATE_API_KEY' not in script
    assert 'RENDER_FREE_HOSTED_STAGING_SMOKE_PASSED' in script
