"""Integrated controlled scenarios for the evidence-to-hypothesis workflow."""

import json
from pathlib import Path

import pytest

from echo.investigation import validate_investigation_contract


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
