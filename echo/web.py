"""Read-only local web interface for ECHO case metadata."""

from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from echo.catalog import CatalogQuery, CatalogQueryError, build_catalog_record, search_gcov


_STATIC = Path(__file__).with_name("static")
_MAX_CATALOG_REQUEST_BYTES = 8 * 1024


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
            if path == "/api/review":
                review_path = case_path.with_name("case-review.json")
                if not review_path.is_file():
                    review_path = case_path.with_name("qa-review.json")
                self._send_file(review_path, "application/json; charset=utf-8")
                return
            if path == "/api/qa-reports":
                self._send_qa_reports()
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

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if urlsplit(self.path).path != "/api/catalog":
                self.send_error(404)
                return
            if self.headers.get_content_type() != "application/json":
                self._send_json({"error": "Content-Type must be application/json"}, 415)
                return
            try:
                content_length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._send_json({"error": "A valid Content-Length is required"}, 411)
                return
            if content_length < 0 or content_length > _MAX_CATALOG_REQUEST_BYTES:
                self._send_json({"error": "Catalog query body is too large"}, 413)
                return
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json({"error": "Catalog query must be valid JSON"}, 400)
                return
            if not isinstance(payload, dict) or set(payload) != {
                "longitude",
                "latitude",
                "start_date",
                "end_date",
                "maturity",
            }:
                self._send_json({"error": "Catalog query fields are invalid"}, 400)
                return

            query = CatalogQuery(
                longitude=payload["longitude"],
                latitude=payload["latitude"],
                start_date=payload["start_date"],
                end_date=payload["end_date"],
                maturity=payload["maturity"],
                max_results=250,
            )
            try:
                query.validate()
            except CatalogQueryError as exc:
                self._send_json({"error": str(exc)}, 400)
                return
            try:
                features = search_gcov(query)
                record = build_catalog_record(query, features)
            except CatalogQueryError:
                self._send_json(
                    {"error": "ASF catalog search failed; try again later"}, 502
                )
                return
            self._send_json(record, 200)

        def _send_case(self) -> None:
            try:
                body = case_path.read_bytes()
                json.loads(body)
            except (OSError, json.JSONDecodeError):
                self.send_error(503, "Catalog metadata is unavailable or invalid")
                return
            self._send_bytes(body, "application/json; charset=utf-8")

        def _send_qa_reports(self) -> None:
            review_path = case_path.with_name("case-review.json")
            if not review_path.is_file():
                review_path = case_path.with_name("qa-review.json")
            try:
                review = json.loads(review_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                self._send_json({"schema_version": 1, "records": []}, 200)
                return
            except (OSError, json.JSONDecodeError):
                self.send_error(503, "Case review metadata is unavailable or invalid")
                return
            if not isinstance(review, dict) or not isinstance(review.get("products", []), list):
                self.send_error(503, "Case review metadata has an invalid shape")
                return

            scene_ids = {
                item.get("scene_id")
                for item in review.get("products", [])
                if isinstance(item, dict) and isinstance(item.get("scene_id"), str)
            }
            candidate = review.get("candidate_pair", {})
            if isinstance(candidate, dict):
                for position in ("before", "after"):
                    scene = candidate.get(position)
                    if isinstance(scene, dict) and isinstance(scene.get("scene_id"), str):
                        scene_ids.add(scene["scene_id"])

            records = []
            for position in ("before", "after"):
                report_path = case_path.parent / f"qa-report-{position}.json"
                if not report_path.is_file():
                    continue
                try:
                    record = json.loads(report_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    self.send_error(503, "QA report evidence is invalid")
                    return
                if not isinstance(record, dict) or not isinstance(record.get("scene_id"), str):
                    self.send_error(503, "QA report evidence has an invalid shape")
                    return
                if record["scene_id"] in scene_ids:
                    records.append(record)
            self._send_json({"schema_version": 1, "records": records}, 200)

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
            self._send_response(body, content_type, 200)

        def _send_json(self, record: dict[str, object], status: int) -> None:
            body = json.dumps(record, separators=(",", ":")).encode("utf-8")
            self._send_response(body, "application/json; charset=utf-8", status)

        def _send_response(self, body: bytes, content_type: str, status: int) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; script-src 'self'; "
                "img-src 'self' data: https://gibs.earthdata.nasa.gov; connect-src 'self'; object-src 'none'; "
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
