from hashlib import sha256
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from echo.catalog import CatalogQueryError
from echo.qa import parse_qa_summary
from echo.investigation_draft import assess_investigation_draft, build_investigation_draft
import echo.web as web_module
from echo.opera_rtc_quality import build_opera_rtc_pair_quality_review
from echo.web import _validate_assessment_artifacts, _validate_assessment_record, make_handler


def test_active_t024_assessment_revalidates_soil_moisture_source_chain():
    root = Path(__file__).parents[1]
    case = json.loads((root / "data/cases/rio-grande-do-sul-t024-2024/investigation.json").read_text())
    assessment_path = root / case["evidence_records"]["cross_sensor_assessment"]
    assessment = json.loads(assessment_path.read_text())
    evidence_ids = _validate_assessment_record(assessment, root)
    assert "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN" in evidence_ids
    assert "ISMN-SOIL-MOISTURE-STATION-COVERAGE" in evidence_ids


def test_local_interface_serves_static_app_and_read_only_catalog(tmp_path):
    record = {"feature_count": 0, "features": [], "source": {"catalog_only": True}}
    case_file = tmp_path / "catalog.json"
    expected_json = (json.dumps(record) + "\n").encode()
    case_file.write_bytes(expected_json)
    qa_record = {"products": []}
    (tmp_path / "qa-review.json").write_text(json.dumps(qa_record), encoding="utf-8")
    context_record = {"record_type": "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON", "map_samples": []}
    (tmp_path / "context.json").write_text(json.dumps(context_record), encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"dswx_context": "context.json"},
    }), encoding="utf-8")

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
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
            assert 'id="caseSelector"' in page
            assert 'id="openCaseInvestigation" hidden' in page
            assert '<dialog class="investigation-dialog" id="investigationDialog"' in page
            assert 'id="closeInvestigationDialog"' in page
            assert 'id="investigationDraftDialog"' in page
            assert 'id="draftFollowupTarget"' in page
            assert "Search GCOV catalog metadata by point or selected map area" in page
            assert 'id="catalogFollowupContext"' in page
            assert 'id="openBhoonidhi"' in page
            assert 'id="bhoonidhiDialog"' in page
            assert 'id="bhoonidhiTimelineTrack"' in page
            assert 'id="bhoonidhiInspector"' in page
            assert "provider QA are not retrieved by this search" in page
            assert 'id="qaEvidenceStage"' in page
            assert '<script src="/investigation.js" defer></script>' in page

        with urlopen(base + "/app.js") as response:
            script = response.read().decode()
            assert response.status == 200
            assert "renderAcquisitionChronology(timelineRows,offsetText)" in script
            assert '"/api/bhoonidhi-catalog"' in script
            assert "function renderBhoonidhiInspector()" in script
            assert "function validBhoonidhiRings(feature)" in script
            assert '"/api/investigation-draft/attach-catalog-screen"' in script
            assert '"/api/investigation-draft/attach-catalog-failure"' in script
            assert "FAILED CATALOG ATTEMPTS" in script
            assert '"/api/investigation-draft/attach-provider-qa"' in script
            assert 'startSingleObservationInvestigationDraft' in script
            assert "One real NISAR GCOV acquisition" in script
            assert "ECHO retrieved the canonical ASF QA CSV" in script

        with urlopen(base + "/api/case") as response:
            assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
            assert response.read() == expected_json

        with urlopen(base + "/api/qa") as response:
            assert json.load(response) == qa_record

        with urlopen(base + "/api/review") as response:
            assert json.load(response) == qa_record

        with urlopen(base + "/app.js") as response:
            assert response.headers["Content-Type"].startswith("text/javascript")

        with urlopen(base + "/investigation.js") as response:
            investigation_js = response.read()
            assert response.headers["Content-Type"].startswith("text/javascript")
            assert b"window.renderAcquisitionChronology" in investigation_js
            assert b"window.renderInvestigationReasoning" in investigation_js
            assert b"EVIDENCE COVERAGE" in investigation_js
            assert b"not negative evidence" in investigation_js

        with urlopen(base + "/context.css") as response:
            assert response.headers["Content-Type"].startswith("text/css")
            context_css = response.read()
            assert b".dswx-context-cell" in context_css
            assert b".investigation-dialog-toolbar{position:sticky" in context_css
            assert b".hypothesis-evidence-coverage" in context_css

        with urlopen(base + "/api/dswx-context") as response:
            context = json.load(response)
            assert context["record_type"] == "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON"
            assert context == context_record

        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/opera-temporal-series")
        assert error.value.code == 404
        error.value.close()

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


def test_bhoonidhi_catalog_api_is_loopback_same_origin_and_keeps_credentials_transient(
    tmp_path, monkeypatch, caplog
):
    case_file = tmp_path / "catalog.json"
    case_file.write_text(json.dumps({"feature_count": 0, "features": [], "source": {}}), encoding="utf-8")
    seen = {}

    def fake_authenticate(user_id, password):
        seen["credentials"] = (user_id, password)
        return "temporary-access-token"

    def fake_search(token, **kwargs):
        seen["search"] = (token, kwargs)
        return {
            "provider": "ISRO NRSC Bhoonidhi",
            "instrument": "S-SAR",
            "feature_count": 1,
            "feature_collection": {
                "type": "FeatureCollection",
                "features": [{"type": "Feature", "id": "item-1", "geometry": None, "properties": {}}],
            },
            "pagination_complete": True,
        }

    monkeypatch.setattr(web_module, "authenticate", fake_authenticate)
    monkeypatch.setattr(web_module, "search_ssar_gcov", fake_search)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    payload = {
        "user_id": "local-test-user",
        "password": "never-log-this-password",
        "bounds_wgs84": [33.0, -25.0, 34.0, -24.0],
        "start": "2026-07-01T00:00:00Z",
        "end": "2026-07-02T00:00:00Z",
        "limit": 100,
        "max_pages": 10,
    }
    request = Request(
        base + "/api/bhoonidhi-catalog",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Origin": base},
        method="POST",
    )
    try:
        with urlopen(request) as response:
            record = json.load(response)
            assert response.status == 200
        assert record["feature_count"] == 1
        assert "temporary-access-token" not in json.dumps(record)
        assert seen["credentials"] == ("local-test-user", "never-log-this-password")
        assert seen["search"][0] == "temporary-access-token"
        assert seen["search"][1]["bounds_wgs84"] == [33.0, -25.0, 34.0, -24.0]
        assert "never-log-this-password" not in caplog.text
    finally:
        server.shutdown()
        worker.join(timeout=2)
        server.server_close()


@pytest.mark.parametrize("origin", [None, "https://attacker.invalid", "http://127.0.0.1:9"])
def test_bhoonidhi_catalog_api_rejects_missing_or_cross_origin_requests(tmp_path, monkeypatch, origin):
    case_file = tmp_path / "catalog.json"
    case_file.write_text(json.dumps({"feature_count": 0, "features": [], "source": {}}), encoding="utf-8")
    monkeypatch.setattr(web_module, "authenticate", lambda *_args: pytest.fail("must reject before authentication"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    headers = {"Content-Type": "application/json"}
    if origin is not None:
        headers["Origin"] = origin
    request = Request(
        base + "/api/bhoonidhi-catalog",
        data=b"{}",
        headers=headers,
        method="POST",
    )
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 403
        error.value.close()
    finally:
        server.shutdown()
        worker.join(timeout=2)
        server.server_close()


def test_opera_temporal_series_endpoint_rejects_manifest_checksum_mismatch(tmp_path):
    from urllib.request import urlopen

    case_dir = tmp_path / "data" / "cases" / "temporal-case"
    case_dir.mkdir(parents=True)
    catalog = case_dir / "catalog.json"
    catalog.write_text(json.dumps({"feature_count": 0, "features": []}), encoding="utf-8")
    (case_dir / "case-review.json").write_text(json.dumps({"case_id": "temporal-case"}), encoding="utf-8")
    record = {
        "record_type": "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS",
        "status": "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES",
        "observations": [{}, {}, {}],
        "adjacent_intervals": [{}, {}],
    }
    payload = json.dumps(record).encode()
    record_path = tmp_path / "series.json"
    record_path.write_bytes(payload)
    (case_dir / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"opera_temporal_series": "series.json"},
        "evidence_sha256": {"opera_temporal_series": "0" * 64},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(catalog, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with pytest.raises(HTTPError) as error:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/opera-temporal-series")
        assert error.value.code == 409
        assert json.load(error.value)["error"].startswith("OPERA temporal-series record failed")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_local_investigation_drafts_can_be_saved_listed_and_reopened(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text(json.dumps({"feature_count": 0, "features": []}), encoding="utf-8")
    store_dir = tmp_path / "private-data" / "drafts"
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path, draft_store_dir=store_dir))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
        "measurement": None, "manifest": None,
    }
    hypotheses = [
        {"statement": f"Mechanism {n}", "scope_limit": "selected AOI", "expected_observation": f"expected {n}", "would_weaken_if": f"absent {n}", "required_evidence": f"independent evidence {n}"}
        for n in (1, 2)
    ]
    next_observation = {
        "target_hypothesis_id": "H1", "action": "Retrieve independent observations for the same area and dates.",
        "discriminating_question": "Does independent evidence distinguish this explanation?",
        "possible_interpretation": "A matching pattern is consistent with the explanation within scope.",
        "priority_reason": "This tests one alternative with an independent source.",
        "expected_observation": "Quality-accepted observations show the registered pattern.",
        "would_weaken_if": "Suitable observations show no registered pattern.",
        "inconclusive_if": "Timing, quality, or coverage prevents interpretation.",
        "acceptance_gates": "Independent source\nSuitable timing\nAdequate support",
        "interpretation_limit": "This does not validate the held SAR measurement or establish cause.",
    }
    draft = build_investigation_draft(
        source,
        question="Which explanation is consistent with this radar response?",
        hypotheses=hypotheses,
        next_observation=next_observation,
    )
    try:
        request = Request(base + "/api/investigation-drafts", data=json.dumps({"draft": draft}).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            saved = json.load(response)
            assert response.status == 201
            assert saved["record_type"] == "ECHO_LOCAL_INVESTIGATION_DRAFT_SAVE"
        with urlopen(base + "/api/investigation-drafts") as response:
            listing = json.load(response)
            assert response.status == 200
            assert listing["records"][0]["integrity"] == "VALID"
            assert listing["records"][0]["draft_id"] == saved["draft_id"]
        with urlopen(base + f"/api/investigation-drafts/{saved['draft_id']}") as response:
            restored = json.load(response)
            assert response.status == 200
            assert restored == draft

        assessed = assess_investigation_draft(draft, [{
            "hypothesis_id": "H1",
            "evidence_id": draft["evidence_artifacts"][0]["evidence_id"],
            "relationship": "DOES_NOT_DISTINGUISH",
            "evidence_fit": "UNKNOWN",
            "rationale": "The QA-held pair cannot distinguish this explanation.",
            "review_basis": "Inspected the retained pair record and provider QA status.",
            "limitations": "The source has no accepted temporal measurement for interpretation.",
        }])
        assessed_save_request = Request(
            base + "/api/investigation-drafts",
            data=json.dumps({"draft": assessed}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(assessed_save_request) as response:
            assessed_saved = json.load(response)
        revised_plan = {
            **next_observation,
            "target_hypothesis_id": "H2",
            "action": "Retrieve independent soil-moisture observations across both acquisition dates.",
        }
        revise_request = Request(
            base + "/api/investigation-drafts/revise",
            data=json.dumps({
                "parent_draft_id": assessed_saved["draft_id"],
                "next_observation": revised_plan,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(revise_request) as response:
            revised = json.load(response)
            assert response.status == 201
        assert revised["status"] == "DRAFT_NOT_ASSESSED"
        assert revised["revision"]["parent_draft_sha256"] == assessed_saved["draft_id"]
        assert revised["revision"]["parent_assessment_sha256"] == assessed["analyst_assessment"]["assessment_sha256"]
        assert revised["follow_up_evidence"][0]["target_hypothesis_ids"] == ["H2"]
        assert all(item["state"] == "NOT_EVALUATED" for item in revised["hypotheses"])
        revised_save_request = Request(
            base + "/api/investigation-drafts",
            data=json.dumps({"draft": revised}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(revised_save_request) as response:
            revised_saved = json.load(response)
            assert response.status == 201
        with urlopen(base + f"/api/investigation-drafts/{revised_saved['draft_id']}") as response:
            assert json.load(response) == revised

        second_assessed = assess_investigation_draft(revised, [{
            "hypothesis_id": "H2",
            "evidence_id": revised["evidence_artifacts"][0]["evidence_id"],
            "relationship": "DOES_NOT_DISTINGUISH",
            "evidence_fit": "UNKNOWN",
            "rationale": "The retained pair still cannot distinguish the second explanation.",
            "review_basis": "Inspected the retained source and its unchanged QA disposition.",
            "limitations": "This assessment round contains no newly retrieved measurement.",
        }])
        second_parent_save_request = Request(
            base + "/api/investigation-drafts",
            data=json.dumps({"draft": second_assessed}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(second_parent_save_request) as response:
            second_parent_saved = json.load(response)
        second_plan = {
            **next_observation,
            "target_hypothesis_id": "H1",
            "action": "Retrieve a suitable independent observation for the water mechanism.",
        }
        second_revise_request = Request(
            base + "/api/investigation-drafts/revise",
            data=json.dumps({
                "parent_draft_id": second_parent_saved["draft_id"],
                "next_observation": second_plan,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(second_revise_request) as response:
            second_revision = json.load(response)
            assert response.status == 201
        assert second_revision["revision"]["revision_number"] == 2
        assert second_revision["revision"]["parent_draft_sha256"] == second_parent_saved["draft_id"]
        second_revision_save_request = Request(
            base + "/api/investigation-drafts",
            data=json.dumps({"draft": second_revision}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(second_revision_save_request) as response:
            second_revision_saved = json.load(response)
        with urlopen(base + f"/api/investigation-drafts/{second_revision_saved['draft_id']}") as response:
            assert json.load(response) == second_revision
        restore_revision_request = Request(
            base + "/api/investigation-draft/restore",
            data=json.dumps({"draft": revised}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(restore_revision_request) as response:
            assert json.load(response) == revised
        broken_revision = json.loads(json.dumps(revised))
        broken_revision["revision"]["parent_draft_sha256"] = "0" * 64
        broken_restore_request = Request(
            base + "/api/investigation-draft/restore",
            data=json.dumps({"draft": broken_revision}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(broken_restore_request)
        assert error.value.code == 409
        with urlopen(base + f"/api/investigation-drafts/{assessed_saved['draft_id']}") as response:
            assert json.load(response) == assessed

        changed = dict(draft)
        changed["status"] = "FAKE_VALIDATED_FINDING"
        request = Request(base + "/api/investigation-drafts", data=json.dumps({"draft": changed}).encode(), headers={"Content-Type": "application/json"})
        try:
            urlopen(request)
        except HTTPError as error:
            assert error.code == 422
        else:
            raise AssertionError("invalid investigation draft must not be persisted")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)

    restarted = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path, draft_store_dir=store_dir))
    restarted_worker = Thread(target=restarted.serve_forever, daemon=True)
    restarted_worker.start()
    try:
        with urlopen(f"http://127.0.0.1:{restarted.server_port}/api/investigation-drafts/{saved['draft_id']}") as response:
            reopened = json.load(response)
            assert response.status == 200
            assert reopened == draft
    finally:
        restarted.shutdown()
        restarted.server_close()
        restarted_worker.join(timeout=2)


def test_investigation_draft_api_preserves_source_and_rejects_unsupported_records(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text(json.dumps({"feature_count": 0, "features": []}), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}/api/investigation-draft"
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
        "measurement": None,
        "manifest": None,
    }
    hypotheses = [
        {"statement": "Mechanism A", "scope_limit": "Selected AOI", "expected_observation": "Signal A", "would_weaken_if": "No signal A", "required_evidence": "Independent measurement A"},
        {"statement": "Mechanism B", "scope_limit": "Selected AOI", "expected_observation": "Signal B", "would_weaken_if": "No signal B", "required_evidence": "Independent measurement B"},
    ]
    next_observation = {
        "target_hypothesis_id": "H1",
        "action": "Retrieve independent water observations at the SAR dates.",
        "discriminating_question": "Does independent evidence show a water transition in this AOI?",
        "possible_interpretation": "A transition is consistent with the authored hypothesis within scope.",
        "priority_reason": "It directly tests one named alternative with independent observations.",
        "expected_observation": "Quality-accepted water observations overlap the reported change.",
        "would_weaken_if": "Suitable quality-accepted observations show no water transition.",
        "inconclusive_if": "Coverage, timing, or QA prevents the comparison.",
        "acceptance_gates": "Independent source\nSuitable timing\nAdequate AOI support",
        "interpretation_limit": "Does not establish cause or validate a held SAR product.",
    }
    try:
        payload = {"source_record": source, "question": "What remains uncertain about this response?", "hypotheses": hypotheses, "next_observation": next_observation}
        request = Request(base, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            draft = json.load(response)
        artifact = draft["evidence_artifacts"][0]
        assert draft["status"] == "DRAFT_NOT_ASSESSED"
        assert artifact["role"] == "SAR_PAIR_HELD_AT_PROVIDER_QA"
        assert draft["source_records"][artifact["evidence_id"]] == source
        assert all(item["state"] == "NOT_EVALUATED" and not item["evidence_refs"] for item in draft["hypotheses"])
        assert draft["follow_up_evidence"][0]["test_design"]["hypothesis_under_test_id"] == "H1"

        scene_id = "NISAR_L2_PR_GCOV_028_048_D_074_4005_DHDH_A_20260816T125812_20260816T125846_P05023_N_F_J_001"
        collection = "NISAR_L2_GCOV_PROVISIONAL_V1"
        product_url = f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/{scene_id}/{scene_id}.h5"
        feature = {"id": scene_id, "properties": {"fileID": scene_id, "sceneName": scene_id, "processingLevel": "GCOV", "collectionName": collection, "url": product_url}, "geometry": None}
        catalog_record = {
            "schema_version": 1,
            "queried_at_utc": "2026-11-08T12:00:00+00:00",
            "source": {
                "provider": "Alaska Satellite Facility DAAC", "catalog_only": True,
                "pixels_downloaded": False, "returned_feature_count": 1, "potentially_truncated": False,
            },
            "query": {
                "dataset": "NISAR", "processing_level": "GCOV", "data_maturity": "PROVISIONAL",
                "longitude": -51.2, "latitude": -30.1, "bounds_wgs84": None,
                "start_date": "2026-11-01", "end_date": "2026-11-08",
            },
            "feature_count": 1, "features": [feature],
        }
        catalog_attach = Request(
            base + "/attach-catalog-screen",
            data=json.dumps({"draft": draft, "catalog_record": catalog_record}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(catalog_attach) as response:
            catalog_staged = json.load(response)
        catalog_artifact = catalog_staged["evidence_artifacts"][1]
        assert catalog_artifact["role"] == "CATALOG_AVAILABILITY_METADATA_ONLY"
        assert catalog_staged["source_records"][catalog_artifact["evidence_id"]]["catalog_record"] == catalog_record
        assert catalog_staged["follow_up_evidence"][0]["availability_state"] == "CANDIDATE_RETRIEVED_UNASSESSED"
        assert catalog_staged["follow_up_evidence"][0]["evidence_refs"] == [catalog_artifact["evidence_id"]]
        assert all(not item["evidence_refs"] for item in catalog_staged["hypotheses"])

        failure_record = {
            "schema_version": 1, "observer": "ECHO", "provider": "ASF", "service": "ASF_CMR_GCOV_CATALOG",
            "outcome": "REQUEST_FAILED_NO_RESULT", "failure_code": "CATALOG_REQUEST_FAILED",
            "retryable": True, "attempted_at_utc": "2026-11-08T12:00:00+00:00",
            "completed_at_utc": "2026-11-08T12:00:30+00:00",
            "query": {
                "dataset": "NISAR", "processing_level": "GCOV", "data_maturity": "PROVISIONAL",
                "longitude": -51.2, "latitude": -30.1, "bounds_wgs84": None,
                "start_date": "2026-11-01", "end_date": "2026-11-08", "result_limit": 1000,
            },
        }
        failed_attach = Request(
            base + "/attach-catalog-failure",
            data=json.dumps({"draft": draft, "failure_record": failure_record}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(failed_attach) as response:
            failed_draft = json.load(response)
        assert failed_draft["follow_up_evidence"][0]["availability_state"] == "SEARCH_FAILED_RETRYABLE"
        assert failed_draft["follow_up_evidence"][0]["evidence_refs"] == []
        assert len(failed_draft["follow_up_evidence"][0]["catalog_search_attempts"]) == 1
        retry_attach = Request(
            base + "/attach-catalog-screen",
            data=json.dumps({"draft": failed_draft, "catalog_record": catalog_record}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(retry_attach) as response:
            retried_draft = json.load(response)
        assert retried_draft["follow_up_evidence"][0]["availability_state"] == "CANDIDATE_RETRIEVED_UNASSESSED"
        assert len(retried_draft["follow_up_evidence"][0]["catalog_search_attempts"]) == 1
        assert all(item["state"] == "NOT_EVALUATED" and not item["evidence_refs"] for item in retried_draft["hypotheses"])

        qa_csv = (
            b"Tool,Check,Result,Threshold,Actual,Notes\n"
            b"QA,Able to open input NISAR file?,PASS,,,\n"
            b"QA,Coordinate grid metadata cubes are valid?,PASS,,,\n"
            b"QA,Calibration information LUTs are valid?,PASS,,,\n"
            b"QA,Passes all `identification` group checks?,FAIL,,,\n"
            b"QA,QA completed with no exceptions?,PASS,,,\n"
        )
        qa_retrieval = parse_qa_summary(
            qa_csv,
            scene_id=scene_id,
            artifact_uri=product_url.rsplit("/", 1)[0] + f"/{scene_id}_QA_SUMMARY.csv",
            product_metadata={},
            retrieval={"provider": "Alaska Satellite Facility DAAC", "authentication": "Earthdata Login via local netrc", "method": "HTTPS byte-range streaming", "network_retrieval": True, "fsspec_range_bytes_requested": 115},
        )
        qa_fetches = []
        def retrieve_qa(received_feature, *, product_metadata):
            qa_fetches.append((received_feature, product_metadata))
            return qa_retrieval
        monkeypatch.setattr("echo.web.read_qa_summary", retrieve_qa)
        invalid_scene_attach = Request(
            base + "/attach-provider-qa",
            data=json.dumps({
                "draft": catalog_staged,
                "catalog_availability_evidence_id": catalog_artifact["evidence_id"],
                "scene_id": "NISAR_OTHER_CATALOG_SCENE",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as invalid_scene_response:
            urlopen(invalid_scene_attach)
        assert invalid_scene_response.value.code == 422
        assert not qa_fetches
        provider_qa_attach = Request(
            base + "/attach-provider-qa",
            data=json.dumps({
                "draft": catalog_staged,
                "catalog_availability_evidence_id": catalog_artifact["evidence_id"],
                "scene_id": scene_id,
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(provider_qa_attach) as response:
            qa_staged = json.load(response)
        qa_artifact = qa_staged["evidence_artifacts"][2]
        assert qa_artifact["role"] == "FOLLOWUP_PROVIDER_QA_METADATA_ONLY"
        qa_source = qa_staged["source_records"][qa_artifact["evidence_id"]]
        assert qa_source["scene_id"] == scene_id
        assert qa_source["provider_response_verification"] == "ASF_QA_CSV_RETRIEVED_BY_ECHO_AT_ATTACHMENT"
        assert qa_source["provider_qa_record"]["provider_qa_summary"]["evidence"]["status"] == "FAIL"
        assert qa_fetches == [(feature, {})]
        assert qa_staged["follow_up_evidence"][0]["availability_state"] == "CANDIDATE_RETRIEVED_UNASSESSED"
        assert qa_staged["follow_up_evidence"][0]["evidence_refs"] == [catalog_artifact["evidence_id"], qa_artifact["evidence_id"]]
        assert all(not item["evidence_refs"] for item in qa_staged["hypotheses"])

        source_record = {"record_type": "NASA_CONTEXT_RECORD", "status": "QUALITY_LIMITED", "provider": "NASA"}
        attach_request = Request(
            base + "/attach-source",
            data=json.dumps({"draft": qa_staged, "source_record": source_record}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(attach_request) as response:
            updated = json.load(response)
        staged = updated["evidence_artifacts"][3]
        assert staged["role"] == "USER_SUPPLIED_SOURCE_NOT_REVIEWED"
        assert staged["status"] == "QUALITY_LIMITED"
        assert all(not hypothesis["evidence_refs"] for hypothesis in updated["hypotheses"])

        screen_request = Request(
            base + "/screen-followup",
            data=json.dumps({
                "draft": updated,
                "evidence_id": staged["evidence_id"],
                "gate_results": [
                    {"gate": gate, "result": "UNKNOWN" if index == 0 else "MET"}
                    for index, gate in enumerate(next_observation["acceptance_gates"].splitlines())
                ],
                "review_basis": "The attached context lacks a verified source-quality indicator.",
                "limitations": "This analyst screen does not authenticate the record or its source.",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(screen_request) as response:
            screened = json.load(response)
        assert screened["follow_up_evidence"][0]["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
        assert screened["follow_up_evidence"][0]["evidence_refs"] == [staged["evidence_id"]]
        assert all(item["state"] == "NOT_EVALUATED" for item in screened["hypotheses"])

        reviewed_pair = {
            "hypothesis_id": "H1",
            "evidence_id": artifact["evidence_id"],
            "relationship": "LIMITS_INTERPRETATION",
            "evidence_fit": "UNKNOWN",
            "rationale": "The pair remains held and has no accepted measurement arrays.",
            "review_basis": "I inspected the retained provider QA and analysis gate records.",
            "limitations": "This record cannot establish whether the hypothesized process occurred.",
        }
        assessment_request = Request(
            base + "/assess",
            data=json.dumps({"draft": screened, "assessments": [reviewed_pair]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(assessment_request) as response:
            assessed = json.load(response)
        assert assessed["status"] == "DRAFT_ANALYST_ASSESSED_UNVERIFIED"
        assert assessed["hypotheses"][0]["state"] == "UNRESOLVED"
        assert assessed["follow_up_evidence"][0]["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
        assert assessed["source_records"][artifact["evidence_id"]]["provider_qa"]["before"]["evidence"]["status"] == "FAIL"
        assert assessed["evidence_artifacts"][3]["source_review_state"] == "NOT_REVIEWED"

        payload["source_record"]["status"] = "SYNTHETIC_FIXTURE_ONLY"
        request = Request(base, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with pytest.raises(HTTPError) as error:
            urlopen(request)
        assert error.value.code == 422
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_single_observation_preview_enters_investigation_draft_api_without_change_claim(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text(json.dumps({"feature_count": 0, "features": []}), encoding="utf-8")
    draft_store_dir = tmp_path / "private-drafts"
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(case_file, evidence_root=tmp_path, draft_store_dir=draft_store_dir),
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}/api/investigation-draft"
    source = json.loads(
        (Path(__file__).resolve().parents[1] / "data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json")
        .read_text(encoding="utf-8")
    )
    hypotheses = [
        {"statement": "Surface-water change contributed to the response.", "scope_limit": "Selected AOI only.", "expected_observation": "Independent water classifications show a transition.", "would_weaken_if": "Suitable observations show no transition.", "required_evidence": "Independent water observations."},
        {"statement": "Soil-moisture variation contributed to the response.", "scope_limit": "Selected AOI only.", "expected_observation": "Independent moisture evidence changes over the AOI.", "would_weaken_if": "Suitable moisture evidence remains stable.", "required_evidence": "Independent soil-moisture observations."},
    ]
    next_observation = {
        "target_hypothesis_id": "H1",
        "action": "Retrieve independent, quality-screened surface-water observations spanning the target period.",
        "discriminating_question": "Do independent water observations show a spatially aligned transition in the AOI?",
        "possible_interpretation": "A matching transition is consistent with the stated water explanation within this AOI.",
        "priority_reason": "This adds an independent measurement that can test one explicit alternative.",
        "expected_observation": "Quality-accepted water observations show a transition in the AOI.",
        "would_weaken_if": "Suitable water observations cover the area and show no transition.",
        "inconclusive_if": "Timing, cloud, spatial resolution, or product quality prevents comparison.",
        "acceptance_gates": "Independent measurement\nSuitable temporal coverage\nAdequate AOI support and QA",
        "interpretation_limit": "This follow-up would not validate provider QA or establish causation by itself.",
    }
    try:
        source_json = json.dumps(source, separators=(",", ":"), ensure_ascii=False)
        payload = {
            "source_record": source,
            "source_record_json": source_json,
            "question": "What additional evidence could distinguish the possible causes of this radar response?",
            "hypotheses": hypotheses,
            "next_observation": next_observation,
        }
        request = Request(base, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            draft = json.load(response)
        assert draft["status"] == "DRAFT_NOT_ASSESSED"
        assert draft["evidence_artifacts"][0]["role"] == "DESCRIPTIVE_NISAR_SINGLE_OBSERVATION"
        assert draft["source_records"][draft["evidence_artifacts"][0]["evidence_id"]] == source_json
        assert draft["follow_up_evidence"][0]["availability_state"] == "NOT_SEARCHED"
        assert all(item["state"] == "NOT_EVALUATED" for item in draft["hypotheses"])
        assert any("no temporal change" in item for item in draft["interpretation_limits"])

        save_request = Request(
            base + "s", data=json.dumps({"draft": draft}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(save_request) as response:
            saved = json.load(response)
            assert response.status == 201
            assert saved["record_type"] == "ECHO_LOCAL_INVESTIGATION_DRAFT_SAVE"

        with urlopen(base + "s/" + saved["draft_id"]) as response:
            restored = json.load(response)
            assert response.status == 200
        assert restored == draft
        restored_artifact = restored["evidence_artifacts"][0]
        assert restored_artifact["role"] == "DESCRIPTIVE_NISAR_SINGLE_OBSERVATION"
        assert restored_artifact["status"] == "QA_HELD_DIAGNOSTIC_PREVIEW"
        assert restored["source_records"][restored_artifact["evidence_id"]] == source_json
        assert json.loads(source_json)["scientific_disposition"] == "QA_HELD_DIAGNOSTIC_PREVIEW"
        assert restored["follow_up_evidence"][0]["availability_state"] == "NOT_SEARCHED"
        assert all(item["state"] == "NOT_EVALUATED" for item in restored["hypotheses"])
        assert any("no temporal change" in item for item in restored["interpretation_limits"])
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_investigation_draft_imports_only_validated_case_sources_for_exact_sar_pair():
    from pathlib import Path

    root = Path(__file__).parents[1]
    case_file = root / "data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json"
    pair_path = root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
    pair = json.loads(pair_path.read_text(encoding="utf-8"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=root))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    hypotheses = [
        {"statement": "Water change contributed to the radar response.", "scope_limit": "Selected AOI only.", "expected_observation": "Independent water change overlaps.", "would_weaken_if": "Suitable observations show no change.", "required_evidence": "Independent water observations."},
        {"statement": "Soil-moisture change contributed to the radar response.", "scope_limit": "Selected AOI only.", "expected_observation": "Independent moisture readings vary.", "would_weaken_if": "Suitable readings remain stable.", "required_evidence": "Independent soil-moisture data."},
    ]
    next_observation = {
        "target_hypothesis_id": "H1", "action": "Retrieve independent water observations for both dates.",
        "discriminating_question": "Is a water transition observed in the AOI?",
        "possible_interpretation": "A transition is consistent with the scoped hypothesis.",
        "priority_reason": "It directly examines one open explanation.",
        "expected_observation": "Quality-accepted observations show a transition.",
        "would_weaken_if": "Adequate observations show no transition.",
        "inconclusive_if": "Timing, coverage, or quality is inadequate.",
        "acceptance_gates": "Independent source\nSuitable dates\nAdequate AOI support",
        "interpretation_limit": "This test does not establish cause.",
    }
    try:
        build_request = Request(
            base + "/api/investigation-draft",
            data=json.dumps({"source_record": pair, "question": "What could explain this measured response?", "hypotheses": hypotheses, "next_observation": next_observation}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(build_request) as response:
            draft = json.load(response)

        options_request = Request(
            base + "/api/investigation-draft/import-case-evidence",
            data=json.dumps({"draft": draft}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(options_request) as response:
            options = json.load(response)
        assert "absence of recorded links does not establish independence" in options["interpretation_limit"]
        selected = next(item for item in options["options"] if item["evidence_id"] == "NASA-OPERA-DSWX-HLS")
        assert selected["role"] == "OPTICAL_PRODUCT_CONTEXT"
        assert selected["status"] == "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION"

        import_request = Request(
            base + "/api/investigation-draft/import-case-evidence",
            data=json.dumps({"draft": draft, "evidence_id": selected["evidence_id"]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(import_request) as response:
            imported = json.load(response)
        artifact = imported["evidence_artifacts"][-1]
        provenance = artifact["case_provenance"]
        assert artifact["ingest_method"] == "VALIDATED_LOCAL_CASE_ASSESSMENT"
        assert artifact["source_review_state"] == "CASE_RECORD_INTEGRITY_VALIDATED"
        assert artifact["independence_state"] == "NOT_ASSESSED"
        assert provenance["source_relative_path"] == "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
        assert provenance["source_sha256"] == sha256((root / provenance["source_relative_path"]).read_bytes()).hexdigest()

        access_record_id = "ANA-GUAIBA-PRIMARY-SERIES-ACCESS-SCREEN"
        access_import_request = Request(
            base + "/api/investigation-draft/import-case-evidence",
            data=json.dumps({"draft": draft, "evidence_id": access_record_id}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(access_import_request) as response:
            access_imported = json.load(response)
        access_artifact = access_imported["evidence_artifacts"][-1]
        assert access_artifact["role"] == "PRIMARY_GAUGE_SERIES_ACCESS_METADATA_ONLY"
        access_source = json.loads(access_imported["source_records"][access_artifact["evidence_id"]])
        assert access_source["access_review"]["series_retrieved"] is False
        assert access_source["access_review"]["authorization_request_sent"] is False
        access_screen_request = Request(
            base + "/api/investigation-draft/screen-followup",
            data=json.dumps({
                "draft": access_imported,
                "evidence_id": access_artifact["evidence_id"],
                "gate_results": [
                    {"gate": gate, "result": "MET"}
                    for gate in access_imported["follow_up_evidence"][0]["test_design"]["acceptance_gates"]
                ],
                "review_basis": "Inspected the official archive access instructions and record metadata.",
                "limitations": "No station measurements were retrieved or checked against the test gates.",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as access_error:
            urlopen(access_screen_request)
        assert access_error.value.code == 422
        assert "not a retrieved observation" in json.loads(access_error.value.read())["error"]
        access_error.value.close()
        directional_access_assessment = {
            "hypothesis_id": "H1",
            "evidence_id": access_artifact["evidence_id"],
            "relationship": "SUPPORTS",
            "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The record states that an official gauge series exists.",
            "review_basis": "Inspected the official access route and archive note.",
            "limitations": "No gauge observations were retrieved for either SAR date.",
        }
        directional_request = Request(
            base + "/api/investigation-draft/assess",
            data=json.dumps({"draft": access_imported, "assessments": [directional_access_assessment]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as directional_error:
            urlopen(directional_request)
        assert directional_error.value.code == 422
        assert "cannot directionally support or contradict" in json.loads(directional_error.value.read())["error"]
        directional_error.value.close()

        followup = imported["follow_up_evidence"][0]
        screen_request = Request(
            base + "/api/investigation-draft/screen-followup",
            data=json.dumps({
                "draft": imported,
                "evidence_id": artifact["evidence_id"],
                "gate_results": [
                    {"gate": gate, "result": "UNKNOWN" if index == 0 else "MET"}
                    for index, gate in enumerate(followup["test_design"]["acceptance_gates"])
                ],
                "review_basis": "Inspected the retained optical context source and date summaries.",
                "limitations": "Optical context cannot validate an SAR-derived water boundary.",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(screen_request) as response:
            screened = json.load(response)
        assert screened["follow_up_evidence"][0]["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
        assert screened["follow_up_evidence"][0]["evidence_refs"] == [artifact["evidence_id"]]

        relation = {
            "hypothesis_id": "H1", "evidence_id": artifact["evidence_id"],
            "relationship": "LIMITS_INTERPRETATION", "evidence_fit": "UNKNOWN",
            "rationale": "This optical record supplies water context but not SAR validation.",
            "review_basis": "I inspected the retained role, source metadata, and temporal summaries.",
            "limitations": "Its optical classifications cannot validate an SAR-derived flood boundary.",
        }
        tampered = json.loads(json.dumps(imported))
        tampered_artifact = tampered["evidence_artifacts"][-1]
        tampered_artifact["case_provenance"]["assessment_sha256"] = "0" * 64
        tampered["source_staging_history"][-1]["case_provenance"]["assessment_sha256"] = "0" * 64
        tampered_request = Request(
            base + "/api/investigation-draft/assess",
            data=json.dumps({"draft": tampered, "assessments": [relation]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(tampered_request)
        assert error.value.code == 409
        error.value.close()

        tampered_screen_request = Request(
            base + "/api/investigation-draft/screen-followup",
            data=json.dumps({
                "draft": tampered,
                "evidence_id": artifact["evidence_id"],
                "gate_results": [
                    {"gate": gate, "result": "MET"}
                    for gate in followup["test_design"]["acceptance_gates"]
                ],
                "review_basis": "Inspected the retained optical context source and date summaries.",
                "limitations": "Optical context cannot validate an SAR-derived water boundary.",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(tampered_screen_request)
        assert error.value.code == 409
        error.value.close()

        assessment_request = Request(
            base + "/api/investigation-draft/assess",
            data=json.dumps({"draft": screened, "assessments": [relation]}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(assessment_request) as response:
            assessed = json.load(response)
        assert assessed["status"] == "DRAFT_ANALYST_ASSESSED_UNVERIFIED"
        assert assessed["hypotheses"][0]["state"] == "UNRESOLVED"

        restore_request = Request(
            base + "/api/investigation-draft/restore",
            data=json.dumps({"draft": assessed}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(restore_request) as response:
            restored = json.load(response)
        assert restored == assessed

        stale_case_link = json.loads(json.dumps(assessed))
        stale_case_link["evidence_artifacts"][-1]["case_provenance"]["assessment_sha256"] = "0" * 64
        stale_case_link["source_staging_history"][-1]["case_provenance"]["assessment_sha256"] = "0" * 64
        stale_restore = Request(
            base + "/api/investigation-draft/restore",
            data=json.dumps({"draft": stale_case_link}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(stale_restore)
        assert error.value.code == 409
        error.value.close()

        corrupted = json.loads(json.dumps(assessed))
        corrupted_artifact = corrupted["evidence_artifacts"][-1]
        corrupted["source_records"][corrupted_artifact["evidence_id"]] += " "
        restore_corrupted = Request(
            base + "/api/investigation-draft/restore",
            data=json.dumps({"draft": corrupted}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(restore_corrupted)
        assert error.value.code == 422
        error.value.close()

        mismatched_pair = json.loads(json.dumps(pair))
        mismatched_pair["source_products"]["after"]["scene_id"] = "UNMATCHED_SCENE"
        mismatched_request = Request(
            base + "/api/investigation-draft",
            data=json.dumps({"source_record": mismatched_pair, "question": "What could explain this measured response?", "hypotheses": hypotheses, "next_observation": next_observation}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(HTTPError) as error:
            urlopen(mismatched_request)
        assert error.value.code == 422
        error.value.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_local_case_registry_switches_assessment_and_rejects_unknown_case():
    from pathlib import Path

    root = Path(__file__).parents[1]
    t024 = root / "data/cases/rio-grande-do-sul-t024-2024/catalog.json"
    t163 = root / "data/cases/rio-grande-do-sul-t163-349925-2024/catalog.json"
    t024_id = "rio-grande-do-sul-cross-sensor-diagnostic-2024"
    t163_id = "rio-grande-do-sul-t163-349925-diagnostic-2024"
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        make_handler(t163),
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/api/cases") as response:
            registry = json.load(response)
        assert registry["default_case_id"] == t163_id
        registered_ids = {item["case_id"] for item in registry["cases"]}
        assert {t024_id, t163_id} <= registered_ids
        assessments_by_case = {
            item["case_id"]: item["has_investigation_assessment"]
            for item in registry["cases"]
        }
        assert assessments_by_case[t024_id] is True
        assert assessments_by_case[t163_id] is True

        with urlopen(base + f"/api/cross-sensor-assessment?case_id={t163_id}") as response:
            t163_assessment = json.load(response)
        soil_search = next(
            item for item in t163_assessment["follow_up_evidence"]
            if item["follow_up_id"] == "F7_INDEPENDENT_SOIL_MOISTURE_SEARCH"
        )
        assert {
            "NASA-SPL2SMAP-S-CANDIDATE-SCREEN",
            "NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN",
            "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN",
            "ISMN-SOIL-MOISTURE-STATION-COVERAGE",
        } <= set(soil_search["evidence_refs"])
        mod09ga_summary = t163_assessment["observations"]["mod09ga_vegetation_candidate_screen"]
        assert mod09ga_summary["land_water_class_codes"] == [2, 3]
        assert mod09ga_summary["cloud_state_codes"] == [0, 2]
        assert t163_assessment["status"] == "CAUSAL_INTERPRETATION_UNRESOLVED"
        gauge_followup = next(
            item for item in t163_assessment["follow_up_evidence"]
            if item["follow_up_id"] == "F11_GUAIBA_PRIMARY_SERIES"
        )
        assert gauge_followup["availability_state"] == "ACCESS_REQUIRED"
        assert gauge_followup["action_track"] == "NEW_EVIDENCE_SEARCH"
        with urlopen(
            base + f"/api/investigation-evidence?evidence_id=ANA-GUAIBA-PRIMARY-SERIES-ACCESS-SCREEN&case_id={t163_id}"
        ) as response:
            access_payload = response.read()
        access_record = json.loads(access_payload)
        access_artifact = next(
            item for item in t163_assessment["evidence_artifacts"]
            if item["evidence_id"] == "ANA-GUAIBA-PRIMARY-SERIES-ACCESS-SCREEN"
        )
        assert sha256(access_payload).hexdigest() == access_artifact["sha256"]
        assert access_record["access_review"]["series_retrieved"] is False
        assert access_record["station"]["station_code"] == "87444000"

        with urlopen(base + f"/api/cross-sensor-assessment?case_id={t024_id}") as response:
            assessment = json.load(response)
        assert assessment["case_id"] == t024_id
        assert len(assessment["hypotheses"]) == 6
        soil_followup = next(item for item in assessment["follow_up_evidence"] if item["follow_up_id"] == "F6_INDEPENDENT_SOIL_MOISTURE_SEARCH")
        assert {
            "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN",
            "ISMN-SOIL-MOISTURE-STATION-COVERAGE",
            "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN",
        } <= set(soil_followup["evidence_refs"])
        for evidence_id, expected_type in (
            ("NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN", "ECHO_CATALOG_AVAILABILITY_SCREEN"),
            ("ISMN-SOIL-MOISTURE-STATION-COVERAGE", "ECHO_STATION_CATALOG_AVAILABILITY_SCREEN"),
        ):
            with urlopen(base + f"/api/investigation-evidence?evidence_id={evidence_id}&case_id={t024_id}") as response:
                source_payload = response.read()
            source_record = json.loads(source_payload)
            source_artifact = next(item for item in assessment["evidence_artifacts"] if item["evidence_id"] == evidence_id)
            assert sha256(source_payload).hexdigest() == source_artifact["sha256"]
            assert source_record["record_type"] == expected_type
        rainfall_hypothesis = next(item for item in assessment["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
        rainfall_relation = next(item for item in rainfall_hypothesis["evidence_assessments"] if item["evidence_id"] == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY")
        assert rainfall_relation["relationship"] == "DOES_NOT_DISTINGUISH"
        assert assessment["observations"]["gpm_precipitation_context"]["interacquisition"]["complete_days"] == 23
        with urlopen(base + f"/api/investigation-evidence?evidence_id=NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY&case_id={t024_id}") as response:
            rainfall_payload = response.read()
        rainfall_record = json.loads(rainfall_payload)
        rainfall_artifact = next(item for item in assessment["evidence_artifacts"] if item["evidence_id"] == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY")
        assert sha256(rainfall_payload).hexdigest() == rainfall_artifact["sha256"]
        assert rainfall_record["record_type"] == "ECHO_GPM_IMERG_INTERACQUISITION_CHRONOLOGY"

        with urlopen(base + f"/api/investigation-evidence?evidence_id=SAR-RTC-S1-PAIR&case_id={t024_id}") as response:
            pair_payload = response.read()
        pair_record = json.loads(pair_payload)
        pair_artifact = next(item for item in assessment["evidence_artifacts"] if item["evidence_id"] == "SAR-RTC-S1-PAIR")
        assert sha256(pair_payload).hexdigest() == pair_artifact["sha256"]
        assert [pair_record["source_products"][role]["scene_id"] for role in ("before", "after")] == assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"]

        with urlopen(base + f"/api/opera-temporal-series?case_id={t024_id}") as response:
            series_payload = response.read()
            series_hash = response.headers["X-ECHO-Content-SHA256"]
            source_path = response.headers["X-ECHO-Source-Path"]
        series = json.loads(series_payload)
        assert sha256(series_payload).hexdigest() == series_hash
        assert source_path == "data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json"
        assert series["record_type"] == "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS"
        assert series["status"] == "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
        assert series["schema_version"] == 2
        assert series["quality_review"]["status"] == "REVIEW_RECORDED_WITH_UNRESOLVED_SCENE_QUALITY_LIMITS"
        assert series["quality_review"]["provider_qa"]["scene_level_verdict"] == "NOT_PROVIDED"
        assert series["quality_review"]["assessment_boundary"]["provider_qa_overridden"] is False
        assert len(series["observations"]) == 3
        assert len(series["adjacent_intervals"]) == 2
        assert [item["measured_pixel_count"] for item in series["adjacent_intervals"]] == [1034, 1034]

        with pytest.raises(HTTPError) as error:
            urlopen(base + "/api/case?case_id=not-registered")
        assert error.value.code == 404
        assert json.load(error.value)["error"] == "Unknown investigation case"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_cross_sensor_assessment_endpoint_serves_unresolved_evidence_record(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    source = {"record_type": "ECHO_TEST_EVIDENCE", "status": "READY"}
    source_bytes = json.dumps(source).encode()
    (tmp_path / "source.json").write_bytes(source_bytes)
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "case_id": "case-from-manifest",
        "status": "CAUSAL_INTERPRETATION_UNRESOLVED",
        "evidence_artifacts": [{
            "evidence_id": "E1",
            "role": "SYNTHETIC_TEST_EVIDENCE",
            "relative_path": "source.json",
            "sha256": sha256(source_bytes).hexdigest(),
            "record_type": source["record_type"],
            "status": source["status"],
        }],
        "hypotheses": [{
            "id": "H1",
            "statement": "A bounded descriptive claim.",
            "state": "SUPPORTED_WITHIN_SCOPE",
            "scope_limit": "Only this synthetic fixture.",
            "expected_observation": "The retained test measurement is present.",
            "would_weaken_if": "The retained test measurement is absent.",
            "testability_state": "DESCRIPTIVE_ONLY",
            "testability_reason": "The fixture contains its declared measurement.",
            "required_evidence": ["A test measurement"],
            "evidence_refs": ["E1"],
            "evidence_assessments": [{
                "evidence_id": "E1",
                "relationship": "SUPPORTS",
                "rationale": "The fixture demonstrates the declared test behavior.",
            }],
        }],
        "follow_up_evidence": [],
        "assessment": {"nisar_measurement_present": False},
    }
    (tmp_path / "assessment.json").write_text(json.dumps(assessment), encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "assessment.json"},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/api/cross-sensor-assessment") as response:
            result = json.load(response)
        assert result["record_type"] == "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT"
        assert result == assessment
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_counterfactual_preview_is_hash_bound_and_does_not_write_assessment(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    source = {"record_type": "ECHO_TEST_EVIDENCE", "status": "READY"}
    source_bytes = json.dumps(source).encode()
    (tmp_path / "source.json").write_bytes(source_bytes)
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "case_id": "counterfactual-test-case",
        "status": "CAUSAL_INTERPRETATION_UNRESOLVED",
        "evidence_artifacts": [{
            "evidence_id": "E1",
            "role": "SYNTHETIC_TEST_EVIDENCE",
            "relative_path": "source.json",
            "sha256": sha256(source_bytes).hexdigest(),
            "record_type": source["record_type"],
            "status": source["status"],
        }],
        "hypotheses": [{
            "id": "H1",
            "statement": "A bounded synthetic test explanation.",
            "state": "SUPPORTED_WITHIN_SCOPE",
            "scope_limit": "Only this synthetic fixture.",
            "expected_observation": "The retained measurement matches its declared pattern.",
            "would_weaken_if": "The retained measurement contradicts that pattern.",
            "testability_state": "DESCRIPTIVE_ONLY",
            "testability_reason": "One synthetic source is retained.",
            "required_evidence": ["A source-linked test measurement"],
            "evidence_refs": ["E1"],
            "evidence_assessments": [{
                "evidence_id": "E1",
                "relationship": "SUPPORTS",
                "rationale": "The synthetic measurement matches its predeclared pattern.",
            }],
        }],
        "follow_up_evidence": [],
    }
    assessment_bytes = json.dumps(assessment).encode()
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_bytes(assessment_bytes)
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "assessment.json"},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}/api/investigation-counterfactual-preview"
    request_payload = {
        "case_id": assessment["case_id"],
        "assessment_sha256": sha256(assessment_bytes).hexdigest(),
        "hypothesis_id": "H1",
        "evidence_id": "E1",
        "proposed_relationship": "CONTRADICTS",
    }
    try:
        request = Request(
            base,
            data=json.dumps(request_payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            preview = json.load(response)
        assert preview["record_type"] == "ECHO_COUNTERFACTUAL_EVIDENCE_RECLASSIFICATION_PREVIEW"
        assert preview["status"] == "COUNTERFACTUAL_ONLY"
        assert preview["current_disposition"] == "SUPPORTED_WITHIN_SCOPE"
        assert preview["counterfactual_disposition"] == "CONTRADICTED_WITHIN_SCOPE"
        assert assessment_path.read_bytes() == assessment_bytes

        request_payload["assessment_sha256"] = "0" * 64
        stale_request = Request(
            base,
            data=json.dumps(request_payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(stale_request)
        assert error.value.code == 409

        qa_source = {"record_type": "ECHO_TEST_EVIDENCE", "status": "QA_HELD"}
        qa_source_bytes = json.dumps(qa_source).encode()
        (tmp_path / "source.json").write_bytes(qa_source_bytes)
        qa_assessment = json.loads(json.dumps(assessment))
        qa_artifact = qa_assessment["evidence_artifacts"][0]
        qa_artifact.update(
            role="SAR_PAIR_HELD_AT_PROVIDER_QA",
            status="QA_HELD",
            sha256=sha256(qa_source_bytes).hexdigest(),
        )
        qa_assessment["hypotheses"][0]["state"] = "UNRESOLVED"
        qa_assessment["hypotheses"][0]["evidence_assessments"][0]["relationship"] = "DOES_NOT_DISTINGUISH"
        qa_assessment_bytes = json.dumps(qa_assessment).encode()
        assessment_path.write_bytes(qa_assessment_bytes)
        request_payload.update(
            assessment_sha256=sha256(qa_assessment_bytes).hexdigest(),
            proposed_relationship="SUPPORTS",
        )
        qa_preview_request = Request(
            base,
            data=json.dumps(request_payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(qa_preview_request)
        assert error.value.code == 400
        assert "non-directional evidence cannot be previewed" in error.value.read().decode()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_cross_sensor_assessment_endpoint_rejects_stale_hypothesis_disposition(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    source = {"record_type": "ECHO_TEST_EVIDENCE", "status": "READY"}
    source_bytes = json.dumps(source).encode()
    (tmp_path / "source.json").write_bytes(source_bytes)
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "evidence_artifacts": [{
            "evidence_id": "E1",
            "role": "SYNTHETIC_TEST_EVIDENCE",
            "relative_path": "source.json",
            "sha256": sha256(source_bytes).hexdigest(),
            "record_type": source["record_type"],
            "status": source["status"],
        }],
        "hypotheses": [{
            "id": "H1",
            "statement": "A bounded descriptive claim.",
            "state": "SUPPORTED_WITHIN_SCOPE",
            "scope_limit": "Only this fixture.",
            "expected_observation": "A measurement is present.",
            "would_weaken_if": "The measurement is absent.",
            "testability_state": "DESCRIPTIVE_ONLY",
            "testability_reason": "The fixture has a cited measurement.",
            "required_evidence": ["A test measurement"],
            "evidence_refs": ["E1"],
            "evidence_assessments": [{
                "evidence_id": "E1",
                "relationship": "CONTRADICTS",
                "rationale": "This intentionally conflicts with the stale disposition.",
            }],
        }],
        "follow_up_evidence": [],
    }
    (tmp_path / "assessment.json").write_text(json.dumps(assessment), encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "assessment.json"},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/cross-sensor-assessment")
        except HTTPError as error:
            assert error.code == 503
            assert "does not match evidence relationships" in json.load(error)["error"]
        else:
            raise AssertionError("stale hypothesis dispositions must not be served")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_cross_sensor_assessment_reports_hypotheses_affected_by_changed_source_artifact(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    (tmp_path / "source.json").write_text(
        json.dumps({"record_type": "ECHO_TEST_EVIDENCE", "status": "READY"}),
        encoding="utf-8",
    )
    derived = {"record_type": "ECHO_TEST_DERIVED", "status": "READY", "derived_from": ["E1"]}
    derived_bytes = json.dumps(derived).encode()
    (tmp_path / "derived.json").write_bytes(derived_bytes)
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "status": "UNRESOLVED",
        "evidence_artifacts": [
            {
                "evidence_id": "E1",
                "role": "SYNTHETIC_TEST_EVIDENCE",
                "relative_path": "source.json",
                "sha256": "0" * 64,
                "record_type": "ECHO_TEST_EVIDENCE",
                "status": "READY",
                "lineage": {"derived_from_evidence_ids": [], "shares_source_observations_with": []},
            },
            {
                "evidence_id": "E2",
                "role": "SYNTHETIC_DERIVED_TEST_EVIDENCE",
                "relative_path": "derived.json",
                "sha256": sha256(derived_bytes).hexdigest(),
                "record_type": "ECHO_TEST_DERIVED",
                "status": "READY",
                "lineage": {"derived_from_evidence_ids": ["E1"], "shares_source_observations_with": []},
            },
        ],
        "hypotheses": [{
            "id": "H1",
            "statement": "Synthetic test hypothesis",
            "state": "UNRESOLVED",
            "evidence_refs": ["E2"],
        }],
        "follow_up_evidence": [{
            "follow_up_id": "F1",
            "action": "Synthetic test follow-up",
            "target_hypothesis_ids": ["H1"],
            "evidence_refs": ["E2"],
        }],
    }
    (tmp_path / "assessment.json").write_text(json.dumps(assessment), encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "assessment.json"},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/cross-sensor-assessment")
        except HTTPError as error:
            assert error.code == 409
            response = json.load(error)
            assert "checksum mismatch" in response["error"]
            impact = response["integrity_impact"]
            assert impact["status"] == "REASSESSMENT_REQUIRED"
            assert impact["assessment_sha256"] == sha256((tmp_path / "assessment.json").read_bytes()).hexdigest()
            assert impact["changed_evidence"][0]["evidence_id"] == "E1"
            assert impact["affected_evidence_ids"] == ["E1", "E2"]
            assert impact["affected_hypotheses"][0]["hypothesis_id"] == "H1"
            assert impact["affected_follow_ups"][0]["follow_up_id"] == "F1"
        else:
            raise AssertionError("changed source evidence must not be served as current")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_cross_sensor_assessment_reports_changed_nested_source_asset(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    (tmp_path / "daily.bin").write_bytes(b"changed daily sample")
    source = {
        "record_type": "ECHO_GPM_IMERG_DAILY_CONTEXT",
        "status": "READY",
        "query": {"start_date_utc": "2026-01-01", "end_date_utc": "2026-01-01"},
        "daily_observations": [{"asset": {
            "relative_path": "daily.bin",
            "sha256": "0" * 64,
        }}],
    }
    source_bytes = json.dumps(source).encode()
    (tmp_path / "gpm.json").write_bytes(source_bytes)
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "evidence_artifacts": [{
            "evidence_id": "NASA-GPM-DAY",
            "role": "NASA_PRECIPITATION_CONTEXT",
            "relative_path": "gpm.json",
            "sha256": sha256(source_bytes).hexdigest(),
            "record_type": "ECHO_GPM_IMERG_DAILY_CONTEXT",
            "status": "READY",
            "lineage": {"derived_from_evidence_ids": [], "shares_source_observations_with": []},
        }],
        "hypotheses": [],
    }
    (tmp_path / "assessment.json").write_text(json.dumps(assessment), encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "assessment.json"},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/cross-sensor-assessment")
        except HTTPError as error:
            assert error.code == 409
            impact = json.load(error)["integrity_impact"]
            assert impact["changed_evidence"] == [{
                "evidence_id": "NASA-GPM-DAY",
                "role": "NASA_PRECIPITATION_CONTEXT",
                "asset_path": "daily.bin",
                "integrity_state": "NESTED_ASSET_CHECKSUM_MISMATCH",
                "expected_sha256": "0" * 64,
                "observed_sha256": sha256(b"changed daily sample").hexdigest(),
            }]
            assert impact["affected_evidence_ids"] == ["NASA-GPM-DAY"]
        else:
            raise AssertionError("changed nested source assets must not be served as current evidence")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_investigation_evidence_endpoint_serves_only_hash_verified_assessment_artifacts(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    source = {"record_type": "ECHO_TEST_EVIDENCE", "status": "READY", "value": 7}
    source_bytes = json.dumps(source).encode()
    (tmp_path / "source.json").write_bytes(source_bytes)
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "evidence_artifacts": [{
            "evidence_id": "E1",
            "role": "SYNTHETIC_TEST_EVIDENCE",
            "relative_path": "source.json",
            "sha256": sha256(source_bytes).hexdigest(),
            "record_type": "ECHO_TEST_EVIDENCE",
            "status": "READY",
        }],
        "hypotheses": [{
            "id": "H1",
            "statement": "A testable synthetic statement.",
            "state": "SUPPORTED_WITHIN_SCOPE",
            "scope_limit": "Test only.",
            "expected_observation": "A value of seven.",
            "would_weaken_if": "The value differs.",
            "testability_state": "DESCRIPTIVE_ONLY",
            "testability_reason": "The fixture contains a value.",
            "required_evidence": ["A synthetic value"],
            "evidence_refs": ["E1"],
            "evidence_assessments": [{
                "evidence_id": "E1",
                "relationship": "SUPPORTS",
                "rationale": "The fixture value is seven.",
            }],
        }],
        "follow_up_evidence": [],
    }
    (tmp_path / "assessment.json").write_text(json.dumps(assessment), encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "assessment.json"},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/api/investigation-evidence?evidence_id=E1") as response:
            assert json.load(response) == source
        try:
            urlopen(base + "/api/investigation-evidence?evidence_id=UNLINKED")
        except HTTPError as error:
            assert error.code == 404
            assert "not linked" in json.load(error)["error"]
        else:
            raise AssertionError("the endpoint must not serve evidence outside the assessment")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_investigation_evidence_endpoint_rejects_tampered_artifact(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    source = {"record_type": "ECHO_TEST_EVIDENCE", "status": "READY"}
    source_bytes = json.dumps(source).encode()
    source_path = tmp_path / "source.json"
    source_path.write_bytes(source_bytes)
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "evidence_artifacts": [{
            "evidence_id": "E1",
            "role": "SYNTHETIC_TEST_EVIDENCE",
            "relative_path": "source.json",
            "sha256": sha256(source_bytes).hexdigest(),
            "record_type": "ECHO_TEST_EVIDENCE",
            "status": "READY",
        }],
        "hypotheses": [],
    }
    (tmp_path / "assessment.json").write_text(json.dumps(assessment), encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "assessment.json"},
    }), encoding="utf-8")
    source_path.write_text('{"record_type":"ECHO_TEST_EVIDENCE","status":"READY","tampered":true}')
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/investigation-evidence?evidence_id=E1")
        except HTTPError as error:
            assert error.code == 503
            assert "checksum mismatch" in json.load(error)["error"]
        else:
            raise AssertionError("tampered linked evidence must not be served")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_assessment_validation_binds_spatial_overlay_to_exact_sar_and_optical_records(tmp_path):
    sources = {
        "SAR-RTC-S1-PAIR": {"record_type": "ECHO_SAR", "status": "DIAGNOSTIC"},
        "NASA-OPERA-DSWX-HLS": {"record_type": "ECHO_OPTICAL", "status": "CONTEXT"},
    }
    artifacts = []
    for evidence_id, source in sources.items():
        path = tmp_path / f"{evidence_id}.json"
        payload = json.dumps(source).encode()
        path.write_bytes(payload)
        artifacts.append({
            "evidence_id": evidence_id,
            "role": "TEST_SOURCE",
            "relative_path": path.name,
            "sha256": sha256(payload).hexdigest(),
            "record_type": source["record_type"],
            "status": source["status"],
        })
    overlay = {
        "record_type": "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC",
        "status": "DIAGNOSTIC_SPATIAL_ASSOCIATION",
        "sources": {
            "sar_pair_record_sha256": artifacts[0]["sha256"],
            "optical_context_record_sha256": artifacts[1]["sha256"],
        },
    }
    overlay_path = tmp_path / "overlay.json"
    overlay_bytes = json.dumps(overlay).encode()
    overlay_path.write_bytes(overlay_bytes)
    artifacts.append({
        "evidence_id": "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
        "role": "DIAGNOSTIC_CROSS_SENSOR_SPATIAL_ASSOCIATION",
        "relative_path": overlay_path.name,
        "sha256": sha256(overlay_bytes).hexdigest(),
        "record_type": overlay["record_type"],
        "status": overlay["status"],
    })
    assessment = {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "evidence_artifacts": artifacts,
        "hypotheses": [{
            "id": "H1",
            "statement": "A testable statement.",
            "state": "NOT_EVALUATED",
            "scope_limit": "Test only.",
            "expected_observation": "An expected observation.",
            "would_weaken_if": "A weakening observation.",
            "testability_state": "NOT_TESTED",
            "testability_reason": "The fixture has not been tested.",
            "required_evidence": ["A test observation"],
            "evidence_refs": [],
            "evidence_assessments": [],
        }],
        "follow_up_evidence": [],
    }

    _validate_assessment_record(assessment, tmp_path)

    assessment["evidence_artifacts"][0]["lineage"] = {
        "derived_from_evidence_ids": ["NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"],
    }
    assessment["evidence_artifacts"][2]["lineage"] = {
        "derived_from_evidence_ids": ["SAR-RTC-S1-PAIR", "NASA-OPERA-DSWX-HLS"],
    }
    with pytest.raises(ValueError, match="lineage.*cycle"):
        _validate_assessment_record(assessment, tmp_path)
    assessment["evidence_artifacts"][0].pop("lineage")
    assessment["evidence_artifacts"][2].pop("lineage")
    assessment["follow_up_evidence"] = [{
        "follow_up_id": "F1",
        "target_hypothesis_ids": ["H1"],
        "purpose": "DISCRIMINATING_OBSERVATION",
        "availability_state": "NOT_SEARCHED",
        "action_track": "QUALITY_PREREQUISITE",
        "action": "Search for a suitable observation.",
        "discriminating_question": "Would a new observation distinguish the explanations?",
        "possible_interpretation": "Different outcomes would alter the assessment.",
        "priority_reason": "This evidence has not been searched.",
        "evidence_refs": [],
        "test_design": {
            "mechanism_branch": "Test a narrow water explanation.",
            "hypothesis_under_test_id": "H1",
            "expected_observation": "Suitable observations show a prespecified spatial association.",
            "would_weaken_if": "Suitable observations show no prespecified association.",
            "inconclusive_if": "Quality, timing, or coverage is inadequate.",
            "acceptance_gates": ["Acceptable quality", "Suitable support"],
            "does_not_test_hypothesis_ids": [],
            "interpretation_limit": "Association does not establish cause.",
        },
    }]
    with pytest.raises(ValueError, match="action track does not match"):
        _validate_assessment_record(assessment, tmp_path)
    assessment["follow_up_evidence"] = []

    overlay["sources"]["sar_pair_record_sha256"] = "0" * 64
    bad_overlay = json.dumps(overlay).encode()
    overlay_path.write_bytes(bad_overlay)
    assessment["evidence_artifacts"][2]["sha256"] = sha256(bad_overlay).hexdigest()
    with pytest.raises(ValueError, match="does not reference the linked SAR and optical records"):
        _validate_assessment_record(assessment, tmp_path)


def test_case_evidence_manifest_rejects_paths_outside_project_root(tmp_path):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    (tmp_path / "investigation.json").write_text(json.dumps({
        "schema_version": 1,
        "evidence_records": {"cross_sensor_assessment": "../outside.json"},
    }), encoding="utf-8")
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file, evidence_root=tmp_path))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        try:
            urlopen(f"http://127.0.0.1:{server.server_port}/api/cross-sensor-assessment")
        except HTTPError as error:
            assert error.code == 503
            assert "evidence path escapes the project root" in json.load(error)["error"]
        else:
            raise AssertionError("case evidence paths must stay inside the project root")
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


def test_assessment_artifact_validation_reproduces_opera_pair_quality_review(tmp_path):
    root = Path(__file__).resolve().parents[1]
    record = json.loads(
        (root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json").read_text(encoding="utf-8")
    )
    record["schema_version"] = 2
    record["quality_review"] = build_opera_rtc_pair_quality_review(record)
    payload = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (tmp_path / "pair.json").write_bytes(payload)
    artifact = {
        "evidence_id": "SAR-RTC-S1-PAIR",
        "relative_path": "pair.json",
        "sha256": sha256(payload).hexdigest(),
        "record_type": record["record_type"],
        "status": record["status"],
        "role": "DIAGNOSTIC_MEASUREMENT",
    }
    assert _validate_assessment_artifacts({"evidence_artifacts": [artifact]}, tmp_path) == {"SAR-RTC-S1-PAIR"}

    record["quality_review"]["per_observation"][0]["rfi_metadata"]["in_band_out_band_power_ratio"] = 0
    tampered = (json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n").encode()
    (tmp_path / "pair.json").write_bytes(tampered)
    artifact["sha256"] = sha256(tampered).hexdigest()
    with pytest.raises(ValueError, match="OPERA pair quality review does not reproduce"):
        _validate_assessment_artifacts({"evidence_artifacts": [artifact]}, tmp_path)


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


def test_opera_catalog_endpoint_returns_distinct_product_screen(tmp_path, monkeypatch):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    features = [
        {
            "type": "Feature",
            "properties": {
                "fileID": (
                    "OPERA_L2_RTC-S1_T163-349924-IW2_20240508T100000Z_"
                    "20240509T100000Z_S1A_30_v1.0"
                ),
                "startTime": "2024-05-08T10:00:00Z",
            },
            "geometry": None,
        }
    ]
    seen = {}

    def search(query):
        seen["query"] = query
        return features, 1

    monkeypatch.setattr("echo.web.search_opera_rtc_s1_with_pagination", search)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        payload = {
            "bounds_wgs84": [-51.35, -30.12, -51.10, -29.94],
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
        }
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/opera-catalog",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            record = json.load(response)
        assert response.status == 200
        assert record["record_type"] == "ASF_OPERA_RTC_S1_CATALOG"
        assert record["returned_feature_count"] == 1
        assert record["pagination"]["pages_retrieved"] == 1
        assert "not NISAR" in record["mission_product"]
        assert seen["query"].bounds_wgs84 == payload["bounds_wgs84"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_opera_pair_endpoint_validates_shape_and_returns_diagnostic_record(
    tmp_path, monkeypatch
):
    case_file = tmp_path / "catalog.json"
    case_file.write_text("{}", encoding="utf-8")
    expected = {
        "record_type": "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS",
        "provider_qa": {"status": "NOT_RETRIEVED"},
    }
    seen = {}

    def build(before, after, **kwargs):
        seen["payload"] = (before, after, kwargs)
        return expected

    monkeypatch.setattr("echo.web.build_opera_rtc_s1_pair_record", build)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(case_file))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        scene_a = "OPERA_L2_RTC-S1_T163-349924-IW2_20240508T100000Z_20240509T100000Z_S1A_30_v1.0"
        scene_b = "OPERA_L2_RTC-S1_T163-349924-IW2_20240601T100000Z_20240602T100000Z_S1A_30_v1.0"
        feature = lambda scene: {
            "properties": {
                "fileID": scene,
                "url": f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene}_VV.tif",
                "startTime": "2024-05-08T10:00:00Z",
                "bytes": {"scene_VV.tif": {"bytes": 3, "format": "GeoTIFF"}},
            }
        }
        payload = {
            "before": feature(scene_a),
            "after": feature(scene_b),
            "bounds_wgs84": [-51.25, -30.08, -51.24, -30.07],
            "polarization": "VV",
        }
        request = Request(
            f"http://127.0.0.1:{server.server_port}/api/opera-pair-analysis",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            record = json.load(response)
        assert response.status == 200
        assert record == expected
        assert seen["payload"] == (
            payload["before"],
            payload["after"],
            {
                "bounds_wgs84": payload["bounds_wgs84"],
                "polarization": "VV",
            },
        )

        payload["unexpected"] = True
        bad = Request(
            f"http://127.0.0.1:{server.server_port}/api/opera-pair-analysis",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(bad)
        assert error.value.code == 400
        error.value.close()
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
        failure_response = json.load(error.value)
        assert failure_response["error"] == "ASF catalog search failed; try again later"
        assert failure_response["failure_record"]["provider"] == "ASF"
        assert failure_response["failure_record"]["outcome"] == "REQUEST_FAILED_NO_RESULT"
        assert failure_response["failure_record"]["query"] == {
            "dataset": "NISAR", "processing_level": "GCOV", "data_maturity": "BETA",
            "longitude": 33.5, "latitude": -24.5, "bounds_wgs84": None,
            "start_date": "2026-01-01", "end_date": "2026-01-31", "result_limit": 1000,
        }
        assert "upstream details" not in json.dumps(failure_response)
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


def test_case_assessment_checksums_all_retained_gpm_subsets():
    from pathlib import Path

    root = Path(__file__).parents[1]
    case_path = root / "data/cases/rio-grande-do-sul-t163-349925-2024"
    manifest = json.loads((case_path / "investigation.json").read_text(encoding="utf-8"))
    assessment_path = root / manifest["evidence_records"]["cross_sensor_assessment"]
    assessment = json.loads(assessment_path.read_text(encoding="utf-8"))

    evidence_ids = _validate_assessment_record(assessment, root)

    assert "NASA-GPM-IMERG-BEFORE-PRE-SAR" in evidence_ids
    assert "NASA-GPM-IMERG-AFTER-PRE-SAR" in evidence_ids
    assert "NASA-GPM-IMERG-INTERVENING-DAILY-CONTEXT" in evidence_ids
    assert "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY" in evidence_ids
    assert "NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN" in evidence_ids
    assert "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY" in evidence_ids
    assert "NASA-HLS-S30-VEGETATION-SCREEN" in evidence_ids
    assert "NASA-HLS-S30-NDVI-SAR-ASSOCIATION" in evidence_ids
    l30_context = assessment["observations"]["hls_l30_vegetation_context"]
    assert [item["sar_cells"] for item in l30_context["association_coverage_sensitivity"]] == [312, 265, 218]
    radiometer = assessment["observations"]["smap_radiometer_spatial_suitability_screen"]
    assert radiometer["selected_daily_granule_dates"] == ["2024-05-08", "2024-06-01"]
    assert radiometer["pixel_data_retrieved"] is False
    context = assessment["observations"]["official_hydrologic_event_context"]
    assert context["timestamped_readings_retrieved"] is False
    assert context["period_local_dates"] == {"start_date": "2024-05-02", "end_date": "2024-06-01"}
    s30_context = assessment["observations"]["hls_s30_vegetation_context"]
    assert assessment["schema_version"] == 3
    assert s30_context["common_clear_land_pixel_count"] == 25
    assert s30_context["association_at_75_percent_common_support"]["sar_cells"] == 11
    assert [item["sar_cells"] for item in s30_context["association_coverage_sensitivity"]] == [39, 25, 11]
    s30_association = json.loads((root / "data/research/hls-s30-rtc-ndvi-association-T163-349925-2026-11-08.json").read_text())
    assert s30_context["association_coverage_sensitivity"] == s30_association["coverage_sensitivity"]
    altered_s30 = json.loads(json.dumps(assessment))
    altered_s30["observations"]["hls_s30_vegetation_context"]["association_coverage_sensitivity"][0]["sar_cells"] -= 1
    with pytest.raises(ValueError, match="HLS S30 coverage sensitivity does not match"):
        _validate_assessment_record(altered_s30, root)
    water_hypothesis = next(item for item in assessment["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    gauge_relation = next(item for item in water_hypothesis["evidence_assessments"] if item["evidence_id"] == "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY")
    assert gauge_relation["relationship"] == "DOES_NOT_DISTINGUISH"
    assert water_hypothesis["state"] == "UNRESOLVED"
    altered = json.loads(json.dumps(assessment))
    altered_h2 = next(item for item in altered["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    altered_relation = next(item for item in altered_h2["evidence_assessments"] if item["evidence_id"] == "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY")
    altered_relation["relationship"] = "SUPPORTS"
    with pytest.raises(ValueError, match="must remain narrative-only, case-linked, and nondiscriminating"):
        _validate_assessment_record(altered, root)
    altered = json.loads(json.dumps(assessment))
    altered["observations"]["official_hydrologic_event_context"]["period_local_dates"]["end_date"] = "2024-05-31"
    with pytest.raises(ValueError, match="must remain narrative-only, case-linked, and nondiscriminating"):
        _validate_assessment_record(altered, root)
    chronology = json.loads(
        (root / "data/research/gpm-imerg-interacquisition-T163-349925-2024-05-08-06-01.json").read_text(encoding="utf-8")
    )
    assert chronology["summary"]["days_with_complete_nearest_cell_samples"] == 23
    assert chronology["summary"]["maximum_daily_precipitation_date_utc"] == "2024-05-23"


def test_t024_active_assessment_validates_sar_and_rainfall_context_relationships():
    from pathlib import Path

    root = Path(__file__).parents[1]
    case_path = root / "data/cases/rio-grande-do-sul-t024-2024"
    manifest = json.loads((case_path / "investigation.json").read_text(encoding="utf-8"))
    assessment = json.loads((root / manifest["evidence_records"]["cross_sensor_assessment"]).read_text(encoding="utf-8"))

    evidence_ids = _validate_assessment_record(assessment, root)
    assert "NASA-OPERA-RTC-S1-TEMPORAL-SERIES" in evidence_ids
    assert "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY" in evidence_ids
    assert "NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN" in evidence_ids
    assert "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN" in evidence_ids
    assert "NASA-HLS-L30-VEGETATION-SCREEN" in evidence_ids
    assert "NASA-HLS-L30-NDVI-SAR-ASSOCIATION" in evidence_ids
    water = next(item for item in assessment["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    relation = next(item for item in water["evidence_assessments"] if item["evidence_id"] == "NASA-OPERA-RTC-S1-TEMPORAL-SERIES")
    assert relation["relationship"] == "DOES_NOT_DISTINGUISH"
    rainfall_relation = next(item for item in water["evidence_assessments"] if item["evidence_id"] == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY")
    assert rainfall_relation["relationship"] == "DOES_NOT_DISTINGUISH"
    assert "does not measure AOI surface-water extent" in rainfall_relation["rationale"]
    assert water["state"] == "UNRESOLVED"
    assert assessment["observations"]["sar_temporal_series"]["common_support_count"] == 1034
    assert assessment["schema_version"] == 4
    vegetation_candidate = assessment["observations"]["hls_l30_extended_candidate_screen"]
    assert vegetation_candidate["common_clear_land_ndvi_pixel_count"] == 0
    assert vegetation_candidate["after_fmask_class_counts"] == {"194": 1152}
    followup = next(item for item in assessment["follow_up_evidence"] if item["follow_up_id"] == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION")
    assert followup["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    vegetation = next(item for item in assessment["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    candidate_relation = next(item for item in vegetation["evidence_assessments"] if item["evidence_id"] == "NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN")
    assert candidate_relation["relationship"] == "LIMITS_INTERPRETATION"
    assert vegetation["state"] == "UNRESOLVED"
    assert assessment["observations"]["sar_temporal_series"]["temporal_direction_screen"]["pixel_counts"]["direction_reversal"] == 650
    assert assessment["observations"]["gpm_precipitation_context"]["interacquisition"]["complete_days"] == 23
    vegetation = next(item for item in assessment["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    vegetation_relation = next(item for item in vegetation["evidence_assessments"] if item["evidence_id"] == "NASA-HLS-L30-NDVI-SAR-ASSOCIATION")
    assert vegetation["state"] == "UNRESOLVED"
    assert vegetation_relation["relationship"] == "DOES_NOT_DISTINGUISH"
    hls_context = assessment["observations"]["hls_l30_vegetation_context"]
    assert hls_context["association_at_75_percent_common_support"]["sar_cells"] == 218
    assert [item["sar_cells"] for item in hls_context["association_coverage_sensitivity"]] == [312, 265, 218]
    association = json.loads((root / "data/research/hls-l30-ndvi-sar-association-T024-050661-2026-11-09.json").read_text())
    assert hls_context["association_coverage_sensitivity"] == association["coverage_sensitivity"]
    altered_hls = json.loads(json.dumps(assessment))
    altered_hls["observations"]["hls_l30_vegetation_context"]["association_coverage_sensitivity"][0]["sar_cells"] -= 1
    with pytest.raises(ValueError, match="coverage sensitivity does not match"):
        _validate_assessment_record(altered_hls, root)
    altered_candidate = json.loads(json.dumps(assessment))
    altered_candidate["observations"]["hls_l30_extended_candidate_screen"]["common_clear_land_ndvi_pixel_count"] = 1
    with pytest.raises(ValueError, match="summary does not reproduce"):
        _validate_assessment_record(altered_candidate, root)
    h3 = next(item for item in assessment["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
    l4_relation = next(
        item for item in h3["evidence_assessments"]
        if item["evidence_id"] == "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN"
    )
    assert l4_relation["relationship"] == "DOES_NOT_DISTINGUISH"
    assert h3["state"] == "UNRESOLVED"
    assert h3["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    l4_context = assessment["observations"]["smap_l4_regional_soil_moisture_context"]
    assert l4_context["after_minus_before_model_analysis_m3_m3"] == pytest.approx(0.003538, abs=1e-6)
    follow_up = next(
        item for item in assessment["follow_up_evidence"]
        if item["follow_up_id"] == "F6_INDEPENDENT_SOIL_MOISTURE_SEARCH"
    )
    assert follow_up["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    assert follow_up["action_track"] == "NEW_EVIDENCE_SEARCH"

    altered = json.loads(json.dumps(assessment))
    altered_h3 = next(item for item in altered["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
    altered_l4_relation = next(
        item for item in altered_h3["evidence_assessments"]
        if item["evidence_id"] == "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN"
    )
    altered_l4_relation["relationship"] = "SUPPORTS"
    with pytest.raises(ValueError, match="SMAP L4 context must remain non-distinguishing"):
        _validate_assessment_record(altered, root)

    altered = json.loads(json.dumps(assessment))
    altered_water = next(item for item in altered["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    altered_relation = next(item for item in altered_water["evidence_assessments"] if item["evidence_id"] == "NASA-OPERA-RTC-S1-TEMPORAL-SERIES")
    altered_relation["relationship"] = "SUPPORTS"
    with pytest.raises(ValueError, match="cannot directionally assess a hypothesis"):
        _validate_assessment_record(altered, root)

    altered = json.loads(json.dumps(assessment))
    altered["observations"]["sar_temporal_series"]["temporal_direction_screen"]["pixel_counts"]["direction_reversal"] -= 1
    with pytest.raises(ValueError, match="temporal direction summary does not reproduce"):
        _validate_assessment_record(altered, root)

    altered = json.loads(json.dumps(assessment))
    altered_h4 = next(item for item in altered["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    altered_candidate_relation = next(
        item for item in altered_h4["evidence_assessments"]
        if item["evidence_id"] == "NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN"
    )
    altered_candidate_relation["relationship"] = "SUPPORTS"
    with pytest.raises(ValueError, match="cannot directionally assess a hypothesis"):
        _validate_assessment_record(altered, root)

    altered = json.loads(json.dumps(assessment))
    altered_water = next(item for item in altered["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    altered_rainfall = next(item for item in altered_water["evidence_assessments"] if item["evidence_id"] == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY")
    altered_rainfall["relationship"] = "SUPPORTS"
    with pytest.raises(ValueError, match="GPM precipitation chronology must remain linked as non-distinguishing context"):
        _validate_assessment_record(altered, root)


def test_all_active_case_assessments_validate_open_follow_up_designs():
    from pathlib import Path

    root = Path(__file__).parents[1]
    manifests = sorted((root / "data/cases").glob("*/investigation.json"))
    active = 0
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        relative_assessment = manifest.get("evidence_records", {}).get("cross_sensor_assessment")
        if not relative_assessment:
            continue
        assessment_path = root / relative_assessment
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        _validate_assessment_record(assessment, root)
        open_searches = [
            item for item in assessment["follow_up_evidence"]
            if item["purpose"] == "DISCRIMINATING_OBSERVATION"
            and item["availability_state"] == "NOT_SEARCHED"
        ]
        assert all(item.get("test_design") for item in open_searches), relative_assessment
        active += 1

    assert active >= 2
