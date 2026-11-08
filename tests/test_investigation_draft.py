import hashlib
import json
from datetime import datetime, timezone

import pytest

from echo.investigation import validate_investigation_contract
from echo.investigation_draft import InvestigationDraftError, build_investigation_draft


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
