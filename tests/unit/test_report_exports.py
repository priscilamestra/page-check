"""Exporter tests: portable offline HTML and CSV with safe local screenshot paths."""
import csv
import io
import json
import zipfile

from pagecheck.reporting.exports import findings_csv, html_export, json_export, zip_export
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



def test_json_export_preserves_accents():
    assert json.loads(json_export(sample_report()))["niche"] == "Tecnología"


def test_csv_contains_findings_and_header():
    content = findings_csv(sample_report()).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(content)))
    assert rows[0]["issue"] == "Missing alt"
    assert rows[0]["priority"] == "high"


def test_csv_formula_injection_is_neutralized():
    report = sample_report()
    report["findings"][0]["title"] = "=HYPERLINK(\"https://bad.example\")"
    content = findings_csv(report).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(content)))
    assert rows[0]["issue"].startswith("'=")


def test_html_escapes_untrusted_text_and_has_summary():
    report = sample_report()
    report["findings"][0]["title"] = '<script>alert("hello")</script>'
    html = html_export(report).decode("utf-8")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "75/100" in html
    assert "No verified screenshots" in html


def test_zip_export_has_json_csv_html_and_readme(tmp_path):
    payload = zip_export(sample_report(), tmp_path)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert set(archive.namelist()) == {"report.html", "report.json", "findings.csv", "README.txt"}
        assert b"Tecnolog" in archive.read("report.json")


def test_zip_includes_only_allowed_existing_screenshot(tmp_path):
    allowed = tmp_path / "artifacts" / "test" / "ok.png"
    allowed.parent.mkdir(parents=True)
    allowed.write_bytes(b"\x89PNG\r\n\x1a\nhello")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"secret")
    report = sample_report()
    report["screenshots"] = {"desktop": {"annotated": str(allowed)},
                             "mobile": {"annotated": str(outside)}}
    payload = zip_export(report, tmp_path)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert "screenshots/desktop.png" in archive.namelist()
        assert "screenshots/mobile.png" not in archive.namelist()
        html = archive.read("report.html").decode()
        assert 'src="screenshots/desktop.png"' in html


def test_empty_findings_still_export_header(tmp_path):
    report = sample_report()
    report["findings"] = []
    assert len(findings_csv(report).decode("utf-8-sig").splitlines()) == 1
    assert b"No findings in executed checks" in html_export(report)
