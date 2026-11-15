"""Fail-closed environment helper does not require FastAPI integration."""
import pytest
from pagecheck.common.security.deployment import is_local_development, live_fetch_enabled


@pytest.mark.parametrize("mode", ["local", "dev", "development", "test"])
def test_local_modes_require_fetch_flag(monkeypatch, mode):
    monkeypatch.setenv("PAGECHECK_ENV", mode)
    monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_FETCH", raising=False)
    assert is_local_development()
    assert not live_fetch_enabled()
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    assert live_fetch_enabled()


@pytest.mark.parametrize("mode", ["production", "prod", "staging", "public", "oops"])
def test_unknown_or_public_modes_never_fetch(monkeypatch, mode):
    monkeypatch.setenv("PAGECHECK_ENV", mode)
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    assert not is_local_development()
    assert not live_fetch_enabled()
