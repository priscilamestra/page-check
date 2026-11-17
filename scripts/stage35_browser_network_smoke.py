"""Offline container smoke test: guarded Chromium vs direct loopback egress.

Run inside the stage35 API Docker image. No internet, Neon, or real site needed.
This only tests the browser-level proxy guard, not host firewall isolation.
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from playwright.sync_api import Error as PlaywrightError, sync_playwright

from pagecheck.acquisition.browser.egress_guard import launch_guarded_chromium


class _Endpoint(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SHOULD_NOT_BE_REACHED")

    def log_message(self, *args):
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Endpoint)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as playwright:
            browser = launch_guarded_chromium(playwright.chromium)
            try:
                context = browser.new_context(
                    java_script_enabled=False, service_workers="block",
                    accept_downloads=False,
                )
                try:
                    page = context.new_page()
                    local = f"http://127.0.0.1:{server.server_port}/"
                    try:
                        page.goto(local, wait_until="domcontentloaded", timeout=5000)
                    except PlaywrightError:
                        pass
                    else:
                        raise RuntimeError("FAIL: Chromium reached loopback without guarded routes")
                    print("BROWSER_DIRECT_LOOPBACK_BLOCKED")

                    # Requests explicitly intercepted by the application still
                    # render, demonstrating the guarded route pathway works.
                    context.route(
                        "**/*", lambda route: route.fulfill(
                            status=200, content_type="text/html",
                            body="<html><body>GUARDED_ROUTE_OK</body></html>",
                        ),
                    )
                    page.goto("https://www.example.com/", wait_until="domcontentloaded", timeout=5000)
                    if "GUARDED_ROUTE_OK" not in page.content():
                        raise RuntimeError("FAIL: guarded fulfillment did not render")
                    print("GUARDED_ROUTE_FULFILL_OK")
                finally:
                    context.close()
            finally:
                browser.close()
        print("STAGE35_BROWSER_PROXY_SMOKE_PASSED")
        print("OS_LEVEL_EGRESS_ISOLATION_NOT_VERIFIED")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


if __name__ == "__main__":
    main()
