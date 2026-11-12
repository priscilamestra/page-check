from fastapi.testclient import TestClient
from pagecheck.api.app import app
from pagecheck.api.routes import audit as route

client = TestClient(app)
PAYLOAD={"url":"https://example.com", "niche":"Technology", "objective":"leads"}


def test_static_engines_remain_opt_in(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.delenv("PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES", raising=False)
    monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_BROWSER", raising=False)
    kwargs=[]
    def fake(url, **args):
        kwargs.append(args)
        return {"schema_version":"audit-report-1.0"}
    monkeypatch.setattr(route, "audit_page_html", fake)
    r=client.post("/v1/audits/page", json=PAYLOAD)
    assert r.status_code == 200
    assert "external_collector" not in kwargs[0]


def test_static_engine_activation_rejects_remote_client(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.setenv("PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES", "1")
    monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_BROWSER", raising=False)
    from starlette.requests import Request
    import asyncio
    scope={"type":"http", "http_version":"1.1", "method":"POST", "scheme":"http", "path":"/v1/audits/page", "root_path":"", "query_string":b"", "headers":[], "client":("192.0.2.3", 10000), "server":("localhost", 8000)}
    request=Request(scope)
    from pagecheck.api.schemas.audit import PageAuditRequest
    from fastapi import HTTPException
    with __import__('pytest').raises(HTTPException) as exc:
        route.audit_page(PageAuditRequest(**PAYLOAD), request)
    assert exc.value.status_code==403


def test_static_engine_activation_passes_collector_locally(monkeypatch):
    monkeypatch.setenv("PAGECHECK_ALLOW_LIVE_FETCH", "1")
    monkeypatch.setenv("PAGECHECK_ALLOW_LOCAL_STATIC_ENGINES", "1")
    monkeypatch.delenv("PAGECHECK_ALLOW_LIVE_BROWSER", raising=False)
    monkeypatch.setattr(route,"audit_page_html", lambda url,**kwargs: {"collector": "external_collector" in kwargs})
    from starlette.requests import Request
    from pagecheck.api.schemas.audit import PageAuditRequest
    scope={"type":"http","http_version":"1.1","method":"POST","scheme":"http","path":"/v1/audits/page","root_path":"","query_string":b"","headers":[],"client":("127.0.0.1",1000),"server":("localhost",8000)}
    report=route.audit_page(PageAuditRequest(**PAYLOAD),Request(scope))
    assert report["collector"] is True
