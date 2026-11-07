import pytest

from echo.investigation import EvidenceAssessment, EvidenceRelation, evaluate_hypothesis


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
