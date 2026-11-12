"""Demonstra integração externa com fixtures offline, sem APIs e sem URLs arbitrárias.

Modo padrão: consome relatórios de referência. --live-local requer npm install.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from pagecheck.application.use_cases.external_engines import combine_engines
from pagecheck.integrations.axe.adapter import normalize_axe
from pagecheck.integrations.engine_result import unavailable
from pagecheck.integrations.impeccable.adapter import normalize_impeccable
from pagecheck.integrations.lighthouse.adapter import normalize_lighthouse
from pagecheck.integrations.cli_runner import local_binary, run_local_json_command

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "engines"
HTML = ROOT / "tests" / "fixtures" / "pages" / "visual_scroll.html"
OUT = ROOT / "artifacts" / "external_stage14"


def reference():
    return {
        "lighthouse": normalize_lighthouse(json.loads((FIXTURES / "lighthouse.json").read_text("utf-8"))),
        "axe": normalize_axe(json.loads((FIXTURES / "axe.json").read_text("utf-8"))),
        "impeccable": normalize_impeccable(json.loads((FIXTURES / "impeccable.json").read_text("utf-8"))),
    }


def live_local():
    """Executa somente contra fixture local controlada, nunca aceita URL do usuário."""
    report = {}
    fixture = HTML.resolve()
    if not fixture.is_file():
        raise FileNotFoundError(fixture)

    impeccable = local_binary(ROOT, "impeccable")
    report["impeccable"] = (
        run_local_json_command("impeccable", [str(impeccable), "detect", "--json", str(fixture)], root=ROOT)
        if impeccable else unavailable("impeccable", "Impeccable não instalado localmente."))

    try:
        from playwright.sync_api import sync_playwright
        from pagecheck.integrations.axe.runner import run_axe_on_page
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                context = browser.new_context(service_workers="block", java_script_enabled=True)
                # Fixture controlada, sem conexões externas permitidas.
                context.route("http://**/*", lambda route: route.abort())
                context.route("https://**/*", lambda route: route.abort())
                page = context.new_page()
                page.goto(fixture.as_uri(), wait_until="load", timeout=12000)
                report["axe"] = run_axe_on_page(page, project_root=ROOT)
                context.close()
            finally:
                browser.close()
    except Exception as exc:
        report["axe"] = unavailable("axe", f"Navegador indisponível: {type(exc).__name__}")

    lighthouse = local_binary(ROOT, "lighthouse")
    if not lighthouse:
        report["lighthouse"] = unavailable("lighthouse", "Lighthouse não instalado localmente.")
    else:
        body = fixture.read_bytes()
        class FixtureHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_args):
                pass
        # Loopback: somente para teste local, URL fixa gerada pelo servidor.
        with ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/"
                report["lighthouse"] = run_local_json_command(
                    "lighthouse", [str(lighthouse), url, "--quiet", "--output=json",
                                   "--output-path=stdout", "--chrome-flags=--headless"],
                    root=ROOT, timeout=120)
            finally:
                server.shutdown()
                thread.join(timeout=2)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-local", action="store_true", help="Executa CLIs e axe na fixture local.")
    args = parser.parse_args()
    summary = combine_engines(live_local() if args.live_local else reference())
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / ("local_engines.json" if args.live_local else "reference_engines.json")
    dest.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"file": str(dest), "status": summary["status"],
                      "engines": {k: v["status"] for k, v in summary["engines"].items()}},
                     ensure_ascii=False, indent=2))
