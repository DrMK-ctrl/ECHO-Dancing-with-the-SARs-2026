"""Build source-linked, analyst-authored investigation drafts from SAR pair records."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from echo.investigation import (
    EvidenceAssessment,
    EvidenceRelation,
    FollowUpAvailability,
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
    "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_TEMPORAL_SERIES",
    "OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT",
    "CATALOG_AVAILABILITY_METADATA_ONLY",
    "FOLLOWUP_PROVIDER_QA_METADATA_ONLY",
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
_CASE_IMPORT_METHOD = "VALIDATED_LOCAL_CASE_ASSESSMENT"
_USER_IMPORT_METHOD = "USER_SUPPLIED_LOCAL_JSON_RECORD"
_CATALOG_SCREEN_METHOD = "ECHO_FOLLOWUP_ASF_GCOV_CATALOG_SCREEN"
_FOLLOWUP_QA_METHOD = "ECHO_FOLLOWUP_ASF_GCOV_QA_METADATA"
_QA_RETRIEVED_AT_ATTACHMENT = "ASF_QA_CSV_RETRIEVED_BY_ECHO_AT_ATTACHMENT"
_QA_SNAPSHOT_NOT_REVERIFIED = "RETRIEVAL_PROVENANCE_RETAINED_NOT_REVERIFIED_AT_ATTACHMENT"
_CASE_PROVENANCE_FIELDS = {
    "active_case_id", "case_id", "assessment_record_type", "assessment_status",
    "assessment_relative_path", "assessment_sha256", "source_evidence_id",
    "source_relative_path", "source_sha256", "source_record_type", "source_status",
    "source_role", "source_content_sha256", "imported_at_utc",
}
_FOLLOWUP_SCREEN_FIELDS = {
    "method", "reviewer", "screened_at_utc", "source_evidence_id", "source_sha256",
    "gate_results", "review_basis", "limitations", "sha256",
}
_FOLLOWUP_GATE_RESULTS = {"MET", "NOT_MET", "UNKNOWN"}


def _is_relative_evidence_path(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value)


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


def _validate_followup_catalog_screen(record: dict[str, Any]) -> None:
    """Validate a metadata-only NISAR catalog screen retained for one test."""
    if (
        record.get("record_type") != "ECHO_FOLLOWUP_CATALOG_SCREEN"
        or record.get("schema_version") != 1
        or record.get("status") != "CATALOG_METADATA_ONLY"
    ):
        raise InvestigationDraftError("follow-up catalog screen identity or status is unsupported")
    link = record.get("follow_up_link")
    catalog = record.get("catalog_record")
    source = catalog.get("source") if isinstance(catalog, dict) else None
    query = catalog.get("query") if isinstance(catalog, dict) else None
    features = catalog.get("features") if isinstance(catalog, dict) else None
    result_count = catalog.get("feature_count") if isinstance(catalog, dict) else None
    if (
        not isinstance(link, dict)
        or not isinstance(link.get("follow_up_id"), str)
        or not isinstance(link.get("target_hypothesis_id"), str)
        or not _is_sha256(link.get("test_design_sha256"))
        or not isinstance(source, dict)
        or source.get("provider") != "Alaska Satellite Facility DAAC"
        or source.get("catalog_only") is not True
        or source.get("pixels_downloaded") is not False
        or not isinstance(query, dict)
        or query.get("dataset") != "NISAR"
        or query.get("processing_level") != "GCOV"
        or not isinstance(features, list)
        or isinstance(result_count, bool)
        or not isinstance(result_count, int)
        or result_count != len(features)
        or isinstance(source.get("returned_feature_count"), bool)
        or not isinstance(source.get("returned_feature_count"), int)
        or result_count != source.get("returned_feature_count")
        or not isinstance(source.get("potentially_truncated"), bool)
        or not isinstance(record.get("catalog_record_sha256"), str)
        or record.get("catalog_record_sha256") != hashlib.sha256(_canonical_json(catalog)).hexdigest()
        or not isinstance(record.get("search_result"), dict)
        or record["search_result"].get("state") != ("MATCHES_FOUND" if result_count else "NO_MATCHES")
        or record["search_result"].get("returned_feature_count") != result_count
        or record["search_result"].get("potentially_truncated") != source.get("potentially_truncated")
        or record.get("test_compatibility_state") != "NOT_ASSESSED_METADATA_ONLY"
    ):
        raise InvestigationDraftError("follow-up catalog search provenance or result count is invalid")
    if not isinstance(record.get("created_at_utc"), str):
        raise InvestigationDraftError("follow-up catalog screen timestamp is missing")
    try:
        timestamp = datetime.fromisoformat(record["created_at_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestigationDraftError("follow-up catalog screen timestamp is invalid") from exc
    if timestamp.tzinfo is None:
        raise InvestigationDraftError("follow-up catalog screen timestamp must include a timezone")


def _validate_followup_provider_qa_screen(record: dict[str, Any]) -> None:
    """Validate a provider QA record linked to one retained catalog candidate."""
    inspection = record.get("provider_qa_record")
    source_catalog = inspection.get("source_catalog") if isinstance(inspection, dict) else None
    feature = source_catalog.get("feature") if isinstance(source_catalog, dict) else None
    properties = feature.get("properties") if isinstance(feature, dict) else None
    summary = inspection.get("provider_qa_summary") if isinstance(inspection, dict) else None
    scene_id = record.get("scene_id")
    if (
        record.get("record_type") != "ECHO_FOLLOWUP_PROVIDER_QA_SCREEN"
        or record.get("schema_version") != 1
        or record.get("status") != "PROVIDER_QA_METADATA_ONLY"
        or record.get("provider") != "Alaska Satellite Facility DAAC"
        or not isinstance(scene_id, str)
        or not scene_id
        or not isinstance(record.get("catalog_availability_evidence_id"), str)
        or not _is_sha256(record.get("catalog_record_sha256"))
        or record.get("test_compatibility_state") != "NOT_ASSESSED_METADATA_ONLY"
        or record.get("provider_response_verification") not in {
            _QA_RETRIEVED_AT_ATTACHMENT,
            _QA_SNAPSHOT_NOT_REVERIFIED,
        }
        or not isinstance(record.get("follow_up_link"), dict)
        or not isinstance(inspection, dict)
        or inspection.get("record_type") != "ECHO_PROVIDER_QA_INSPECTION"
        or not isinstance(source_catalog, dict)
        or source_catalog.get("provider") != "Alaska Satellite Facility DAAC"
        or not isinstance(feature, dict)
        or not isinstance(properties, dict)
        or properties.get("fileID") != scene_id
        or not isinstance(summary, dict)
        or summary.get("scene_id") != scene_id
        or not _is_sha256(record.get("provider_qa_record_sha256"))
        or record.get("provider_qa_record_sha256") != hashlib.sha256(_canonical_json(inspection)).hexdigest()
    ):
        raise InvestigationDraftError("follow-up provider-QA record identity or source linkage is invalid")
    source_query = source_catalog.get("query")
    if (
        not isinstance(source_query, dict)
        or source_query.get("dataset") != "NISAR"
        or source_query.get("processing_level") != "GCOV"
    ):
        raise InvestigationDraftError("follow-up provider-QA source is not a NISAR GCOV catalog candidate")
    try:
        created = datetime.fromisoformat(str(record.get("created_at_utc", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestigationDraftError("follow-up provider-QA timestamp is invalid") from exc
    if created.tzinfo is None:
        raise InvestigationDraftError("follow-up provider-QA timestamp must include a timezone")
    if record["provider_response_verification"] == _QA_RETRIEVED_AT_ATTACHMENT:
        retrieval = summary.get("retrieval")
        evidence = summary.get("evidence")
        uri = summary.get("artifact_uri")
        try:
            parsed_uri = urlsplit(uri) if isinstance(uri, str) else None
            retrieved = datetime.fromisoformat(str(summary.get("retrieved_at_utc", "")).replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvestigationDraftError("retrieved provider-QA provenance is invalid") from exc
        if (
            not isinstance(retrieval, dict)
            or retrieval.get("provider") != "Alaska Satellite Facility DAAC"
            or retrieval.get("authentication") != "Earthdata Login via local netrc"
            or retrieval.get("method") != "HTTPS byte-range streaming"
            or retrieval.get("network_retrieval") is not True
            or isinstance(retrieval.get("fsspec_range_bytes_requested"), bool)
            or not isinstance(retrieval.get("fsspec_range_bytes_requested"), int)
            or retrieval.get("fsspec_range_bytes_requested") <= 0
            or not isinstance(evidence, dict)
            or summary.get("artifact_sha256") != evidence.get("artifact_sha256")
            or uri != evidence.get("artifact_uri")
            or parsed_uri is None
            or parsed_uri.scheme != "https"
            or parsed_uri.netloc != "nisar.asf.earthdatacloud.nasa.gov"
            or parsed_uri.query
            or parsed_uri.fragment
            or parsed_uri.path.rsplit("/", 1)[-1] != f"{scene_id}_QA_SUMMARY.csv"
            or retrieved.tzinfo is None
        ):
            raise InvestigationDraftError("retrieved provider-QA provenance is incomplete or inconsistent")


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
    if kind == "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS":
        source = record.get("source")
        qa = record.get("provider_qa")
        observations = record.get("observations")
        intervals = record.get("adjacent_intervals")
        grid = record.get("grid")
        if (
            status != "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
            or not isinstance(source, dict)
            or source.get("provider") != "Alaska Satellite Facility DAAC"
            or "OPERA RTC-S1" not in str(source.get("mission_product", ""))
            or "not NISAR" not in str(source.get("mission_product", ""))
            or not isinstance(qa, dict)
            or qa.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
            or record.get("processing", {}).get("intervals_share_observations") is not True
            or not isinstance(observations, list)
            or not 3 <= len(observations) <= 12
            or not isinstance(intervals, list)
            or len(intervals) != len(observations) - 1
            or not isinstance(grid, dict)
        ):
            raise InvestigationDraftError("OPERA temporal series identity or diagnostic QA status is unsupported")
        shape = grid.get("window", {}).get("shape") if isinstance(grid.get("window"), dict) else None
        if (
            not isinstance(shape, list)
            or len(shape) != 2
            or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in shape)
            or shape[0] * shape[1] > 65536
        ):
            raise InvestigationDraftError("OPERA temporal series grid shape is invalid or exceeds the supported bound")
        scene_ids: list[str] = []
        previous_time: datetime | None = None
        for index, observation in enumerate(observations):
            if not isinstance(observation, dict) or not all(
                isinstance(observation.get(field), str) and observation[field]
                for field in ("scene_id", "acquisition_start_utc", "burst_id", "platform", "product_version", "polarization")
            ):
                raise InvestigationDraftError("OPERA temporal series observation metadata are incomplete")
            if any(observation[field] != source.get(source_field) for field, source_field in (
                ("burst_id", "burst_id"), ("platform", "platform"),
                ("product_version", "product_version"), ("polarization", "polarization"),
            )):
                raise InvestigationDraftError("OPERA temporal series observations do not share their declared source identity")
            try:
                acquired = datetime.fromisoformat(observation["acquisition_start_utc"].replace("Z", "+00:00"))
            except ValueError as exc:
                raise InvestigationDraftError("OPERA temporal series acquisition timestamp is invalid") from exc
            if acquired.tzinfo is None or (previous_time is not None and acquired <= previous_time):
                raise InvestigationDraftError("OPERA temporal series acquisitions must be timezone-aware and increasing")
            previous_time = acquired
            scene_ids.append(observation["scene_id"])
            values = observation.get("backscatter_db_on_common_support")
            if (
                not isinstance(values, list)
                or len(values) != shape[0]
                or any(not isinstance(row, list) or len(row) != shape[1] for row in values)
            ):
                raise InvestigationDraftError("OPERA temporal series observation arrays do not match the declared grid")
        if len(scene_ids) != len(set(scene_ids)):
            raise InvestigationDraftError("OPERA temporal series scene identifiers must be unique")
        per_observation_qa = qa.get("per_observation")
        if (
            not isinstance(per_observation_qa, list)
            or len(per_observation_qa) != len(observations)
            or any(
                not isinstance(item, dict)
                or item.get("scene_id") != scene_ids[index]
                or not isinstance(item.get("quality_metadata"), dict)
                or item["quality_metadata"].get("status")
                != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
                for index, item in enumerate(per_observation_qa)
            )
        ):
            raise InvestigationDraftError("OPERA temporal series per-observation QA links are incomplete")
        for index, interval in enumerate(intervals):
            if (
                not isinstance(interval, dict)
                or interval.get("before_scene_id") != scene_ids[index]
                or interval.get("after_scene_id") != scene_ids[index + 1]
                or not isinstance(interval.get("values_db"), list)
                or len(interval["values_db"]) != shape[0]
                or any(not isinstance(row, list) or len(row) != shape[1] for row in interval["values_db"])
                or not isinstance(interval.get("valid_mask"), list)
                or len(interval["valid_mask"]) != shape[0]
                or any(not isinstance(row, list) or len(row) != shape[1] for row in interval["valid_mask"])
            ):
                raise InvestigationDraftError("OPERA temporal series intervals do not match adjacent observations and grid")
        return "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_TEMPORAL_SERIES"
    raise InvestigationDraftError("source record must be a supported GCOV or OPERA RTC-S1 pair analysis")


def build_investigation_draft(
    source_record: dict[str, Any],
    *,
    source_record_json: str | None = None,
    question: str,
    hypotheses: list[dict[str, str]],
    next_observation: dict[str, Any],
    created_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Create a reproducible draft without assigning evidence relationships.

    When supplied, the exact submitted JSON text is retained and checksummed.
    Direct callers without source text use a canonical serialization. Neither
    method re-fetches or authenticates the provider response.
    """
    if not isinstance(source_record, dict):
        raise InvestigationDraftError("source record must be an object")
    if not isinstance(question, str) or len(question.strip()) < 12:
        raise InvestigationDraftError("investigation question must contain at least 12 characters")
    if not isinstance(hypotheses, list) or not 2 <= len(hypotheses) <= 6:
        raise InvestigationDraftError("enter between two and six competing hypotheses")

    source_copy = deepcopy(source_record)
    if source_record_json is not None:
        if not isinstance(source_record_json, str):
            raise InvestigationDraftError("source record JSON text must be a string")
        try:
            parsed_source = json.loads(source_record_json)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise InvestigationDraftError("source record JSON text is invalid") from exc
        if _canonical_json(parsed_source) != _canonical_json(source_copy):
            raise InvestigationDraftError("source record JSON text does not match the parsed source object")
        source_bytes = source_record_json.encode("utf-8")
        retained_source: dict[str, Any] | str = source_record_json
    else:
        source_bytes = _canonical_json(source_copy)
        retained_source = source_copy
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
        "revision": None,
        "created_at_utc": created_at_utc.astimezone(timezone.utc).isoformat(),
        "question": question.strip(),
        "evidence_artifacts": [artifact],
        "source_records": {evidence_id: retained_source},
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


def revise_investigation_draft(
    parent: dict[str, Any],
    *,
    next_observation: dict[str, Any],
    question: str | None = None,
    revised_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Start a new unassessed round linked to an assessed immutable draft.

    The prior snapshot remains the record of the previous assessment. The new
    round reuses its source artifacts and hypothesis definitions, but clears
    their dispositions so analysts must review the evidence again. This does
    not add evidence or validate the prior relationships.
    """
    validate_investigation_draft(parent)
    if parent.get("status") != _DRAFT_ASSESSED:
        raise InvestigationDraftError("only an assessed saved investigation can start a revision")
    source_artifacts = parent["evidence_artifacts"]
    primary = next(
        artifact for artifact in source_artifacts
        if artifact.get("role") in _NON_DIRECTIONAL_ROLES
    )
    staged_artifacts = [
        artifact for artifact in source_artifacts
        if artifact["evidence_id"] != primary["evidence_id"]
    ]
    primary_record_value = parent["source_records"][primary["evidence_id"]]
    if isinstance(primary_record_value, str):
        try:
            primary_record = json.loads(primary_record_value)
        except (json.JSONDecodeError, RecursionError) as exc:
            raise InvestigationDraftError("prior SAR source record is invalid") from exc
        primary_record_json = primary_record_value
    elif isinstance(primary_record_value, dict):
        primary_record = primary_record_value
        primary_record_json = None
    else:
        raise InvestigationDraftError("prior SAR source record is malformed")

    hypothesis_inputs = []
    for hypothesis in parent["hypotheses"]:
        hypothesis_inputs.append({
            "statement": hypothesis["statement"],
            "scope_limit": hypothesis["scope_limit"],
            "expected_observation": hypothesis["expected_observation"],
            "would_weaken_if": hypothesis["would_weaken_if"],
            "required_evidence": "\n".join(hypothesis["required_evidence"]),
        })

    revised_at_utc = revised_at_utc or datetime.now(timezone.utc)
    if revised_at_utc.tzinfo is None:
        raise InvestigationDraftError("revision timestamp must include a timezone")
    current_question = question if question is not None else parent["question"]
    revision = build_investigation_draft(
        primary_record,
        source_record_json=primary_record_json,
        question=current_question,
        hypotheses=hypothesis_inputs,
        next_observation=next_observation,
        created_at_utc=revised_at_utc,
    )

    # Preserve the exact staged evidence records and their ingestion history;
    # only the analyst's prior hypothesis relationships are cleared.
    revision["evidence_artifacts"].extend(deepcopy(staged_artifacts))
    for artifact in staged_artifacts:
        evidence_id = artifact["evidence_id"]
        revision["source_records"][evidence_id] = deepcopy(parent["source_records"][evidence_id])
    revision["source_staging_history"] = deepcopy(parent.get("source_staging_history", []))
    parent_assessment = parent["analyst_assessment"]
    parent_revision = parent.get("revision")
    parent_revision_number = parent_revision.get("revision_number", 0) if isinstance(parent_revision, dict) else 0
    revision["revision"] = {
        "parent_draft_sha256": hashlib.sha256(_canonical_json(parent)).hexdigest(),
        "parent_assessment_sha256": parent_assessment["assessment_sha256"],
        "revision_number": parent_revision_number + 1,
        "created_at_utc": revised_at_utc.astimezone(timezone.utc).isoformat(),
    }
    revision["interpretation_limits"].append(
        "This revision starts a new assessment round. Its prior immutable draft is linked by checksum; "
        "previous hypothesis relationships were cleared for independent reassessment."
    )
    validate_investigation_draft(revision)
    return revision


def validate_investigation_draft(record: dict[str, Any]) -> dict[str, Any]:
    """Verify source integrity and either the unassessed or provisional assessed state."""
    if (
        not isinstance(record, dict)
        or record.get("record_type") != "ECHO_INVESTIGATION_DRAFT"
        or record.get("schema_version") != 1
        or record.get("status") not in {_DRAFT_UNASSESSED, _DRAFT_ASSESSED}
    ):
        raise InvestigationDraftError("record is not a supported unassessed investigation draft")
    revision = record.get("revision")
    if revision is not None:
        revision_fields = {
            "parent_draft_sha256", "parent_assessment_sha256", "revision_number", "created_at_utc"
        }
        if not isinstance(revision, dict) or set(revision) != revision_fields:
            raise InvestigationDraftError("draft revision lineage is malformed")
        if not all(_is_sha256(revision.get(field)) for field in ("parent_draft_sha256", "parent_assessment_sha256")):
            raise InvestigationDraftError("draft revision lineage checksums are invalid")
        if (
            not isinstance(revision.get("revision_number"), int)
            or isinstance(revision.get("revision_number"), bool)
            or revision["revision_number"] < 1
        ):
            raise InvestigationDraftError("draft revision number is invalid")
        try:
            revision_time = datetime.fromisoformat(str(revision.get("created_at_utc", "")).replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvestigationDraftError("draft revision timestamp is invalid") from exc
        if revision_time.tzinfo is None:
            raise InvestigationDraftError("draft revision timestamp must include a timezone")
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
            "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_TEMPORAL_SERIES",
            "OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT",
        }
    ]
    if len(primary_artifacts) != 1 or len(artifacts) > 13:
        raise InvestigationDraftError("draft must retain one SAR source and no more than twelve staged sources")
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
        source_value = sources[evidence_id]
        source_json: str | None = None
        if isinstance(source_value, dict):
            source = source_value
            digest = hashlib.sha256(_canonical_json(source)).hexdigest()
        elif isinstance(source_value, str) and (
            artifact is primary_artifacts[0] or artifact.get("ingest_method") == _CASE_IMPORT_METHOD
        ):
            source_json = source_value
            try:
                source = json.loads(source_json)
            except (json.JSONDecodeError, RecursionError) as exc:
                raise InvestigationDraftError(f"case-linked source JSON is invalid: {evidence_id}") from exc
            if not isinstance(source, dict):
                raise InvestigationDraftError(f"case-linked source record is not an object: {evidence_id}")
            digest = hashlib.sha256(source_json.encode("utf-8")).hexdigest()
        else:
            raise InvestigationDraftError(f"draft source record is malformed: {evidence_id}")
        if not isinstance(artifact.get("sha256"), str):
            raise InvestigationDraftError(f"draft source record is malformed: {evidence_id}")
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
        else:
            method = artifact.get("ingest_method")
            if (
                artifact.get("independence_state") != "NOT_ASSESSED"
                or artifact.get("lineage") != {
                    "derived_from_evidence_ids": [],
                    "shares_source_observations_with": [],
                }
            ):
                raise InvestigationDraftError(f"staged source review labels are invalid: {evidence_id}")
            if method == _USER_IMPORT_METHOD:
                if (
                    artifact.get("role") != "USER_SUPPLIED_SOURCE_NOT_REVIEWED"
                    or artifact.get("source_review_state") != "NOT_REVIEWED"
                ):
                    raise InvestigationDraftError(f"staged source review labels are invalid: {evidence_id}")
            elif method == _CATALOG_SCREEN_METHOD:
                _validate_followup_catalog_screen(source)
                if (
                    artifact.get("role") != "CATALOG_AVAILABILITY_METADATA_ONLY"
                    or artifact.get("source_review_state") != "CATALOG_STRUCTURE_VALIDATED_METADATA_ONLY"
                ):
                    raise InvestigationDraftError(f"catalog screen status labels are invalid: {evidence_id}")
            elif method == _FOLLOWUP_QA_METHOD:
                _validate_followup_provider_qa_screen(source)
                if (
                    artifact.get("role") != "FOLLOWUP_PROVIDER_QA_METADATA_ONLY"
                    or artifact.get("source_review_state") != "PROVIDER_QA_LINKED_METADATA_ONLY"
                ):
                    raise InvestigationDraftError(f"provider-QA source status labels are invalid: {evidence_id}")
            elif method == _CASE_IMPORT_METHOD:
                provenance = artifact.get("case_provenance")
                if (
                    artifact.get("source_review_state") != "CASE_RECORD_INTEGRITY_VALIDATED"
                    or not isinstance(provenance, dict)
                    or set(provenance) != _CASE_PROVENANCE_FIELDS
                    or provenance.get("source_role") != artifact.get("role")
                    or provenance.get("source_record_type") != artifact.get("record_type")
                    or provenance.get("source_status") != artifact.get("status")
                    or provenance.get("source_content_sha256") != digest
                    or (source_json is not None and provenance.get("source_sha256") != digest)
                    or not all(_is_sha256(provenance.get(field)) for field in ("assessment_sha256", "source_sha256", "source_content_sha256"))
                    or not all(_is_relative_evidence_path(provenance.get(field)) for field in ("assessment_relative_path", "source_relative_path"))
                    or not all(isinstance(provenance.get(field), str) and provenance[field] for field in ("active_case_id", "case_id", "assessment_record_type", "assessment_status", "source_evidence_id"))
                ):
                    raise InvestigationDraftError(f"validated case source provenance is invalid: {evidence_id}")
                try:
                    imported_at = datetime.fromisoformat(str(provenance.get("imported_at_utc", "")).replace("Z", "+00:00"))
                except ValueError as exc:
                    raise InvestigationDraftError(f"validated case source timestamp is invalid: {evidence_id}") from exc
                if imported_at.tzinfo is None:
                    raise InvestigationDraftError(f"validated case source timestamp must include a timezone: {evidence_id}")
            else:
                raise InvestigationDraftError(f"staged source ingestion method is unsupported: {evidence_id}")
        if artifact is not primary_artifacts[0]:
            history = history_by_id[evidence_id]
            try:
                timestamp = datetime.fromisoformat(str(history.get("attached_at_utc", "")).replace("Z", "+00:00"))
            except ValueError as exc:
                raise InvestigationDraftError(f"staged source timestamp is invalid: {evidence_id}") from exc
            if (
                timestamp.tzinfo is None
                or history.get("method") != artifact.get("ingest_method")
                or history.get("independence_state") != "NOT_ASSESSED"
                or history.get("sha256") != artifact["sha256"]
            ):
                raise InvestigationDraftError(f"staged source history does not match its artifact: {evidence_id}")
            if artifact.get("ingest_method") == _USER_IMPORT_METHOD and history.get("source_review_state") != "NOT_REVIEWED":
                raise InvestigationDraftError(f"staged source history does not match its artifact: {evidence_id}")
            if artifact.get("ingest_method") == _CATALOG_SCREEN_METHOD and history.get("source_review_state") != "CATALOG_STRUCTURE_VALIDATED_METADATA_ONLY":
                raise InvestigationDraftError(f"catalog source history does not match its artifact: {evidence_id}")
            if artifact.get("ingest_method") == _FOLLOWUP_QA_METHOD and history.get("source_review_state") != "PROVIDER_QA_LINKED_METADATA_ONLY":
                raise InvestigationDraftError(f"provider-QA source history does not match its artifact: {evidence_id}")
            if artifact.get("ingest_method") == _CASE_IMPORT_METHOD and history.get("case_provenance") != artifact.get("case_provenance"):
                raise InvestigationDraftError(f"case source history does not match its artifact: {evidence_id}")
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
    ):
        raise InvestigationDraftError("draft next-observation record is invalid")
    follow_up = follow_ups[0]
    followup_design = follow_up.get("test_design")
    for artifact in artifacts:
        method = artifact.get("ingest_method")
        if method not in {_CATALOG_SCREEN_METHOD, _FOLLOWUP_QA_METHOD}:
            continue
        screen = sources[artifact["evidence_id"]]
        link = screen["follow_up_link"]
        if (
            link.get("follow_up_id") != follow_up.get("follow_up_id")
            or not isinstance(followup_design, dict)
            or link.get("target_hypothesis_id") != followup_design.get("hypothesis_under_test_id")
            or link.get("test_design_sha256") != hashlib.sha256(_canonical_json(followup_design)).hexdigest()
        ):
            raise InvestigationDraftError("staged discovery source is not linked to this draft's current follow-up test")
        if method == _FOLLOWUP_QA_METHOD:
            parent_id = screen["catalog_availability_evidence_id"]
            parent = next((item for item in artifacts if item["evidence_id"] == parent_id), None)
            parent_record = sources.get(parent_id)
            parent_catalog = parent_record.get("catalog_record") if isinstance(parent_record, dict) else None
            parent_features = parent_catalog.get("features") if isinstance(parent_catalog, dict) else None
            if (
                parent is None
                or parent.get("ingest_method") != _CATALOG_SCREEN_METHOD
                or not isinstance(parent_record, dict)
                or parent_record.get("catalog_record_sha256") != screen.get("catalog_record_sha256")
                or not isinstance(parent_features, list)
                or not any(
                    isinstance(item, dict)
                    and isinstance(item.get("properties"), dict)
                    and item["properties"].get("fileID") == screen.get("scene_id")
                    for item in parent_features
                )
            ):
                raise InvestigationDraftError("provider-QA source is not linked to a scene in its retained catalog search")
    availability = follow_up.get("availability_state")
    screening = follow_up.get("screening_review")
    if availability == FollowUpAvailability.NOT_SEARCHED.value:
        if follow_up.get("evidence_refs") or screening is not None:
            raise InvestigationDraftError("unsearched next observation cannot contain evidence or a screening result")
    elif availability in {
        FollowUpAvailability.SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE.value,
        FollowUpAvailability.CANDIDATE_RETRIEVED_UNASSESSED.value,
    }:
        refs = follow_up.get("evidence_refs")
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(item, str) for item in refs)
            or len(refs) != len(set(refs))
            or screening is not None
        ):
            raise InvestigationDraftError("open follow-up search must retain unique metadata evidence without a gate screen")
        linked_catalogs: list[dict[str, Any]] = []
        linked_qa_parent_ids: set[str] = set()
        for evidence_id in refs:
            artifact = next((item for item in artifacts if item.get("evidence_id") == evidence_id), None)
            source = sources.get(evidence_id)
            if artifact is None or not isinstance(source, dict):
                raise InvestigationDraftError("open follow-up evidence references an unknown staged source")
            if artifact.get("ingest_method") == _CATALOG_SCREEN_METHOD:
                linked_catalogs.append(source)
            elif artifact.get("ingest_method") == _FOLLOWUP_QA_METHOD:
                linked_qa_parent_ids.add(source.get("catalog_availability_evidence_id"))
            else:
                raise InvestigationDraftError("open follow-up evidence must remain catalog or provider-QA metadata")
        if not linked_catalogs or not linked_qa_parent_ids.issubset(set(refs)):
            raise InvestigationDraftError("open follow-up metadata must retain its parent catalog evidence")
        has_candidate = any(
            isinstance(source.get("catalog_record"), dict)
            and source["catalog_record"].get("feature_count", 0) > 0
            for source in linked_catalogs
        )
        expected_availability = (
            FollowUpAvailability.CANDIDATE_RETRIEVED_UNASSESSED.value
            if has_candidate else FollowUpAvailability.SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE.value
        )
        if availability != expected_availability:
            raise InvestigationDraftError("open follow-up state does not match its linked catalog candidates")
    elif availability in {
        FollowUpAvailability.ANALYST_SCREENED_CANDIDATE.value,
        FollowUpAvailability.RETRIEVED_QUALITY_LIMITED.value,
    }:
        _validate_followup_screen(follow_up, artifacts)
    else:
        raise InvestigationDraftError("draft next-observation availability state is unsupported")
    try:
        validate_investigation_contract(record)
    except (TypeError, ValueError) as exc:
        raise InvestigationDraftError(f"investigation draft contract failed: {exc}") from exc
    return record


def _validate_followup_screen(
    follow_up: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> None:
    screening = follow_up.get("screening_review")
    if not isinstance(screening, dict) or set(screening) != _FOLLOWUP_SCREEN_FIELDS:
        raise InvestigationDraftError("next-observation screening record is missing or malformed")
    if (
        screening.get("method") != "ANALYST_DECLARED_FOLLOWUP_GATE_SCREEN"
        or screening.get("reviewer") != "LOCAL_USER_UNAUTHENTICATED"
        or not isinstance(screening.get("source_evidence_id"), str)
        or screening.get("source_sha256") != next(
            (item.get("sha256") for item in artifacts if item.get("evidence_id") == screening.get("source_evidence_id")),
            None,
        )
        or screening.get("source_evidence_id") not in follow_up.get("evidence_refs", [])
        or follow_up.get("evidence_refs") != [screening.get("source_evidence_id")]
    ):
        raise InvestigationDraftError("next-observation screening source identity is inconsistent")
    source_artifact = next(
        (item for item in artifacts if item.get("evidence_id") == screening.get("source_evidence_id")),
        None,
    )
    if not isinstance(source_artifact, dict) or source_artifact.get("ingest_method") not in {
        _USER_IMPORT_METHOD,
        _CASE_IMPORT_METHOD,
    }:
        raise InvestigationDraftError("next-observation screening must reference a staged source record")
    try:
        timestamp = datetime.fromisoformat(str(screening.get("screened_at_utc", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvestigationDraftError("next-observation screening timestamp is invalid") from exc
    if timestamp.tzinfo is None:
        raise InvestigationDraftError("next-observation screening timestamp must include a timezone")
    basis, limitations = screening.get("review_basis"), screening.get("limitations")
    if not isinstance(basis, str) or len(basis.strip()) < 12 or not isinstance(limitations, str) or len(limitations.strip()) < 12:
        raise InvestigationDraftError("next-observation screening requires substantive review basis and limitations")
    design = follow_up.get("test_design")
    expected_gates = design.get("acceptance_gates") if isinstance(design, dict) else None
    results = screening.get("gate_results")
    if (
        not isinstance(expected_gates, list)
        or not isinstance(results, list)
        or len(results) != len(expected_gates)
        or any(not isinstance(item, dict) or set(item) != {"gate", "result"} for item in results)
        or [item.get("gate") for item in results] != expected_gates
        or any(item.get("result") not in _FOLLOWUP_GATE_RESULTS for item in results)
    ):
        raise InvestigationDraftError("next-observation screening results do not match the declared acceptance gates")
    all_met = all(item["result"] == "MET" for item in results)
    expected_state = (
        FollowUpAvailability.ANALYST_SCREENED_CANDIDATE.value
        if all_met else FollowUpAvailability.RETRIEVED_QUALITY_LIMITED.value
    )
    if follow_up.get("availability_state") != expected_state:
        raise InvestigationDraftError("next-observation availability conflicts with its recorded gate results")
    payload = {key: value for key, value in screening.items() if key != "sha256"}
    digest = hashlib.sha256(_canonical_json(payload)).hexdigest()
    if screening.get("sha256") != digest:
        raise InvestigationDraftError("next-observation screening checksum mismatch")


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
    catalog_screen = source_record.get("record_type") == "ECHO_FOLLOWUP_CATALOG_SCREEN"
    provider_qa_screen = source_record.get("record_type") == "ECHO_FOLLOWUP_PROVIDER_QA_SCREEN"
    if catalog_screen:
        _validate_followup_catalog_screen(source_record)
    if provider_qa_screen:
        _validate_followup_provider_qa_screen(source_record)
    attached_at_utc = attached_at_utc or datetime.now(timezone.utc)
    if attached_at_utc.tzinfo is None:
        raise InvestigationDraftError("source staging timestamp must include a timezone")
    source_status = source_record.get("status")
    artifact = {
        "evidence_id": evidence_id,
        "role": "CATALOG_AVAILABILITY_METADATA_ONLY" if catalog_screen else "FOLLOWUP_PROVIDER_QA_METADATA_ONLY" if provider_qa_screen else "USER_SUPPLIED_SOURCE_NOT_REVIEWED",
        "record_type": source_record["record_type"],
        "status": source_status if isinstance(source_status, str) and source_status else "SOURCE_STATUS_NOT_RECORDED",
        "sha256": source_sha256,
        "source_review_state": "CATALOG_STRUCTURE_VALIDATED_METADATA_ONLY" if catalog_screen else "PROVIDER_QA_LINKED_METADATA_ONLY" if provider_qa_screen else "NOT_REVIEWED",
        "independence_state": "NOT_ASSESSED",
        "ingest_method": _CATALOG_SCREEN_METHOD if catalog_screen else _FOLLOWUP_QA_METHOD if provider_qa_screen else _USER_IMPORT_METHOD,
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
        "method": _CATALOG_SCREEN_METHOD if catalog_screen else _FOLLOWUP_QA_METHOD if provider_qa_screen else _USER_IMPORT_METHOD,
        "source_review_state": "CATALOG_STRUCTURE_VALIDATED_METADATA_ONLY" if catalog_screen else "PROVIDER_QA_LINKED_METADATA_ONLY" if provider_qa_screen else "NOT_REVIEWED",
        "independence_state": "NOT_ASSESSED",
        "sha256": source_sha256,
    })
    updated["interpretation_limits"] = list(updated.get("interpretation_limits", []))
    updated["interpretation_limits"].append(
        "A catalog availability screen records NISAR GCOV metadata only; product pixels, QA suitability, and hypothesis relevance were not retrieved or validated."
        if catalog_screen else
        "An ASF provider-QA summary is metadata only. It applies to one cataloged product and does not establish spatial or temporal suitability, independence, or any physical hypothesis."
        if provider_qa_screen else
        "A user-supplied source record is staged but has not been reviewed, linked to a hypothesis, or assessed for independence."
    )
    validate_investigation_draft(updated)
    return updated


def attach_followup_catalog_screen(
    draft: dict[str, Any],
    catalog_record: dict[str, Any],
    *,
    attached_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Retain an ASF NISAR GCOV metadata search against the draft's one test."""
    validate_investigation_draft(draft)
    if draft.get("status") != _DRAFT_UNASSESSED:
        raise InvestigationDraftError("catalog searches can only be attached to an unassessed draft")
    followups = draft.get("follow_up_evidence")
    if not isinstance(followups, list) or len(followups) != 1:
        raise InvestigationDraftError("draft must contain one pre-registered follow-up test")
    followup = followups[0]
    design = followup.get("test_design") if isinstance(followup, dict) else None
    if (
        not isinstance(design, dict)
        or followup.get("purpose") != "DISCRIMINATING_OBSERVATION"
        or followup.get("availability_state") not in {
            FollowUpAvailability.NOT_SEARCHED.value,
            FollowUpAvailability.SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE.value,
            FollowUpAvailability.CANDIDATE_RETRIEVED_UNASSESSED.value,
        }
    ):
        raise InvestigationDraftError("draft follow-up is not an open evidence search")
    if not isinstance(catalog_record, dict):
        raise InvestigationDraftError("ASF GCOV catalog response must be an object")
    source = catalog_record.get("source")
    query = catalog_record.get("query")
    if (
        not isinstance(source, dict)
        or source.get("provider") != "Alaska Satellite Facility DAAC"
        or source.get("catalog_only") is not True
        or source.get("pixels_downloaded") is not False
        or not isinstance(query, dict)
        or query.get("dataset") != "NISAR"
        or query.get("processing_level") != "GCOV"
    ):
        raise InvestigationDraftError("catalog response is not a metadata-only ASF NISAR GCOV search")
    attached_at_utc = attached_at_utc or datetime.now(timezone.utc)
    if attached_at_utc.tzinfo is None:
        raise InvestigationDraftError("catalog attachment timestamp must include a timezone")
    wrapped = {
        "record_type": "ECHO_FOLLOWUP_CATALOG_SCREEN",
        "schema_version": 1,
        "status": "CATALOG_METADATA_ONLY",
        "created_at_utc": attached_at_utc.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "follow_up_link": {
            "follow_up_id": followup["follow_up_id"],
            "target_hypothesis_id": design["hypothesis_under_test_id"],
            "test_design_sha256": hashlib.sha256(_canonical_json(design)).hexdigest(),
        },
        "catalog_record_sha256": hashlib.sha256(_canonical_json(catalog_record)).hexdigest(),
        "search_result": {
            "state": "MATCHES_FOUND" if catalog_record.get("feature_count") else "NO_MATCHES",
            "returned_feature_count": catalog_record.get("feature_count"),
            "potentially_truncated": source.get("potentially_truncated"),
        },
        "test_compatibility_state": "NOT_ASSESSED_METADATA_ONLY",
        "catalog_record": deepcopy(catalog_record),
        "interpretation_limit": "Catalog metadata indicate availability only. No radar pixels, provider QA, grid compatibility, scientific suitability, test fit, or source independence were assessed.",
    }
    _validate_followup_catalog_screen(wrapped)
    updated = attach_unreviewed_source(draft, wrapped, attached_at_utc=attached_at_utc)
    updated_followup = updated["follow_up_evidence"][0]
    linked_catalog_records = [
        updated["source_records"].get(item["evidence_id"], {}).get("catalog_record", {})
        for item in updated["evidence_artifacts"]
        if item.get("ingest_method") == _CATALOG_SCREEN_METHOD
    ]
    updated_followup["availability_state"] = (
        FollowUpAvailability.CANDIDATE_RETRIEVED_UNASSESSED.value
        if any(isinstance(item, dict) and item.get("feature_count", 0) > 0 for item in linked_catalog_records)
        else FollowUpAvailability.SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE.value
    )
    updated_followup["action_track"] = "NEW_EVIDENCE_SEARCH"
    updated_followup["evidence_refs"] = list(dict.fromkeys([
        *updated_followup.get("evidence_refs", []),
        updated["evidence_artifacts"][-1]["evidence_id"],
    ]))
    validate_investigation_draft(updated)
    return updated


def followup_catalog_candidate(
    draft: dict[str, Any],
    *,
    catalog_availability_evidence_id: str,
    scene_id: str,
) -> dict[str, Any]:
    """Return a scene feature only when it belongs to an open draft follow-up search."""
    validate_investigation_draft(draft)
    if draft.get("status") != _DRAFT_UNASSESSED:
        raise InvestigationDraftError("provider QA can only be attached to an unassessed draft")
    artifact = next((item for item in draft["evidence_artifacts"] if item["evidence_id"] == catalog_availability_evidence_id), None)
    catalog_screen = draft["source_records"].get(catalog_availability_evidence_id)
    if (
        artifact is None
        or artifact.get("ingest_method") != _CATALOG_SCREEN_METHOD
        or not isinstance(catalog_screen, dict)
    ):
        raise InvestigationDraftError("provider QA must link to a retained catalog availability screen")
    followup = draft["follow_up_evidence"][0]
    if followup.get("purpose") != "DISCRIMINATING_OBSERVATION" or followup.get("availability_state") not in {
        FollowUpAvailability.NOT_SEARCHED.value,
        FollowUpAvailability.SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE.value,
        FollowUpAvailability.CANDIDATE_RETRIEVED_UNASSESSED.value,
    }:
        raise InvestigationDraftError("provider QA follow-up is not an open discriminating test")
    retained_catalog = catalog_screen.get("catalog_record")
    retained_features = retained_catalog.get("features") if isinstance(retained_catalog, dict) else None
    feature = next((
        item for item in retained_features or []
        if isinstance(item, dict)
        and isinstance(item.get("properties"), dict)
        and item["properties"].get("fileID") == scene_id
    ), None)
    if not isinstance(feature, dict):
        raise InvestigationDraftError("provider QA candidate does not match a scene in the linked catalog screen")
    return deepcopy(feature)


def attach_followup_provider_qa_screen(
    draft: dict[str, Any],
    *,
    catalog_availability_evidence_id: str,
    provider_qa_record: dict[str, Any],
    retrieval_verified_at_attachment: bool = False,
    attached_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Attach fetched ASF provider QA to a scene in an open follow-up catalog search."""
    validate_investigation_draft(draft)
    catalog_screen = draft["source_records"].get(catalog_availability_evidence_id)
    if not isinstance(provider_qa_record, dict) or provider_qa_record.get("record_type") != "ECHO_PROVIDER_QA_INSPECTION":
        raise InvestigationDraftError("provider QA inspection record is unsupported")
    source_catalog = provider_qa_record.get("source_catalog")
    feature = source_catalog.get("feature") if isinstance(source_catalog, dict) else None
    properties = feature.get("properties") if isinstance(feature, dict) else None
    scene_id = properties.get("fileID") if isinstance(properties, dict) else None
    if not isinstance(scene_id, str) or followup_catalog_candidate(
        draft,
        catalog_availability_evidence_id=catalog_availability_evidence_id,
        scene_id=scene_id,
    ) != feature:
        raise InvestigationDraftError("provider QA candidate does not match a scene in the linked catalog screen")
    qa_summary = provider_qa_record.get("provider_qa_summary")
    if not isinstance(qa_summary, dict) or qa_summary.get("scene_id") != scene_id:
        raise InvestigationDraftError("provider QA summary is for a different catalog scene")
    attached_at_utc = attached_at_utc or datetime.now(timezone.utc)
    if attached_at_utc.tzinfo is None:
        raise InvestigationDraftError("provider QA attachment timestamp must include a timezone")
    if not isinstance(retrieval_verified_at_attachment, bool):
        raise InvestigationDraftError("provider QA retrieval verification state must be boolean")
    verification = _QA_RETRIEVED_AT_ATTACHMENT if retrieval_verified_at_attachment else _QA_SNAPSHOT_NOT_REVERIFIED
    provenance_limit = (
        "ECHO retrieved and checksummed the canonical ASF QA CSV during attachment over its validated Earthdata HTTPS path; this verifies retrieval and retained bytes, not product suitability or the provider's interpretation."
        if retrieval_verified_at_attachment else
        "The supplied provider-QA snapshot is checksummed, but its retrieval provenance was not reverified during draft attachment."
    )
    wrapped = {
        "record_type": "ECHO_FOLLOWUP_PROVIDER_QA_SCREEN",
        "schema_version": 1,
        "status": "PROVIDER_QA_METADATA_ONLY",
        "created_at_utc": attached_at_utc.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "follow_up_link": deepcopy(catalog_screen["follow_up_link"]),
        "catalog_availability_evidence_id": catalog_availability_evidence_id,
        "catalog_record_sha256": catalog_screen["catalog_record_sha256"],
        "scene_id": scene_id,
        "provider_qa_record_sha256": hashlib.sha256(_canonical_json(provider_qa_record)).hexdigest(),
        "test_compatibility_state": "NOT_ASSESSED_METADATA_ONLY",
        "provider_response_verification": verification,
        "provider_qa_record": deepcopy(provider_qa_record),
        "interpretation_limit": f"Provider QA applies only to this product. {provenance_limit} It does not establish test fit, source independence, AOI coverage, temporal suitability, or a physical change; no radar pixel arrays were read by this QA request.",
    }
    _validate_followup_provider_qa_screen(wrapped)
    updated = attach_unreviewed_source(draft, wrapped, attached_at_utc=attached_at_utc)
    followup = updated["follow_up_evidence"][0]
    followup["evidence_refs"] = list(dict.fromkeys([
        *followup.get("evidence_refs", []),
        updated["evidence_artifacts"][-1]["evidence_id"],
    ]))
    validate_investigation_draft(updated)
    return updated


def attach_validated_case_source(
    draft: dict[str, Any],
    source_record: dict[str, Any],
    *,
    source_record_json: str,
    case_provenance: dict[str, Any],
    source_role: str,
    imported_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Embed a case-linked record whose manifest and artifact were verified by ECHO."""
    validate_investigation_draft(draft)
    if draft["status"] != _DRAFT_UNASSESSED:
        raise InvestigationDraftError("case evidence cannot be imported after analyst assessment")
    if not isinstance(source_record, dict) or not isinstance(source_role, str) or not source_role:
        raise InvestigationDraftError("validated case source identity is incomplete")
    if (
        not isinstance(case_provenance, dict)
        or set(case_provenance) != _CASE_PROVENANCE_FIELDS - {"source_content_sha256", "imported_at_utc"}
    ):
        raise InvestigationDraftError("validated case source provenance fields are invalid")
    if not isinstance(source_record_json, str):
        raise InvestigationDraftError("validated case source must retain its exact JSON record text")
    try:
        parsed_text_record = json.loads(source_record_json)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise InvestigationDraftError("validated case source JSON text is invalid") from exc
    if parsed_text_record != source_record:
        raise InvestigationDraftError("validated case source text does not reproduce its parsed record")
    source_digest = hashlib.sha256(source_record_json.encode("utf-8")).hexdigest()
    if not _is_sha256(case_provenance.get("source_sha256")) or source_digest != case_provenance["source_sha256"]:
        raise InvestigationDraftError("validated case source file checksum does not match its retained text")
    imported_at_utc = imported_at_utc or datetime.now(timezone.utc)
    if imported_at_utc.tzinfo is None:
        raise InvestigationDraftError("case evidence import timestamp must include a timezone")
    provenance = {
        **case_provenance,
        "source_content_sha256": source_digest,
        "imported_at_utc": imported_at_utc.astimezone(timezone.utc).isoformat(),
    }
    evidence_id = f"CASE-SOURCE-{source_digest[:16].upper()}"
    if evidence_id in draft["source_records"] or any(
        artifact.get("sha256") == source_digest for artifact in draft["evidence_artifacts"]
    ):
        raise InvestigationDraftError("this case source record is already present in the draft")
    if len(draft["evidence_artifacts"]) >= 13:
        raise InvestigationDraftError("a draft can contain at most twelve additional source records")
    source_status = source_record.get("status")
    artifact = {
        "evidence_id": evidence_id,
        "role": source_role,
        "record_type": source_record.get("record_type"),
        "status": source_status if isinstance(source_status, str) and source_status else "SOURCE_STATUS_NOT_RECORDED",
        "sha256": source_digest,
        "source_review_state": "CASE_RECORD_INTEGRITY_VALIDATED",
        "independence_state": "NOT_ASSESSED",
        "ingest_method": _CASE_IMPORT_METHOD,
        "case_provenance": provenance,
        "lineage": {
            "derived_from_evidence_ids": [],
            "shares_source_observations_with": [],
        },
    }
    updated = deepcopy(draft)
    updated["evidence_artifacts"].append(artifact)
    updated["source_records"][evidence_id] = source_record_json
    updated.setdefault("source_staging_history", []).append({
        "evidence_id": evidence_id,
        "attached_at_utc": provenance["imported_at_utc"],
        "method": _CASE_IMPORT_METHOD,
        "independence_state": "NOT_ASSESSED",
        "sha256": source_digest,
        "case_provenance": provenance,
    })
    updated["interpretation_limits"] = list(updated.get("interpretation_limits", [])) + [
        "This source was imported from an ECHO case after linked assessment, contract, path, and checksum validation; those checks do not validate provider authenticity, scientific suitability, or independence."
    ]
    validate_investigation_draft(updated)
    return updated


def screen_followup_source(
    draft: dict[str, Any],
    *,
    evidence_id: str,
    gate_results: list[dict[str, str]],
    review_basis: str,
    limitations: str,
    screened_at_utc: datetime | None = None,
) -> dict[str, Any]:
    """Record an analyst-declared screen of a staged source against the planned test gates."""
    validate_investigation_draft(draft)
    if draft["status"] != _DRAFT_UNASSESSED:
        raise InvestigationDraftError("follow-up evidence must be screened before the initial hypothesis assessment")
    follow_up = draft["follow_up_evidence"][0]
    if follow_up.get("availability_state") not in {
        FollowUpAvailability.NOT_SEARCHED.value,
        FollowUpAvailability.SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE.value,
        FollowUpAvailability.CANDIDATE_RETRIEVED_UNASSESSED.value,
    }:
        raise InvestigationDraftError("the planned next observation already has a screening result")
    if not isinstance(evidence_id, str) or not isinstance(gate_results, list):
        raise InvestigationDraftError("follow-up screening source and gate results are required")
    artifacts_by_id = {item["evidence_id"]: item for item in draft["evidence_artifacts"]}
    artifact = artifacts_by_id.get(evidence_id)
    if artifact is None or artifact.get("role") in {
        "SAR_PAIR_HELD_AT_PROVIDER_QA",
        "SAR_PAIR_HELD_AT_PRODUCT_MATURITY",
        "DESCRIPTIVE_NISAR_SAR_MEASUREMENT",
        "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT",
        "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_TEMPORAL_SERIES",
        "OPERA_PAIR_WITH_NO_COMMON_CLEAR_MEASUREMENT",
        "CATALOG_AVAILABILITY_METADATA_ONLY",
        "FOLLOWUP_PROVIDER_QA_METADATA_ONLY",
    }:
        raise InvestigationDraftError("follow-up screening must reference a staged non-primary source record")
    if not isinstance(review_basis, str) or len(review_basis.strip()) < 12:
        raise InvestigationDraftError("follow-up screening requires a substantive review basis")
    if not isinstance(limitations, str) or len(limitations.strip()) < 12:
        raise InvestigationDraftError("follow-up screening requires substantive limitations")
    design = follow_up.get("test_design")
    expected_gates = design.get("acceptance_gates") if isinstance(design, dict) else None
    if not isinstance(expected_gates, list) or len(gate_results) != len(expected_gates):
        raise InvestigationDraftError("provide one screening result for every pre-registered acceptance gate")
    normalized_results: list[dict[str, str]] = []
    for expected_gate, supplied in zip(expected_gates, gate_results, strict=True):
        if not isinstance(supplied, dict) or set(supplied) != {"gate", "result"} or supplied.get("gate") != expected_gate:
            raise InvestigationDraftError("screening gates must match the pre-registered gate list in order")
        result = supplied.get("result")
        if not isinstance(result, str) or result not in _FOLLOWUP_GATE_RESULTS:
            raise InvestigationDraftError("screening gate result must be MET, NOT_MET, or UNKNOWN")
        normalized_results.append({"gate": expected_gate, "result": result})
    screened_at_utc = screened_at_utc or datetime.now(timezone.utc)
    if screened_at_utc.tzinfo is None:
        raise InvestigationDraftError("follow-up screening timestamp must include a timezone")
    state = (
        FollowUpAvailability.ANALYST_SCREENED_CANDIDATE.value
        if all(item["result"] == "MET" for item in normalized_results)
        else FollowUpAvailability.RETRIEVED_QUALITY_LIMITED.value
    )
    screening = {
        "method": "ANALYST_DECLARED_FOLLOWUP_GATE_SCREEN",
        "reviewer": "LOCAL_USER_UNAUTHENTICATED",
        "screened_at_utc": screened_at_utc.astimezone(timezone.utc).isoformat(),
        "source_evidence_id": evidence_id,
        "source_sha256": artifact["sha256"],
        "gate_results": normalized_results,
        "review_basis": review_basis.strip(),
        "limitations": limitations.strip(),
    }
    screening["sha256"] = hashlib.sha256(_canonical_json(screening)).hexdigest()
    updated = deepcopy(draft)
    updated_follow_up = updated["follow_up_evidence"][0]
    updated_follow_up["availability_state"] = state
    updated_follow_up["action_track"] = "REVIEWED_RESULT"
    updated_follow_up["evidence_refs"] = [evidence_id]
    updated_follow_up["screening_review"] = screening
    updated.setdefault("interpretation_limits", []).append(
        "The next-observation gate screen is analyst-declared and unverified. It does not authenticate the source, establish independence, or create a hypothesis finding."
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
