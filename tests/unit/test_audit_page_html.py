from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.application.use_cases.audit_page_html import audit_page_html

HTML = '''<html><head><title>Loja exemplo</title>
<meta name="description" content="Comprar produtos">
<link rel="canonical" href="https://example.com/loja"></head>
<body><h1>Compre agora</h1><a href="/checkout" id="go">Comprar</a>
<form action="/signup"><label for="email">Email</label><input id="email" name="email"></form>
</body></html>'''

def test_unified_result_from_one_fetch():
    calls = []
    def fake_fetch(url):
        calls.append(url)
        return FetchedPage(url, 'https://example.com/loja', 200, HTML,
                           ('https://example.com/loja',))
    result = audit_page_html('https://example.com/loja?utm_source=google&utm_medium=cpc&utm_campaign=x',
                             niche='E-commerce', objective='sales', fetch=fake_fetch)
    assert len(calls) == 1
    assert result['schema_version'] == 'audit-report-1.0'
    assert result['source_states']['seo'] == 'completed'
    assert result['source_states']['conversion'] == 'completed'
    assert result['source_states']['visuals']['mobile'] == 'not_verified'
    assert 'lighthouse' not in result['scores']
    assert result['http']['status_code'] == 200
    assert any(c['id'].endswith('URL_REDIRECT_PARAMETERS') and c['status'] == 'warning' for c in result['checks'])
    assert any(c['module'] == 'navigation' for c in result['checks'])
    assert any(c['module'] == 'forms' for c in result['checks'])
    assert result['status'] == 'partial'

def test_reject_short_niche_before_fetch():
    from pytest import raises
    with raises(ValueError, match='nicho'):
        audit_page_html('https://example.com', niche='x', objective='sales',
                        fetch=lambda _: (_ for _ in ()).throw(RuntimeError('should not fetch')))
