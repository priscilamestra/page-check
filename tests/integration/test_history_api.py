"""Local API history round-trip (all data in temporary directories)."""
from fastapi.testclient import TestClient

from pagecheck.api.app import app
def sample_report():
    return {
        "schema_version": "audit-report-1.0", "audit_id": "sample-id",
        "requested_url": "https://example.com/landing?utm_source=google",
        "final_url": "https://example.com/landing", "niche": "Tecnología",
        "objective": "leads", "status": "partial",
        "audit_context": {"language": "es", "keywords": ["gestión comercial"]},
        "source_states": {"seo": "completed", "conversion": "completed", "visuals": {
            "desktop": "not_verified", "mobile": "not_verified"}, "engines": {}},
        "scores": {"internal": {"seo": {"score": 75}}},
        "summary": {"counts": {"passed": 2, "failed": 1, "warning": 0, "not_verified": 1}},
        "checks": [{"check_id": "SEO_TITLE", "status": "passed"}],
        "findings": [{"title": "Missing alt", "severity": "high", "status": "failed",
                      "recommendation": "Add alt text", "team": "Frontend", "module": "images"}],
        "actions_by_team": [], "screenshots": {},
    }



def _client():
    return TestClient(app, client=("127.0.0.1", 54321))


def test_api_roundtrip_list_and_downloads(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGECHECK_HISTORY_ROOT", str(tmp_path))
    client = _client()
    report = sample_report()
    saved = client.post("/v1/history", json=report)
    assert saved.status_code == 201, saved.text
    key = saved.json()["audit_id"]
    result = client.get("/v1/history")
    assert result.status_code == 200
    assert result.json()["items"][0]["id"] == key
    detail = client.get(f"/v1/history/{key}")
    assert detail.status_code == 200
    assert detail.json()["niche"] == "Tecnología"
    for format in ("json", "csv", "html_zip"):
        response = client.get(f"/v1/history/{key}/export", params={"format": format})
        assert response.status_code == 200
        assert response.content
        assert "attachment" in response.headers["content-disposition"]


def test_api_rejects_non_local_connections(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGECHECK_HISTORY_ROOT", str(tmp_path))
    client = TestClient(app, client=("192.0.2.123", 1234))
    assert client.get("/v1/history").status_code == 403
    assert client.post("/v1/history", json=sample_report()).status_code == 403


def test_api_invalid_payload_is_422(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGECHECK_HISTORY_ROOT", str(tmp_path))
    response = _client().post("/v1/history", json={"foo": "bar"})
    assert response.status_code == 422


def test_api_unknown_audit_returns_404(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGECHECK_HISTORY_ROOT", str(tmp_path))
    assert _client().get("/v1/history/" + "f" * 32).status_code == 404


def test_api_delete_and_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGECHECK_HISTORY_ROOT", str(tmp_path))
    client = _client()
    key = client.post("/v1/history", json=sample_report()).json()["audit_id"]
    assert client.delete(f"/v1/history/{key}").status_code == 204
    assert client.get(f"/v1/history/{key}").status_code == 404
    assert client.delete(f"/v1/history/{key}").status_code == 404


def test_api_rejects_unknown_export_format(tmp_path, monkeypatch):
    monkeypatch.setenv("PAGECHECK_HISTORY_ROOT", str(tmp_path))
    client = _client()
    key = client.post("/v1/history", json=sample_report()).json()["audit_id"]
    assert client.get(f"/v1/history/{key}/export?format=pdf").status_code == 422
