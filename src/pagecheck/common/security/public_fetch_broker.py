"""Broker for *only* validated public GETs from a network-denied audit worker.

The worker is not given internet sockets, database credentials, or the API key.
A trusted API thread performs IP-pinned public GETs and sends bounded bytes over
an AF_UNIX socket. Do not use the broker as a general-purpose HTTP proxy.
"""
from __future__ import annotations

import base64
import json
import socket
import socketserver
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import httpx

from pagecheck.acquisition.http.safe_transport import PublicHTTPTransport, UnsafeDestination
from pagecheck.common.security.url_validation import validate_public_url

MAX_SINGLE_BYTES = 2_000_000
MAX_TOTAL_BYTES = 16_000_000
MAX_REQUESTS = 72
MAX_MESSAGE_BYTES = 3_000_000


# Render runs the secure broker on Linux. Windows must be able to import the API
# for local tests, but must never substitute a TCP broker for the Unix socket.
_BrokerServerBase = getattr(socketserver, "UnixStreamServer", None)
if _BrokerServerBase is None:
    class _BrokerServerBase:
        def __new__(cls, *args, **kwargs):
            raise RuntimeError("The isolated Unix-socket broker is unavailable on this platform.")

class _BrokerServer(_BrokerServerBase):
    allow_reuse_address = False

    def __init__(self, path: str):
        super().__init__(path, _RequestHandler)
        self.fetch_count = 0
        self.total_bytes = 0
        self.lock = threading.Lock()


class _RequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        try:
            raw = self.rfile.readline(8193)
            if not raw.endswith(b"\n") or len(raw) > 8192:
                raise ValueError("Malformed broker request")
            request = json.loads(raw)
            if not isinstance(request, dict) or set(request) != {"method", "url"}:
                raise ValueError("Unrecognized broker command")
            if request["method"] != "GET":
                raise ValueError("Only GET is allowed")
            url = validate_public_url(request["url"])
            server = self.server
            with server.lock:
                if server.fetch_count >= MAX_REQUESTS or server.total_bytes >= MAX_TOTAL_BYTES:
                    raise ValueError("Audit network budget exhausted")
                server.fetch_count += 1
            with httpx.Client(transport=PublicHTTPTransport(), trust_env=False,
                              follow_redirects=False, timeout=httpx.Timeout(7.0),
                              headers={"User-Agent": "PageCheck/0.1 (safe public audit)"}) as client:
                with client.stream("GET", url) as response:
                    data = bytearray()
                    for block in response.iter_bytes():
                        data.extend(block)
                        if len(data) > MAX_SINGLE_BYTES:
                            raise ValueError("Resource exceeded maximum size")
                    content = bytes(data)
                    response_headers = {
                        key: response.headers[key]
                        for key in ("content-type", "location") if key in response.headers
                    }
                    status = response.status_code
            with server.lock:
                if server.total_bytes + len(content) > MAX_TOTAL_BYTES:
                    raise ValueError("Audit network budget exhausted")
                server.total_bytes += len(content)
            result = {"ok": True, "status": status, "headers": response_headers,
                      "content": base64.b64encode(content).decode("ascii")}
        except (ValueError, httpx.HTTPError, OSError) as exc:
            result = {"ok": False, "error": type(exc).__name__}
        payload = json.dumps(result, separators=(",", ":")).encode("utf-8") + b"\n"
        self.wfile.write(payload)


@contextmanager
def public_fetch_broker(socket_path: Path) -> Iterator[None]:
    """Serve one isolated scan; caller owns the private 0700 temp directory."""
    server = _BrokerServer(str(socket_path))
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05},
                              daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class PublicBrokerTransport(httpx.BaseTransport):
    """httpx transport that can connect only to the trusted AF_UNIX broker."""

    def __init__(self, socket_path: str):
        if not socket_path.startswith("/") or len(socket_path.encode()) >= 100:
            raise UnsafeDestination("Invalid scanner broker path")
        self.socket_path = socket_path

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.method != "GET":
            raise UnsafeDestination("Only GET is permitted")
        url = validate_public_url(str(request.url))
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(9.0)
            connection.connect(self.socket_path)
            connection.sendall(json.dumps({"method": "GET", "url": url}).encode() + b"\n")
            buffer = bytearray()
            while not buffer.endswith(b"\n"):
                block = connection.recv(min(65536, MAX_MESSAGE_BYTES - len(buffer)))
                if not block or len(buffer) >= MAX_MESSAGE_BYTES:
                    raise UnsafeDestination("Broker response too large or interrupted")
                buffer.extend(block)
        response = json.loads(buffer)
        if response.get("ok") is not True:
            raise UnsafeDestination("Broker rejected an unsafe or excessive request")
        content = base64.b64decode(response["content"], validate=True)
        if len(content) > MAX_SINGLE_BYTES:
            raise UnsafeDestination("Broker response exceeded the resource limit")
        return httpx.Response(status_code=int(response["status"]),
                              headers=response["headers"], content=content, request=request)
