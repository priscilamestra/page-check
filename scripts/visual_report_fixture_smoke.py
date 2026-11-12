"""Offline fixture with real desktop/mobile visual annotations, no network."""
from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from pagecheck.acquisition.http.fetcher import FetchedPage
from pagecheck.application.use_cases.audit_page_html import audit_page_html
from pagecheck.application.use_cases.audit_visual_viewport import audit_visual_viewport

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests' / 'fixtures' / 'pages' / 'responsive_visual.html'
OUTPUT = ROOT / 'artifacts' / 'page_audits' / 'stage16d_fixture'
URL = 'https://example.com/landing?utm_source=google&utm_medium=cpc'


def main():
    html = FIXTURE.read_text(encoding='utf-8')

    def fetch(url):
        return FetchedPage(url, url, 200, html, ())

    def visuals(url):
        observations = {}
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                executable_path=os.getenv("PAGECHECK_CHROMIUM_EXECUTABLE") or None,
            )
            try:
                for name, width in (('desktop', 1280), ('mobile', 390)):
                    context = browser.new_context(viewport={'width': width, 'height': 720},
                                                  service_workers='block', java_script_enabled=False)
                    context.route('**/*', lambda route: route.abort())
                    try:
                        page = context.new_page()
                        page.set_content(html, wait_until='load')
                        observations[name] = audit_visual_viewport(page, output_dir=OUTPUT / name)
                    finally:
                        context.close()
            finally:
                browser.close()
        return {'visuals': observations, 'errors': {}, 'mode': 'offline_test_fixture'}

    report = audit_page_html(URL, niche='Retail', objective='sales',
                             language='en', keywords=['landing page'],
                             fetch=fetch, visual_collector=visuals)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT / 'consolidated_visual_audit.json'
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({
        'report': str(destination),
        'screenshots': report['screenshots'],
        'visual_states': report['source_states']['visuals'],
    }, indent=2))


if __name__ == '__main__':
    main()
