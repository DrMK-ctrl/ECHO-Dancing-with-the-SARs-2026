import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

from echo.web import make_handler


def test_local_interface_serves_static_app_and_read_only_catalog(tmp_path):
    record = {"feature_count": 0, "features": [], "source": {"catalog_only": True}}
    case_file = tmp_path / "catalog.json"
    expected_json = (json.dumps(record) + "\n").encode()
    case_file.write_bytes(expected_json)

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/") as response:
            page = response.read().decode()
            assert response.status == 200
            assert "ECHO | SAR Investigation" in page
            assert "NO RADAR PIXELS LOADED" in page

        with urlopen(base + "/api/case") as response:
            assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
            assert response.read() == expected_json

        with urlopen(base + "/app.js") as response:
            assert response.headers["Content-Type"].startswith("text/javascript")

        try:
            urlopen(base + "/not-served")
        except HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError("unknown paths must not be served")

        assert case_file.read_bytes() == expected_json
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
