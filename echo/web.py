"""Read-only local web interface for ECHO case metadata."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


_STATIC = Path(__file__).with_name("static")


def make_handler(case_path: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "ECHO/0.1"

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlsplit(self.path).path
            if path == "/api/case":
                self._send_case()
                return
            if path == "/api/qa":
                self._send_file(
                    case_path.with_name("qa-review.json"),
                    "application/json; charset=utf-8",
                )
                return
            if path in {"/", "/index.html"}:
                self._send_file(_STATIC / "index.html", "text/html; charset=utf-8")
                return
            if path == "/styles.css":
                self._send_file(_STATIC / "styles.css", "text/css; charset=utf-8")
                return
            if path == "/app.js":
                self._send_file(_STATIC / "app.js", "text/javascript; charset=utf-8")
                return
            if path == "/eesar-systems-horizontal.jpg":
                self._send_file(_STATIC / "eesar-systems-horizontal.jpg", "image/jpeg")
                return
            self.send_error(404)

        def _send_case(self) -> None:
            try:
                body = case_path.read_bytes()
                json.loads(body)
            except (OSError, json.JSONDecodeError):
                self.send_error(503, "Catalog metadata is unavailable or invalid")
                return
            self._send_bytes(body, "application/json; charset=utf-8")

        def _send_file(self, path: Path, content_type: str) -> None:
            try:
                body = path.read_bytes()
                if content_type.startswith("application/json"):
                    json.loads(body)
                self._send_bytes(body, content_type)
            except OSError:
                self.send_error(500, "Interface asset is missing")
            except json.JSONDecodeError:
                self.send_error(503, "JSON evidence is invalid")

        def _send_bytes(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; script-src 'self'; "
                "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'",
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            logging.info("%s - %s", self.address_string(), fmt % args)

    return Handler


def serve(*, host: str, port: int, case_file: Path) -> int:
    case_path = case_file.expanduser().resolve()
    if not case_path.is_file():
        print(f"echo: catalog file not found: {case_path}")
        return 2
    try:
        server = ThreadingHTTPServer((host, port), make_handler(case_path))
    except OSError as exc:
        print(f"echo: cannot start local interface: {exc}")
        return 2
    print(f"ECHO investigation interface: http://{host}:{server.server_port}/")
    print(f"Catalog source: {case_path}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
