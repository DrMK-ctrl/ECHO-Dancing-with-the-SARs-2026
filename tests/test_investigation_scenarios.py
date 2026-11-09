"""Integrated controlled scenarios for the evidence-to-hypothesis workflow."""

import json
from pathlib import Path

import pytest

from echo.investigation import validate_investigation_contract
from echo.investigation_draft import (
    assess_investigation_draft,
    attach_unreviewed_source,
    build_investigation_draft,
    screen_followup_source,
    validate_investigation_draft,
)


SCENARIO_PATH = Path(__file__).parent / "fixtures" / "investigation-scenario-ambiguous-synthetic.json"


def load_scenario():
    scenario = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    assert scenario["record_type"] == "ECHO_SYNTHETIC_INVESTIGATION_SCENARIO"
    assert scenario["status"] == "SYNTHETIC_TEST_ONLY_NOT_SATELLITE_EVIDENCE"
    assert scenario["synthetic_observation"]["is_satellite_data"] is False
    return scenario


def test_integrated_synthetic_scenario_preserves_ambiguity_lineage_and_next_test():
    scenario = load_scenario()

    result = validate_investigation_contract(scenario)

    hypotheses = {item["id"]: item for item in result["hypotheses"]}
    assert hypotheses["H_WATER"]["state"] == "UNRESOLVED"
    assert hypotheses["H_SURFACE_STATE"]["state"] == "UNRESOLVED"
    assert hypotheses["H_ACQUISITION"]["state"] == "NOT_EVALUATED"
    assert "probability" not in result

    evidence = {item["evidence_id"]: item for item in result["evidence_artifacts"]}
    assert evidence["SYNTHETIC-CROSS-SENSOR-ASSOCIATION"]["lineage"]["derived_from_evidence_ids"] == [
        "SYNTHETIC-SAR-MEASUREMENT",
        "SYNTHETIC-OPTICAL-CONTEXT",
    ]
    assert evidence["SYNTHETIC-CROSS-SENSOR-ASSOCIATION"]["lineage"]["shares_source_observations_with"] == [
        "SYNTHETIC-SAR-MEASUREMENT",
    ]
    assert "SYNTHETIC-SAR-MEASUREMENT" in hypotheses["H_WATER"]["evidence_refs"]
    assert "SYNTHETIC-SAR-MEASUREMENT" in hypotheses["H_SURFACE_STATE"]["evidence_refs"]

    follow_ups = {item["follow_up_id"]: item for item in result["follow_up_evidence"]}
    assert follow_ups["F_QA_GATE"]["action_track"] == "QUALITY_PREREQUISITE"
    water_test = follow_ups["F_WATER_OBSERVATION"]
    assert water_test["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert water_test["target_hypothesis_ids"] == ["H_WATER"]
    assert water_test["test_design"]["does_not_test_hypothesis_ids"] == [
        "H_SURFACE_STATE",
        "H_ACQUISITION",
    ]
    assert water_test["test_design"]["expected_observation"]
    assert water_test["test_design"]["would_weaken_if"]
    assert water_test["test_design"]["inconclusive_if"]
    assert water_test["test_design"]["acceptance_gates"]


def test_integrated_synthetic_scenario_rejects_directional_claim_from_ambiguous_evidence():
    scenario = load_scenario()
    water = next(item for item in scenario["hypotheses"] if item["id"] == "H_WATER")
    water["state"] = "SUPPORTED_WITHIN_SCOPE"

    with pytest.raises(ValueError, match="disposition does not match evidence relationships"):
        validate_investigation_contract(scenario)


def test_integrated_synthetic_scenario_rejects_provider_qa_as_physical_support():
    scenario = load_scenario()
    water = next(item for item in scenario["hypotheses"] if item["id"] == "H_WATER")
    qa_assessment = next(
        item for item in water["evidence_assessments"]
        if item["evidence_id"] == "SYNTHETIC-PROVIDER-QA-HOLD"
    )
    qa_assessment["relationship"] = "SUPPORTS"

    with pytest.raises(ValueError, match="cannot directionally assess a hypothesis"):
        validate_investigation_contract(scenario)


def test_controlled_scenario_runs_through_draft_screening_and_assessment_workflow():
    """Exercise production draft APIs; all source records here are test fixtures."""
    from datetime import datetime, timezone

    sar_fixture = {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "status": "QA_HELD",
        "synthetic_test_only": True,
        "source_products": {
            "before": {"scene_id": "SYNTHETIC_BEFORE"},
            "after": {"scene_id": "SYNTHETIC_AFTER"},
        },
        "provider_qa": {
            "before": {"evidence": {"status": "FAIL"}},
            "after": {"evidence": {"status": "FAIL"}},
        },
        "measurement": None,
        "manifest": None,
        "analysis_gates": {
            "provider_qa": "HELD_NON_PASS",
            "measurement_arrays": "NOT_READ",
            "change_calculation": "NOT_PERFORMED",
        },
    }
    hypotheses = [
        {
            "statement": "Surface-water change explains the synthetic response.",
            "scope_limit": "Controlled software fixture only.",
            "expected_observation": "A quality-valid water transition overlaps the test area.",
            "would_weaken_if": "Suitable observations show no transition.",
            "required_evidence": "Independent water measurements with suitable timing and support.",
        },
        {
            "statement": "Surface-state variation explains the synthetic response.",
            "scope_limit": "Controlled software fixture only.",
            "expected_observation": "A separate surface-state measure changes as predicted.",
            "would_weaken_if": "Suitable measurements remain stable.",
            "required_evidence": "Independent surface-state observations with documented quality.",
        },
    ]
    next_observation = {
        "target_hypothesis_id": "H1",
        "action": "Retrieve a controlled independent water-observation fixture.",
        "discriminating_question": "Does the candidate fixture show the expected transition?",
        "possible_interpretation": "A matching test value is consistent with H1 within this fixture.",
        "priority_reason": "It exercises one pre-registered hypothesis test in the workflow.",
        "expected_observation": "The test-only candidate reports the expected transition.",
        "would_weaken_if": "The test-only candidate reports no transition.",
        "inconclusive_if": "The candidate lacks the declared test fields.",
        "acceptance_gates": "Test source is marked synthetic\nRequired fields are present\nCandidate is linked to this test",
        "interpretation_limit": "No test fixture represents Earth data or validates SAR science.",
    }
    timestamp = datetime(2026, 11, 9, tzinfo=timezone.utc)
    draft = build_investigation_draft(
        sar_fixture,
        question="Can the controlled workflow preserve conflicting evidence?",
        hypotheses=hypotheses,
        next_observation=next_observation,
        created_at_utc=timestamp,
    )
    primary_id = draft["evidence_artifacts"][0]["evidence_id"]
    draft = attach_unreviewed_source(
        draft,
        {"record_type": "SYNTHETIC_SUPPORT_FIXTURE", "status": "TEST_ONLY", "value": "expected"},
        lineage={"shares_source_observations_with": [primary_id]},
        attached_at_utc=timestamp,
    )
    support_id = draft["evidence_artifacts"][1]["evidence_id"]
    draft = attach_unreviewed_source(
        draft,
        {"record_type": "SYNTHETIC_CONTRADICTION_FIXTURE", "status": "TEST_ONLY", "value": "conflicting"},
        lineage={"shares_source_observations_with": [support_id]},
        attached_at_utc=timestamp,
    )
    contradiction_id = draft["evidence_artifacts"][2]["evidence_id"]
    gates = [
        {"gate": gate, "result": "MET"}
        for gate in draft["follow_up_evidence"][0]["test_design"]["acceptance_gates"]
    ]
    for evidence_id in (support_id, contradiction_id):
        draft = screen_followup_source(
            draft,
            evidence_id=evidence_id,
            gate_results=gates,
            review_basis="Inspected the marked test fixture fields required by the registered software test.",
            limitations="These controlled values are not measurements from a satellite or real observation.",
            screened_at_utc=timestamp,
        )
    assessments = [
        {
            "hypothesis_id": "H1", "evidence_id": primary_id,
            "relationship": "LIMITS_INTERPRETATION", "evidence_fit": "UNKNOWN",
            "rationale": "The fixture SAR source is explicitly held at the quality gate.",
            "review_basis": "Inspected the synthetic QA-held source record and its declared status.",
            "limitations": "No raster measurement exists in this software test fixture.",
        },
        {
            "hypothesis_id": "H1", "evidence_id": support_id,
            "relationship": "SUPPORTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The controlled candidate contains the predeclared expected test value.",
            "review_basis": "Inspected the test-only candidate record and its registered gates.",
            "limitations": "This is a deterministic test value, not scientific evidence.",
        },
        {
            "hypothesis_id": "H1", "evidence_id": contradiction_id,
            "relationship": "CONTRADICTS", "evidence_fit": "SUITABLE_FOR_STATED_SCOPE",
            "rationale": "The controlled candidate carries the deliberately conflicting test value.",
            "review_basis": "Inspected the test-only candidate record and its registered gates.",
            "limitations": "The contradiction is injected for software behavior testing only.",
        },
    ]
    assessed = assess_investigation_draft(draft, assessments, assessed_at_utc=timestamp)
    validate_investigation_draft(assessed)

    states = {item["id"]: item["state"] for item in assessed["hypotheses"]}
    assert states == {"H1": "UNRESOLVED", "H2": "NOT_EVALUATED"}
    assert assessed["status"] == "DRAFT_ANALYST_ASSESSED_UNVERIFIED"
    assert assessed["evidence_artifacts"][0]["status"] == "QA_HELD"
    assert assessed["evidence_artifacts"][2]["lineage"]["shares_source_observations_with"] == [support_id]
    assert all(item["independence_state"] == "NOT_ASSESSED" for item in assessed["evidence_artifacts"][1:])
    assert assessed["analyst_assessment"]["records"][1]["followup_screen_sha256"]
    assert assessed["analyst_assessment"]["records"][2]["followup_screen_sha256"]
    assert assessed["source_records"][primary_id]["synthetic_test_only"] is True
