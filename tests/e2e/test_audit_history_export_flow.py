"""Offline Page Check end-to-end contract: audit -> history -> reopen -> exports.

Uses an injected HTTP response and browser observation; no internet, no real
checkout navigation, no external CLI processes, no credentials.
"""
from __future__ import annotations

import io
import zipfile
from base64 import b64decode
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.api.app import app
from pagecheck.api.routes import audit as audit_route
from pagecheck.application.use_cases.audit_page_html import audit_page_html


HTML = """<!doctype html><html lang="en"><head>
<title>Project management software | Example</title>
<meta name="description" content="Project management software for teams.">
<link rel="canonical" href="https://example.com/landing"></head><body>
<h1>Project management software</h1>
<p>Organize projects and keep your team moving.</p>
<a id="start-trial" href="/checkout">Start your trial</a>
<form action="/signup" method="get"><label for="email">Work email</label>
<input id="email" name="email" type="email"></form>
</body></html>"""
# Valid 1x1 PNG, stored locally to exercise the existing export path.
PNG_1PX = b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9YfxiTgAAAAASUVORK5CYII='
)


def _client():
    return TestClient(app, client=("127.0.0.1", 54321))


def _configure_offline_pipeline(monkeypatch, tmp_path, *, with_visuals=True):
    """Patch network boundaries only; keep the real use case and API routes."""
    monkeypatch.setenv("PAGECHECK_HISTORY_ROOT", str(tmp_path))
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    if with_visuals:
        monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_BROWSER", "1")
    else:
        monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_BROWSER", raising=False)

    counts = {"fetch": 0, "visual": 0}

    def fake_fetch(url):
        counts["fetch"] += 1
        return FetchedPage(url, "https://example.com/landing", 200, HTML, ())

    def fake_visual_collector(url):
        counts["visual"] += 1
        base = tmp_path / 'artifacts' / 'e2e'
        base.mkdir(parents=True, exist_ok=True)
        result = {}
        for viewport in ('desktop', 'mobile'):
            path = base / f'{viewport}.png'
            path.write_bytes(PNG_1PX)
            result[viewport] = {
                'findings': [],
                'limitations': ['JavaScript disabled in the guarded test browser.'],
                'screenshots': {'initial': str(path), 'after_scroll': str(path),
                                'annotated': str(path)},
                'scroll_complete': True,
            }
        return {'visuals': result, 'status': 'captured',
                'mode': 'guarded_static_no_javascript', 'errors': {}}

    def injected_audit(url, **kwargs):
        return audit_page_html(url, fetch=fake_fetch, **kwargs)

    monkeypatch.setattr(audit_route, 'audit_page_html', injected_audit)
    monkeypatch.setattr(audit_route, 'collect_public_visuals', fake_visual_collector)
    return counts


PAYLOAD = {
    'url': 'https://example.com/landing?utm_source=google&utm_medium=cpc&utm_campaign=launch',
    'niche': 'Software', 'language': 'en', 'objective': 'leads',
    'keywords': ['project management'],
}


def test_full_audit_save_reopen_zip_without_refetch(tmp_path, monkeypatch):
    counters = _configure_offline_pipeline(monkeypatch, tmp_path)
    client = _client()

    live = client.post('/v1/audits/page', json=PAYLOAD)
    assert live.status_code == 200, live.text
    report = live.json()
    assert counters == {'fetch': 1, 'visual': 1}
    assert report['requested_url'] == PAYLOAD['url']
    assert report['http']['status_code'] == 200
    assert report['source_states']['seo'] == 'completed'
    assert report['source_states']['conversion'] == 'completed'
    assert set(report['screenshots']) == {'desktop', 'mobile'}
    assert report['scores']['lighthouse'] is None
    assert all(v == 'not_verified' for v in report['source_states']['engines'].values())
    assert report['status'] == 'partial'
    assert report['audit_context']['keywords'] == PAYLOAD['keywords']

    saved = client.post('/v1/history', json=report)
    assert saved.status_code == 201, saved.text
    identifier = saved.json()['audit_id']
    assert len(identifier) == 32
    assert (tmp_path / 'data/local/pagecheck_history.sqlite3').is_file()

    index = client.get('/v1/history')
    assert index.status_code == 200
    assert any(item['id'] == identifier for item in index.json()['items'])

    reopened = client.get(f'/v1/history/{identifier}')
    assert reopened.status_code == 200
    restored = reopened.json()
    assert restored['requested_url'] == PAYLOAD['url']
    assert restored['audit_context']['keywords'] == PAYLOAD['keywords']
    assert restored['screenshots']['desktop']['annotated']
    assert counters == {'fetch': 1, 'visual': 1}, 'Opening history must never rerun an audit'

    response = client.get(f'/v1/history/{identifier}/export?format=html_zip')
    assert response.status_code == 200, response.text
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
        assert {'report.html', 'report.json', 'findings.csv',
                'screenshots/desktop.png', 'screenshots/mobile.png'} <= names
        html = archive.read('report.html').decode('utf-8')
        assert 'Project' not in html or '<html' in html
        assert 'https://example.com/landing' in html

    csv = client.get(f'/v1/history/{identifier}/export?format=csv')
    assert csv.status_code == 200
    assert 'priority,status,area,issue' in csv.content.decode('utf-8-sig')
    raw = client.get(f'/v1/history/{identifier}/export?format=json')
    assert raw.status_code == 200
    assert b'audit-report-1.0' in raw.content
    assert counters == {'fetch': 1, 'visual': 1}


def test_executed_html_does_not_imply_external_engines_passed(tmp_path, monkeypatch):
    _configure_offline_pipeline(monkeypatch, tmp_path, with_visuals=False)
    response = _client().post('/v1/audits/page', json=PAYLOAD)
    assert response.status_code == 200, response.text
    report = response.json()
    assert report['source_states']['visuals']['desktop'] == 'not_verified'
    assert report['source_states']['visuals']['mobile'] == 'not_verified'
    assert all(v == 'not_verified' for v in report['source_states']['engines'].values())
    assert report['status'] == 'partial'


def test_local_history_rejects_nonlocal_request_even_when_file_exists(tmp_path, monkeypatch):
    monkeypatch.setenv('PAGECHECK_HISTORY_ROOT', str(tmp_path))
    outside = TestClient(app, client=('192.0.2.50', 40000))
    assert outside.get('/v1/history').status_code == 403
    assert outside.post('/v1/history', json={'schema_version': 'audit-report-1.0'}).status_code == 403


def test_live_audit_opt_in_off_rejects_before_fetch(tmp_path, monkeypatch):
    counters = _configure_offline_pipeline(monkeypatch, tmp_path)
    monkeypatch.delenv('PAGECHECK_ALLOW_LIVE_FETCH', raising=False)
    response = _client().post('/v1/audits/page', json=PAYLOAD)
    assert response.status_code == 503
    assert counters == {'fetch': 0, 'visual': 0}
