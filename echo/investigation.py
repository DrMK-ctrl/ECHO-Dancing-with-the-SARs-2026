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


class FollowUpPurpose(StrEnum):
    QUALITY_GATE = "QUALITY_GATE"
    DISCRIMINATING_OBSERVATION = "DISCRIMINATING_OBSERVATION"


class FollowUpAvailability(StrEnum):
    NOT_SEARCHED = "NOT_SEARCHED"
    PROVIDER_RESPONSE_REQUIRED = "PROVIDER_RESPONSE_REQUIRED"
    RETRIEVED_QUALITY_LIMITED = "RETRIEVED_QUALITY_LIMITED"


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


def validate_follow_up_plan(
    follow_ups: Iterable[dict[str, object]],
    *,
    known_hypothesis_ids: set[str],
    known_evidence_ids: set[str] | None = None,
) -> list[dict[str, object]]:
    """Validate traceable follow-up actions without claiming source availability or rank."""
    items = list(follow_ups)
    seen: set[str] = set()
    required_text = ("action", "discriminating_question", "possible_interpretation", "priority_reason")
    for item in items:
        follow_up_id = item.get("follow_up_id")
        if not isinstance(follow_up_id, str) or not follow_up_id.strip():
            raise ValueError("follow-up identifier is required")
        if follow_up_id in seen:
            raise ValueError(f"duplicate follow-up identifier: {follow_up_id}")
        seen.add(follow_up_id)

        targets = item.get("target_hypothesis_ids")
        if not isinstance(targets, list) or not targets:
            raise ValueError(f"follow-up must target at least one hypothesis: {follow_up_id}")
        if any(not isinstance(target, str) for target in targets):
            raise ValueError(f"hypothesis targets must be identifiers: {follow_up_id}")
        if len(targets) != len(set(targets)):
            raise ValueError(f"duplicate hypothesis target: {follow_up_id}")
        unknown_targets = set(targets) - known_hypothesis_ids
        if unknown_targets:
            raise ValueError(f"unknown hypothesis target in {follow_up_id}: {sorted(unknown_targets)}")

        evidence_refs = item.get("evidence_refs", [])
        if not isinstance(evidence_refs, list) or any(not isinstance(ref, str) for ref in evidence_refs):
            raise ValueError(f"evidence references must be identifiers: {follow_up_id}")
        if len(evidence_refs) != len(set(evidence_refs)):
            raise ValueError(f"duplicate evidence reference: {follow_up_id}")
        if known_evidence_ids is not None:
            unknown_evidence = set(evidence_refs) - known_evidence_ids
            if unknown_evidence:
                raise ValueError(f"unknown evidence reference in {follow_up_id}: {sorted(unknown_evidence)}")

        for field in required_text:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} is required: {follow_up_id}")
        try:
            FollowUpPurpose(item.get("purpose"))
            FollowUpAvailability(item.get("availability_state"))
        except ValueError as exc:
            raise ValueError(f"unsupported purpose or availability in {follow_up_id}") from exc
    return items
