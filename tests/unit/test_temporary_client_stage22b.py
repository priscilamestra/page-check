"""Restore screenshots and JSON through private POST calls; no Streamlit required."""
import base64
from pathlib import Path

import httpx
import pytest

from pagecheck.persistence.postgres.temporary import new_recovery_token
from pagecheck.ui import temporary_client as client
from pagecheck.ui.browser_recovery import BRIDGE_JS

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9WlNrZcAAAAASUVORK5CYII=")


def test_browser_bridge_never_puts_secret_in_query():
    assert 'localStorage.setItem' in BRIDGE_JS
    assert 'localStorage.getItem' in BRIDGE_JS
    assert 'localStorage.removeItem' in BRIDGE_JS
    assert 'location.search' not in BRIDGE_JS
    assert 'window.location' not in BRIDGE_JS
    assert "data?.command === 'set' || data?.command === 'clear'" in BRIDGE_JS


def test_browser_client_post_never_places_secret_in_url(monkeypatch, tmp_path):
    token = new_recovery_token()
    calls = []

    def mock_post(url, *, json, headers, timeout):
        calls.append((url, json, headers))
        request = httpx.Request('POST', url)
        if url.endswith('/save'):
            return httpx.Response(201, request=request, json={'recovery_token': token})
        if url.endswith('/restore'):
            return httpx.Response(200, request=request, json={
                'schema_version':'audit-report-1.0', 'requested_url':'https://example.org',
                'screenshots':{'desktop':{'initial':'temporary-image://desktop/initial'}},
            })
        if url.endswith('/image'):
            return httpx.Response(200, request=request, content=PNG)
        return httpx.Response(204, request=request)

    monkeypatch.setattr(client.httpx, 'post', mock_post)
    monkeypatch.setenv('PAGECHECK_PRIVATE_API_KEY', 'k'*40)
    saved = client.save_temporary('http://127.0.0.1:8000', {'requested_url':'https://example.org'})
    assert saved == token
    report = client.restore_temporary('http://127.0.0.1:8000', token, tmp_path)
    local = Path(report['screenshots']['desktop']['initial'])
    assert local.is_file() and local.read_bytes() == PNG
    assert local.is_relative_to(tmp_path / 'artifacts')
    assert all(token not in url for url, _, _ in calls)
    assert all(h.get('X-PageCheck-Service-Key') == 'k'*40 for _, _, h in calls)
    assert token in str(calls[1][1])
    client.revoke_temporary('http://127.0.0.1:8000', token)
    assert not any(token in url for url, _, _ in calls)


def test_reject_fake_png_and_unrecognized_screenshot_path(monkeypatch, tmp_path):
    token = new_recovery_token()
    def mock_post(url, *, json, headers, timeout):
        request = httpx.Request('POST', url)
        if url.endswith('/restore'):
            return httpx.Response(200, request=request, json={
                'screenshots':{'desktop':{'initial':'temporary-image://desktop/initial',
                                          'annotated':'../../etc/passwd'}}})
        return httpx.Response(200, request=request, content=b'Not a PNG')
    monkeypatch.setattr(client.httpx,'post',mock_post)
    result = client.restore_temporary('http://127.0.0.1:8000', token, tmp_path)
    assert result['screenshots'] == {}
    assert not list((tmp_path / 'artifacts').rglob('*.png'))


def test_private_client_failure_does_not_echo_token(monkeypatch):
    token = new_recovery_token()
    def bad_post(url, *, json, headers, timeout):
        raise httpx.ConnectError('private token='+token)
    monkeypatch.setattr(client.httpx,'post',bad_post)
    with pytest.raises(client.TemporaryRecoveryUnavailable) as exc:
        client.restore_temporary('http://127.0.0.1:8000',token,Path.cwd())
    assert token not in str(exc.value)


def test_local_cache_removes_expired_but_not_recent(tmp_path):
    import os, time
    cache = tmp_path / 'artifacts' / 'temporary_restore'
    old = cache / 'old' / 'desktop'
    recent = cache / 'recent' / 'desktop'
    old.mkdir(parents=True)
    recent.mkdir(parents=True)
    a = old/'initial.png'; b = recent/'initial.png'
    a.write_bytes(PNG); b.write_bytes(PNG)
    now = time.time()
    os.utime(a, (now - 90000,now - 90000))
    assert client.cleanup_stale_screenshots(tmp_path, now=now) == 1
    assert not a.exists() and b.exists()


def test_browser_component_requires_recent_streamlit_runtime():
    from pagecheck.ui import browser_recovery
    assert 'st.components.v2.component' in __import__('inspect').getsource(browser_recovery._component)
