"""Build source-linked, analyst-authored investigation drafts from SAR pair records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from echo.investigation import (
    EvidenceAssessment,
    EvidenceRelation,
    evaluate_hypothesis,
    validate_investigation_contract,
)


_GCOV_STATUSES = {
    "QA_HELD",
    "MATURITY_HELD",
    "MEASURED_DESCRIPTIVE_ONLY",
}
_OPERA_STATUSES = {
    "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON",
    "INCONCLUSIVE_NO_COMMON_CLEAR_VALID_PIXELS",
}


class InvestigationDraftError(ValueError):
    """Raised when a submitted observation or analyst draft is not well formed."""


_DRAFT_UNASSESSED = "DRAFT_NOT_ASSESSED"
_DRAFT_ASSESSED = "DRAFT_ANALYST_ASSESSED_UNVERIFIED"
_NON_DIRECTIONAL_ROLES = {
    "SAR_PAIR_HELD_AT_PROVIDER_QA",
    "SAR_PAIR_HELD_AT_PRODUCT_MATURITY",
    "DESCRIPTIVE_NISAR_SAR_MEASUREMENT",
    "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT",
    "OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT",
}
_EVIDENCE_FITS = {
    "SUITABLE_FOR_STATED_SCOPE",
    "CONTEXT_ONLY",
    "UNSUITABLE",
    "UNKNOWN",
}
_ASSESSMENT_FIELDS = {
    "hypothesis_id",
    "evidence_id",
    "relationship",
    "evidence_fit",
    "rationale",
    "review_basis",
    "limitations",
}
_ASSESSMENT_LIMIT = (
    "This is an analyst-authored, unverified evidence assessment. ECHO records and summarizes the "
    "entered relationships and fit declarations; it does not authenticate the reviewer, validate source quality or "
    "independence, or establish causation."
)


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvestigationDraftError("source record is not canonical JSON data") from exc


def _source_role(record: dict[str, Any]) -> str:
    kind = record.get("record_type")
    status = record.get("status")
    if record.get("schema_version") != 1:
        raise InvestigationDraftError("source pair record has an unsupported schema version")
    if kind == "ECHO_GCOV_PAIR_ANALYSIS":
        if status not in _GCOV_STATUSES:
            raise InvestigationDraftError("NISAR GCOV pair status is unsupported for an investigation draft")
        products = record.get("source_products")
        qa = record.get("provider_qa")
        if not all(isinstance(products, dict) and isinstance(products.get(role), dict) for role in ("before", "after")):
            raise InvestigationDraftError("NISAR pair source product records are incomplete")
        if not all(isinstance(qa, dict) and isinstance(qa.get(role), dict) for role in ("before", "after")):
            raise InvestigationDraftError("NISAR pair provider QA records are incomplete")
        qa_statuses = {
            role: qa[role].get("evidence", {}).get("status")
            if isinstance(qa[role].get("evidence"), dict) else None
            for role in ("before", "after")
        }
        gates = record.get("analysis_gates")
        if status == "QA_HELD":
            if (
                not any(value != "PASS" for value in qa_statuses.values())
                or record.get("measurement") is not None
                or not isinstance(gates, dict)
                or record.get("manifest") is not None
                or gates.get("provider_qa") != "HELD_NON_PASS"
                or gates.get("measurement_arrays") != "NOT_READ"
                or gates.get("change_calculation") != "NOT_PERFORMED"
            ):
                raise InvestigationDraftError("QA-held NISAR record conflicts with its provider QA or measurement gates")
            return "SAR_PAIR_HELD_AT_PROVIDER_QA"
        if status == "MATURITY_HELD":
            if (
                set(qa_statuses.values()) != {"PASS"}
                or record.get("measurement") is not None
                or not isinstance(gates, dict)
                or record.get("manifest") is not None
                or gates.get("provider_qa") != "PASS"
                or gates.get("product_maturity") != "HELD_PRECALIBRATION_OR_UNSUPPORTED"
                or gates.get("measurement_arrays") != "NOT_READ"
            ):
                raise InvestigationDraftError("maturity-held NISAR record conflicts with its QA or product maturity gate")
            return "SAR_PAIR_HELD_AT_PRODUCT_MATURITY"
        measurement = record.get("measurement")
        if (
            set(qa_statuses.values()) != {"PASS"}
            or not isinstance(measurement, dict)
            or not isinstance(measurement.get("values_db"), list)
            or not isinstance(measurement.get("valid_mask"), list)
            or not isinstance(record.get("manifest"), dict)
        ):
            raise InvestigationDraftError("measured NISAR pair record has no measurement object")
        return "DESCRIPTIVE_NISAR_SAR_MEASUREMENT"
    if kind == "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        if status not in _OPERA_STATUSES:
            raise InvestigationDraftError("OPERA RTC-S1 pair status is unsupported for an investigation draft")
        qa = record.get("provider_qa")
        if not isinstance(qa, dict) or qa.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION":
            raise InvestigationDraftError("OPERA source must retain its no-consolidated-verdict QA status")
        products = record.get("source_products")
        if not all(isinstance(products, dict) and isinstance(products.get(role), dict) for role in ("before", "after")):
            raise InvestigationDraftError("OPERA pair source product records are incomplete")
        if status == "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON":
            if not isinstance(record.get("measurement"), dict):
                raise InvestigationDraftError("diagnostic OPERA pair record has no measurement object")
            return "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT"
        return "OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT"
    raise InvestigationDraftError("source record must be a supported GCOV or OPERA RTC-S1 pair analysis")


def build_investigation_draft(
    source_record: dict[str, Any],
    *,
    question: str,
    hypotheses: list[dict[str, str]],
    next_observation: dict[str, Any],
    created_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Create a reproducible draft without assigning evidence relationships.

    The source record is preserved exactly as submitted in the JSON-compatible
    representation. The checksum identifies its canonical serialization; it
    does not independently re-fetch or authenticate the provider response.
    """
    if not isinstance(source_record, dict):
        raise InvestigationDraftError("source record must be an object")
    if not isinstance(question, str) or len(question.strip()) < 12:
        raise InvestigationDraftError("investigation question must contain at least 12 characters")
    if not isinstance(hypotheses, list) or not 2 <= len(hypotheses) <= 6:
        raise InvestigationDraftError("enter between two and six competing hypotheses")

    source_copy = deepcopy(source_record)
    source_bytes = _canonical_json(source_copy)
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    evidence_id = f"SAR-PAIR-{source_sha256[:16].upper()}"
    role = _source_role(source_copy)

    normalized_hypotheses: list[dict[str, Any]] = []
    statements: set[str] = set()
    required_fields = (
        "statement",
        "scope_limit",
        "expected_observation",
        "would_weaken_if",
        "required_evidence",
    )
    for index, hypothesis in enumerate(hypotheses, start=1):
        if not isinstance(hypothesis, dict) or set(hypothesis) != set(required_fields):
            raise InvestigationDraftError(f"hypothesis {index} fields are invalid")
        if any(not isinstance(hypothesis[field], str) or not hypothesis[field].strip() for field in required_fields):
            raise InvestigationDraftError(f"hypothesis {index} must include a statement and test conditions")
        statement_key = hypothesis["statement"].strip().casefold()
        if statement_key in statements:
            raise InvestigationDraftError("competing hypotheses must have distinct statements")
        statements.add(statement_key)
        normalized_hypotheses.append({
            "id": f"H{index}",
            "statement": hypothesis["statement"].strip(),
            "state": "NOT_EVALUATED",
            "scope_limit": hypothesis["scope_limit"].strip(),
            "expected_observation": hypothesis["expected_observation"].strip(),
            "would_weaken_if": hypothesis["would_weaken_if"].strip(),
            "testability_state": "NOT_TESTED",
            "testability_reason": "Analyst-authored draft. No evidence relationships or source suitability judgments have been recorded.",
            "required_evidence": [hypothesis["required_evidence"].strip()],
            "evidence_refs": [],
            "evidence_assessments": [],
        })

    follow_up_fields = {
        "target_hypothesis_id",
        "action",
        "discriminating_question",
        "possible_interpretation",
        "priority_reason",
        "expected_observation",
        "would_weaken_if",
        "inconclusive_if",
        "acceptance_gates",
        "interpretation_limit",
    }
    if not isinstance(next_observation, dict) or set(next_observation) != follow_up_fields:
        raise InvestigationDraftError("next-observation test fields are invalid")
    if any(
        not isinstance(next_observation[field], str) or not next_observation[field].strip()
        for field in follow_up_fields - {"acceptance_gates"}
    ):
        raise InvestigationDraftError("next-observation test design must be fully specified")
    target_id = next_observation["target_hypothesis_id"]
    if target_id not in {hypothesis["id"] for hypothesis in normalized_hypotheses}:
        raise InvestigationDraftError("next observation must target one of the authored hypotheses")
    acceptance_gates = [
        item.strip()
        for item in next_observation["acceptance_gates"].splitlines()
        if item.strip()
    ] if isinstance(next_observation["acceptance_gates"], str) else []
    if not acceptance_gates:
        raise InvestigationDraftError("next-observation test requires at least one acceptance gate")
    target_hypothesis = next(
        hypothesis for hypothesis in normalized_hypotheses if hypothesis["id"] == target_id
    )
    follow_up = {
        "follow_up_id": "F1_NEXT_DISCRIMINATING_OBSERVATION",
        "purpose": "DISCRIMINATING_OBSERVATION",
        "availability_state": "NOT_SEARCHED",
        "action": next_observation["action"].strip(),
        "discriminating_question": next_observation["discriminating_question"].strip(),
        "possible_interpretation": next_observation["possible_interpretation"].strip(),
        "priority_reason": next_observation["priority_reason"].strip(),
        "target_hypothesis_ids": [target_id],
        "evidence_refs": [],
        "action_track": "NEW_EVIDENCE_SEARCH",
        "test_design": {
            "hypothesis_under_test_id": target_id,
            "mechanism_branch": target_hypothesis["statement"],
            "expected_observation": next_observation["expected_observation"].strip(),
            "would_weaken_if": next_observation["would_weaken_if"].strip(),
            "inconclusive_if": next_observation["inconclusive_if"].strip(),
            "does_not_test_hypothesis_ids": [
                hypothesis["id"]
                for hypothesis in normalized_hypotheses
                if hypothesis["id"] != target_id
            ],
            "acceptance_gates": acceptance_gates,
            "interpretation_limit": next_observation["interpretation_limit"].strip(),
        },
    }

    created_at_utc = created_at_utc or datetime.now(timezone.utc)
    if created_at_utc.tzinfo is None:
        raise InvestigationDraftError("draft timestamp must include a timezone")
    artifact = {
        "evidence_id": evidence_id,
        "role": role,
        "record_type": source_copy["record_type"],
        "status": source_copy["status"],
        "sha256": source_sha256,
        "lineage": {
            "derived_from_evidence_ids": [],
            "shares_source_observations_with": [],
        },
    }
    draft = {
        "record_type": "ECHO_INVESTIGATION_DRAFT",
        "schema_version": 1,
        "status": "DRAFT_NOT_ASSESSED",
        "created_at_utc": created_at_utc.astimezone(timezone.utc).isoformat(),
        "question": question.strip(),
        "evidence_artifacts": [artifact],
        "source_records": {evidence_id: source_copy},
        "hypotheses": normalized_hypotheses,
        "follow_up_evidence": [follow_up],
        "interpretation_limits": [
            "This is a user-authored investigation draft, not a scientific finding.",
            "The source record is checksummed as submitted; provider data were not re-fetched for draft creation.",
            "No hypothesis has been evaluated and no evidence relationship has been assigned.",
            "Source product maturity and provider QA remain exactly as recorded in the embedded source record.",
        ],
    }
    try:
        validate_investigation_contract(draft)
    except (TypeError, ValueError) as exc:
        raise InvestigationDraftError(f"investigation draft contract failed: {exc}") from exc
    return draft


def validate_investigation_draft(record: dict[str, Any]) -> dict[str, Any]:
    """Verify source integrity and either the unassessed or provisional assessed state."""
    if (
        not isinstance(record, dict)
        or record.get("record_type") != "ECHO_INVESTIGATION_DRAFT"
        or record.get("schema_version") != 1
        or record.get("status") not in {_DRAFT_UNASSESSED, _DRAFT_ASSESSED}
    ):
        raise InvestigationDraftError("record is not a supported unassessed investigation draft")
    artifacts = record.get("evidence_artifacts")
    sources = record.get("source_records")
    if not isinstance(artifacts, list) or not artifacts or not isinstance(sources, dict):
        raise InvestigationDraftError("draft source artifacts are missing")
    if any(
        not isinstance(artifact, dict)
        or not isinstance(artifact.get("evidence_id"), str)
        or not isinstance(artifact.get("role"), str)
        for artifact in artifacts
    ):
        raise InvestigationDraftError("draft source artifact identifiers are invalid")
    artifact_ids = [artifact["evidence_id"] for artifact in artifacts]
    if len(artifact_ids) != len(set(artifact_ids)) or set(artifact_ids) != set(sources):
        raise InvestigationDraftError("draft source artifact identifiers do not match embedded records")
    primary_artifacts = [
        artifact for artifact in artifacts
        if artifact.get("role") in {
            "SAR_PAIR_HELD_AT_PROVIDER_QA",
            "SAR_PAIR_HELD_AT_PRODUCT_MATURITY",
            "DESCRIPTIVE_NISAR_SAR_MEASUREMENT",
            "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT",
            "OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT",
        }
    ]
    if len(primary_artifacts) != 1 or len(artifacts) > 13:
        raise InvestigationDraftError("draft must retain one SAR pair and no more than twelve staged sources")
    staged_artifacts = [artifact for artifact in artifacts if artifact is not primary_artifacts[0]]
    staging_history = record.get("source_staging_history", [])
    if not isinstance(staging_history, list) or len(staging_history) != len(staged_artifacts):
        raise InvestigationDraftError("staged source history does not match the draft artifacts")
    if any(
        not isinstance(entry, dict) or not isinstance(entry.get("evidence_id"), str)
        for entry in staging_history
    ):
        raise InvestigationDraftError("staged source history entries are malformed")
    history_by_id = {entry["evidence_id"]: entry for entry in staging_history}
    if len(history_by_id) != len(staging_history) or set(history_by_id) != {
        artifact["evidence_id"] for artifact in staged_artifacts
    }:
        raise InvestigationDraftError("staged source history identifiers are invalid")
    for artifact in artifacts:
        evidence_id = artifact["evidence_id"]
        source = sources[evidence_id]
        if not isinstance(source, dict) or not isinstance(artifact.get("sha256"), str):
            raise InvestigationDraftError(f"draft source record is malformed: {evidence_id}")
        digest = hashlib.sha256(_canonical_json(source)).hexdigest()
        if (
            digest != artifact["sha256"]
            or artifact.get("record_type") != source.get("record_type")
            or artifact.get("status") != (
                source.get("status")
                if isinstance(source.get("status"), str) and source.get("status")
                else "SOURCE_STATUS_NOT_RECORDED"
            )
        ):
            raise InvestigationDraftError(f"draft source checksum or identity mismatch: {evidence_id}")
        if artifact is primary_artifacts[0]:
            expected_role = _source_role(source)
            if artifact.get("role") != expected_role:
                raise InvestigationDraftError("primary SAR source role does not match its retained QA and maturity status")
        elif (
            artifact.get("role") != "USER_SUPPLIED_SOURCE_NOT_REVIEWED"
            or artifact.get("source_review_state") != "NOT_REVIEWED"
            or artifact.get("independence_state") != "NOT_ASSESSED"
            or artifact.get("ingest_method") != "USER_SUPPLIED_LOCAL_JSON_RECORD"
            or artifact.get("lineage") != {
                "derived_from_evidence_ids": [],
                "shares_source_observations_with": [],
            }
        ):
            raise InvestigationDraftError(f"staged source review labels are invalid: {evidence_id}")
        if artifact is not primary_artifacts[0]:
            history = history_by_id[evidence_id]
            try:
                timestamp = datetime.fromisoformat(str(history.get("attached_at_utc", "")).replace("Z", "+00:00"))
            except ValueError as exc:
                raise InvestigationDraftError(f"staged source timestamp is invalid: {evidence_id}") from exc
            if (
                timestamp.tzinfo is None
                or history.get("method") != "USER_SUPPLIED_LOCAL_JSON_RECORD"
                or history.get("source_review_state") != "NOT_REVIEWED"
                or history.get("independence_state") != "NOT_ASSESSED"
                or history.get("sha256") != artifact["sha256"]
            ):
                raise InvestigationDraftError(f"staged source history does not match its artifact: {evidence_id}")
    hypotheses = record.get("hypotheses")
    if not isinstance(hypotheses, list) or not hypotheses or any(not isinstance(item, dict) for item in hypotheses):
        raise InvestigationDraftError("draft hypotheses are missing")
    if record["status"] == _DRAFT_UNASSESSED:
        if record.get("analyst_assessment") is not None or any(
            hypothesis.get("state") != "NOT_EVALUATED"
            or hypothesis.get("evidence_refs")
            or hypothesis.get("evidence_assessments")
            for hypothesis in hypotheses
            if isinstance(hypothesis, dict)
        ):
            raise InvestigationDraftError("unassessed draft cannot contain hypothesis evidence relationships")
    else:
        _validate_analyst_assessment(record, hypotheses, artifacts)
    follow_ups = record.get("follow_up_evidence")
    if (
        not isinstance(follow_ups, list)
        or len(follow_ups) != 1
        or not isinstance(follow_ups[0], dict)
        or follow_ups[0].get("availability_state") != "NOT_SEARCHED"
        or follow_ups[0].get("evidence_refs")
    ):
        raise InvestigationDraftError("unassessed draft next-observation state is inconsistent")
    try:
        validate_investigation_contract(record)
    except (TypeError, ValueError) as exc:
        raise InvestigationDraftError(f"investigation draft contract failed: {exc}") from exc
    return record


def _validate_analyst_assessment(
    record: dict[str, Any],
    hypotheses: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> None:
    assessment = record.get("analyst_assessment")
    if (
        not isinstance(assessment, dict)
        or assessment.get("method") != "ANALYST_REVIEWED_SOURCE_RELATIONSHIPS"
        or assessment.get("reviewer") != "LOCAL_USER_UNAUTHENTICATED"
        or not isinstance(assessment.get("reviewed_at_utc"), str)
        or assessment.get("interpretation_limit") != _ASSESSMENT_LIMIT
        or not isinstance(assessment.get("records"), list)
        or not assessment["records"]
    ):
        raise InvestigationDraftError("analyst assessment record is missing or malformed")
    try:
        reviewed_at = datetime.fromisoformat(assessment["reviewed_at_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestigationDraftError("analyst assessment timestamp is invalid") from exc
    if reviewed_at.tzinfo is None:
        raise InvestigationDraftError("analyst assessment timestamp must include a timezone")
    assessment_payload = {key: value for key, value in assessment.items() if key != "assessment_sha256"}
    if assessment.get("assessment_sha256") != hashlib.sha256(_canonical_json(assessment_payload)).hexdigest():
        raise InvestigationDraftError("analyst assessment checksum mismatch")

    by_id = {artifact["evidence_id"]: artifact for artifact in artifacts}
    hypothesis_by_id = {item["id"]: item for item in hypotheses}
    records = assessment["records"]
    keys: set[tuple[str, str]] = set()
    expected_by_hypothesis: dict[str, list[dict[str, Any]]] = {key: [] for key in hypothesis_by_id}
    for item in records:
        if not isinstance(item, dict) or set(item) != _ASSESSMENT_FIELDS | {"source_sha256"}:
            raise InvestigationDraftError("analyst relationship record fields are invalid")
        hypothesis_id = item.get("hypothesis_id")
        evidence_id = item.get("evidence_id")
        if (
            not isinstance(hypothesis_id, str)
            or hypothesis_id not in hypothesis_by_id
            or not isinstance(evidence_id, str)
            or evidence_id not in by_id
        ):
            raise InvestigationDraftError("analyst relationship references an unknown hypothesis or source")
        key = (hypothesis_id, evidence_id)
        if key in keys:
            raise InvestigationDraftError("duplicate analyst relationship for a hypothesis and source")
        keys.add(key)
        artifact = by_id[evidence_id]
        if item.get("source_sha256") != artifact.get("sha256"):
            raise InvestigationDraftError("analyst relationship source checksum does not match the retained record")
        for field in ("rationale", "review_basis", "limitations"):
            value = item.get(field)
            if not isinstance(value, str) or len(value.strip()) < 12:
                raise InvestigationDraftError(f"analyst relationship requires a substantive {field}")
        try:
            relation = EvidenceRelation(item.get("relationship"))
        except (TypeError, ValueError) as exc:
            raise InvestigationDraftError("analyst relationship type is unsupported") from exc
        evidence_fit = item.get("evidence_fit")
        if not isinstance(evidence_fit, str) or evidence_fit not in _EVIDENCE_FITS:
            raise InvestigationDraftError("analyst-declared evidence fit is unsupported")
        if relation in {EvidenceRelation.SUPPORTS, EvidenceRelation.CONTRADICTS} and evidence_fit != "SUITABLE_FOR_STATED_SCOPE":
            raise InvestigationDraftError("directional relationships require evidence declared suitable for the stated scope")
        if artifact.get("role") in _NON_DIRECTIONAL_ROLES and relation in {
            EvidenceRelation.SUPPORTS,
            EvidenceRelation.CONTRADICTS,
        }:
            raise InvestigationDraftError(
                "quality-held or diagnostic SAR records cannot directionally support or contradict a hypothesis"
            )
        expected_by_hypothesis[hypothesis_id].append({
            "evidence_id": evidence_id,
            "relationship": relation.value,
            "evidence_fit": evidence_fit,
            "rationale": item["rationale"],
            "review_basis": item["review_basis"],
            "limitations": item["limitations"],
            "source_sha256": item["source_sha256"],
        })

    known_ids = set(by_id)
    for hypothesis_id, hypothesis in hypothesis_by_id.items():
        expected = expected_by_hypothesis[hypothesis_id]
        actual = hypothesis.get("evidence_assessments")
        if not expected:
            if hypothesis.get("state") != "NOT_EVALUATED" or hypothesis.get("evidence_refs") or actual:
                raise InvestigationDraftError("hypothesis state is inconsistent with analyst relationship records")
            continue
        if not isinstance(actual, list) or actual != expected:
            raise InvestigationDraftError(f"hypothesis relationships do not match the analyst review record: actual={actual!r}, expected={expected!r}")
        if hypothesis.get("evidence_refs") != [item["evidence_id"] for item in expected]:
            raise InvestigationDraftError("hypothesis evidence references do not match analyst relationships")
        calculated = evaluate_hypothesis(
            [EvidenceAssessment(item["evidence_id"], EvidenceRelation(item["relationship"]), item["rationale"]) for item in expected],
            known_evidence_ids=known_ids,
        )
        if hypothesis.get("state") != calculated["disposition"] or hypothesis.get("testability_state") != "DESCRIPTIVE_ONLY":
            raise InvestigationDraftError("hypothesis disposition does not match its analyst-coded relationships")


def attach_unreviewed_source(
    draft: dict[str, Any],
    source_record: dict[str, Any],
    *,
    attached_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Stage a supplied source without relating it to any hypothesis."""
    validate_investigation_draft(draft)
    if draft["status"] != _DRAFT_UNASSESSED:
        raise InvestigationDraftError("sources cannot be staged after analyst assessment")
    if (
        not isinstance(source_record, dict)
        or not isinstance(source_record.get("record_type"), str)
        or not source_record["record_type"].strip()
    ):
        raise InvestigationDraftError("staged source must be a record object with a record_type")
    source_bytes = _canonical_json(source_record)
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    evidence_id = f"USER-SOURCE-{source_sha256[:16].upper()}"
    if evidence_id in draft["source_records"] or any(
        artifact.get("sha256") == source_sha256 for artifact in draft["evidence_artifacts"]
    ):
        raise InvestigationDraftError("this source record is already staged in the draft")
    if len(draft["evidence_artifacts"]) >= 13:
        raise InvestigationDraftError("a draft can contain at most twelve staged source records")
    attached_at_utc = attached_at_utc or datetime.now(timezone.utc)
    if attached_at_utc.tzinfo is None:
        raise InvestigationDraftError("source staging timestamp must include a timezone")
    source_status = source_record.get("status")
    artifact = {
        "evidence_id": evidence_id,
        "role": "USER_SUPPLIED_SOURCE_NOT_REVIEWED",
        "record_type": source_record["record_type"],
        "status": source_status if isinstance(source_status, str) and source_status else "SOURCE_STATUS_NOT_RECORDED",
        "sha256": source_sha256,
        "source_review_state": "NOT_REVIEWED",
        "independence_state": "NOT_ASSESSED",
        "ingest_method": "USER_SUPPLIED_LOCAL_JSON_RECORD",
        "lineage": {
            "derived_from_evidence_ids": [],
            "shares_source_observations_with": [],
        },
    }
    updated = deepcopy(draft)
    updated["evidence_artifacts"].append(artifact)
    updated["source_records"][evidence_id] = deepcopy(source_record)
    updated.setdefault("source_staging_history", []).append({
        "evidence_id": evidence_id,
        "attached_at_utc": attached_at_utc.astimezone(timezone.utc).isoformat(),
        "method": "USER_SUPPLIED_LOCAL_JSON_RECORD",
        "source_review_state": "NOT_REVIEWED",
        "independence_state": "NOT_ASSESSED",
        "sha256": source_sha256,
    })
    updated["interpretation_limits"] = list(updated.get("interpretation_limits", []))
    updated["interpretation_limits"].append(
        "A user-supplied source record is staged but has not been reviewed, linked to a hypothesis, or assessed for independence."
    )
    validate_investigation_draft(updated)
    return updated


def assess_investigation_draft(
    draft: dict[str, Any],
    assessments: list[dict[str, Any]],
    *,
    assessed_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Record explicit analyst relationships without authenticating sources or claims."""
    validate_investigation_draft(draft)
    if draft["status"] != _DRAFT_UNASSESSED:
        raise InvestigationDraftError("only an unassessed draft can receive its initial analyst assessment")
    if not isinstance(assessments, list) or not assessments or len(assessments) > 78:
        raise InvestigationDraftError("provide between one and 78 explicit source-to-hypothesis assessments")
    updated = deepcopy(draft)
    evidence_by_id = {item["evidence_id"]: item for item in updated["evidence_artifacts"]}
    hypotheses_by_id = {item["id"]: item for item in updated["hypotheses"]}
    seen: set[tuple[str, str]] = set()
    normalized: list[dict[str, Any]] = []
    by_hypothesis: dict[str, list[dict[str, Any]]] = {key: [] for key in hypotheses_by_id}
    for item in assessments:
        if not isinstance(item, dict) or set(item) != _ASSESSMENT_FIELDS:
            raise InvestigationDraftError("assessment input fields are invalid")
        hypothesis_id, evidence_id = item.get("hypothesis_id"), item.get("evidence_id")
        if (
            not isinstance(hypothesis_id, str)
            or hypothesis_id not in hypotheses_by_id
            or not isinstance(evidence_id, str)
            or evidence_id not in evidence_by_id
        ):
            raise InvestigationDraftError("assessment references an unknown hypothesis or source")
        key = (hypothesis_id, evidence_id)
        if key in seen:
            raise InvestigationDraftError("duplicate assessment for a hypothesis and source")
        seen.add(key)
        artifact = evidence_by_id[evidence_id]
        values = {field: item.get(field) for field in _ASSESSMENT_FIELDS}
        for field in ("rationale", "review_basis", "limitations"):
            value = values[field]
            if not isinstance(value, str) or len(value.strip()) < 12:
                raise InvestigationDraftError(f"assessment requires a substantive {field}")
            values[field] = value.strip()
        try:
            relation = EvidenceRelation(values["relationship"])
        except (TypeError, ValueError) as exc:
            raise InvestigationDraftError("assessment relationship is unsupported") from exc
        evidence_fit = values["evidence_fit"]
        if not isinstance(evidence_fit, str) or evidence_fit not in _EVIDENCE_FITS:
            raise InvestigationDraftError("analyst-declared evidence fit is unsupported")
        if relation in {EvidenceRelation.SUPPORTS, EvidenceRelation.CONTRADICTS} and evidence_fit != "SUITABLE_FOR_STATED_SCOPE":
            raise InvestigationDraftError("directional relationships require evidence declared suitable for the stated scope")
        if artifact["role"] in _NON_DIRECTIONAL_ROLES and relation in {
            EvidenceRelation.SUPPORTS,
            EvidenceRelation.CONTRADICTS,
        }:
            raise InvestigationDraftError(
                "quality-held or diagnostic SAR records cannot directionally support or contradict a hypothesis"
            )
        values["relationship"] = relation.value
        values["evidence_fit"] = evidence_fit
        values["source_sha256"] = artifact["sha256"]
        by_hypothesis[hypothesis_id].append({key: value for key, value in values.items() if key != "hypothesis_id"})
        normalized.append({"hypothesis_id": hypothesis_id, **values})

    for hypothesis_id, hypothesis in hypotheses_by_id.items():
        entries = by_hypothesis[hypothesis_id]
        if not entries:
            continue
        calculated = evaluate_hypothesis(
            [EvidenceAssessment(item["evidence_id"], EvidenceRelation(item["relationship"]), item["rationale"]) for item in entries],
            known_evidence_ids=set(evidence_by_id),
        )
        hypothesis["state"] = calculated["disposition"]
        hypothesis["evidence_assessments"] = entries
        hypothesis["evidence_refs"] = [item["evidence_id"] for item in entries]
        hypothesis["testability_state"] = "DESCRIPTIVE_ONLY"
        hypothesis["testability_reason"] = (
            "Relationships were entered by an unauthenticated local user. This deterministic disposition "
            "summarizes those entries; source credibility, suitability, independence, and scientific claims "
            "were not independently verified."
        )
    assessed_at_utc = assessed_at_utc or datetime.now(timezone.utc)
    if assessed_at_utc.tzinfo is None:
        raise InvestigationDraftError("assessment timestamp must include a timezone")
    updated["status"] = _DRAFT_ASSESSED
    analyst_assessment = {
        "method": "ANALYST_REVIEWED_SOURCE_RELATIONSHIPS",
        "reviewer": "LOCAL_USER_UNAUTHENTICATED",
        "reviewed_at_utc": assessed_at_utc.astimezone(timezone.utc).isoformat(),
        "records": normalized,
        "interpretation_limit": _ASSESSMENT_LIMIT,
    }
    analyst_assessment["assessment_sha256"] = hashlib.sha256(_canonical_json(analyst_assessment)).hexdigest()
    updated["analyst_assessment"] = analyst_assessment
    updated["interpretation_limits"] = list(updated.get("interpretation_limits", [])) + [
        "Analyst-coded evidence relationships are provisional and unauthenticated; source credibility, suitability, independence, and scientific interpretations remain unverified."
    ]
    validate_investigation_draft(updated)
    return updated
