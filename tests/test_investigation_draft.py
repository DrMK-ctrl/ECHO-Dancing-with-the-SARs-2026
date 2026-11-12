import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from echo.draft_store import LocalDraftStore
from echo.investigation import validate_investigation_contract
from echo.investigation_draft import (
    InvestigationDraftError,
    assess_investigation_draft,
    attach_followup_catalog_failure,
    attach_followup_catalog_screen,
    attach_followup_provider_qa_screen,
    attach_unreviewed_source,
    build_investigation_draft,
    revise_investigation_draft,
    screen_followup_source,
    validate_investigation_draft,
    _canonical_json,
)


def _hypotheses():
    return [
        {
            "statement": "Surface water change contributed to the measured radar response.",
            "scope_limit": "Only the selected AOI and acquisition interval.",
            "expected_observation": "An independently classified water transition overlaps the radar response.",
            "would_weaken_if": "Quality-valid water observations show no relevant transition.",
            "required_evidence": "Independent water observations with suitable time and spatial support.",
        },
        {
            "statement": "Soil moisture variation contributed to the measured radar response.",
            "scope_limit": "Only the selected AOI and acquisition interval.",
            "expected_observation": "Independent soil-moisture measurements vary over the affected cells.",
            "would_weaken_if": "Suitable soil-moisture observations remain stable over the interval.",
            "required_evidence": "Independent soil-moisture data with quality and scale appropriate to the AOI.",
        },
    ]


def _next_observation():
    return {
        "target_hypothesis_id": "H1",
        "action": "Retrieve an independent water classification covering both SAR acquisition dates.",
        "discriminating_question": "Does independent water evidence show a transition in the selected AOI?",
        "possible_interpretation": "A matching transition is consistent with the water hypothesis within the tested AOI.",
        "priority_reason": "It directly tests one open explanation using a source independent of the SAR pair.",
        "expected_observation": "Quality-accepted water observations show a spatially overlapping transition.",
        "would_weaken_if": "Quality-accepted observations cover the AOI but show no transition.",
        "inconclusive_if": "Cloud, timing, scale, or quality limits prevent an interpretable comparison.",
        "acceptance_gates": "Independent source\nSuitable acquisition timing\nAdequate AOI support and provider QA",
        "interpretation_limit": "This does not validate the SAR measurement or establish flood extent or cause.",
    }


def _asf_gcov_catalog_record():
    feature = {
        "id": "NISAR_TEST_SCENE",
        "properties": {"sceneName": "NISAR_TEST_SCENE", "processingLevel": "GCOV"},
        "geometry": None,
    }
    return {
        "schema_version": 1,
        "queried_at_utc": "2026-11-08T12:00:00+00:00",
        "source": {
            "provider": "Alaska Satellite Facility DAAC",
            "catalog_only": True,
            "pixels_downloaded": False,
            "returned_feature_count": 1,
            "potentially_truncated": False,
        },
        "query": {
            "dataset": "NISAR", "processing_level": "GCOV", "data_maturity": "PROVISIONAL",
            "longitude": -51.2, "latitude": -30.1, "bounds_wgs84": None,
            "start_date": "2026-11-01", "end_date": "2026-11-08",
        },
        "feature_count": 1,
        "features": [feature],
    }


def test_qa_held_nisar_pair_starts_unassessed_draft_without_inventing_pixels():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {
            "before": {"scene_id": "NISAR_BEFORE", "product_maturity": "PROVISIONAL"},
            "after": {"scene_id": "NISAR_AFTER", "product_maturity": "PROVISIONAL"},
        },
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "measurement": None,
        "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }

    draft = build_investigation_draft(
        source,
        question="Which mechanisms could explain a change in this area?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
        created_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )

    evidence_id = draft["evidence_artifacts"][0]["evidence_id"]
    assert draft["status"] == "DRAFT_NOT_ASSESSED"
    assert draft["evidence_artifacts"][0]["role"] == "SAR_PAIR_HELD_AT_PROVIDER_QA"
    assert draft["evidence_artifacts"][0]["status"] == "QA_HELD"
    assert draft["source_records"][evidence_id] == source
    assert draft["evidence_artifacts"][0]["sha256"] == hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()
    assert all(item["state"] == "NOT_EVALUATED" for item in draft["hypotheses"])
    assert all(item["evidence_refs"] == item["evidence_assessments"] == [] for item in draft["hypotheses"])
    assert draft["follow_up_evidence"][0]["target_hypothesis_ids"] == ["H1"]
    assert draft["follow_up_evidence"][0]["test_design"]["does_not_test_hypothesis_ids"] == ["H2"]
    assert draft["follow_up_evidence"][0]["availability_state"] == "NOT_SEARCHED"
    validate_investigation_contract(draft)


def test_identity_held_nisar_pair_stays_nondirectional_in_investigation_draft():
    identity = {"status": "MISMATCH", "checks": [{"field": "orbit", "result": "MISMATCH"}]}
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "IDENTITY_HELD",
        "source_products": {"before": {"scene_id": "before"}, "after": {"scene_id": "after"}},
        "provider_qa": {
            role: {"evidence": {"status": "PASS", "catalog_identity_crosscheck": identity}}
            for role in ("before", "after")
        },
        "held_roles": ["before"],
        "analysis_gates": {
            "provider_qa": "PASS",
            "product_identification": "HELD_CATALOG_CROSSCHECK",
            "measurement_arrays": "NOT_READ",
            "change_calculation": "NOT_PERFORMED",
        },
        "measurement": None,
        "manifest": None,
    }

    draft = build_investigation_draft(
        source,
        question="Which explanations remain open for this observation pair?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
        created_at_utc=datetime(2026, 11, 9, tzinfo=timezone.utc),
    )

    assert draft["evidence_artifacts"][0]["role"] == "SAR_PAIR_HELD_AT_PRODUCT_IDENTITY"
    assert draft["evidence_artifacts"][0]["status"] == "IDENTITY_HELD"
    assert all(item["state"] == "NOT_EVALUATED" for item in draft["hypotheses"])
    validate_investigation_contract(draft)


def test_followup_catalog_search_is_traceable_metadata_only_and_cannot_satisfy_test():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(
        sar_source,
        question="Which explanations remain compatible with these observations?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )
    original_followup = json.loads(json.dumps(draft["follow_up_evidence"]))
    catalog = _asf_gcov_catalog_record()
    staged = attach_followup_catalog_screen(
        draft, catalog, attached_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc)
    )
    artifact = staged["evidence_artifacts"][1]
    source_record = staged["source_records"][artifact["evidence_id"]]
    assert source_record["schema_version"] == 2
    assert artifact["role"] == "CATALOG_AVAILABILITY_METADATA_ONLY"
    assert artifact["source_review_state"] == "CATALOG_STRUCTURE_VALIDATED_METADATA_ONLY"
    assert source_record["follow_up_link"]["follow_up_id"] == original_followup[0]["follow_up_id"]
    assert source_record["follow_up_link"]["target_hypothesis_id"] == "H1"
    assert source_record["search_window_comparison"]["state"] == "NO_PLANNED_WINDOW"
    assert source_record["test_compatibility_state"] == "NOT_ASSESSED_METADATA_ONLY"
    assert source_record["catalog_record"] == catalog
    linked_followup = staged["follow_up_evidence"][0]
    assert linked_followup["availability_state"] == "CANDIDATE_RETRIEVED_UNASSESSED"
    assert linked_followup["evidence_refs"] == [artifact["evidence_id"]]
    assert linked_followup["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert all(item["state"] == "NOT_EVALUATED" and not item["evidence_refs"] for item in staged["hypotheses"])
    assert validate_investigation_draft(json.loads(json.dumps(staged))) == json.loads(json.dumps(staged))

    no_match_catalog = json.loads(json.dumps(catalog))
    no_match_catalog["features"] = []
    no_match_catalog["feature_count"] = 0
    no_match_catalog["source"]["returned_feature_count"] = 0
    no_match = attach_followup_catalog_screen(draft, no_match_catalog)
    assert no_match["follow_up_evidence"][0]["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    assert no_match["follow_up_evidence"][0]["evidence_refs"] == [no_match["evidence_artifacts"][1]["evidence_id"]]

    failed = attach_followup_catalog_failure(draft, {
        "schema_version": 1, "observer": "ECHO", "provider": "ASF", "service": "ASF_CMR_GCOV_CATALOG",
        "outcome": "REQUEST_FAILED_NO_RESULT", "failure_code": "CATALOG_REQUEST_FAILED",
        "retryable": True, "attempted_at_utc": "2026-11-08T12:00:00+00:00",
        "completed_at_utc": "2026-11-08T12:00:30+00:00",
        "query": {
            "dataset": "NISAR", "processing_level": "GCOV", "data_maturity": "PROVISIONAL",
            "longitude": -51.2, "latitude": -30.1, "bounds_wgs84": None,
            "start_date": "2026-11-01", "end_date": "2026-11-08", "result_limit": 1000,
        },
    })
    failed_followup = failed["follow_up_evidence"][0]
    assert failed_followup["availability_state"] == "SEARCH_FAILED_RETRYABLE"
    assert failed_followup["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert failed_followup["evidence_refs"] == []
    assert len(failed_followup["catalog_search_attempts"]) == 1
    attempt = failed_followup["catalog_search_attempts"][0]
    assert attempt["query"]["start_date"] == "2026-11-01"
    assert attempt["follow_up_link"]["test_design_sha256"] == hashlib.sha256(
        _canonical_json(failed_followup["test_design"])
    ).hexdigest()
    assert all(item["state"] == "NOT_EVALUATED" and not item["evidence_refs"] for item in failed["hypotheses"])
    assert validate_investigation_draft(json.loads(json.dumps(failed))) == json.loads(json.dumps(failed))

    tampered = json.loads(json.dumps(failed))
    tampered["follow_up_evidence"][0]["catalog_search_attempts"][0]["query"]["start_date"] = "2026-10-01"
    with pytest.raises(InvestigationDraftError, match="checksum"):
        validate_investigation_draft(tampered)

    retry_succeeded = attach_followup_catalog_screen(failed, catalog)
    assert retry_succeeded["follow_up_evidence"][0]["availability_state"] == "CANDIDATE_RETRIEVED_UNASSESSED"
    assert len(retry_succeeded["follow_up_evidence"][0]["catalog_search_attempts"]) == 1
    assert retry_succeeded["follow_up_evidence"][0]["evidence_refs"] == [retry_succeeded["evidence_artifacts"][1]["evidence_id"]]

    with pytest.raises(InvestigationDraftError, match="cannot directionally support"):
        assess_investigation_draft(staged, [{
            "hypothesis_id": "H1", "evidence_id": artifact["evidence_id"],
            "relationship": "SUPPORTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The catalog listed a matching observation.",
            "review_basis": "I inspected the metadata search record and its query.",
            "limitations": "No product pixels or QA were retrieved or reviewed.",
        }])
    with pytest.raises(InvestigationDraftError, match="follow-up screening must reference"):
        screen_followup_source(
            staged, evidence_id=artifact["evidence_id"],
            gate_results=[{"gate": gate, "result": "MET"} for gate in _next_observation()["acceptance_gates"].splitlines()],
            review_basis="I inspected the catalog response and its search metadata.",
            limitations="Catalog availability does not show suitability or provider quality.",
        )

    malformed = _asf_gcov_catalog_record()
    malformed["feature_count"] = 2
    with pytest.raises(InvestigationDraftError, match="provenance or result count"):
        attach_followup_catalog_screen(draft, malformed)


def test_catalog_search_window_deviation_is_recorded_and_validated():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    planned = {
        "start_date_inclusive": "2026-10-25",
        "end_date_inclusive": "2026-11-06",
    }
    draft = build_investigation_draft(
        sar_source,
        question="Which explanations fit the selected radar response?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation() | {"catalog_search_window": planned},
    )
    catalog = _asf_gcov_catalog_record()
    deviated = attach_followup_catalog_screen(draft, catalog)
    artifact_id = deviated["follow_up_evidence"][0]["evidence_refs"][0]
    source = deviated["source_records"][artifact_id]
    assert source["search_window_comparison"] == {
        "state": "DEVIATES_FROM_PLANNED_WINDOW",
        "planned_window": planned,
        "executed_window": {
            "start_date_inclusive": "2026-11-01",
            "end_date_inclusive": "2026-11-08",
        },
    }
    validate_investigation_draft(deviated)

    tampered = json.loads(json.dumps(deviated))
    tampered["source_records"][artifact_id]["search_window_comparison"]["state"] = "MATCHES_PLANNED_WINDOW"
    tampered_artifact = next(item for item in tampered["evidence_artifacts"] if item["evidence_id"] == artifact_id)
    import hashlib
    tampered_artifact["sha256"] = hashlib.sha256(_canonical_json(tampered["source_records"][artifact_id])).hexdigest()
    tampered["source_staging_history"][0]["sha256"] = tampered_artifact["sha256"]
    with pytest.raises(InvestigationDraftError, match="search-window comparison does not match its query"):
        validate_investigation_draft(tampered)

    missing_comparison = json.loads(json.dumps(deviated))
    del missing_comparison["source_records"][artifact_id]["search_window_comparison"]
    missing_artifact = next(item for item in missing_comparison["evidence_artifacts"] if item["evidence_id"] == artifact_id)
    missing_artifact["sha256"] = hashlib.sha256(_canonical_json(missing_comparison["source_records"][artifact_id])).hexdigest()
    missing_comparison["source_staging_history"][0]["sha256"] = missing_artifact["sha256"]
    with pytest.raises(InvestigationDraftError, match="missing its search-window comparison"):
        validate_investigation_draft(missing_comparison)


def test_followup_provider_qa_links_exact_catalog_scene_without_becoming_hypothesis_evidence():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(
        sar_source,
        question="Which explanations remain compatible with these observations?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )
    catalog = _asf_gcov_catalog_record()
    catalog["features"][0]["properties"]["fileID"] = "NISAR_TEST_SCENE"
    draft = attach_followup_catalog_screen(draft, catalog)
    catalog_artifact = draft["evidence_artifacts"][1]
    qa_record = {
        "record_type": "ECHO_PROVIDER_QA_INSPECTION",
        "record_version": 1,
        "exported_at_utc": "2026-11-08T12:30:00+00:00",
        "source_catalog": {"provider": "Alaska Satellite Facility DAAC", "query": catalog["query"], "feature": catalog["features"][0]},
        "provider_qa_summary": {
            "scene_id": "NISAR_TEST_SCENE", "retrieved_at_utc": "2026-11-08T12:29:00+00:00",
            "artifact_size_bytes": 128, "artifact_sha256": "a" * 64,
            "evidence": {"status": "FAIL", "check_details": []},
            "retrieval": {"provider": "Alaska Satellite Facility DAAC", "method": "bounded HTTPS range"},
        },
        "interpretation_limits": ["Provider QA does not establish scientific suitability."],
    }
    staged = attach_followup_provider_qa_screen(
        draft,
        catalog_availability_evidence_id=catalog_artifact["evidence_id"],
        provider_qa_record=qa_record,
        attached_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )
    artifact = staged["evidence_artifacts"][2]
    source = staged["source_records"][artifact["evidence_id"]]
    assert artifact["role"] == "FOLLOWUP_PROVIDER_QA_METADATA_ONLY"
    assert artifact["source_review_state"] == "PROVIDER_QA_LINKED_METADATA_ONLY"
    assert source["scene_id"] == "NISAR_TEST_SCENE"
    assert source["catalog_availability_evidence_id"] == catalog_artifact["evidence_id"]
    assert source["provider_qa_record"]["provider_qa_summary"]["evidence"]["status"] == "FAIL"
    assert source["test_compatibility_state"] == "NOT_ASSESSED_METADATA_ONLY"
    assert source["provider_response_verification"] == "RETRIEVAL_PROVENANCE_RETAINED_NOT_REVERIFIED_AT_ATTACHMENT"
    assert staged["follow_up_evidence"][0]["availability_state"] == "CANDIDATE_RETRIEVED_UNASSESSED"
    assert staged["follow_up_evidence"][0]["evidence_refs"] == [catalog_artifact["evidence_id"], artifact["evidence_id"]]
    assert all(item["state"] == "NOT_EVALUATED" and not item["evidence_refs"] for item in staged["hypotheses"])
    assert validate_investigation_draft(json.loads(json.dumps(staged))) == json.loads(json.dumps(staged))

    with pytest.raises(InvestigationDraftError, match="cannot directionally support"):
        assess_investigation_draft(staged, [{
            "hypothesis_id": "H1", "evidence_id": artifact["evidence_id"],
            "relationship": "SUPPORTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The QA record is related to this hypothesis.",
            "review_basis": "I inspected the provider QA CSV record.",
            "limitations": "The QA summary does not measure the hypothesized surface process.",
        }])

    with pytest.raises(InvestigationDraftError, match="follow-up screening must reference"):
        screen_followup_source(
            staged,
            evidence_id=artifact["evidence_id"],
            gate_results=[],
            review_basis="The product QA status alone cannot assess test gates.",
            limitations="This metadata does not establish a compatible observation.",
        )

    with pytest.raises(InvestigationDraftError, match="does not match a scene"):
        attach_followup_provider_qa_screen(
            draft,
            catalog_availability_evidence_id=catalog_artifact["evidence_id"],
            provider_qa_record={**qa_record, "source_catalog": {**qa_record["source_catalog"], "feature": {**qa_record["source_catalog"]["feature"], "properties": {"fileID": "OTHER_SCENE"}}}},
        )


def test_exact_primary_source_json_survives_serialized_draft_round_trip():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {
            "before": {"scene_id": "NISAR_BEFORE", "product_maturity": "PROVISIONAL"},
            "after": {"scene_id": "NISAR_AFTER", "product_maturity": "PROVISIONAL"},
        },
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "measurement": None,
        "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
        "numeric_probe": 1.0,
    }
    source_json = json.dumps(source, separators=(",", ":"), ensure_ascii=False)
    draft = build_investigation_draft(
        source,
        source_record_json=source_json,
        question="Which mechanisms could explain a change in this area?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )
    restored = json.loads(json.dumps(draft))
    evidence_id = draft["evidence_artifacts"][0]["evidence_id"]
    assert restored["source_records"][evidence_id] == source_json
    assert draft["evidence_artifacts"][0]["sha256"] == hashlib.sha256(source_json.encode()).hexdigest()
    validate_investigation_draft(restored)
    mismatched_text = source_json.replace('"numeric_probe":1.0', '"numeric_probe":true')
    with pytest.raises(InvestigationDraftError, match="does not match"):
        build_investigation_draft(
            source,
            source_record_json=mismatched_text,
            question="Which mechanisms could explain a change in this area?",
            hypotheses=_hypotheses(),
            next_observation=_next_observation(),
        )


def test_measured_provisional_nisar_draft_preserves_provider_qa_and_maturity():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "MEASURED_DESCRIPTIVE_ONLY",
        "source_products": {
            "before": {"scene_id": "NISAR_BEFORE", "product_maturity": "PROVISIONAL"},
            "after": {"scene_id": "NISAR_AFTER", "product_maturity": "PROVISIONAL"},
        },
        "provider_qa": {"before": {"evidence": {"status": "PASS"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": {"quantity": "signed_gamma0_log_ratio_db", "values_db": [[0.0]], "valid_mask": [[True]]},
        "manifest": {"analysis": {"method": "fixture for contract test"}},
    }

    draft = build_investigation_draft(
        source,
        question="Which mechanisms could explain a change in this area?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )

    copied = draft["source_records"][draft["evidence_artifacts"][0]["evidence_id"]]
    assert copied["source_products"]["before"]["product_maturity"] == "PROVISIONAL"
    assert copied["provider_qa"]["before"]["evidence"]["status"] == "PASS"
    assert draft["evidence_artifacts"][0]["role"] == "DESCRIPTIVE_NISAR_SAR_MEASUREMENT"
    assert draft["interpretation_limits"]


def test_retained_opera_temporal_series_can_start_a_diagnostic_investigation_draft():
    source = json.loads(
        (Path(__file__).resolve().parents[1] / "data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json")
        .read_text(encoding="utf-8")
    )
    draft = build_investigation_draft(
        source,
        question="Which explanations remain compatible with this SAR time series?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )

    artifact = draft["evidence_artifacts"][0]
    assert artifact["role"] == "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_TEMPORAL_SERIES"
    assert artifact["status"] == "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
    assert len(draft["source_records"][artifact["evidence_id"]]["observations"]) == 3
    with pytest.raises(InvestigationDraftError, match="cannot directionally support"):
        assess_investigation_draft(draft, [{
            "hypothesis_id": "H1", "evidence_id": artifact["evidence_id"],
            "relationship": "SUPPORTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The series appears consistent with the water hypothesis.",
            "review_basis": "I inspected the retained three-date diagnostic series.",
            "limitations": "No consolidated provider QA verdict is available for these observations.",
        }])
    assessed = assess_investigation_draft(draft, [{
        "hypothesis_id": "H1", "evidence_id": artifact["evidence_id"],
        "relationship": "DOES_NOT_DISTINGUISH", "evidence_fit": "CONTEXT_ONLY",
        "rationale": "The diagnostic series does not isolate the physical driver.",
        "review_basis": "I inspected the retained three-date diagnostic series.",
        "limitations": "No consolidated provider QA verdict is available for these observations.",
    }])
    assert assessed["status"] == "DRAFT_ANALYST_ASSESSED_UNVERIFIED"
    assert assessed["hypotheses"][0]["state"] == "UNRESOLVED"


def test_saved_draft_challenge_reports_recorded_evidence_without_recomputing_or_upgrading_qa():
    from echo.adversarial import build_draft_adversarial_challenge

    source = json.loads(
        (Path(__file__).resolve().parents[1] / "data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json")
        .read_text(encoding="utf-8")
    )
    draft = build_investigation_draft(
        source,
        question="Which explanations remain compatible with this SAR time series?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )
    assessed = assess_investigation_draft(draft, [{
        "hypothesis_id": "H1",
        "evidence_id": draft["evidence_artifacts"][0]["evidence_id"],
        "relationship": "DOES_NOT_DISTINGUISH",
        "evidence_fit": "CONTEXT_ONLY",
        "rationale": "The diagnostic time series does not isolate the physical driver.",
        "review_basis": "Inspected the retained observations and their diagnostic disposition.",
        "limitations": "Provider QA remains unresolved for the series.",
    }])

    report = build_draft_adversarial_challenge(
        assessed, hypothesis_id="H1", draft_sha256="a" * 64
    )

    assert report["status"] == "PROVISIONAL_UNVERIFIED_DRAFT_CHALLENGE"
    assert report["observation"]["source_status"] == "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
    assert report["observation"]["measurement_values_recomputed"] is False
    assert report["evidence_review"]["recorded_relationships"][0]["relationship"] == "DOES_NOT_DISTINGUISH"
    assert report["evidence_review"]["recorded_relationships"][0]["relationship_basis"] == "RECORDED_UNAUTHENTICATED_ANALYST_ASSESSMENT"
    assert report["sensitivity_review"]["state"] == "NOT_RECOMPUTED_FOR_DRAFT"
    assert "H1" in report["next_observations"][0]["target_hypothesis_ids"]
    assert "does not validate provider QA" in report["interpretation_limit"]

    with pytest.raises(ValueError, match="only a saved, analyst-assessed draft"):
        build_draft_adversarial_challenge(draft, hypothesis_id="H1", draft_sha256="a" * 64)
    with pytest.raises(ValueError, match="exactly one"):
        build_draft_adversarial_challenge(assessed, hypothesis_id="missing", draft_sha256="a" * 64)


def test_opera_temporal_series_draft_rejects_altered_quality_review():
    source = json.loads(
        (Path(__file__).resolve().parents[1] / "data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json")
        .read_text(encoding="utf-8")
    )
    source["quality_review"]["per_observation"][0]["rfi_metadata"]["in_band_out_band_power_ratio"] = 0
    with pytest.raises(InvestigationDraftError, match="quality review does not match its retained inputs"):
        build_investigation_draft(
            source,
            question="Which explanations remain compatible with this SAR time series?",
            hypotheses=_hypotheses(),
            next_observation=_next_observation(),
        )


def test_real_single_observation_preview_starts_non_directional_investigation_draft():
    source = json.loads(
        (Path(__file__).resolve().parents[1] / "data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json")
        .read_text(encoding="utf-8")
    )
    draft = build_investigation_draft(
        source,
        question="What additional evidence could distinguish the possible causes of this radar response?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )

    artifact = draft["evidence_artifacts"][0]
    assert artifact["role"] == "DESCRIPTIVE_NISAR_SINGLE_OBSERVATION"
    assert artifact["status"] == "QA_HELD_DIAGNOSTIC_PREVIEW"
    assert artifact["record_type"] == "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW"
    assert artifact["evidence_id"].startswith("NISAR-OBS-")
    assert draft["source_records"][artifact["evidence_id"]] == source
    assert "no temporal change" in draft["interpretation_limits"][-1]
    assert all(hypothesis["state"] == "NOT_EVALUATED" for hypothesis in draft["hypotheses"])

    with pytest.raises(InvestigationDraftError, match="cannot directionally support"):
        assess_investigation_draft(draft, [{
            "hypothesis_id": "H1",
            "evidence_id": artifact["evidence_id"],
            "relationship": "SUPPORTS",
            "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The measured backscatter is consistent with the water hypothesis.",
            "review_basis": "I inspected the selected NISAR single-observation preview.",
            "limitations": "Only one acquisition is available and provider QA reports FAIL.",
        }])


def test_single_observation_preview_rejects_mismatched_provider_qa_and_measurement_grid():
    source = json.loads(
        (Path(__file__).resolve().parents[1] / "data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json")
        .read_text(encoding="utf-8")
    )
    mismatched_qa = json.loads(json.dumps(source))
    mismatched_qa["source"]["provider_qa_status"] = "PASS"
    with pytest.raises(InvestigationDraftError, match="identity or QA provenance"):
        build_investigation_draft(
            mismatched_qa,
            question="What additional evidence could distinguish the possible causes of this radar response?",
            hypotheses=_hypotheses(),
            next_observation=_next_observation(),
        )

    mismatched_grid = json.loads(json.dumps(source))
    mismatched_grid["grid"]["window"]["shape"][0] -= 1
    with pytest.raises(InvestigationDraftError, match="does not match its bounded grid"):
        build_investigation_draft(
            mismatched_grid,
            question="What additional evidence could distinguish the possible causes of this radar response?",
            hypotheses=_hypotheses(),
            next_observation=_next_observation(),
        )


def test_opera_temporal_series_rejects_missing_per_observation_qa_links():
    source = json.loads(
        (Path(__file__).resolve().parents[1] / "data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json")
        .read_text(encoding="utf-8")
    )
    source["provider_qa"]["per_observation"] = source["provider_qa"]["per_observation"][:-1]
    with pytest.raises(InvestigationDraftError, match="per-observation QA links"):
        build_investigation_draft(
            source,
            question="Which explanations remain compatible with this SAR time series?",
            hypotheses=_hypotheses(),
            next_observation=_next_observation(),
        )


def test_diagnostic_opera_source_remains_distinct_and_quality_limited():
    source = {
        "record_type": "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON",
        "provider_qa": {"status": "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"},
        "measurement": {"quantity": "signed_gamma0_log_ratio_db", "values_db": [[-1.0]]},
        "grid": {"window": {"bounds_wgs84": [0, 0, 1, 1]}},
        "source_products": {"before": {"scene_id": "S1_BEFORE"}, "after": {"scene_id": "S1_AFTER"}},
    }

    draft = build_investigation_draft(
        source,
        question="Which mechanisms could explain a change in this area?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )

    artifact = draft["evidence_artifacts"][0]
    assert artifact["role"] == "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT"
    assert artifact["status"] == "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
    assert draft["source_records"][artifact["evidence_id"]]["provider_qa"]["status"].endswith("NO_CONSOLIDATED_DISPOSITION")
    with pytest.raises(InvestigationDraftError, match="cannot directionally support"):
        assess_investigation_draft(draft, [{
            "hypothesis_id": "H1", "evidence_id": artifact["evidence_id"],
            "relationship": "SUPPORTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The diagnostic measurement appears consistent with the hypothesis.",
            "review_basis": "I inspected the diagnostic product pair record.",
            "limitations": "The source has no consolidated provider quality disposition.",
        }])


@pytest.mark.parametrize(
    "source,question,hypotheses",
    [
        ({"record_type": "ECHO_GCOV_PAIR_ANALYSIS", "status": "UNKNOWN"}, "Which mechanisms could explain a change?", _hypotheses()),
        ({"record_type": "ECHO_GCOV_PAIR_ANALYSIS", "status": "QA_HELD"}, "Which mechanisms could explain a change?", _hypotheses()[:1]),
        ({"record_type": "ECHO_GCOV_PAIR_ANALYSIS", "status": "QA_HELD"}, "Short", _hypotheses()),
        ({"record_type": "ECHO_GCOV_PAIR_ANALYSIS", "status": "QA_HELD"}, "Which mechanisms could explain a change?", [_hypotheses()[0], _hypotheses()[0]]),
    ],
)
def test_invalid_or_noncompeting_draft_inputs_are_rejected(source, question, hypotheses):
    with pytest.raises(InvestigationDraftError):
        build_investigation_draft(source, question=question, hypotheses=hypotheses, next_observation=_next_observation())


def test_next_observation_must_target_one_hypothesis_and_have_acceptance_gates():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None,
        "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    bad_target = _next_observation() | {"target_hypothesis_id": "H9"}
    with pytest.raises(InvestigationDraftError, match="one of the authored hypotheses"):
        build_investigation_draft(source, question="What remains unknown here?", hypotheses=_hypotheses(), next_observation=bad_target)
    no_gates = _next_observation() | {"acceptance_gates": " \n "}
    with pytest.raises(InvestigationDraftError, match="at least one acceptance gate"):
        build_investigation_draft(source, question="What remains unknown here?", hypotheses=_hypotheses(), next_observation=no_gates)


def test_next_observation_catalog_window_is_validated_and_retained():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    next_observation = _next_observation() | {
        "catalog_search_window": {
            "start_date_inclusive": "2026-10-25",
            "end_date_inclusive": "2026-11-06",
        }
    }
    draft = build_investigation_draft(
        source,
        question="Which mechanisms could explain this observation?",
        hypotheses=_hypotheses(),
        next_observation=next_observation,
    )
    assert draft["follow_up_evidence"][0]["test_design"]["catalog_search_window"] == next_observation["catalog_search_window"]

    reversed_window = _next_observation() | {
        "catalog_search_window": {
            "start_date_inclusive": "2026-11-06",
            "end_date_inclusive": "2026-10-25",
        }
    }
    with pytest.raises(InvestigationDraftError, match="start must not follow its end"):
        build_investigation_draft(
            source,
            question="Which mechanisms could explain this observation?",
            hypotheses=_hypotheses(),
            next_observation=reversed_window,
        )


def test_attached_source_is_checksummed_but_does_not_enter_hypothesis_assessments():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None,
        "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(
        sar_source,
        question="What remains uncertain about this area?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )
    attached = {
        "record_type": "USER_PROVIDED_CONTEXT_RECORD",
        "status": "REPORT_CONTEXT_ONLY",
        "provider": "Example research institution",
        "observation_time_utc": "2026-01-01T00:00:00Z",
    }

    updated = attach_unreviewed_source(draft, attached, attached_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc))
    artifact = updated["evidence_artifacts"][1]
    assert artifact["role"] == "USER_SUPPLIED_SOURCE_NOT_REVIEWED"
    assert artifact["source_review_state"] == "NOT_REVIEWED"
    assert artifact["independence_state"] == "NOT_ASSESSED"
    assert artifact["sha256"] == hashlib.sha256(
        json.dumps(attached, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()
    assert all(not hypothesis["evidence_refs"] and not hypothesis["evidence_assessments"] for hypothesis in updated["hypotheses"])
    assert updated["follow_up_evidence"][0]["availability_state"] == "NOT_SEARCHED"
    assert validate_investigation_draft(updated) == updated
    with pytest.raises(InvestigationDraftError, match="unassessed draft cannot contain"):
        altered_relationship = json.loads(json.dumps(updated))
        altered_relationship["hypotheses"][0]["state"] = "SUPPORTED_WITHIN_SCOPE"
        validate_investigation_draft(altered_relationship)
    with pytest.raises(InvestigationDraftError, match="history does not match"):
        altered_history = json.loads(json.dumps(updated))
        altered_history["source_staging_history"][0]["sha256"] = "0" * 64
        validate_investigation_draft(altered_history)
    with pytest.raises(InvestigationDraftError, match="staged source history does not match its artifact"):
        altered_lineage = json.loads(json.dumps(updated))
        altered_lineage["evidence_artifacts"][1]["lineage"]["derived_from_evidence_ids"] = [
            altered_lineage["evidence_artifacts"][0]["evidence_id"]
        ]
        validate_investigation_draft(altered_lineage)
    with pytest.raises(InvestigationDraftError, match="already staged"):
        attach_unreviewed_source(updated, attached)


def test_staged_sources_retain_declared_lineage_and_reject_cycles_or_unknown_ids():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(
        sar_source,
        question="Which explanations remain plausible for this measured area?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
        created_at_utc=datetime(2026, 11, 9, tzinfo=timezone.utc),
    )
    primary_id = draft["evidence_artifacts"][0]["evidence_id"]
    first = attach_unreviewed_source(
        draft,
        {"record_type": "NASA_CONTEXT_RECORD", "provider": "NASA", "status": "SCREENED"},
        lineage={"shares_source_observations_with": [primary_id]},
        attached_at_utc=datetime(2026, 11, 9, 0, 1, tzinfo=timezone.utc),
    )
    first_id = first["evidence_artifacts"][1]["evidence_id"]
    second = attach_unreviewed_source(
        first,
        {"record_type": "DERIVED_CONTEXT_RECORD", "provider": "NASA", "status": "DERIVED"},
        lineage={"derived_from_evidence_ids": [first_id]},
        attached_at_utc=datetime(2026, 11, 9, 0, 2, tzinfo=timezone.utc),
    )
    second_id = second["evidence_artifacts"][2]["evidence_id"]
    assert second["evidence_artifacts"][1]["lineage"] == {
        "derived_from_evidence_ids": [],
        "shares_source_observations_with": [primary_id],
    }
    assert second["evidence_artifacts"][2]["lineage"] == {
        "derived_from_evidence_ids": [first_id],
        "shares_source_observations_with": [],
    }
    assert second["source_staging_history"][1]["lineage"] == second["evidence_artifacts"][2]["lineage"]
    assert all(item["independence_state"] == "NOT_ASSESSED" for item in second["evidence_artifacts"][1:])
    assert validate_investigation_draft(second) == second

    with pytest.raises(InvestigationDraftError, match="not already staged"):
        attach_unreviewed_source(
            draft,
            {"record_type": "UNLINKED_SOURCE"},
            lineage={"derived_from_evidence_ids": ["MISSING-EVIDENCE-ID"]},
        )

    cyclic = json.loads(json.dumps(second))
    cyclic["evidence_artifacts"][1]["lineage"]["derived_from_evidence_ids"] = [second_id]
    cyclic["source_staging_history"][0]["lineage"] = cyclic["evidence_artifacts"][1]["lineage"]
    with pytest.raises(InvestigationDraftError, match="evidence derivation links contain a cycle"):
        validate_investigation_draft(cyclic)


def test_followup_screen_links_staged_evidence_without_evaluating_hypotheses(tmp_path):
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(
        sar_source,
        question="What remains uncertain about this area?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )
    source = {"record_type": "USER_PROVIDED_CONTEXT_RECORD", "status": "NOT_REVIEWED", "provider": "Example source"}
    draft = attach_unreviewed_source(draft, source)
    evidence_id = draft["evidence_artifacts"][1]["evidence_id"]
    gates = [{"gate": gate, "result": "MET"} for gate in _next_observation()["acceptance_gates"].splitlines()]

    limited = screen_followup_source(
        draft,
        evidence_id=evidence_id,
        gate_results=[
            {**item, "result": "NOT_MET" if index == 0 else item["result"]}
            for index, item in enumerate(gates)
        ],
        review_basis="Inspected source metadata, product quality, and AOI/date coverage records.",
        limitations="Analyst-entered gate results do not authenticate the source or establish causation.",
        screened_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )
    assert limited["follow_up_evidence"][0]["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    legacy_single_screen = json.loads(json.dumps(limited))
    legacy_single_screen["follow_up_evidence"][0].pop("screening_history")
    assert validate_investigation_draft(legacy_single_screen) == legacy_single_screen
    second_source = {
        "record_type": "SECOND_USER_CONTEXT_RECORD",
        "status": "NOT_REVIEWED",
        "provider": "Another source",
    }
    compared = attach_unreviewed_source(limited, second_source)
    second_evidence_id = compared["evidence_artifacts"][2]["evidence_id"]
    screened = screen_followup_source(
        compared,
        evidence_id=second_evidence_id,
        gate_results=gates,
        review_basis="Inspected the second source's acquisition, product quality, and AOI/date coverage.",
        limitations="The analyst-entered screen does not authenticate this source or establish causation.",
        screened_at_utc=datetime(2026, 11, 8, 1, tzinfo=timezone.utc),
    )
    followup = screened["follow_up_evidence"][0]
    assert followup["availability_state"] == "ANALYST_SCREENED_CANDIDATE"
    assert followup["evidence_refs"] == [evidence_id, second_evidence_id]
    assert [item["source_evidence_id"] for item in followup["screening_history"]] == [evidence_id, second_evidence_id]
    assert followup["screening_review"]["source_sha256"] == screened["evidence_artifacts"][2]["sha256"]
    assert all(item["state"] == "NOT_EVALUATED" for item in screened["hypotheses"])
    assert screened["evidence_artifacts"][1]["source_review_state"] == "NOT_REVIEWED"
    assert validate_investigation_draft(json.loads(json.dumps(screened))) == json.loads(json.dumps(screened))
    store = LocalDraftStore(tmp_path / "drafts")
    saved = store.save(screened)
    assert store.load(saved["draft_id"]) == screened

    with pytest.raises(InvestigationDraftError, match="already has a follow-up screen"):
        screen_followup_source(
            screened, evidence_id=second_evidence_id, gate_results=gates,
            review_basis="Inspected the second source and its metadata.",
            limitations="This source was already screened under the same registered test.",
        )

    with pytest.raises(InvestigationDraftError, match="one screening result for every"):
        screen_followup_source(
            draft, evidence_id=evidence_id, gate_results=gates[:-1],
            review_basis="Inspected the source record and its stated metadata.",
            limitations="The source coverage and processing quality remain unknown.",
        )
    with pytest.raises(InvestigationDraftError, match="match the pre-registered gate list"):
        screen_followup_source(
            draft, evidence_id=evidence_id, gate_results=list(reversed(gates)),
            review_basis="Inspected the source record and its stated metadata.",
            limitations="The source coverage and processing quality remain unknown.",
        )
    with pytest.raises(InvestigationDraftError, match="source record"):
        screen_followup_source(
            draft, evidence_id=draft["evidence_artifacts"][0]["evidence_id"], gate_results=gates,
            review_basis="Inspected the source record and its stated metadata.",
            limitations="The source coverage and processing quality remain unknown.",
        )
    corrupted = json.loads(json.dumps(screened))
    corrupted["follow_up_evidence"][0]["screening_review"]["review_basis"] += " altered"
    corrupted["follow_up_evidence"][0]["screening_history"][-1]["review_basis"] += " altered"
    with pytest.raises(InvestigationDraftError, match="checksum mismatch"):
        validate_investigation_draft(corrupted)


def test_target_hypothesis_cannot_use_staged_candidate_directionally_before_all_gates_pass():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(
        sar_source,
        question="Which explanation is consistent with the available observation?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
    )
    draft = attach_unreviewed_source(draft, {
        "record_type": "USER_PROVIDED_CONTEXT_RECORD", "status": "NOT_REVIEWED", "provider": "Example source",
    })
    evidence_id = draft["evidence_artifacts"][1]["evidence_id"]
    relation = {
        "hypothesis_id": "H1", "evidence_id": evidence_id,
        "relationship": "SUPPORTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
        "rationale": "The source describes an observation expected by this explanation.",
        "review_basis": "I inspected the source metadata and relevant observation description.",
        "limitations": "Provider authenticity and the observation's scientific quality remain unverified.",
    }
    with pytest.raises(InvestigationDraftError, match="must first pass every pre-registered follow-up gate"):
        assess_investigation_draft(draft, [relation])

    gates = [{"gate": gate, "result": "MET"} for gate in _next_observation()["acceptance_gates"].splitlines()]
    limited = screen_followup_source(
        draft,
        evidence_id=evidence_id,
        gate_results=[{**item, "result": "NOT_MET" if index == 0 else item["result"]} for index, item in enumerate(gates)],
        review_basis="Inspected the candidate record, its stated date, and the coverage metadata.",
        limitations="Provider quality and the failed observation-timing gate remain unresolved.",
    )
    for relationship in ("SUPPORTS", "CONTRADICTS"):
        with pytest.raises(InvestigationDraftError, match="failed or left any registered gate unknown"):
            assess_investigation_draft(limited, [{**relation, "relationship": relationship}])
    nondirectional = assess_investigation_draft(limited, [{
        **relation,
        "relationship": "DOES_NOT_DISTINGUISH",
        "evidence_fit": "UNKNOWN",
    }])
    assert nondirectional["hypotheses"][0]["state"] == "UNRESOLVED"

    passed = screen_followup_source(
        draft,
        evidence_id=evidence_id,
        gate_results=gates,
        review_basis="Inspected the candidate record, its stated date, and the coverage metadata.",
        limitations="Provider authenticity and the source's scientific quality remain unverified.",
    )
    assessed = assess_investigation_draft(passed, [relation])
    assert assessed["hypotheses"][0]["state"] == "SUPPORTED_WITHIN_SCOPE"
    assert assessed["evidence_artifacts"][1]["source_review_state"] == "NOT_REVIEWED"
    screen_sha256 = passed["follow_up_evidence"][0]["screening_history"][0]["sha256"]
    assert assessed["analyst_assessment"]["records"][0]["followup_screen_sha256"] == screen_sha256
    assert assessed["hypotheses"][0]["evidence_assessments"][0]["followup_screen_sha256"] == screen_sha256

    changed_basis = json.loads(json.dumps(assessed))
    basis_follow_up = changed_basis["follow_up_evidence"][0]
    basis_screen = basis_follow_up["screening_history"][0]
    basis_screen["review_basis"] += " Additional reviewed note."
    basis_screen["sha256"] = hashlib.sha256(
        _canonical_json({key: value for key, value in basis_screen.items() if key != "sha256"})
    ).hexdigest()
    basis_follow_up["screening_review"] = basis_screen
    with pytest.raises(InvestigationDraftError, match="follow-up screen checksum does not match"):
        validate_investigation_draft(changed_basis)

    changed_gate = json.loads(json.dumps(assessed))
    follow_up = changed_gate["follow_up_evidence"][0]
    screen = follow_up["screening_history"][0]
    screen["gate_results"][0]["result"] = "NOT_MET"
    screen["sha256"] = hashlib.sha256(_canonical_json({key: value for key, value in screen.items() if key != "sha256"})).hexdigest()
    follow_up["screening_review"] = screen
    follow_up["availability_state"] = "RETRIEVED_QUALITY_LIMITED"
    changed_gate["analyst_assessment"]["records"][0]["followup_screen_sha256"] = screen["sha256"]
    changed_gate["hypotheses"][0]["evidence_assessments"][0]["followup_screen_sha256"] = screen["sha256"]
    assessment_record = changed_gate["analyst_assessment"]
    assessment_record["assessment_sha256"] = hashlib.sha256(
        _canonical_json({key: value for key, value in assessment_record.items() if key != "assessment_sha256"})
    ).hexdigest()
    with pytest.raises(InvestigationDraftError, match="failed or left any registered gate unknown"):
        validate_investigation_draft(changed_gate)

    legacy = json.loads(json.dumps(assessed))
    legacy_follow_up = legacy["follow_up_evidence"][0]
    legacy_follow_up.pop("screening_history")
    legacy_follow_up.pop("screening_review")
    legacy_follow_up["availability_state"] = "NOT_SEARCHED"
    legacy_follow_up["action_track"] = "NEW_EVIDENCE_SEARCH"
    legacy_follow_up["evidence_refs"] = []
    legacy_assessment = legacy["analyst_assessment"]
    legacy_assessment["method"] = "ANALYST_REVIEWED_SOURCE_RELATIONSHIPS"
    legacy_assessment["records"][0].pop("followup_screen_sha256")
    legacy["hypotheses"][0]["evidence_assessments"][0].pop("followup_screen_sha256")
    legacy_assessment["assessment_sha256"] = hashlib.sha256(
        _canonical_json({key: value for key, value in legacy_assessment.items() if key != "assessment_sha256"})
    ).hexdigest()
    assert validate_investigation_draft(legacy) == legacy


def test_revision_links_prior_assessment_and_resets_hypotheses_for_new_round():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "FAIL"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(
        source,
        question="Which explanation remains consistent with the observation?",
        hypotheses=_hypotheses(),
        next_observation=_next_observation(),
        created_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )
    draft = attach_unreviewed_source(draft, {
        "record_type": "NASA_CONTEXT_CANDIDATE_SCREEN",
        "status": "RETRIEVED_QUALITY_LIMITED",
        "screen": "Staged source carried forward without an evidence relationship.",
    })
    assessed = assess_investigation_draft(draft, [{
        "hypothesis_id": "H1",
        "evidence_id": draft["evidence_artifacts"][0]["evidence_id"],
        "relationship": "DOES_NOT_DISTINGUISH",
        "evidence_fit": "UNKNOWN",
        "rationale": "The QA-held observation cannot discriminate this explanation.",
        "review_basis": "Inspected the retained pair record and provider QA disposition.",
        "limitations": "The source remains QA-held and has no accepted change measurement.",
    }], assessed_at_utc=datetime(2026, 11, 8, 1, tzinfo=timezone.utc))
    assessed["evidence_artifacts"] = list(reversed(assessed["evidence_artifacts"]))
    parent_bytes = json.dumps(assessed, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    next_observation = {**_next_observation(), "target_hypothesis_id": "H2", "action": "Retrieve independent soil-moisture observations across the interval."}

    revised = revise_investigation_draft(
        assessed,
        next_observation=next_observation,
        revised_at_utc=datetime(2026, 11, 8, 2, tzinfo=timezone.utc),
    )

    assert assessed["hypotheses"][0]["state"] == "UNRESOLVED"
    assert revised["revision"] == {
        "parent_draft_sha256": hashlib.sha256(parent_bytes).hexdigest(),
        "parent_assessment_sha256": assessed["analyst_assessment"]["assessment_sha256"],
        "revision_number": 1,
        "created_at_utc": "2026-11-08T02:00:00+00:00",
    }
    assert revised["status"] == "DRAFT_NOT_ASSESSED"
    assert all(item["state"] == "NOT_EVALUATED" for item in revised["hypotheses"])
    assert all(not item["evidence_refs"] and not item["evidence_assessments"] for item in revised["hypotheses"])
    assert revised["follow_up_evidence"][0]["target_hypothesis_ids"] == ["H2"]
    assert [artifact["role"] for artifact in revised["evidence_artifacts"]] == [
        "SAR_PAIR_HELD_AT_PROVIDER_QA",
        "USER_SUPPLIED_SOURCE_NOT_REVIEWED",
    ]
    assert {
        artifact["evidence_id"] for artifact in revised["evidence_artifacts"]
    } == {artifact["evidence_id"] for artifact in assessed["evidence_artifacts"]}
    assert revised["source_records"] == assessed["source_records"]
    assert validate_investigation_draft(revised) == revised

    corrupted = json.loads(json.dumps(revised))
    corrupted["revision"]["parent_assessment_sha256"] = "z" * 64
    with pytest.raises(InvestigationDraftError, match="lineage checksums are invalid"):
        validate_investigation_draft(corrupted)
    with pytest.raises(InvestigationDraftError, match="only an assessed"):
        revise_investigation_draft(draft, next_observation=_next_observation())


def test_tampered_source_cannot_be_staged_into_an_unassessed_draft():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None,
        "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(sar_source, question="What remains uncertain here?", hypotheses=_hypotheses(), next_observation=_next_observation())
    source_id = draft["evidence_artifacts"][0]["evidence_id"]
    draft["source_records"][source_id]["status"] = "MEASURED_DESCRIPTIVE_ONLY"
    with pytest.raises(InvestigationDraftError, match="checksum or identity mismatch"):
        attach_unreviewed_source(draft, {"record_type": "CONTEXT"})


def test_analyst_assessment_is_traceable_and_quality_held_pair_cannot_be_directional():
    sar_source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None,
        "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(sar_source, question="What remains uncertain about this area?", hypotheses=_hypotheses(), next_observation=_next_observation())
    evidence_id = draft["evidence_artifacts"][0]["evidence_id"]
    relation = {
        "hypothesis_id": "H1",
        "evidence_id": evidence_id,
        "relationship": "LIMITS_INTERPRETATION",
        "evidence_fit": "UNKNOWN",
        "rationale": "The pair record is held and contains no accepted measurement arrays.",
        "review_basis": "I inspected the embedded provider QA and analysis gate fields.",
        "limitations": "This record cannot establish whether the proposed surface process occurred.",
    }
    assessed = assess_investigation_draft(
        draft,
        [relation],
        assessed_at_utc=datetime(2026, 11, 8, tzinfo=timezone.utc),
    )
    assert assessed["status"] == "DRAFT_ANALYST_ASSESSED_UNVERIFIED"
    assert assessed["hypotheses"][0]["state"] == "UNRESOLVED"
    assert assessed["hypotheses"][0]["evidence_refs"] == [evidence_id]
    assert assessed["analyst_assessment"]["reviewer"] == "LOCAL_USER_UNAUTHENTICATED"
    assert assessed["analyst_assessment"]["records"][0]["source_sha256"] == assessed["evidence_artifacts"][0]["sha256"]
    assert validate_investigation_draft(assessed) == assessed
    with pytest.raises(InvestigationDraftError, match="cannot directionally support"):
        assess_investigation_draft(draft, [{**relation, "relationship": "SUPPORTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE"}])
    tampered = json.loads(json.dumps(assessed))
    tampered["hypotheses"][0]["evidence_assessments"][0]["rationale"] = "Edited after review."
    with pytest.raises(InvestigationDraftError, match="do not match the analyst review record"):
        validate_investigation_draft(tampered)
    tampered_assessment = json.loads(json.dumps(assessed))
    tampered_assessment["analyst_assessment"]["records"][0]["limitations"] = "Edited limitation after assessment."
    with pytest.raises(InvestigationDraftError, match="assessment checksum mismatch"):
        validate_investigation_draft(tampered_assessment)
    with pytest.raises(InvestigationDraftError, match="after analyst assessment"):
        attach_unreviewed_source(assessed, {"record_type": "CONTEXT"})


def test_directional_relation_requires_explicit_analyst_fit_declaration():
    source = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS", "schema_version": 1, "status": "QA_HELD",
        "source_products": {"before": {"scene_id": "A"}, "after": {"scene_id": "B"}},
        "provider_qa": {"before": {"evidence": {"status": "FAIL"}}, "after": {"evidence": {"status": "PASS"}}},
        "measurement": None, "manifest": None,
        "analysis_gates": {"provider_qa": "HELD_NON_PASS", "measurement_arrays": "NOT_READ", "change_calculation": "NOT_PERFORMED"},
    }
    draft = build_investigation_draft(source, question="What remains uncertain about this area?", hypotheses=_hypotheses(), next_observation=_next_observation())
    draft = attach_unreviewed_source(draft, {"record_type": "USER_SUPPLIED_CONTEXT", "status": "REPORT_CONTEXT_ONLY"})
    context_id = draft["evidence_artifacts"][1]["evidence_id"]
    draft = screen_followup_source(
        draft,
        evidence_id=context_id,
        gate_results=[{"gate": gate, "result": "MET"} for gate in _next_observation()["acceptance_gates"].splitlines()],
        review_basis="Inspected the source description, date, and stated spatial coverage.",
        limitations="The source remains user supplied and provider quality is unverified.",
    )
    relation = {
        "hypothesis_id": "H1", "evidence_id": context_id, "relationship": "SUPPORTS",
        "evidence_fit": "UNKNOWN",
        "rationale": "The report describes the event expected by this explanation.",
        "review_basis": "I inspected the user-supplied report summary and its date.",
        "limitations": "The report cannot validate a SAR-derived spatial boundary.",
    }
    with pytest.raises(InvestigationDraftError, match="require evidence declared suitable"):
        assess_investigation_draft(draft, [relation])
    with pytest.raises(InvestigationDraftError, match="unknown hypothesis or source"):
        assess_investigation_draft(draft, [{**relation, "hypothesis_id": []}])
    with pytest.raises(InvestigationDraftError, match="fit is unsupported"):
        assess_investigation_draft(draft, [{**relation, "evidence_fit": []}])
    assessed = assess_investigation_draft(draft, [{**relation, "evidence_fit": "SUITABLE_FOR_STATED_SCOPE"}])
    assert assessed["hypotheses"][0]["state"] == "SUPPORTED_WITHIN_SCOPE"
    assert assessed["analyst_assessment"]["records"][0]["evidence_fit"] == "SUITABLE_FOR_STATED_SCOPE"
    assert assessed["evidence_artifacts"][1]["source_review_state"] == "NOT_REVIEWED"
    assert assessed["evidence_artifacts"][1]["independence_state"] == "NOT_ASSESSED"
