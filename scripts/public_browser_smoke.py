"""Smoke opcional de página pública CONFIÁVEL em desenvolvimento local.

Uso: definir PAGECHECK_ALLOW_LIVE_BROWSER=1 no PowerShell antes de executar.
Não executar como endpoint exposto a usuários. JavaScript permanece desativado.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

from pagecheck.acquisition.browser.public_navigation import inspect_public_page

if __name__ == "__main__":
    if os.environ.get("PAGECHECK_ALLOW_LIVE_BROWSER") != "1":
        raise SystemExit("Defina PAGECHECK_ALLOW_LIVE_BROWSER=1 somente para teste local.")
    url = "https://example.com"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            result = inspect_public_page(
                browser, url=url,
                output_dir=Path("artifacts/browser_stage11"),
                width=1000, height=650,
            )
        finally:
            browser.close()
    print(json.dumps({
        "navigation_status": result["navigation_status"],
        "network": result["network"],
        "screenshots": result.get("visual", {}).get("screenshots", {}),
    }, indent=2, ensure_ascii=False))
