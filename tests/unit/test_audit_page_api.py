from fastapi.testclient import TestClient
from pagecheck.api.app import app
from pagecheck.api.routes import audit as route_module

client = TestClient(app)
PAYLOAD = {'url': 'https://example.com', 'niche': 'Tecnologia', 'objective': 'sales'}

def test_route_exists_and_opt_in_is_required(monkeypatch):
    monkeypatch.delenv('PAGECHECK_ALLOW_LIVE_FETCH', raising=False)
    assert client.post('/v1/audits/page', json=PAYLOAD).status_code == 503

def test_route_returns_consolidated_json(monkeypatch):
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_FETCH', '1')
    monkeypatch.setattr(route_module, 'audit_page_html', lambda url, niche, objective: {
        'schema_version': 'audit-report-1.0', 'requested_url': url,
        'final_url': url, 'niche': niche, 'objective': objective, 'status': 'partial',
        'summary': {}, 'scores': {}, 'checks': [], 'findings': [],
        'actions_by_team': [], 'source_states': {}
    })
    result = client.post('/v1/audits/page', json=PAYLOAD)
    assert result.status_code == 200
    assert result.json()['niche'] == 'Tecnologia'

def test_invalid_url_returns_error_without_fetch(monkeypatch):
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_FETCH', '1')
    assert client.post('/v1/audits/page', json={**PAYLOAD, 'url': 'http://127.0.0.1'}).status_code == 403

def test_invalid_objective_validation(monkeypatch):
    monkeypatch.setenv('PAGECHECK_ALLOW_LIVE_FETCH', '1')
    assert client.post('/v1/audits/page', json={**PAYLOAD, 'objective': 'unsupported'}).status_code == 422
