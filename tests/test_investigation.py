import pytest

from echo.investigation import (
    EvidenceAssessment,
    EvidenceRelation,
    evaluate_hypothesis,
    validate_follow_up_plan,
    validate_hypotheses,
)


def assessment(evidence_id, relation, rationale="Test evidence statement."):
    return EvidenceAssessment(evidence_id, EvidenceRelation(relation), rationale)


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        ([], "NOT_EVALUATED"),
        ([assessment("E1", "SUPPORTS")], "SUPPORTED_WITHIN_SCOPE"),
        ([assessment("E1", "CONTRADICTS")], "CONTRADICTED_WITHIN_SCOPE"),
        ([assessment("E1", "DOES_NOT_DISTINGUISH")], "UNRESOLVED"),
        ([assessment("E1", "LIMITS_INTERPRETATION")], "UNRESOLVED"),
        ([assessment("E1", "SUPPORTS"), assessment("E2", "CONTRADICTS")], "UNRESOLVED"),
        ([assessment("E1", "SUPPORTS"), assessment("E2", "DOES_NOT_DISTINGUISH")], "UNRESOLVED"),
        ([assessment("E1", "SUPPORTS"), assessment("E2", "LIMITS_INTERPRETATION")], "UNRESOLVED"),
    ],
)
def test_disposition_is_conservative_and_has_no_probability_score(items, expected):
    result = evaluate_hypothesis(items, known_evidence_ids={"E1", "E2"})

    assert result["disposition"] == expected
    assert "probability" not in result
    assert len(result["evidence_assessments"]) == len(items)


def test_unknown_evidence_reference_is_rejected():
    with pytest.raises(ValueError, match="unknown evidence reference"):
        evaluate_hypothesis(
            [assessment("UNREGISTERED", "SUPPORTS")],
            known_evidence_ids={"E1"},
        )


def test_duplicate_reference_is_rejected():
    with pytest.raises(ValueError, match="duplicate evidence assessment"):
        evaluate_hypothesis(
            [assessment("E1", "SUPPORTS"), assessment("E1", "CONTRADICTS")],
            known_evidence_ids={"E1"},
        )


def test_empty_rationale_is_rejected():
    with pytest.raises(ValueError, match="rationale is required"):
        evaluate_hypothesis(
            [assessment("E1", "SUPPORTS", "  ")],
            known_evidence_ids={"E1"},
        )


def _hypothesis(**overrides):
    item = {
        "id": "H1",
        "statement": "A testable explanation.",
        "scope_limit": "Only this case.",
        "expected_observation": "An expected observation.",
        "would_weaken_if": "An observation that weakens it.",
        "testability_state": "NOT_TESTED",
        "testability_reason": "Required evidence is absent.",
        "required_evidence": ["A suitable measurement"],
        "evidence_refs": [],
    }
    item.update(overrides)
    return item


def test_hypothesis_contract_requires_falsifiable_test_conditions():
    item = _hypothesis()

    result = validate_hypotheses([item], known_evidence_ids={"E1"})

    assert result[0]["would_weaken_if"] == "An observation that weakens it."
    assert result[0]["testability_state"] == "NOT_TESTED"


@pytest.mark.parametrize(
    ("item", "known", "message"),
    [
        (_hypothesis(expected_observation=" "), {"E1"}, "expected_observation is required"),
        (_hypothesis(testability_state="LIKELY"), {"E1"}, "unsupported testability state"),
        (_hypothesis(required_evidence=[]), {"E1"}, "nonempty list"),
        (_hypothesis(evidence_refs=["UNKNOWN"]), {"E1"}, "unknown evidence reference"),
        (_hypothesis(testability_state="DESCRIPTIVE_ONLY"), {"E1"}, "must cite evidence"),
    ],
)
def test_hypothesis_contract_rejects_missing_or_untraceable_test_conditions(item, known, message):
    with pytest.raises(ValueError, match=message):
        validate_hypotheses([item], known_evidence_ids=known)


def test_hypothesis_contract_rejects_duplicate_ids():
    with pytest.raises(ValueError, match="duplicate hypothesis identifier"):
        validate_hypotheses([_hypothesis(), _hypothesis()], known_evidence_ids=set())


def _follow_up(**overrides):
    item = {
        "follow_up_id": "F1",
        "target_hypothesis_ids": ["H1"],
        "purpose": "DISCRIMINATING_OBSERVATION",
        "availability_state": "NOT_SEARCHED",
        "action": "Search for compatible observations.",
        "discriminating_question": "Do observations distinguish the explanations?",
        "possible_interpretation": "A match could support; a mismatch could weaken.",
        "priority_reason": "The hypothesis is unresolved.",
    }
    item.update(overrides)
    return item


def test_follow_up_plan_links_a_search_candidate_without_claiming_availability():
    result = validate_follow_up_plan([_follow_up()], known_hypothesis_ids={"H1"})

    assert result[0]["availability_state"] == "NOT_SEARCHED"
    assert result[0]["target_hypothesis_ids"] == ["H1"]


@pytest.mark.parametrize(
    ("items", "known_ids", "message"),
    [
        ([_follow_up(), _follow_up()], {"H1"}, "duplicate follow-up identifier"),
        ([_follow_up(target_hypothesis_ids=["H2"])], {"H1"}, "unknown hypothesis target"),
        ([_follow_up(target_hypothesis_ids=[])], {"H1"}, "at least one hypothesis"),
        ([_follow_up(availability_state="AVAILABLE")], {"H1"}, "unsupported purpose or availability"),
        ([_follow_up(action=" ")], {"H1"}, "action is required"),
    ],
)
def test_follow_up_plan_rejects_untraceable_or_unsupported_entries(items, known_ids, message):
    with pytest.raises(ValueError, match=message):
        validate_follow_up_plan(items, known_hypothesis_ids=known_ids)
