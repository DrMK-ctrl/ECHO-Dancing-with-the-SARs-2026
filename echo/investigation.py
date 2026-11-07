"""Small deterministic primitives for evidence-to-hypothesis assessment.

These rules organize analyst-authored evidence relationships. They are not a
probabilistic model and do not determine whether an observation is scientifically
valid; source QA and measurement suitability remain upstream gates.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Iterable


class EvidenceRelation(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DOES_NOT_DISTINGUISH = "DOES_NOT_DISTINGUISH"
    LIMITS_INTERPRETATION = "LIMITS_INTERPRETATION"


class HypothesisDisposition(StrEnum):
    SUPPORTED_WITHIN_SCOPE = "SUPPORTED_WITHIN_SCOPE"
    CONTRADICTED_WITHIN_SCOPE = "CONTRADICTED_WITHIN_SCOPE"
    UNRESOLVED = "UNRESOLVED"
    NOT_EVALUATED = "NOT_EVALUATED"


@dataclass(frozen=True)
class EvidenceAssessment:
    evidence_id: str
    relationship: EvidenceRelation
    rationale: str


def evaluate_hypothesis(
    assessments: Iterable[EvidenceAssessment],
    *,
    known_evidence_ids: set[str],
) -> dict[str, object]:
    """Summarize explicit evidence relations without scores or hidden weighting.

    Directional evidence mixed with contradictory evidence or an explicit
    interpretive limitation remains unresolved. A directional result is emitted
    only when every assessed item is directionally consistent within the
    analyst-declared scope.
    """
    items = list(assessments)
    seen: set[str] = set()
    for item in items:
        if not isinstance(item.relationship, EvidenceRelation):
            raise ValueError(f"unsupported evidence relationship: {item.relationship}")
        if item.evidence_id not in known_evidence_ids:
            raise ValueError(f"unknown evidence reference: {item.evidence_id}")
        if item.evidence_id in seen:
            raise ValueError(f"duplicate evidence assessment: {item.evidence_id}")
        seen.add(item.evidence_id)
        if not item.rationale.strip():
            raise ValueError(f"evidence rationale is required: {item.evidence_id}")

    relations = {item.relationship for item in items}
    if not items:
        disposition = HypothesisDisposition.NOT_EVALUATED
    elif EvidenceRelation.SUPPORTS in relations and relations == {EvidenceRelation.SUPPORTS}:
        disposition = HypothesisDisposition.SUPPORTED_WITHIN_SCOPE
    elif EvidenceRelation.CONTRADICTS in relations and relations == {EvidenceRelation.CONTRADICTS}:
        disposition = HypothesisDisposition.CONTRADICTED_WITHIN_SCOPE
    else:
        disposition = HypothesisDisposition.UNRESOLVED

    return {
        "disposition": disposition.value,
        "evidence_assessments": [asdict(item) | {"relationship": item.relationship.value} for item in items],
    }
