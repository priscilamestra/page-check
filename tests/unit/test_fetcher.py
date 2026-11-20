import httpx
import pytest

from pagecheck.acquisition.http.fetcher import FetchError, fetch_html, fetch_resource
from pagecheck.common.security.url_validation import URLValidationError


def test_reads_html():
    mock = httpx.MockTransport(lambda request: httpx.Response(200, headers={'content-type':'text/html; charset=utf-8'},text='<h1>OK</h1>'))
    result = fetch_html('https://example.com/home', transport=mock)
    assert result.status_code == 200
    assert result.html == '<h1>OK</h1>'
    assert result.final_url == 'https://example.com/home'


def test_safe_redirect():
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        if len(calls)==1:return httpx.Response(301,headers={'location':'/final'})
        return httpx.Response(200,headers={'content-type':'text/html'}, text='done')
    page=fetch_html('https://example.com/old',transport=httpx.MockTransport(handler))
    assert page.redirects == ('https://example.com/final',)
    assert page.html == 'done'
    assert len(calls)==2


def test_rejects_local_redirect_without_request():
    calls=[]
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302,headers={'location':'http://127.0.0.1/admin'})
    with pytest.raises(URLValidationError):
        fetch_html('https://example.com/start',transport=httpx.MockTransport(handler))
    assert len(calls)==1


def test_blocks_local_initial_url():
    with pytest.raises(URLValidationError):
        fetch_html('http://localhost/')


def test_rejects_non_html():
    with pytest.raises(FetchError,match='HTML'):
        fetch_html('https://example.com/file', transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={'content-type':'application/pdf'},content=b'pdf')
        ))


def test_rejects_large_body(monkeypatch):
    from pagecheck.acquisition.http import fetcher
    monkeypatch.setattr(fetcher,'MAX_BODY_BYTES',8)
    with pytest.raises(FetchError, match='maior'):
        fetch_html('https://example.com', transport=httpx.MockTransport(
            lambda request: httpx.Response(200, headers={'content-type':'text/html'},content=b'123456789')
        ))


def test_http_error():
    with pytest.raises(FetchError,match='HTTPStatusError'):
        fetch_html('https://example.com', transport=httpx.MockTransport(
            lambda request: httpx.Response(404,headers={'content-type':'text/html'})
        ))


def test_redirect_limit():
    with pytest.raises(FetchError,match='Limite'):
        fetch_html('https://example.com', transport=httpx.MockTransport(
            lambda request: httpx.Response(302,headers={'location':'/again'})
        ))


def test_resource_fetch_preserves_broken_status_as_evidence():
    result = fetch_resource('https://example.com/missing', transport=httpx.MockTransport(
        lambda request: httpx.Response(404, headers={'content-type': 'text/html'}, text='missing')
    ))
    assert result.status_code == 404
    assert result.text == 'missing'


def test_resource_fetch_revalidates_redirect_before_second_request():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={'location': 'http://127.0.0.1/private'})
    with pytest.raises(URLValidationError):
        fetch_resource('https://example.com/start', transport=httpx.MockTransport(handler))
    assert calls == ['https://example.com/start']
