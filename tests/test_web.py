import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from echo.catalog import CatalogQueryError
from echo.qa import parse_qa_summary
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
        assert seen["query"].max_results == 1000
        assert record["source"]["result_limit"] == 1000
        assert record["source"]["pages_retrieved"] == 1
        assert record["source"]["potentially_truncated"] is False
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


def test_gunw_catalog_endpoint_returns_allowlisted_metadata_only_features(
    tmp_path, monkeypatch
):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    payload = {
        "longitude": 28.99,
        "latitude": 41.105,
        "start_date": "2026-10-01",
        "end_date": "2026-11-07",
        "maturity": "PROVISIONAL",
    }
    scene_id = (
        "NISAR_L2_PR_GUNW_032_137_D_068_033_2000_SH_"
        "20261009T170432_20261009T170506_20261021T170432_20261021T170507_"
        "P05023_N_F_J_001"
    )
    feature = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[28, 41], [29, 41], [29, 42], [28, 41]]]},
        "properties": {
            "fileID": scene_id,
            "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GUNW_PROVISIONAL_V1/{scene_id}/{scene_id}.h5",
            "processingLevel": "GUNW",
            "collectionName": "NISAR_L2_GUNW_PROVISIONAL_V1",
            "startTime": "2026-10-09T17:04:32Z",
            "stopTime": "2026-10-21T17:05:07Z",
            "secret_or_unneeded_provider_field": "must not be returned",
        },
    }
    query_seen = {}

    def search(query):
        query_seen["query"] = query
        return [feature]

    monkeypatch.setattr("echo.web.search_gunw", search)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/gunw-catalog",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            record = json.load(response)
        assert query_seen["query"].max_results == 100
        assert record["record_type"] == "ECHO_GUNW_CATALOG_QUERY"
        assert record["source"]["metadata_only"] is True
        assert record["source"]["dataset"] == "NISAR L2 GUNW"
        assert record["source"]["potentially_truncated"] is False
        assert record["features"][0]["properties"]["fileID"] == scene_id
        assert "secret_or_unneeded_provider_field" not in record["features"][0]["properties"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_gunw_catalog_endpoint_rejects_beta_before_search(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "echo.web.search_gunw", lambda query: pytest.fail("search must not run")
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        payload = {
            "longitude": 28.99,
            "latitude": 41.105,
            "start_date": "2026-10-01",
            "end_date": "2026-11-07",
            "maturity": "BETA",
        }
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/gunw-catalog",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 400
        assert json.load(error.value)["error"] == "GUNW maturity must be PROVISIONAL or VALIDATED"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_gcov_preview_endpoint_returns_source_linked_measurement_record(
    tmp_path, monkeypatch
):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    scene_id = (
        "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_"
        "20260819T233953_P05023_N_F_J_001"
    )
    feature = {
        "properties": {
            "fileID": scene_id,
            "url": (
                "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
                f"NISAR_L2_GCOV_PROVISIONAL_V1/{scene_id}/{scene_id}.h5"
            ),
            "processingLevel": "GCOV",
            "collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1",
            "startTime": "2026-08-19T23:39:18Z",
        }
    }
    bounds = [85.545, 28.295, 85.555, 28.305]
    expected = {
        "record_type": "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW",
        "source": {"scene_id": scene_id, "provider_qa_status": "FAIL"},
    }
    seen = {}

    def build(feature_arg, **kwargs):
        seen["feature"] = feature_arg
        seen["kwargs"] = kwargs
        return expected

    monkeypatch.setattr("echo.web.build_gcov_preview", build)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/gcov-preview",
            data=json.dumps(
                {
                    "feature": feature,
                    "bounds_wgs84": bounds,
                    "frequency": "A",
                    "layer": "HHHH",
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            record = json.load(response)
        assert response.status == 200
        assert record == expected
        assert seen["feature"] == feature
        assert seen["kwargs"] == {
            "bounds_wgs84": bounds,
            "frequency": "A",
            "layer": "HHHH",
        }
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_on_demand_qa_summary_endpoint_returns_hashed_provider_record(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    scene_id = "NISAR_L2_PR_GCOV_028_048_D_074_4005_DHDH_A_20260816T125812_20260816T125846_P05023_N_F_J_001"
    collection = "NISAR_L2_GCOV_PROVISIONAL_V1"
    product_uri = (
        f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/"
        f"{scene_id}/{scene_id}.h5"
    )
    feature = {
        "properties": {
            "fileID": scene_id,
            "url": product_uri,
            "processingLevel": "GCOV",
            "collectionName": collection,
        }
    }
    content = (
        b"Tool,Check,Result,Threshold,Actual,Notes\n"
        b"QA,Able to open input NISAR file?,PASS,,,\n"
        b"QA,Coordinate grid metadata cubes are valid?,PASS,,,\n"
        b"QA,Calibration information LUTs are valid?,PASS,,,\n"
        b"QA,Passes all `identification` group checks?,PASS,,,\n"
        b"QA,QA completed with no exceptions?,PASS,,,\n"
    )
    seen = {}

    def retrieve(received_feature, *, product_metadata):
        seen["feature"] = received_feature
        seen["product_metadata"] = product_metadata
        return parse_qa_summary(
            content,
            scene_id=scene_id,
            artifact_uri=product_uri.rsplit("/", 1)[0] + f"/{scene_id}_QA_SUMMARY.csv",
            product_metadata=product_metadata,
            retrieval={"provider": "ASF", "method": "test fixture", "network_retrieval": True},
        )

    monkeypatch.setattr("echo.web.read_qa_summary", retrieve)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/qa-summary",
            data=json.dumps({"feature": feature}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            record = json.load(response)
            assert response.status == 200
        assert record["scene_id"] == scene_id
        assert record["artifact_sha256"]
        assert record["evidence"]["status"] == "PASS"
        assert record["evidence"]["check_details"][0]["result"] == "PASS"
        assert record["retrieval"]["network_retrieval"] is True
        assert seen["feature"] == feature
        assert seen["product_metadata"] == {}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_on_demand_qa_summary_endpoint_rejects_untrusted_product_host(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    feature = {
        "properties": {
            "fileID": "NISAR_L2_PR_GCOV_028_048_D_074_4005_DHDH_A_20260816T125812_20260816T125846_P05023_N_F_J_001",
            "url": "https://example.com/product.h5",
            "processingLevel": "GCOV",
            "collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1",
        }
    }
    monkeypatch.setattr(
        "echo.web.read_qa_summary",
        lambda *args, **kwargs: pytest.fail("untrusted host must fail before retrieval"),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/qa-summary",
            data=json.dumps({"feature": feature}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 400
        assert "plain ASF NISAR HTTPS" in error.value.read().decode()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_on_demand_qa_summary_endpoint_enforces_request_body_limit(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "echo.web.read_qa_summary",
        lambda *args, **kwargs: pytest.fail("oversized request must fail before retrieval"),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/qa-summary",
            data=b" " * (4 * 1024 + 1),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 413
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_qa_evidence_export_returns_source_linked_attachment(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    scene_id = "NISAR_L2_PR_GCOV_028_048_D_074_4005_DHDH_A_20260816T125812_20260816T125846_P05023_N_F_J_001"
    collection = "NISAR_L2_GCOV_PROVISIONAL_V1"
    product_uri = (
        f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/"
        f"{scene_id}/{scene_id}.h5"
    )
    summary_uri = product_uri.rsplit("/", 1)[0] + f"/{scene_id}_QA_SUMMARY.csv"
    digest = "a" * 64
    record = {
        "record_type": "ECHO_PROVIDER_QA_INSPECTION",
        "record_version": 1,
        "exported_at_utc": "2026-11-07T00:00:00+00:00",
        "source_catalog": {
            "provider": "Alaska Satellite Facility DAAC",
            "query": {"data_maturity": "PROVISIONAL"},
            "feature": {
                "properties": {
                    "fileID": scene_id,
                    "url": product_uri,
                    "processingLevel": "GCOV",
                    "collectionName": collection,
                }
            },
        },
        "provider_qa_summary": {
            "scene_id": scene_id,
            "artifact_uri": summary_uri,
            "artifact_sha256": digest,
            "evidence": {
                "scene_id": scene_id,
                "artifact_uri": summary_uri,
                "artifact_sha256": digest,
                "status": "FAIL",
            },
        },
        "interpretation_limits": ["QA status does not establish measurement suitability."],
    }
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/qa-evidence-export",
            data=urlencode({"evidence_record": json.dumps(record)}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urlopen(request) as response:
            exported = json.load(response)
            assert response.status == 200
            assert response.headers["Content-Disposition"] == (
                f'attachment; filename="{scene_id}_provider-qa-evidence.json"'
            )
        assert exported["source_catalog"]["feature"]["properties"]["fileID"] == scene_id
        assert exported["provider_qa_summary"]["evidence"]["status"] == "FAIL"
        bad_record = json.loads(json.dumps(record))
        bad_record["provider_qa_summary"]["scene_id"] = "NISAR_OTHER_SCENE"
        invalid_request = Request(
            f"http://127.0.0.1:{server.server_port}/api/qa-evidence-export",
            data=urlencode({"evidence_record": json.dumps(bad_record)}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(invalid_request)
        assert error.value.code == 400
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


def test_gcov_pair_analysis_endpoint_connects_bounded_request(tmp_path, monkeypatch):
    import echo.web as web

    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    seen = {}
    expected = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "status": "QA_HELD",
        "measurement": None,
    }

    def build(before, after, **kwargs):
        seen.update({"before": before, "after": after, **kwargs})
        return expected

    monkeypatch.setattr(web, "build_gcov_pair_analysis", build)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    before = {
        "properties": {
            "fileID": "before",
            "url": "https://example.test/before",
            "processingLevel": "GCOV",
            "collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1",
        }
    }
    after = {
        "properties": {
            "fileID": "after",
            "url": "https://example.test/after",
            "processingLevel": "GCOV",
            "collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1",
        }
    }
    payload = {
        "before": before,
        "after": after,
        "bounds_wgs84": [85.5, 28.2, 85.6, 28.3],
        "frequency": "A",
        "layer": "HHHH",
    }
    request = Request(
        f"http://127.0.0.1:{server.server_port}/api/gcov-pair-analysis",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request) as response:
            assert response.status == 200
            assert json.load(response) == expected
        assert seen == {
            "before": before,
            "after": after,
            "bounds_wgs84": [85.5, 28.2, 85.6, 28.3],
            "frequency": "A",
            "layer": "HHHH",
        }
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
