"""Stage36 application contract; no browser or Docker required."""
from __future__ import annotations

from pathlib import Path

import pytest

from pagecheck.acquisition.browser.egress_guard import (
    BrowserSandboxUnavailable, launch_guarded_chromium,
)

ROOT = Path(__file__).resolve().parents[2]


class FakeChromium:
    executable_path = "/opt/chromium/chrome"

    def __init__(self):
        self.settings = None

    def launch(self, **settings):
        self.settings = settings
        return "browser"


def test_dev_keeps_old_proxy_guard_when_no_kernel_launcher(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "development")
    monkeypatch.delenv("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", raising=False)
    chromium = FakeChromium()
    assert launch_guarded_chromium(chromium) == "browser"
    assert chromium.settings["proxy"]["server"] == "http://127.0.0.1:9"
    assert "executable_path" not in chromium.settings


def test_production_cannot_launch_browser_without_kernel_guard(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.delenv("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", raising=False)
    with pytest.raises(BrowserSandboxUnavailable, match="requires"):
        launch_guarded_chromium(FakeChromium())


def test_production_missing_wrapper_fails_closed(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    monkeypatch.setenv("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", "/path/does/not/exist")
    with pytest.raises(BrowserSandboxUnavailable, match="missing"):
        launch_guarded_chromium(FakeChromium())


def test_launcher_receives_no_api_secrets(monkeypatch, tmp_path):
    monkeypatch.setenv("PAGECHECK_ENV", "production")
    launcher = tmp_path / "sandbox"
    launcher.write_text("#!/bin/sh\nexit 0\n")
    launcher.chmod(0o755)
    monkeypatch.setenv("PAGECHECK_BROWSER_SECCOMP_LAUNCHER", str(launcher))
    monkeypatch.setenv("PAGECHECK_DATABASE_URL", "postgresql://private-secret")
    monkeypatch.setenv("PAGECHECK_PRIVATE_API_KEY", "another-private-secret")
    chromium = FakeChromium()
    assert launch_guarded_chromium(chromium) == "browser"
    assert chromium.settings["executable_path"] == str(launcher)
    environment = chromium.settings["env"]
    assert "PAGECHECK_DATABASE_URL" not in environment
    assert "PAGECHECK_PRIVATE_API_KEY" not in environment
    assert environment["PAGECHECK_BROWSER_REAL_EXECUTABLE"] == "/opt/chromium/chrome"
    assert chromium.settings["proxy"]["server"] == "http://127.0.0.1:9"




