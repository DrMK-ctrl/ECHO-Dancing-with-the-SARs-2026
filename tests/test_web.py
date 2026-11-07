import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from echo.catalog import CatalogQueryError
from echo.web import make_handler


def test_local_interface_serves_static_app_and_read_only_catalog(tmp_path):
    record = {"feature_count": 0, "features": [], "source": {"catalog_only": True}}
    case_file = tmp_path / "catalog.json"
    expected_json = (json.dumps(record) + "\n").encode()
    case_file.write_bytes(expected_json)
    qa_record = {"products": []}
    (tmp_path / "qa-review.json").write_text(json.dumps(qa_record), encoding="utf-8")

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
            assert 'id="drawArea"' in page
            assert "Search GCOV catalog metadata by point or selected map area" in page

        with urlopen(base + "/api/case") as response:
            assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
            assert response.read() == expected_json

        with urlopen(base + "/api/qa") as response:
            assert json.load(response) == qa_record

        with urlopen(base + "/api/review") as response:
            assert json.load(response) == qa_record

        with urlopen(base + "/app.js") as response:
            assert response.headers["Content-Type"].startswith("text/javascript")

        with urlopen(base + "/eesar-systems-horizontal.jpg") as response:
            assert response.headers["Content-Type"] == "image/jpeg"
            assert response.read(2) == b"\xff\xd8"

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


def test_review_endpoint_prefers_case_review_record(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    qa_record = {"review_status": "QA_HOLD"}
    case_record = {"case_id": "nepal-2026-rasuwa", "status": "CANDIDATE_QA_HOLD"}
    (tmp_path / "qa-review.json").write_text(json.dumps(qa_record), encoding="utf-8")
    (tmp_path / "case-review.json").write_text(json.dumps(case_record), encoding="utf-8")

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/review") as response:
            assert json.load(response) == case_record
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_qa_report_endpoint_only_serves_reports_for_reviewed_scenes(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    before_id = "scene-before"
    after_id = "scene-after"
    review = {
        "candidate_pair": {
            "before": {"scene_id": before_id},
            "after": {"scene_id": after_id},
        }
    }
    (tmp_path / "case-review.json").write_text(json.dumps(review), encoding="utf-8")
    before_record = {"scene_id": before_id, "artifact_sha256": "before-hash"}
    stale_after_record = {"scene_id": "unrelated-scene", "artifact_sha256": "stale-hash"}
    for position, record in (("before", before_record), ("after", stale_after_record)):
        (tmp_path / f"qa-report-{position}.json").write_text(
            json.dumps(record), encoding="utf-8"
        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/qa-reports") as response:
            result = json.load(response)
        assert result["schema_version"] == 1
        assert [item["scene_id"] for item in result["records"]] == [before_id]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_catalog_endpoint_returns_bounded_metadata_only_record(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    query_payload = {
        "longitude": 33.5,
        "latitude": -24.5,
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
        "maturity": "BETA",
    }
    feature = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[33, -25], [34, -25], [34, -24], [33, -25]]]},
        "properties": {
            "fileID": "sample",
            "startTime": "2026-01-05T03:42:32Z",
            "stopTime": "2026-01-05T03:42:42Z",
            "collectionName": "NISAR_L2_GCOV_BETA_V1",
            "processingLevel": "GCOV",
            "pathNumber": 114,
            "frameNumber": 165,
            "flightDirection": "ASCENDING",
            "rangeBandwidth": ["40+5"],
            "mainBandPolarization": ["HH", "HV"],
            "productionConfiguration": "PR",
            "crid": "X05010",
            "orbit": 1,
            "sideBandPolarization": ["HH", "HV"],
        },
    }
    seen = {}

    def search(query):
        seen["query"] = query
        return [feature]

    monkeypatch.setattr("echo.web.search_gcov", search)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/catalog",
            data=json.dumps(query_payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            record = json.load(response)
            assert response.status == 200
            assert response.headers["Content-Security-Policy"].startswith(
                "default-src 'self'"
            )
        assert record["source"]["catalog_only"] is True
        assert record["source"]["pixels_downloaded"] is False
        assert record["query"]["data_maturity"] == "BETA"
        assert record["feature_count"] == 1
        assert seen["query"].max_results == 250
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_catalog_endpoint_accepts_bounded_wgs84_area_search(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    payload = {
        "longitude": 33.0,
        "latitude": -24.0,
        "bounds_wgs84": [32.9, -24.1, 33.1, -23.9],
        "start_date": "2026-10-01",
        "end_date": "2026-10-31",
        "maturity": "VALIDATED",
    }
    seen = {}

    def search(query):
        seen["query"] = query
        return []

    monkeypatch.setattr("echo.web.search_gcov", search)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/catalog",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            record = json.load(response)
        assert seen["query"].bounds_wgs84 == payload["bounds_wgs84"]
        assert record["query"]["bounds_wgs84"] == payload["bounds_wgs84"]
        assert record["source"]["pixels_downloaded"] is False
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_catalog_endpoint_rejects_invalid_input_without_calling_asf(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    called = False

    def search(_query):
        nonlocal called
        called = True
        raise AssertionError("invalid query must not reach ASF")

    monkeypatch.setattr("echo.web.search_gcov", search)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        payload = {
            "longitude": float("nan"),
            "latitude": -24.5,
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "maturity": "BETA",
        }
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/catalog",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 400
        assert json.load(error.value)["error"] == "longitude must be a finite number"
        assert not called
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_catalog_endpoint_returns_gateway_error_when_asf_fails(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "echo.web.search_gcov",
        lambda _query: (_ for _ in ()).throw(CatalogQueryError("upstream details")),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        payload = {
            "longitude": 33.5,
            "latitude": -24.5,
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "maturity": "BETA",
        }
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/catalog",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 502
        assert json.load(error.value)["error"] == "ASF catalog search failed; try again later"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
