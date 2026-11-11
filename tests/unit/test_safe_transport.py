import socket
from unittest.mock import Mock

import pytest

from pagecheck.acquisition.http.safe_transport import PublicNetworkBackend, UnsafeDestination
from pagecheck.common.security.url_validation import URLValidationError


def test_pins_validated_ip(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))])
    backend=PublicNetworkBackend()
    connector=Mock(return_value=object())
    monkeypatch.setattr(backend._backend, 'connect_tcp',connector)
    backend.connect_tcp('example.com',443)
    assert connector.call_args.args[:2] == ('93.184.216.34',443)


def test_blocks_mixed_ip_answers(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443)),(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))])
    backend=PublicNetworkBackend()
    conn=Mock()
    monkeypatch.setattr(backend._backend,'connect_tcp',conn)
    with pytest.raises(URLValidationError):backend.connect_tcp('example.com',443)
    conn.assert_not_called()


def test_invalid_port():
    with pytest.raises(UnsafeDestination): PublicNetworkBackend().connect_tcp('example.com',8080)


def test_unix_socket_disabled():
    with pytest.raises(UnsafeDestination):PublicNetworkBackend().connect_unix_socket('/tmp/socket')


def test_transport_preserves_original_hostname_for_http_and_tls():
    import httpx
    import httpcore
    from pagecheck.acquisition.http.safe_transport import PublicHTTPTransport

    class FakePool:
        def __init__(self): self.sent = None
        def handle_request(self, req):
            self.sent = req
            return httpcore.Response(200, headers=[(b'content-type', b'text/html')], content=b'<h1>Hello</h1>')
        def close(self): pass

    transport = PublicHTTPTransport()
    fake = FakePool()
    transport.pool.close()
    transport.pool = fake
    with httpx.Client(transport=transport, trust_env=False) as client:
        response = client.get('https://example.com/landing')
    assert response.status_code == 200
    assert fake.sent.url.host == b'example.com'
    assert fake.sent.url.target == b'/landing'
