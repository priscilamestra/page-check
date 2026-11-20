"""Stage 16D: no external networking, no false positives on blocked resources."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.api.app import app
from pagecheck.application.use_cases import collect_public_visuals as collector
from pagecheck.application.use_cases.audit_page_html import audit_page_html

HTML = '''<html lang="en"><head><title>Example Product</title>
<meta name="description" content="Purchase this example product"></head>
<body><h1>Example Product</h1><a href="/checkout">Buy now</a></body></html>'''


def fake_fetch(url):
    return FetchedPage(url, 'https://example.com/final', 200, HTML, ('https://example.com/final',))


def valid_visual():
    return {
        'scroll_complete': True,
        'geometry': {'document_width': 390, 'document_height': 800, 'truncated': False},
        'images': {'total': 1, 'broken': 1, 'not_verified': 0},
        'findings': [{
            'id': 'image-broken-1', 'category': 'images', 'severity': 'high',
            'title': 'Image failed to load', 'action': 'Check the image URL',
            'owner': 'Frontend', 'box': {'x': 10, 'y': 20, 'width': 100, 'height': 60},
        }],
        'screenshots': {'annotated': 'artifacts/page_audits/test/mobile/after_scroll_annotated.png'},
        'limitations': ['Interactive actions are not executed.'],
    }


def test_html_fetch_once_and_visual_capture_receives_final_url():
    calls = []
    def fetch(url):
        calls.append(('html', url))
        return fake_fetch(url)
    def capture(url):
        calls.append(('browser', url))
        return {'visuals': {'mobile': valid_visual()}, 'errors': {'desktop': 'offline'},
                'mode': 'guarded_javascript_get_only'}
    report = audit_page_html('https://example.com/?utm_source=test', niche='Retail',
                             objective='sales', fetch=fetch, visual_collector=capture)
    assert calls == [('html', 'https://example.com/?utm_source=test'),
                     ('browser', 'https://example.com/final')]
    assert report['source_states']['visuals']['mobile'] == 'partial'
    assert report['source_states']['visuals']['desktop'] == 'not_verified'
    assert report['status'] == 'partial'
    assert report['screenshots']['mobile']['annotated'].endswith('after_scroll_annotated.png')
    assert any(c['source'] == 'playwright' and c['viewport'] == 'mobile' for c in report['checks'])
    assert report['scores']['internal']['seo']['score'] is not None
    assert 'lighthouse' not in report['scores']
    assert report['visual_capture']['errors']['desktop'] == 'offline'


def test_visual_failure_does_not_erase_html_audit():
    def broken(_):
        raise RuntimeError('Browser not installed')
    report = audit_page_html('https://example.com/', niche='Retail', objective='sales',
                             fetch=fake_fetch, visual_collector=broken)
    assert report['source_states']['seo'] == 'completed'
    assert report['source_states']['visuals']['mobile'] == 'not_verified'
    assert report['visual_capture']['status'] == 'not_verified'
    assert report['screenshots'] == {}


def test_original_audit_remains_backward_compatible():
    report = audit_page_html('https://example.com/', niche='Retail', objective='sales', fetch=fake_fetch)
    assert 'visual_capture' not in report
    assert report['source_states']['visuals']['desktop'] == 'not_verified'


class FakePage:
    def __init__(self, *, response_ok=True, document_height=800):
        self.response_ok = response_ok
        self.document_height = document_height
        self.visited = None
    def goto(self, url, **kwargs):
        self.visited = url
        return SimpleNamespace(ok=self.response_ok)
    def evaluate(self, code):
        return self.document_height
    def wait_for_timeout(self, milliseconds):
        assert milliseconds == 750


class FakeContext:
    def __init__(self, page):
        self.page = page
        self.closed = False
    def route(self, *args):
        pass
    def route_web_socket(self, *args):
        pass
    def new_page(self):
        return self.page
    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, pages):
        self.pages = pages
        self.contexts = []
        self.options = []
    def new_context(self, **kwargs):
        self.options.append(kwargs)
        context = FakeContext(self.pages[len(self.contexts)])
        self.contexts.append(context)
        return context


def test_guarded_visual_collector_uses_two_javascript_contexts(monkeypatch, tmp_path):
    browser = FakeBrowser([FakePage(), FakePage()])
    monkeypatch.setattr(collector, 'audit_visual_viewport',
                        lambda page, **kw: valid_visual())
    result = collector.capture_with_browser(browser, url='https://example.com', output_dir=tmp_path)
    assert result['status'] == 'captured'
    assert set(result['visuals']) == {'desktop', 'mobile'}
    assert result['mode'] == 'guarded_javascript_get_only'
    assert all(options['java_script_enabled'] is True and
               options['service_workers'] == 'block' and
               options['accept_downloads'] is False
               for options in browser.options)
    assert all(context.closed for context in browser.contexts)
    assert browser.contexts[0].page.visited == 'https://example.com'
    assert all(row['limitations'] for row in result['visuals'].values())


def test_failing_viewport_does_not_block_other_viewport(monkeypatch, tmp_path):
    browser = FakeBrowser([FakePage(response_ok=False), FakePage()])
    monkeypatch.setattr(collector, 'audit_visual_viewport',
                        lambda page, **kw: valid_visual())
    result = collector.capture_with_browser(browser, url='https://example.com', output_dir=tmp_path)
    assert 'desktop' in result['errors']
    assert list(result['visuals']) == ['mobile']
    assert all(context.closed for context in browser.contexts)


def test_height_limit_prevents_giant_screenshots(monkeypatch, tmp_path):
    browser = FakeBrowser([FakePage(document_height=100_000), FakePage(document_height=100_000)])
    monkeypatch.setattr(collector, 'audit_visual_viewport',
                        lambda *a, **kw: pytest.fail('Should not take screenshots'))
    result = collector.capture_with_browser(browser, url='https://example.com', output_dir=tmp_path)
    assert not result['visuals']
    assert len(result['errors']) == 2


def test_private_destination_rejected_before_browser_creation(tmp_path):
    with pytest.raises(ValueError):
        collector.capture_with_browser(FakeBrowser([]), url='http://127.0.0.1/', output_dir=tmp_path)


def test_api_does_not_allow_remote_client_to_enable_visual_mode(monkeypatch):
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_FETCH', '1')
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_BROWSER', '1')
    response = TestClient(app).post('/v1/audits/page', json={
        'url': 'https://example.com', 'niche': 'Technology', 'objective': 'leads'})
    assert response.status_code == 403  # TestClient's synthetic remote host is not loopback.


def test_api_legacy_json_works_without_browser_flag(monkeypatch):
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_FETCH', '1')
    monkeypatch.delenv('PAGECHECK_ALLOW_LIVE_BROWSER', raising=False)
    from pagecheck.api.routes import audit
    def fake_audit(url, **kwargs):
        kwargs.pop('crawler', None)
        return {'requested_url': url, **kwargs}
    monkeypatch.setattr(audit, 'audit_page_html', fake_audit)
    response = TestClient(app).post('/v1/audits/page', json={
        'url': 'https://example.com', 'niche': 'Technology', 'objective': 'leads'})
    assert response.status_code == 200
    assert 'visual_collector' not in response.json()
