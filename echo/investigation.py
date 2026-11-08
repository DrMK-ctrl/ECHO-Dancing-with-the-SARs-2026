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


class HypothesisTestability(StrEnum):
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
    DESCRIPTIVE_ASSOCIATION_ONLY = "DESCRIPTIVE_ASSOCIATION_ONLY"
    NOT_TESTED = "NOT_TESTED"
    NOT_TESTABLE_WITH_RETAINED_EVIDENCE = "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"


class FollowUpPurpose(StrEnum):
    QUALITY_GATE = "QUALITY_GATE"
    DISCRIMINATING_OBSERVATION = "DISCRIMINATING_OBSERVATION"


class FollowUpAvailability(StrEnum):
    NOT_SEARCHED = "NOT_SEARCHED"
    CATALOG_SCREENED_CONTEXT_RETRIEVED = "CATALOG_SCREENED_CONTEXT_RETRIEVED"
    PROVIDER_RESPONSE_REQUIRED = "PROVIDER_RESPONSE_REQUIRED"
    RETRIEVED_QUALITY_LIMITED = "RETRIEVED_QUALITY_LIMITED"


class FollowUpActionTrack(StrEnum):
    QUALITY_PREREQUISITE = "QUALITY_PREREQUISITE"
    NEW_EVIDENCE_SEARCH = "NEW_EVIDENCE_SEARCH"
    REVIEWED_RESULT = "REVIEWED_RESULT"


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


def validate_hypotheses(
    hypotheses: Iterable[dict[str, object]],
    *,
    known_evidence_ids: set[str],
) -> list[dict[str, object]]:
    """Validate falsifiable hypothesis records without judging their science."""
    items = list(hypotheses)
    seen: set[str] = set()
    required_text = (
        "statement",
        "state",
        "scope_limit",
        "expected_observation",
        "would_weaken_if",
        "testability_reason",
    )
    for item in items:
        hypothesis_id = item.get("id")
        if not isinstance(hypothesis_id, str) or not hypothesis_id.strip():
            raise ValueError("hypothesis identifier is required")
        if hypothesis_id in seen:
            raise ValueError(f"duplicate hypothesis identifier: {hypothesis_id}")
        seen.add(hypothesis_id)
        for field in required_text:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} is required: {hypothesis_id}")
        try:
            testability = HypothesisTestability(item.get("testability_state"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unsupported testability state: {hypothesis_id}") from exc

        requirements = item.get("required_evidence")
        if not isinstance(requirements, list) or not requirements or any(
            not isinstance(value, str) or not value.strip() for value in requirements
        ):
            raise ValueError(f"required evidence must be a nonempty list: {hypothesis_id}")
        evidence_refs = item.get("evidence_refs", [])
        if not isinstance(evidence_refs, list) or any(not isinstance(value, str) for value in evidence_refs):
            raise ValueError(f"evidence references must be identifiers: {hypothesis_id}")
        if len(evidence_refs) != len(set(evidence_refs)):
            raise ValueError(f"duplicate evidence reference: {hypothesis_id}")
        unknown = set(evidence_refs) - known_evidence_ids
        if unknown:
            raise ValueError(f"unknown evidence reference in {hypothesis_id}: {sorted(unknown)}")
        assessments = item.get("evidence_assessments", [])
        if not isinstance(assessments, list) or any(
            not isinstance(assessment, dict)
            or not isinstance(assessment.get("evidence_id"), str)
            for assessment in assessments
        ):
            raise ValueError(f"evidence assessments must identify their source: {hypothesis_id}")
        assessment_ids = [assessment["evidence_id"] for assessment in assessments]
        if len(assessment_ids) != len(set(assessment_ids)):
            raise ValueError(f"duplicate evidence assessment: {hypothesis_id}")
        if set(assessment_ids) != set(evidence_refs):
            raise ValueError(f"evidence references do not match assessments: {hypothesis_id}")
        if testability != HypothesisTestability.NOT_TESTED and not evidence_refs:
            raise ValueError(f"evaluated hypothesis must cite evidence: {hypothesis_id}")

        parsed_assessments: list[EvidenceAssessment] = []
        for assessment in assessments:
            try:
                relationship = EvidenceRelation(assessment.get("relationship"))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"unsupported evidence relationship: {hypothesis_id}") from exc
            rationale = assessment.get("rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                raise ValueError(f"evidence rationale is required: {hypothesis_id}")
            parsed_assessments.append(
                EvidenceAssessment(assessment["evidence_id"], relationship, rationale)
            )

        try:
            declared_state = HypothesisDisposition(item.get("state"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unsupported hypothesis disposition: {hypothesis_id}") from exc
        evaluated_state = evaluate_hypothesis(
            parsed_assessments,
            known_evidence_ids=known_evidence_ids,
        )["disposition"]
        if declared_state.value != evaluated_state:
            raise ValueError(
                f"hypothesis disposition does not match evidence relationships: {hypothesis_id}"
            )
        item["testability_state"] = testability.value
    return items


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

        test_design = item.get("test_design")
        if test_design is not None:
            if not isinstance(test_design, dict):
                raise ValueError(f"test design must be an object: {follow_up_id}")
            required_design_text = (
                "mechanism_branch",
                "expected_observation",
                "would_weaken_if",
                "inconclusive_if",
                "interpretation_limit",
            )
            for field in required_design_text:
                value = test_design.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"test design {field} is required: {follow_up_id}")
            hypothesis_under_test = test_design.get("hypothesis_under_test_id")
            if not isinstance(hypothesis_under_test, str) or hypothesis_under_test not in known_hypothesis_ids:
                raise ValueError(f"test design hypothesis is unknown: {follow_up_id}")
            if hypothesis_under_test not in targets:
                raise ValueError(f"test design hypothesis must be a follow-up target: {follow_up_id}")
            non_discriminating = test_design.get("does_not_test_hypothesis_ids")
            if (
                not isinstance(non_discriminating, list)
                or any(not isinstance(value, str) or value not in known_hypothesis_ids for value in non_discriminating)
                or len(non_discriminating) != len(set(non_discriminating))
                or hypothesis_under_test in non_discriminating
            ):
                raise ValueError(f"test design must identify other hypotheses it does not test: {follow_up_id}")
            if set(non_discriminating) & set(targets):
                raise ValueError(f"test design non-target hypotheses cannot be follow-up targets: {follow_up_id}")
            if set(non_discriminating) != known_hypothesis_ids - set(targets):
                raise ValueError(f"test design must identify all hypotheses outside its targets: {follow_up_id}")
            if targets != [hypothesis_under_test]:
                raise ValueError(f"test design must target exactly its one hypothesis under test: {follow_up_id}")
            gates = test_design.get("acceptance_gates")
            if not isinstance(gates, list) or not gates or any(not isinstance(value, str) or not value.strip() for value in gates):
                raise ValueError(f"test design acceptance gates must be a nonempty text list: {follow_up_id}")

        for field in required_text:
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} is required: {follow_up_id}")
        try:
            purpose = FollowUpPurpose(item.get("purpose"))
            availability = FollowUpAvailability(item.get("availability_state"))
        except ValueError as exc:
            raise ValueError(f"unsupported purpose or availability in {follow_up_id}") from exc
        if (
            purpose == FollowUpPurpose.DISCRIMINATING_OBSERVATION
            and availability == FollowUpAvailability.NOT_SEARCHED
            and test_design is None
        ):
            raise ValueError(f"open evidence search requires a falsifiable test design: {follow_up_id}")
        if purpose == FollowUpPurpose.QUALITY_GATE and availability in {
            FollowUpAvailability.NOT_SEARCHED,
            FollowUpAvailability.PROVIDER_RESPONSE_REQUIRED,
        }:
            expected_track = FollowUpActionTrack.QUALITY_PREREQUISITE.value
        elif (
            purpose == FollowUpPurpose.DISCRIMINATING_OBSERVATION
            and availability == FollowUpAvailability.NOT_SEARCHED
        ):
            expected_track = FollowUpActionTrack.NEW_EVIDENCE_SEARCH.value
        else:
            expected_track = FollowUpActionTrack.REVIEWED_RESULT.value
        declared_track = item.get("action_track")
        if declared_track is not None and declared_track != expected_track:
            raise ValueError(f"action track does not match purpose and availability: {follow_up_id}")
        item["action_track"] = expected_track
    return items


def validate_evidence_lineage(artifacts: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    """Validate explicit derivation and shared-observation links between records.

    A derivation edge means an output was computed using another evidence
    record. A shared-observation edge records common source acquisitions without
    claiming that one product was derived from the other.
    """
    items = list(artifacts)
    ids = [item.get("evidence_id") for item in items]
    if any(not isinstance(value, str) or not value.strip() for value in ids):
        raise ValueError("evidence lineage requires nonempty evidence identifiers")
    if len(ids) != len(set(ids)):
        raise ValueError("evidence lineage identifiers must be unique")
    known = set(ids)
    derived: dict[str, list[str]] = {}
    for item in items:
        evidence_id = item["evidence_id"]
        lineage = item.get("lineage", {})
        if not isinstance(lineage, dict):
            raise ValueError(f"evidence lineage must be an object: {evidence_id}")
        derived_ids = lineage.get("derived_from_evidence_ids", [])
        shared_ids = lineage.get("shares_source_observations_with", [])
        for field, references in (
            ("derived_from_evidence_ids", derived_ids),
            ("shares_source_observations_with", shared_ids),
        ):
            if not isinstance(references, list) or any(not isinstance(ref, str) for ref in references):
                raise ValueError(f"{field} must be a list of identifiers: {evidence_id}")
            if len(references) != len(set(references)):
                raise ValueError(f"duplicate {field} reference: {evidence_id}")
            if evidence_id in references:
                raise ValueError(f"self-referential {field}: {evidence_id}")
            unknown = set(references) - known
            if unknown:
                raise ValueError(f"unknown {field} reference in {evidence_id}: {sorted(unknown)}")
        derived[evidence_id] = derived_ids

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(evidence_id: str) -> None:
        if evidence_id in visiting:
            raise ValueError("evidence derivation links contain a cycle")
        if evidence_id in visited:
            return
        visiting.add(evidence_id)
        for parent in derived[evidence_id]:
            visit(parent)
        visiting.remove(evidence_id)
        visited.add(evidence_id)

    for evidence_id in derived:
        visit(evidence_id)
    return items
