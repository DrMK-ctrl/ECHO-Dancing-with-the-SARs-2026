"""Deterministic, source-linked challenge views for retained investigations."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import fmean, median
from typing import Any


_SENSITIVITY_TERMS = ("SENSITIVITY", "SPATIAL-SUPPORT", "MASK-SUPPORT")


def build_adversarial_challenge(
    assessment: dict[str, Any], *, hypothesis_id: str, assessment_sha256: str,
    evidence_root: Path,
) -> dict[str, Any]:
    """Assemble a review dossier from an already validated assessment.

    This function reorganizes retained evidence and declared relationships,
    and independently reproduces the linked pair's mean and median from its
    checksummed values and masks. It does not verify analyst interpretations
    or revise the assessment.
    """
    hypotheses = assessment.get("hypotheses")
    artifacts = assessment.get("evidence_artifacts")
    follow_ups = assessment.get("follow_up_evidence", [])
    if not isinstance(hypotheses, list) or not isinstance(artifacts, list):
        raise ValueError("assessment hypotheses and evidence artifacts are required")
    selected = [item for item in hypotheses if isinstance(item, dict) and item.get("id") == hypothesis_id]
    if len(selected) != 1:
        raise ValueError("hypothesis must identify exactly one assessment explanation")
    hypothesis = selected[0]
    by_id = {
        artifact["evidence_id"]: artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and isinstance(artifact.get("evidence_id"), str)
    }
    evidence_refs = hypothesis.get("evidence_refs", [])
    relations = hypothesis.get("evidence_assessments", [])
    if not isinstance(evidence_refs, list) or not isinstance(relations, list):
        raise ValueError("hypothesis evidence references are invalid")
    relation_ids = [item.get("evidence_id") for item in relations if isinstance(item, dict)]
    if len(relation_ids) != len(relations) or len(relation_ids) != len(set(relation_ids)):
        raise ValueError("hypothesis evidence relationships are invalid or duplicated")
    if set(evidence_refs) - set(by_id):
        raise ValueError("hypothesis references missing evidence artifacts")

    reviewed_evidence = []
    for relation in relations:
        artifact = by_id.get(relation["evidence_id"])
        if artifact is None or relation["evidence_id"] not in evidence_refs:
            raise ValueError("hypothesis relationship is not linked to a cited source")
        reviewed_evidence.append({
            "evidence_id": relation["evidence_id"],
            "relationship": relation.get("relationship", "UNASSESSED"),
            "rationale": relation.get("rationale", ""),
            "relationship_basis": "RECORDED_ANALYST_ASSESSMENT",
            "role": artifact.get("role", "ROLE_NOT_RECORDED"),
            "source_status": artifact.get("status", "STATUS_NOT_RECORDED"),
            "record_type": artifact.get("record_type", "RECORD_TYPE_NOT_RECORDED"),
            "sha256": artifact.get("sha256"),
            "lineage": artifact.get("lineage", {}),
        })

    observations = assessment.get("observations", {})
    sar = observations.get("sar_diagnostic_measurement", {}) if isinstance(observations, dict) else {}
    scene_ids = sar.get("scene_ids") if isinstance(sar, dict) else None
    if scene_ids is not None and (
        not isinstance(scene_ids, list)
        or len(scene_ids) != 2
        or any(not isinstance(scene_id, str) or not scene_id for scene_id in scene_ids)
        or scene_ids[0] == scene_ids[1]
    ):
        raise ValueError("SAR comparison must identify two distinct acquisition records")
    pair_artifact = by_id.get("SAR-RTC-S1-PAIR")
    measurement_reproduction: dict[str, Any] | None = None
    pair_record: dict[str, Any] | None = None
    pair_record_sha256: str | None = None
    if sar and pair_artifact is None:
        raise ValueError("SAR measurement has no linked comparison source")
    if sar and pair_artifact is not None:
        relative_path = pair_artifact.get("relative_path")
        if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
            raise ValueError("linked SAR comparison source path is invalid")
        root = evidence_root.resolve()
        pair_path = (root / relative_path).resolve()
        if not pair_path.is_relative_to(root):
            raise ValueError("linked SAR comparison source escapes the project root")
        try:
            pair_bytes = pair_path.read_bytes()
            pair_record = json.loads(pair_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("linked SAR comparison source cannot be read") from exc
        pair_record_sha256 = sha256(pair_bytes).hexdigest()
        if pair_record_sha256 != pair_artifact.get("sha256"):
            raise ValueError("linked SAR comparison source checksum does not match")
        if not isinstance(pair_record, dict):
            raise ValueError("linked SAR comparison source is not a JSON object")
        source_products = pair_record.get("source_products", {})
        if not isinstance(source_products, dict) or any(
            not isinstance(source_products.get(role), dict) for role in ("before", "after")
        ):
            raise ValueError("linked SAR comparison source product metadata is invalid")
        source_scene_ids = [
            source_products.get(role, {}).get("scene_id")
            for role in ("before", "after")
        ]
        if (
            pair_record.get("record_type") != pair_artifact.get("record_type")
            or pair_record.get("status") != pair_artifact.get("status")
            or source_scene_ids != scene_ids
        ):
            raise ValueError("SAR comparison identity does not match its linked measurement record")
        pair_measurement = pair_record.get("measurement", {})
        if not isinstance(pair_measurement, dict):
            raise ValueError("linked SAR comparison has no measurement record")
        before_source = source_products.get("before", {})
        after_source = source_products.get("after", {})
        if (
            pair_measurement.get("quantity") != sar.get("quantity")
            or pair_measurement.get("units") != sar.get("units")
            or pair_measurement.get("polarization") != sar.get("polarization")
            or before_source.get("acquisition_start_utc") != sar.get("acquisition_before_utc")
            or after_source.get("acquisition_start_utc") != sar.get("acquisition_after_utc")
            or pair_measurement.get("aoi_pixel_count") != sar.get("aoi_pixel_count")
            or pair_measurement.get("common_clear_pixel_count") != sar.get("common_clear_pixel_count")
        ):
            raise ValueError("SAR measurement metadata or support does not match the linked comparison")
        values = pair_measurement.get("values_db")
        valid_mask = pair_measurement.get("valid_mask")
        common_clear_mask = pair_measurement.get("common_clear_mask")
        if (
            not isinstance(values, list) or not values
            or not isinstance(valid_mask, list) or len(valid_mask) != len(values)
            or not isinstance(common_clear_mask, list) or len(common_clear_mask) != len(values)
        ):
            raise ValueError("linked SAR comparison values and masks are incompatible")
        samples: list[float] = []
        clear_count = 0
        for value_row, valid_row, clear_row in zip(values, valid_mask, common_clear_mask, strict=True):
            if (
                not isinstance(value_row, list) or not isinstance(valid_row, list)
                or not isinstance(clear_row, list)
                or len(value_row) != len(valid_row) or len(value_row) != len(clear_row)
            ):
                raise ValueError("linked SAR comparison rows have incompatible shapes")
            for value, is_valid, is_clear in zip(value_row, valid_row, clear_row, strict=True):
                if is_clear is True:
                    clear_count += 1
                if is_valid is True:
                    if is_clear is not True or not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise ValueError("SAR comparison validity mask admits an invalid or non-clear value")
                    samples.append(float(value))
        if clear_count != sar.get("common_clear_pixel_count") or not samples:
            raise ValueError("SAR comparison common support does not reproduce")
        reproduced_mean = fmean(samples)
        reproduced_median = median(samples)
        for key, reproduced in (("mean_db", reproduced_mean), ("median_db", reproduced_median)):
            observed = sar.get(key)
            if not isinstance(observed, (int, float)) or not math.isclose(
                float(observed), reproduced, rel_tol=1e-10, abs_tol=1e-10
            ):
                raise ValueError(f"SAR {key} does not reproduce from the checksummed measurement")
        measurement_reproduction = {
            "status": "LINKED_MEAN_MEDIAN_AND_MASK_REPRODUCED",
            "valid_sample_count": len(samples),
            "common_clear_pixel_count": clear_count,
            "mean_db": reproduced_mean,
            "median_db": reproduced_median,
            "method": "Mean and median recomputed from the checksummed pair values_db under its recorded valid_mask and common_clear_mask.",
        }
    provider_qa = sar.get("provider_qa_state") if isinstance(sar, dict) else None
    if provider_qa == "PASS":
        qa_gate = "PROVIDER_QA_PASS_RECORDED"
    elif provider_qa == "FAIL" or (isinstance(provider_qa, str) and "HELD" in provider_qa):
        qa_gate = "PROVIDER_QA_HELD"
    else:
        qa_gate = "PROVIDER_QA_UNRESOLVED"

    sensitivity_sources = [
        {
            "evidence_id": evidence_id,
            "role": by_id[evidence_id].get("role", "ROLE_NOT_RECORDED"),
            "source_status": by_id[evidence_id].get("status", "STATUS_NOT_RECORDED"),
            "record_type": by_id[evidence_id].get("record_type", "RECORD_TYPE_NOT_RECORDED"),
            "sha256": by_id[evidence_id].get("sha256"),
        }
        for evidence_id in evidence_refs
        if any(term in evidence_id.upper() for term in _SENSITIVITY_TERMS)
    ]
    if not sensitivity_sources:
        sensitivity_state = "NO_LINKED_SENSITIVITY_RECORD"
    else:
        sensitivity_state = "LINKED_VARIANT_RECORDS_NO_AGGREGATE_STABILITY_VERDICT"

    comparability_review: dict[str, Any] | None = None
    comparability_artifact = by_id.get("NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW")
    if comparability_artifact is not None:
        relative_path = comparability_artifact.get("relative_path")
        if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
            raise ValueError("linked acquisition-condition review path is invalid")
        root = evidence_root.resolve()
        review_path = (root / relative_path).resolve()
        if not review_path.is_relative_to(root):
            raise ValueError("linked acquisition-condition review path escapes the project root")
        try:
            review_bytes = review_path.read_bytes()
            review_record = json.loads(review_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("linked acquisition-condition review cannot be read") from exc
        review_sha256 = sha256(review_bytes).hexdigest()
        if review_sha256 != comparability_artifact.get("sha256"):
            raise ValueError("linked acquisition-condition review checksum does not match")
        if not isinstance(review_record, dict):
            raise ValueError("linked acquisition-condition review is not a JSON object")
        if pair_record is None or pair_record_sha256 is None:
            raise ValueError("acquisition-condition review has no checksummed SAR pair")
        from .opera_rtc_conditions import validate_acquisition_condition_review

        try:
            validate_acquisition_condition_review(
                review_record,
                pair_record=pair_record,
                pair_record_sha256=pair_record_sha256,
                case_id=assessment.get("case_id"),
            )
        except ValueError as exc:
            raise ValueError("linked acquisition-condition review does not reproduce") from exc
        comparability_review = {
            "state": review_record["status"],
            "evidence_id": comparability_artifact["evidence_id"],
            "source_status": comparability_artifact.get("status"),
            "sha256": review_sha256,
            "scope": (
                "LINKED_TO_SELECTED_HYPOTHESIS"
                if comparability_artifact["evidence_id"] in evidence_refs
                else "CASE_WIDE_NOT_LINKED_TO_SELECTED_HYPOTHESIS"
            ),
            "summary": review_record["summary"],
            "comparisons": review_record["comparisons"],
            "interpretation": review_record["interpretation"],
            "limitations": review_record["limitations"],
        }

    alternatives = [
        {
            "hypothesis_id": item.get("id"),
            "statement": item.get("statement"),
            "recorded_state": item.get("state"),
            "testability_state": item.get("testability_state"),
            "would_weaken_if": item.get("would_weaken_if"),
            "required_evidence": item.get("required_evidence", []),
        }
        for item in hypotheses
        if isinstance(item, dict) and item.get("id") != hypothesis_id
    ]
    relevant_follow_ups = [
        {
            "follow_up_id": item.get("follow_up_id"),
            "purpose": item.get("purpose"),
            "availability_state": item.get("availability_state"),
            "action": item.get("action"),
            "discriminating_question": item.get("discriminating_question"),
            "test_design": item.get("test_design"),
            "evidence_refs": item.get("evidence_refs", []),
        }
        for item in follow_ups
        if isinstance(item, dict) and hypothesis_id in item.get("target_hypothesis_ids", [])
    ] if isinstance(follow_ups, list) else []

    return {
        "record_type": "ECHO_ADVERSARIAL_EVIDENCE_CHALLENGE",
        "schema_version": 1,
        "status": "REVIEWABLE_WITH_RECORDED_LIMITS",
        "case_id": assessment.get("case_id"),
        "assessment_sha256": assessment_sha256,
        "assessment_status": assessment.get("status"),
        "hypothesis": {
            "hypothesis_id": hypothesis_id,
            "statement": hypothesis.get("statement"),
            "recorded_state": hypothesis.get("state"),
            "testability_state": hypothesis.get("testability_state"),
            "scope_limit": hypothesis.get("scope_limit"),
            "expected_observation": hypothesis.get("expected_observation"),
            "would_weaken_if": hypothesis.get("would_weaken_if"),
            "testability_reason": hypothesis.get("testability_reason"),
            "required_evidence": hypothesis.get("required_evidence", []),
        },
        "observation": {
            "measurement_recorded": bool(sar),
            "measurement": {
                key: sar[key]
                for key in (
                    "scene_ids", "acquisition_before_utc", "acquisition_after_utc",
                    "sensor", "polarization", "quantity", "equation", "units", "grid_crs",
                    "mean_db", "median_db", "common_clear_pixel_count", "aoi_pixel_count",
                    "common_clear_fraction", "analysis_disposition",
                )
                if isinstance(sar, dict) and key in sar
            },
            "measurement_evidence_id": next((
                artifact.get("evidence_id") for artifact in artifacts
                if isinstance(artifact, dict) and artifact.get("role") == "DIAGNOSTIC_SAR_MEASUREMENT"
            ), None),
            "measurement_reproduction": measurement_reproduction,
            "provider_qa_state": provider_qa or "NOT_RECORDED",
            "qa_gate": qa_gate,
            "interpretation_limit": (
                "A recorded radar-response difference does not identify its physical cause. "
                "Diagnostic or unresolved QA does not permit a validated change claim."
            ),
        },
        "evidence_review": {
            "recorded_relationships": reviewed_evidence,
            "unassessed_referenced_evidence_ids": sorted(set(evidence_refs) - set(relation_ids)),
            "relationship_limit": (
                "Relationships are retained analyst assessments. They are not independently "
                "verified by assembling this challenge view."
            ),
        },
        "sensitivity_review": {
            "state": sensitivity_state,
            "linked_sources": sensitivity_sources,
            "interpretation_limit": (
                "Only source-linked variants already present in the assessment are listed. "
                "ECHO does not combine unlike metrics into a stability score or infer a probability."
            ),
        },
        "comparability_review": comparability_review,
        "alternatives": alternatives,
        "next_observations": relevant_follow_ups,
        "reproducibility": {
            "assessment_sha256": assessment_sha256,
            "source_artifacts": [
                {key: source.get(key) for key in ("evidence_id", "sha256", "record_type", "status")}
                for source in reviewed_evidence
            ],
        },
        "interpretation_limit": (
            "This is a deterministic challenge view of one retained assessment, not a new scientific "
            "analysis. It does not alter evidence relationships, QA, measurements, or findings."
        ),
    }


def build_qa_held_observation_challenge(
    case_review: dict[str, Any], *, review_sha256: str,
    preview_record: dict[str, Any], preview_sha256: str,
) -> dict[str, Any]:
    """Return a fail-closed challenge record when a case has no finding to test."""
    candidate = case_review.get("candidate_pair")
    preview = case_review.get("diagnostic_single_observation_preview")
    products = case_review.get("products")
    if (
        not isinstance(candidate, dict) or not isinstance(preview, dict)
        or not isinstance(products, list) or not isinstance(preview_record, dict)
    ):
        raise ValueError("case review does not contain a challengeable observation record")
    preview_source = preview_record.get("source")
    if (
        preview_record.get("record_type") != preview.get("record_type")
        or preview_record.get("scientific_disposition") != preview.get("scientific_disposition")
        or not isinstance(preview_source, dict)
        or preview_source.get("scene_id") != preview.get("scene_id")
        or preview_source.get("provider_qa_status") not in {"FAIL", "QA_FAIL"}
    ):
        raise ValueError("diagnostic preview source does not match the case review and provider QA hold")
    product_records = []
    for product in products:
        if not isinstance(product, dict) or not isinstance(product.get("qa_summary"), dict):
            raise ValueError("case review product QA record is missing")
        qa = product["qa_summary"]
        product_records.append({
            "scene_id": product.get("scene_id"),
            "acquisition_time_utc": product.get("acquisition_time_utc"),
            "provider_qa_state": qa.get("identification_group", "NOT_RECORDED"),
            "qa_summary_sha256": qa.get("artifact_sha256"),
        })
    failures = [item for item in product_records if item["provider_qa_state"] == "FAIL"]
    preview_product = next((item for item in product_records if item["scene_id"] == preview.get("scene_id")), None)
    if preview_product is None or preview_product["provider_qa_state"] != preview_source.get("provider_qa_status"):
        raise ValueError("diagnostic preview QA does not match its case product record")
    qa_held = candidate.get("qa_status") == "QA_HOLD" or bool(failures)
    return {
        "record_type": "ECHO_ADVERSARIAL_EVIDENCE_CHALLENGE",
        "schema_version": 1,
        "status": "QA_HELD_NO_CHANGE_FINDING" if qa_held else "NO_INVESTIGATION_ASSESSMENT",
        "case_id": case_review.get("case_id"),
        "case_review_sha256": review_sha256,
        "finding": None,
        "observation": {
            "record_type": preview.get("record_type"),
            "scientific_disposition": preview.get("scientific_disposition"),
            "scene_id": preview.get("scene_id"),
            "acquired_at_utc": preview.get("acquired_at_utc"),
            "measurement": preview.get("measurement"),
            "units": preview.get("units"),
            "selected_pixel_center_count": preview.get("selected_pixel_center_count"),
            "source_record_sha256": preview.get("record_sha256"),
            "verified_record_sha256": preview_sha256,
        },
        "candidate_pair": {
            "status": candidate.get("status"),
            "qa_status": candidate.get("qa_status"),
            "interval_days": candidate.get("interval_days"),
            "products": product_records,
        },
        "challenge_result": {
            "change_conclusion": None,
            "change_computation_permitted": False,
            "reason": (
                "No change finding exists to challenge: the available single-scene preview is diagnostic, "
                "and provider QA FAIL on one or more candidate-pair products holds temporal analysis."
                if qa_held else "No retained investigation assessment or change finding is available."
            ),
            "next_step": (
                "Use provider-cleared or corrected products, then repeat compatibility and QA checks before "
                "computing any temporal measurement."
                if qa_held else "Create and assess a source-linked investigation before challenging an interpretation."
            ),
        },
        "interpretation_limit": (
            "A diagnostic single-observation preview is not a temporal change measurement, physical explanation, "
            "event boundary, or validation result."
        ),
    }
