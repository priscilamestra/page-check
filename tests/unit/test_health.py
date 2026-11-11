"""Teste do único endpoint implementado no bootstrap."""
from fastapi.testclient import TestClient

from pagecheck.api.app import app


def test_health_responds_ok() -> None:
    response = TestClient(app).get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'service': 'pagecheck-api'}
