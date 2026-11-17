"""Stage35 offline contract: Chromium native egress is disabled by default."""
from __future__ import annotations

from pathlib import Path

from pagecheck.acquisition.browser.egress_guard import launch_guarded_chromium
from pagecheck.common.security import deployment


class DummyChromium:
    def __init__(self):
        self.kwargs = None

    def launch(self, **kwargs):
        self.kwargs = kwargs
        return "guarded-browser"


def test_browser_is_launched_with_nonlistening_loopback_proxy():
    fake = DummyChromium()
    assert launch_guarded_chromium(fake) == "guarded-browser"
    assert fake.kwargs["headless"] is True
    assert fake.kwargs["proxy"]["server"] == "http://127.0.0.1:9"
    assert "--disable-background-networking" in fake.kwargs["args"]


def test_collector_uses_browser_egress_guard_by_default():
    root = Path(__file__).resolve().parents[2]
    source = (root / "src/pagecheck/application/use_cases/collect_public_visuals.py").read_text(encoding="utf-8")
    assert "browser = launch_guarded_chromium(playwright.chromium)" in source
    assert "browser = playwright.chromium.launch(headless=True)" not in source


def test_production_deployment_is_still_disabled_by_default(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    for flag in ("PAGECHECK_EGRESS_ISOLATED", "PAGECHECK_PUBLIC_AUDITS_ENABLED",
                 "PAGECHECK_ALLOW_LIVE_FETCH", "PAGECHECK_ALLOW_LIVE_BROWSER"):
        monkeypatch.delenv(flag, raising=False)
    assert deployment.production_scan_configured() is False


def test_render_configuration_does_not_self_assert_egress_isolation():
    root = Path(__file__).resolve().parents[2]
    blueprint = (root / "render.yaml").read_text(encoding="utf-8")
    assert 'PAGECHECK_EGRESS_ISOLATED\n        value: "0"' in blueprint
    assert 'PAGECHECK_PUBLIC_AUDITS_ENABLED\n        value: "0"' in blueprint
