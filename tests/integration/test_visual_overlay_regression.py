from pathlib import Path
import os

from playwright.sync_api import sync_playwright

from pagecheck.application.use_cases.audit_visual_viewport import audit_visual_viewport


def test_blocked_image_is_unverified_and_not_marked_broken(tmp_path):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            executable_path=os.getenv("PAGECHECK_CHROMIUM_EXECUTABLE") or None,
        )
        try:
            context = browser.new_context(viewport={'width': 390, 'height': 650},
                                          java_script_enabled=False, service_workers='block')
            try:
                context.route('**/*', lambda route: route.abort())
                page = context.new_page()
                page.set_content('''<html><body><h1>Test</h1>
                  <img src="https://example.com/missing.png" width="120" height="90">
                  </body></html>''', wait_until='load')
                report = audit_visual_viewport(
                    page, output_dir=tmp_path,
                    blocked_urls=lambda: {'https://example.com/missing.png'},
                )
            finally:
                context.close()
        finally:
            browser.close()
    assert report['images']['not_verified'] == 1
    assert report['images']['broken'] == 0
    assert not any(item['id'].startswith('image-broken') for item in report['findings'])
    assert Path(report['screenshots']['annotated']).is_file()
