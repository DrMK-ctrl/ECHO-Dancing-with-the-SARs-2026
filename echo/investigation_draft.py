"""Build source-linked, analyst-authored investigation drafts from SAR pair records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from echo.investigation import validate_investigation_contract


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
    """Verify a draft's embedded source checksums and unassessed-state boundary."""
    if (
        not isinstance(record, dict)
        or record.get("record_type") != "ECHO_INVESTIGATION_DRAFT"
        or record.get("schema_version") != 1
        or record.get("status") != "DRAFT_NOT_ASSESSED"
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
    if any(
        hypothesis.get("state") != "NOT_EVALUATED"
        or hypothesis.get("evidence_refs")
        or hypothesis.get("evidence_assessments")
        for hypothesis in hypotheses
        if isinstance(hypothesis, dict)
    ):
        raise InvestigationDraftError("unassessed draft cannot contain hypothesis evidence relationships")
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


def attach_unreviewed_source(
    draft: dict[str, Any],
    source_record: dict[str, Any],
    *,
    attached_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Stage a supplied source without relating it to any hypothesis."""
    validate_investigation_draft(draft)
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
