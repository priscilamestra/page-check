"""No accidental success signal before serverless migration is complete."""

from pagecheck.common.security.vercel_readiness import vercel_readiness


def test_current_app_is_not_marked_ready():
    r = vercel_readiness()
    assert not r["deploy_ready"]
    assert len(r["blocked_by"]) == 5


def test_python_backend_alone_is_insufficient():
    r = vercel_readiness(websocket_ui_replaced=True)
    assert not r["deploy_ready"]
    assert "scanner" in r["blocked_by"]


def test_no_login_is_assumed():
    r = vercel_readiness()
    assert "login" not in r["note"].split("No deployment performed;")[0]
    assert "No deployment performed" in r["note"]


def test_ready_only_after_all_independent_gates():
    r = vercel_readiness(websocket_ui_replaced=True,
                         durable_storage_or_stateless_exports=True,
                         isolated_public_scanner=True,
                         abuse_limits_and_privacy=True,
                         integration_tests_passed=True)
    assert r["deploy_ready"]
    assert r["blocked_by"] == []


def test_missing_single_gate_is_still_blocked():
    r = vercel_readiness(websocket_ui_replaced=True,
                         durable_storage_or_stateless_exports=True,
                         isolated_public_scanner=True,
                         abuse_limits_and_privacy=True)
    assert not r["deploy_ready"]
    assert r["blocked_by"] == ["test"]
