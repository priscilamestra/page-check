import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from pagecheck.acquisition.browser.dom_snapshot import snapshot_dom
from pagecheck.application.use_cases.audit_conversion_page import audit_conversion_html

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pages" / "conversion_tracking.html"
URL = "https://example.com/landing?utm_source=linkedin&utm_medium=paid&utm_campaign=q4"


def test_full_static_pipeline_from_fixture():
    html = FIXTURE.read_text(encoding="utf-8")
    report = audit_conversion_html(html, URL, niche="Tecnologia", objective="leads")
    assert report["score"] is None
    assert report["counts"]["failed"] == 1  # only broken local anchor
    assert report["counts"]["warning"] >= 1  # missing form label
    assert any(c["check_id"] == "TRACK_UTM" and c["status"] == "passed"
               for c in report["checks"])
    assert any(c["module"] == "forms" for c in report["checks"])


def test_rendered_dom_snapshot_does_not_submit_or_navigate():
    html = FIXTURE.read_text(encoding="utf-8")
    # Exclui URL de script remoto do browser fixture: não é necessário para
    # validar tags. A análise das tags é testada no pipeline estático acima.
    html = html.replace('src="https://www.googletagmanager.com/gtm.js?id=GTM-TESTE"',
                        'data-src="gtm-local-fixture"')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True, executable_path=os.getenv("PAGECHECK_TEST_CHROMIUM_PATH") or None
        )
        try:
            page = browser.new_page()
            page.set_content(html)
            snapshot = snapshot_dom(page)
            report = audit_conversion_html(snapshot["html"], URL, objective="leads")
            assert any(c["status"] == "failed" and "Âncora" in c["title"]
                       for c in report["checks"])
            assert any(c["module"] == "forms" for c in report["checks"])
            assert page.url == "about:blank"
        finally:
            browser.close()
