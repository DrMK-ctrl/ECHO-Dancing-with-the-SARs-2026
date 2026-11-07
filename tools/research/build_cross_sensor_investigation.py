#!/usr/bin/env python3
"""Build an evidence-linked, fail-closed assessment from retained ECHO records."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np

from echo.investigation import (
    EvidenceAssessment,
    EvidenceRelation,
    evaluate_hypothesis,
    validate_follow_up_plan,
    validate_hypotheses,
)


class AssessmentError(ValueError):
    """Raised when source records cannot support this assessment."""


def _read_json(path: Path, record_type: str) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssessmentError(f"cannot read source record: {path}") from exc
    if not isinstance(record, dict) or record.get("record_type") != record_type:
        raise AssessmentError(f"unexpected record type in {path}")
    return record


def _artifact(path: Path, record: dict[str, Any], evidence_id: str, role: str) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "role": role,
        "record_type": record["record_type"],
        "status": record.get("status"),
        "relative_path": str(path),
        "sha256": sha256(path.read_bytes()).hexdigest(),
    }


def build_assessment(
    pair_path: Path,
    optical_path: Path,
    nearer_optical_path: Path | None = None,
    catalog_screen_path: Path | None = None,
    case_id: str = "rio-grande-do-sul-cross-sensor-diagnostic-2024",
    spatial_support_path: Path | None = None,
) -> dict[str, Any]:
    if nearer_optical_path is not None and catalog_screen_path is None:
        raise AssessmentError("the nearer optical record requires its CMR screen")
    pair = _read_json(pair_path, "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS")
    optical = _read_json(optical_path, "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON")
    nearer_optical = (
        _read_json(nearer_optical_path, "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON")
        if nearer_optical_path is not None
        else None
    )
    catalog_screen = (
        _read_json(catalog_screen_path, "ECHO_DSWX_HLS_TEMPORAL_CONTEXT_CATALOG_SCREEN")
        if catalog_screen_path is not None
        else None
    )
    spatial_support = (
        _read_json(spatial_support_path, "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC")
        if spatial_support_path is not None
        else None
    )
    if pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON":
        raise AssessmentError("the retained RTC-S1 record is not the expected diagnostic comparison")
    if optical.get("status") != "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION":
        raise AssessmentError("the DSWx-HLS record does not have its optical-context-only disposition")
    if spatial_support is not None:
        sources = spatial_support.get("sources", {})
        if spatial_support.get("status") != "DIAGNOSTIC_SPATIAL_ASSOCIATION":
            raise AssessmentError("the spatial-support record does not have its diagnostic disposition")
        if (
            sources.get("sar_pair_record_sha256") != sha256(pair_path.read_bytes()).hexdigest()
            or sources.get("optical_context_record_sha256") != sha256(optical_path.read_bytes()).hexdigest()
        ):
            raise AssessmentError("the spatial-support record was built from different source records")
        if (
            sources.get("sar_scene_ids") != [
                item.get("scene_id") for item in pair.get("source_products", {}).values()
            ]
            or sources.get("optical_granule_ids") != [
                optical.get("source_products", {}).get(role, {}).get("granule_id")
                for role in ("before", "after")
            ]
        ):
            raise AssessmentError("the spatial-support record identifies different source observations")
        sensitivity = spatial_support.get("summary", {}).get("coverage_sensitivity")
        if not isinstance(sensitivity, list) or not sensitivity:
            raise AssessmentError("the spatial-support record has no coverage-sensitivity summary")
        selected_summary = [
            item for item in sensitivity
            if isinstance(item, dict)
            and item.get("minimum_common_valid_wtr_area_fraction") == 0.75
        ]
        if len(selected_summary) != 1:
            raise AssessmentError("the spatial-support record must contain one 0.75 coverage summary")
        spatial_summary = selected_summary[0]
        numeric_fields = (
            "sar_cells",
            "water_fraction_increased_by_more_than_0_05",
            "water_fraction_decreased_by_more_than_0_05",
            "water_fraction_changed_by_at_most_0_05",
            "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db",
        )
        if any(
            isinstance(spatial_summary.get(field), bool)
            or not isinstance(spatial_summary.get(field), (int, float))
            or not np.isfinite(spatial_summary[field])
            for field in numeric_fields
        ):
            raise AssessmentError("the spatial-support summary has missing or non-finite metrics")
        if sum(spatial_summary[field] for field in numeric_fields[1:4]) != spatial_summary["sar_cells"]:
            raise AssessmentError("the spatial-support change counts do not match the selected cell count")

    pair_bounds = pair.get("grid", {}).get("window", {}).get("bounds_wgs84")
    optical_bounds = optical.get("aoi", {}).get("bounds_west_south_east_north")
    if not isinstance(pair_bounds, list) or pair_bounds != optical_bounds:
        raise AssessmentError("the RTC-S1 and DSWx-HLS records do not describe the same WGS84 AOI")
    if catalog_screen is not None:
        if catalog_screen.get("status") != "METADATA_ONLY_NO_PIXEL_QA":
            raise AssessmentError("the DSWx-HLS catalog screen has an unsupported disposition")
        if catalog_screen.get("bounds_wgs84") != pair_bounds:
            raise AssessmentError("the DSWx-HLS catalog screen does not describe the SAR AOI")
    if nearer_optical is not None:
        nearer_bounds = nearer_optical.get("aoi", {}).get("bounds_west_south_east_north")
        if nearer_optical.get("status") != "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION":
            raise AssessmentError("the nearer DSWx-HLS record is not labeled optical context only")
        if nearer_bounds != pair_bounds:
            raise AssessmentError("the follow-up records do not describe the same WGS84 AOI")

    measurement = pair.get("measurement", {})
    values = np.asarray(measurement.get("values_db"), dtype=np.float64)
    valid = np.asarray(measurement.get("valid_mask"), dtype=bool)
    common_clear = np.asarray(measurement.get("common_clear_mask"), dtype=bool)
    if values.shape != valid.shape or values.shape != common_clear.shape:
        raise AssessmentError("measurement values and validity masks have different shapes")
    valid &= common_clear & np.isfinite(values)
    samples = values[valid]
    measured_count = int(measurement.get("measured_pixel_count", -1))
    if samples.size == 0 or samples.size != measured_count:
        raise AssessmentError("valid diagnostic measurement count does not match the source record")
    if samples.size != int(measurement.get("common_clear_pixel_count", -1)):
        raise AssessmentError("common-clear count does not match the diagnostic measurement samples")

    before = pair.get("source_products", {}).get("before", {})
    after = pair.get("source_products", {}).get("after", {})
    if not before.get("scene_id") or not after.get("scene_id"):
        raise AssessmentError("RTC-S1 source scene identifiers are missing")
    transitions = optical.get("transitions", {})
    wtr = transitions.get("WTR", {})
    wtr2 = transitions.get("WTR-2", {})
    overlap = optical.get("wtr2_confidence_quality_overlap", {})
    if not wtr or not wtr2 or not overlap.get("before") or not overlap.get("after"):
        raise AssessmentError("optical water and confidence-context summaries are incomplete")

    evidence = [
        _artifact(pair_path, pair, "SAR-RTC-S1-PAIR", "DIAGNOSTIC_SAR_MEASUREMENT"),
        _artifact(optical_path, optical, "NASA-OPERA-DSWX-HLS", "OPTICAL_PRODUCT_CONTEXT"),
    ]
    screen_evidence_id = None
    if catalog_screen is not None:
        screen_evidence_id = (
            "NASA-CMR-DSWX-FOLLOWUP-SCREEN"
            if nearer_optical is not None
            else "NASA-CMR-DSWX-TEMPORAL-SCREEN"
        )
        evidence.append(_artifact(catalog_screen_path, catalog_screen, screen_evidence_id, "CATALOG_DISCOVERY_ONLY"))
    nearer_context = None
    if nearer_optical is not None and catalog_screen is not None:
        query_results = catalog_screen.get("query_results", [])
        nearest_by_reference = {
            item.get("reference_label"): item.get("nearest_candidate", {}).get("granule_id")
            for item in query_results
            if isinstance(item, dict) and isinstance(item.get("nearest_candidate"), dict)
        }
        nearer_before = nearer_optical.get("source_products", {}).get("before", {})
        nearer_after = nearer_optical.get("source_products", {}).get("after", {})
        if (
            nearer_before.get("granule_id") != nearest_by_reference.get("before")
            or nearer_after.get("granule_id") != nearest_by_reference.get("after")
        ):
            raise AssessmentError("the follow-up optical products do not match the nearest CMR candidates")
        nearer_transitions = nearer_optical.get("transitions", {})
        nearer_wtr = nearer_transitions.get("WTR", {})
        nearer_wtr2 = nearer_transitions.get("WTR-2", {})
        nearer_overlap = nearer_optical.get("wtr2_confidence_quality_overlap", {})
        if not nearer_wtr or not nearer_wtr2 or not nearer_overlap.get("before"):
            raise AssessmentError("the nearer optical record lacks class or quality summaries")
        earlier_water = int(nearer_wtr2.get("water_class_pixels_before_on_common_valid", -1))
        flagged_water = int(
            nearer_overlap["before"].get("wtr2_water_pixels_with_conf_cloud_or_snow_flag", -1)
        )
        if nearer_wtr.get("common_valid_pixel_count") != 0 or earlier_water <= 0 or flagged_water != earlier_water:
            raise AssessmentError("the selected nearer product pair does not match its quality-limited review")
        evidence.extend(
            [
                _artifact(
                    catalog_screen_path,
                    catalog_screen,
                    "NASA-CMR-DSWX-FOLLOWUP-SCREEN",
                    "CATALOG_DISCOVERY_ONLY",
                ),
                _artifact(
                    nearer_optical_path,
                    nearer_optical,
                    "NASA-OPERA-DSWX-NEARER-CONTEXT",
                    "OPTICAL_CONTEXT_QUALITY_LIMITED",
                ),
            ]
        )
        nearer_context = {
            "before_granule": nearer_before["granule_id"],
            "after_granule": nearer_after["granule_id"],
            "before_acquisition_utc": nearer_before["acquisition_time_utc"],
            "after_acquisition_utc": nearer_after["acquisition_time_utc"],
            "offset_from_rtc_before_days": nearer_optical["temporal_relationship"][
                "optical_before_minus_rtc_before_days"
            ],
            "offset_from_rtc_after_days": nearer_optical["temporal_relationship"][
                "optical_after_minus_rtc_after_days"
            ],
            "wtr_common_valid_count": int(nearer_wtr["common_valid_pixel_count"]),
            "wtr2_water_class_counts_before_after": [
                int(nearer_wtr2["water_class_pixels_before_on_common_valid"]),
                int(nearer_wtr2["water_class_pixels_after_on_common_valid"]),
            ],
            "wtr2_cloud_or_snow_flagged_water_before_after": [
                flagged_water,
                int(
                    nearer_overlap.get("after", {}).get(
                        "wtr2_water_pixels_with_conf_cloud_or_snow_flag", 0
                    )
                ),
            ],
            "interpretation_role": "nearest metadata candidates retrieved and checksum-verified; WTR has no shared valid pixels and earlier WTR-2 water classes are all cloud/snow flagged",
        }
    if spatial_support is not None and spatial_support_path is not None:
        evidence.append(
            _artifact(
                spatial_support_path,
                spatial_support,
                "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
                "DIAGNOSTIC_CROSS_SENSOR_SPATIAL_ASSOCIATION",
            )
        )
    sar = {
        "quantity": measurement["quantity"],
        "equation": measurement["equation"],
        "sensor": "Sentinel-1A via NASA OPERA RTC-S1; not NISAR",
        "polarization": measurement["polarization"],
        "units": measurement["units"],
        "acquisition_before_utc": before["acquisition_start_utc"],
        "acquisition_after_utc": after["acquisition_start_utc"],
        "scene_ids": [before["scene_id"], after["scene_id"]],
        "grid_crs": pair.get("grid", {}).get("crs"),
        "aoi_pixel_count": int(measurement["aoi_pixel_count"]),
        "common_clear_pixel_count": int(samples.size),
        "common_clear_fraction": samples.size / int(measurement["aoi_pixel_count"]),
        "mean_db": float(np.mean(samples)),
        "median_db": float(np.median(samples)),
        "p05_db": float(np.quantile(samples, 0.05)),
        "p95_db": float(np.quantile(samples, 0.95)),
        "minimum_db": float(np.min(samples)),
        "maximum_db": float(np.max(samples)),
        "negative_pixel_count": int(np.count_nonzero(samples < 0)),
        "positive_pixel_count": int(np.count_nonzero(samples > 0)),
        "provider_qa_state": pair.get("provider_qa", {}).get("status"),
        "analysis_disposition": pair["status"],
    }
    optical_before = optical["source_products"]["before"]
    optical_after = optical["source_products"]["after"]
    temporal = optical.get("temporal_relationship", {})
    before_offset = temporal.get("optical_before_minus_rtc_before_days")
    after_offset = temporal.get("optical_after_minus_rtc_after_days")
    if not isinstance(before_offset, (int, float)) or not isinstance(after_offset, (int, float)):
        raise AssessmentError("optical-to-SAR acquisition offsets are missing")
    timing_description = (
        f"The optical acquisitions are {before_offset:+.2f} and {after_offset:+.2f} days "
        "from their corresponding SAR acquisitions."
    )
    spatial_limit = (
        "The products use different native grids; exact area-weighted polygon overlap was evaluated without resampling."
        if spatial_support is not None
        else "The products use different native grids and no pixel-wise cross-sensor comparison was performed."
    )
    optical_context = {
        "product": "NASA OPERA L3 DSWx-HLS; optical HLS-derived classification",
        "before_granule": optical_before["granule_id"],
        "after_granule": optical_after["granule_id"],
        "before_acquisition_utc": optical_before["acquisition_time_utc"],
        "after_acquisition_utc": optical_after["acquisition_time_utc"],
        "wgs84_aoi": optical_bounds,
        "wtr_common_valid_count": wtr["common_valid_pixel_count"],
        "wtr_water_class_counts_before_after": [
            wtr["water_class_pixels_before_on_common_valid"],
            wtr["water_class_pixels_after_on_common_valid"],
        ],
        "wtr2_common_valid_count": wtr2["common_valid_pixel_count"],
        "wtr2_water_class_counts_before_after": [
            wtr2["water_class_pixels_before_on_common_valid"],
            wtr2["water_class_pixels_after_on_common_valid"],
        ],
        "wtr2_water_pixels_with_conf_cloud_or_snow_flags_before_after": [
            overlap["before"]["wtr2_water_pixels_with_conf_cloud_or_snow_flag"],
            overlap["after"]["wtr2_water_pixels_with_conf_cloud_or_snow_flag"],
        ],
        "interpretation_role": "product classification context only; not a field reference or SAR validation",
    }
    temporal = optical.get("temporal_relationship", {})
    evidence_ids = {item["evidence_id"] for item in evidence}
    known_hypothesis_ids = {
        "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
        "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        "H3_OTHER_LAND_SURFACE_OR_ACQUISITION_EFFECTS",
        "H4_SAR_PRODUCT_QUALITY_EFFECT",
    }
    follow_up_items: list[dict[str, object]] = [
        {
            "follow_up_id": "F1_RTC_QA_RESOLUTION",
            "target_hypothesis_ids": [
                "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
                "H4_SAR_PRODUCT_QUALITY_EFFECT",
            ],
            "purpose": "QUALITY_GATE",
            "availability_state": "PROVIDER_RESPONSE_REQUIRED",
            "action": "Obtain an authoritative QA disposition or corrected reprocessing for both exact RTC-S1 granules.",
            "discriminating_question": "Does the provider resolve the product-level quality concerns for these exact observations?",
            "possible_interpretation": "A resolved disposition can remove or confirm a product-quality limitation for this comparison; it cannot establish that water change caused the radar response.",
            "priority_reason": "This comparison remains diagnostic while its provider QA status has no consolidated verdict.",
        },
    ]
    if nearer_context is not None:
        follow_up_items.append(
            {
                "follow_up_id": "F2_CLOSER_WATER_CONTEXT",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED",
                "evidence_refs": ["NASA-CMR-DSWX-FOLLOWUP-SCREEN", "NASA-OPERA-DSWX-NEARER-CONTEXT"],
                "action": "Queried the nearest CMR candidates and retrieved the selected DSWx-HLS pair with asset checksum verification.",
                "discriminating_question": "Does spatially compatible water context co-vary with the radar-response pattern across closely timed acquisitions?",
                "possible_interpretation": f"This closer pair is quality limited: WTR has {nearer_context['wtr_common_valid_count']} common valid pixels; {nearer_context['wtr2_cloud_or_snow_flagged_water_before_after'][0]} of {nearer_context['wtr2_water_class_counts_before_after'][0]} earlier WTR-2 water-coded cells carry cloud/snow flags. It does not resolve the water explanation.",
                "priority_reason": "The nearest catalog candidates were tested; the earlier WTR-2 water classes are cloud/snow flagged and no shared WTR pixels are valid.",
            }
        )
    elif catalog_screen is not None:
        query_results = catalog_screen.get("query_results", [])
        nearest_candidates = {
            item.get("reference_label"): item.get("nearest_candidate")
            for item in query_results
            if isinstance(item, dict) and isinstance(item.get("nearest_candidate"), dict)
        }
        follow_up_items.append(
            {
                "follow_up_id": "F2_CLOSER_WATER_CONTEXT",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "CATALOG_SCREENED_CONTEXT_RETRIEVED",
                "evidence_refs": ["NASA-CMR-DSWX-TEMPORAL-SCREEN", "NASA-OPERA-DSWX-HLS"],
                "action": "Screened NASA CMR around each SAR acquisition and retrieved a bounded DSWx-HLS product pair.",
                "discriminating_question": "Do the closely timed optical classifications and SAR response share a spatial pattern on valid common support?",
                "possible_interpretation": (
                    "The area-weighted overlay on common valid support found few changed WTR fractions and a descriptive Pearson r of "
                    f"{spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}; this does not resolve the water explanation."
                    if spatial_support is not None
                    else "The optical classifications provide closely timed context, but different native grids and the absence of a common-support spatial comparison prevent this record from resolving the water explanation."
                ),
                "priority_reason": (
                    f"The date-anchored catalog screen returned {catalog_screen.get('unique_candidate_count', 0)} candidates. "
                    f"Nearest before: {nearest_candidates.get('before', {}).get('granule_id', 'none')}; "
                    f"nearest after: {nearest_candidates.get('after', {}).get('granule_id', 'none')}. "
                    f"{timing_description} {spatial_limit}"
                ),
            }
        )
    else:
        follow_up_items.append(
            {
                "follow_up_id": "F2_CLOSER_WATER_CONTEXT",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "NOT_SEARCHED",
                "action": "Search for quality-screened, temporally closer optical or water-context observations around the two SAR acquisitions.",
                "discriminating_question": "Does spatially compatible water context co-vary with the radar-response pattern across closely timed acquisitions?",
                "possible_interpretation": "A compatible spatial pattern could add contextual support; a mismatch could weaken this explanation. Neither outcome alone establishes causation.",
                "priority_reason": f"{timing_description} {spatial_limit}",
            }
        )
    if spatial_support is not None:
        follow_up_items.append(
            {
                "follow_up_id": "F3_SPATIAL_ASSOCIATION_REVIEW",
                "target_hypothesis_ids": ["H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"],
                "purpose": "DISCRIMINATING_OBSERVATION",
                "availability_state": "RETRIEVED_QUALITY_LIMITED",
                "evidence_refs": ["NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"],
                "action": "Completed an exact area-weighted spatial overlay between native-grid DSWx-HLS WTR cells and the diagnostic RTC-S1 measurement.",
                "discriminating_question": "Does optical water-fraction change show a stable spatial association with the SAR response on common valid support?",
                "possible_interpretation": (
                    f"At the 0.75 coverage threshold, {spatial_summary['water_fraction_increased_by_more_than_0_05'] + spatial_summary['water_fraction_decreased_by_more_than_0_05']} cells show water-fraction change above 0.05 and the descriptive linear correlation is {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}. "
                    "This does not distinguish the water explanation; unresolved RTC-S1 QA and optical-context limits remain."
                ),
                "priority_reason": "The geometric compatibility question is now tested on retained cells. The next useful evidence is provider-resolved RTC-S1 QA and a quality-valid, temporally appropriate water observation with enough spatial transitions.",
            }
        )
    follow_up_items.append(
        {
            "follow_up_id": "F4_ALTERNATIVE_SURFACE_DRIVERS" if spatial_support is not None else "F3_ALTERNATIVE_SURFACE_DRIVERS",
            "target_hypothesis_ids": ["H3_OTHER_LAND_SURFACE_OR_ACQUISITION_EFFECTS"],
            "purpose": "DISCRIMINATING_OBSERVATION",
            "availability_state": "NOT_SEARCHED",
            "action": "Identify independent moisture, vegetation, or acquisition-condition evidence with spatial and temporal support adequate for this AOI.",
            "discriminating_question": "Do measured alternative drivers predict the observed SAR-response pattern at the acquisition times?",
            "possible_interpretation": "A suitable match would make an alternative mechanism testable; coarse or mistimed context would remain nondiscriminating and should not be used to explain the AOI-scale pattern.",
            "priority_reason": "These explanations currently have no corresponding measurements or controls in the retained records.",
        }
    )
    follow_up_evidence = validate_follow_up_plan(
        follow_up_items,
        known_hypothesis_ids=known_hypothesis_ids,
        known_evidence_ids=evidence_ids,
    )

    def hypothesis(
        hypothesis_id: str,
        statement: str,
        assessments: list[EvidenceAssessment],
        *,
        scope_limit: str,
        expected_observation: str,
        would_weaken_if: str,
        testability_state: str,
        testability_reason: str,
        required_evidence: list[str],
    ) -> dict[str, Any]:
        evaluation = evaluate_hypothesis(assessments, known_evidence_ids=evidence_ids)
        return {
            "id": hypothesis_id,
            "statement": statement,
            "state": evaluation["disposition"],
            "evidence_refs": [item.evidence_id for item in assessments],
            "evidence_assessments": evaluation["evidence_assessments"],
            "scope_limit": scope_limit,
            "expected_observation": expected_observation,
            "would_weaken_if": would_weaken_if,
            "testability_state": testability_state,
            "testability_reason": testability_reason,
            "required_evidence": required_evidence,
        }

    summary = (
        "The records establish a diagnostic Sentinel-1-derived backscatter ratio and a decline in DSWx-HLS water-class counts over the same WGS84 AOI."
        + (
            f" An exact area-weighted native-grid overlay was completed. At the 0.75 coverage threshold, {spatial_summary['sar_cells']} cells were retained, {spatial_summary['water_fraction_changed_by_at_most_0_05']} had at most 0.05 water-fraction change, and descriptive Pearson r was {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}."
            if spatial_support is not None
            else " They do not establish a pixel-level relationship."
        )
        + " The evidence does not establish a causal explanation or validated flood boundary."
    )
    if nearer_context is not None:
        summary += (
            " The temporally nearer DSWx-HLS comparison does not resolve the interpretation: its WTR layer has no common valid AOI pixels, and all earlier WTR-2 water-coded cells are cloud/snow flagged."
        )

    return {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "status": "CAUSAL_INTERPRETATION_UNRESOLVED",
        "question": "Do the available same-AOI observations establish that changing surface water caused the measured SAR backscatter response?",
        "evidence_artifacts": evidence,
        "observations": {
            "sar_diagnostic_measurement": sar,
            "optical_product_classifications": optical_context,
            "nearer_optical_quality_context": nearer_context,
            "spatial_support_diagnostic": (
                {
                    "status": spatial_support["status"],
                    "coverage_sensitivity": spatial_support["summary"]["coverage_sensitivity"],
                    "interpretation_role": "diagnostic descriptive spatial association; not causal evidence or SAR validation",
                }
                if spatial_support is not None
                else None
            ),
            "relative_acquisition_offsets_days": {
                "optical_before_minus_sar_before": temporal.get("optical_before_minus_rtc_before_days"),
                "optical_after_minus_sar_after": temporal.get("optical_after_minus_rtc_after_days"),
            },
        },
        "hypotheses": validate_hypotheses([
            hypothesis(
                "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
                "In the retained DSWx-HLS pair, the later products classify fewer AOI cells as water than the earlier products.",
                [EvidenceAssessment(
                    "NASA-OPERA-DSWX-HLS",
                    EvidenceRelation.SUPPORTS,
                    f"The retained WTR counts change {wtr['water_class_pixels_before_on_common_valid']} to {wtr['water_class_pixels_after_on_common_valid']} and WTR-2 counts change {wtr2['water_class_pixels_before_on_common_valid']} to {wtr2['water_class_pixels_after_on_common_valid']} on their respective common-valid cells.",
                )],
                scope_limit="Supported only as a change in product class counts; this is not ground-truth water extent.",
                expected_observation="The retained DSWx-HLS products classify fewer common-valid AOI cells as water in the later product.",
                would_weaken_if="A recomputation from the retained arrays does not reproduce the reported count changes; this challenges the product-count statement, not ground-truth water extent.",
                testability_state="DESCRIPTIVE_ONLY",
                testability_reason="WTR and WTR-2 count changes are available on their respective common-valid centers, with differing valid support.",
                required_evidence=["Retained WTR and WTR-2 arrays and their product validity masks"],
            ),
            hypothesis(
                "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
                "The optical water-class change explains the measured Sentinel-1-derived backscatter ratio.",
                [
                    EvidenceAssessment(
                        "SAR-RTC-S1-PAIR",
                        EvidenceRelation.DOES_NOT_DISTINGUISH,
                        "The aggregate backscatter ratio measures radar-response change but does not by itself identify a physical cause.",
                    ),
                    EvidenceAssessment(
                        "NASA-OPERA-DSWX-HLS",
                        EvidenceRelation.LIMITS_INTERPRETATION,
                        f"{timing_description} {spatial_limit}",
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "NASA-OPERA-DSWX-NEARER-CONTEXT",
                                EvidenceRelation.LIMITS_INTERPRETATION,
                                "The nearest screened optical pair has zero shared valid WTR pixels; all earlier WTR-2 water-coded cells carry cloud/snow flags.",
                            )
                        ]
                        if nearer_context is not None
                        else []
                    ),
                    *(
                        [
                            EvidenceAssessment(
                                "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
                                EvidenceRelation.DOES_NOT_DISTINGUISH,
                                (
                                    f"At 0.75 common-valid WTR area coverage, {spatial_summary['sar_cells']} SAR cells remain; "
                                    f"{spatial_summary['water_fraction_changed_by_at_most_0_05']} have at most 0.05 water-fraction change, "
                                    f"and the descriptive Pearson r is {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}. "
                                    "This non-inferential association does not distinguish a water driver; the RTC-S1 pair remains diagnostic."
                                ),
                            )
                        ]
                        if spatial_support is not None
                        else []
                    ),
                ],
                scope_limit="No causal attribution; RTC-S1 also lacks a consolidated provider QA verdict.",
                expected_observation="A quality-valid water transition is spatially associated with the SAR response at suitable temporal and common spatial support.",
                would_weaken_if="With adequate quality and coverage, valid water observations show no spatial relationship to the SAR response pattern; missing or masked coverage remains inconclusive.",
                testability_state="NOT_TESTABLE_WITH_RETAINED_EVIDENCE",
                testability_reason=(
                    ("The nearer WTR comparison has zero common valid AOI pixels and all earlier WTR-2 water-coded cells are cloud/snow flagged. " if nearer_context is not None else "")
                    + (
                        (
                            f"An exact area-weighted common-support overlay was completed; {spatial_summary['water_fraction_changed_by_at_most_0_05']} of {spatial_summary['sar_cells']} cells have at most 0.05 water-fraction change, and descriptive Pearson r is {spatial_summary['descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db']:.3f}. "
                            "This does not test the physical explanation. "
                        )
                        if spatial_support is not None
                        else "The retained records do not contain a documented common-support pixel-wise cross-sensor test. "
                    )
                    + "The SAR pair also lacks a consolidated provider QA verdict."
                ),
                required_evidence=[
                    "Provider-resolved RTC-S1 product quality for both acquisitions",
                    "Temporally suitable water observations with valid spatial coverage",
                    "A documented common-support spatial comparison",
                ],
            ),
            hypothesis(
                "H3_OTHER_LAND_SURFACE_OR_ACQUISITION_EFFECTS",
                "Soil moisture, vegetation, or acquisition-condition changes contributed to the SAR response.",
                [],
                scope_limit="Not evaluated because corresponding measurements or controls are absent.",
                expected_observation="An independently measured alternative driver varies with the SAR response at an appropriate spatial and temporal scale.",
                would_weaken_if="Adequate independent driver measurements show no corresponding pattern; absent or coarse measurements remain uninformative.",
                testability_state="NOT_TESTED",
                testability_reason="No independent moisture, vegetation, or acquisition-condition measurements are retained for this AOI and interval.",
                required_evidence=["Independent, time- and scale-appropriate measurements of plausible alternative drivers"],
            ),
            hypothesis(
                "H4_SAR_PRODUCT_QUALITY_EFFECT",
                "Product quality or processing effects account for some or all of the SAR response.",
                [EvidenceAssessment(
                    "SAR-RTC-S1-PAIR",
                    EvidenceRelation.LIMITS_INTERPRETATION,
                    "Per-product metadata and masks are retained, but neither sidecar provides a consolidated PASS/FAIL disposition.",
                )],
                scope_limit="Unresolved pending provider QA clarification or corrected products.",
                expected_observation="Documented quality or processing anomalies are present and spatially or temporally associated with the measured SAR response.",
                would_weaken_if="Provider-resolved quality checks and processing metadata show no relevant anomaly; this would not exclude unmeasured error sources.",
                testability_state="NOT_TESTED",
                testability_reason="The sidecars retain selected metadata but provide neither acquisition a consolidated QA disposition, so a quality-effect test cannot be completed.",
                required_evidence=["Authoritative per-product QA disposition and relevant spatial quality diagnostics"],
            ),
        ], known_evidence_ids=evidence_ids),
        "assessment": {
            "summary": summary,
            "physical_cause": "UNRESOLVED",
            "event_extent": "NOT_ESTABLISHED",
            "nisar_measurement_present": False,
        },
        "follow_up_evidence": validate_follow_up_plan(
            follow_up_items,
            known_hypothesis_ids=known_hypothesis_ids,
            known_evidence_ids=evidence_ids,
        ),
        "processing": {
            "method": "Read the exact retained source records; verify record types, shared WGS84 AOI, measurement-mask shapes and counts; summarize valid log-ratio values; when linked, validate the source checksums and summarize an exact area-weighted polygon overlay of native-grid optical cells on SAR cells without resampling; validate hypothesis predictions, weakening conditions, evidence references, and testability-state fields without deciding their scientific correctness.",
            "software": {"numpy": np.__version__},
            "script": "tools/research/build_cross_sensor_investigation.py",
            "no_statistical_significance_claim": True,
            "no_probability_or_confidence_score": True,
        },
        "interpretation_limits": [
            "OPERA RTC-S1 is Sentinel-1-derived and is not NISAR.",
            "The SAR result remains diagnostic because provider QA metadata contain no consolidated verdict.",
            "DSWx-HLS water classes are optical algorithm outputs, not ground truth.",
            "The two products use different native grids; polygon intersections provide area-weighted descriptive association, not pixel identity or causal evidence.",
            "No event boundary, damage, or physical cause is inferred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sar-record", required=True, type=Path)
    parser.add_argument("--optical-record", required=True, type=Path)
    parser.add_argument("--nearer-optical-record", type=Path)
    parser.add_argument("--catalog-screen-record", type=Path, help="optional CMR screen for the selected optical context")
    parser.add_argument("--spatial-support-record", type=Path, help="optional checksum-linked native-grid spatial overlay record")
    parser.add_argument("--case-id", default="rio-grande-do-sul-cross-sensor-diagnostic-2024")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = build_assessment(
        args.sar_record,
        args.optical_record,
        args.nearer_optical_record,
        args.catalog_screen_record,
        args.case_id,
        args.spatial_support_record,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"status={record['status']}")
    print(f"evidence_artifacts={len(record['evidence_artifacts'])}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
