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
) -> dict[str, Any]:
    if (nearer_optical_path is None) != (catalog_screen_path is None):
        raise AssessmentError("the nearer optical record and its CMR screen must be provided together")
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
    if pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON":
        raise AssessmentError("the retained RTC-S1 record is not the expected diagnostic comparison")
    if optical.get("status") != "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION":
        raise AssessmentError("the DSWx-HLS record does not have its optical-context-only disposition")

    pair_bounds = pair.get("grid", {}).get("window", {}).get("bounds_wgs84")
    optical_bounds = optical.get("aoi", {}).get("bounds_west_south_east_north")
    if not isinstance(pair_bounds, list) or pair_bounds != optical_bounds:
        raise AssessmentError("the RTC-S1 and DSWx-HLS records do not describe the same WGS84 AOI")
    if nearer_optical is not None:
        nearer_bounds = nearer_optical.get("aoi", {}).get("bounds_west_south_east_north")
        if nearer_optical.get("status") != "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION":
            raise AssessmentError("the nearer DSWx-HLS record is not labeled optical context only")
        if nearer_bounds != pair_bounds or catalog_screen.get("bounds_wgs84") != pair_bounds:
            raise AssessmentError("the follow-up records do not describe the same WGS84 AOI")
        if catalog_screen.get("status") != "METADATA_ONLY_NO_PIXEL_QA":
            raise AssessmentError("the DSWx-HLS catalog screen has an unsupported disposition")

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
                "evidence_refs": [
                    "NASA-CMR-DSWX-FOLLOWUP-SCREEN",
                    "NASA-OPERA-DSWX-NEARER-CONTEXT",
                ],
                "action": "Queried the nearest CMR candidates and retrieved the selected DSWx-HLS pair with asset checksum verification.",
                "discriminating_question": "Does spatially compatible water context co-vary with the radar-response pattern across closely timed acquisitions?",
                "possible_interpretation": f"This closer pair is quality limited: WTR has {nearer_context['wtr_common_valid_count']} common valid pixels; {nearer_context['wtr2_cloud_or_snow_flagged_water_before_after'][0]} of {nearer_context['wtr2_water_class_counts_before_after'][0]} earlier WTR-2 water-coded cells carry cloud/snow flags. It does not resolve the water explanation.",
                "priority_reason": "The nearest catalog candidates were tested; the earlier WTR-2 water classes are cloud/snow flagged and no shared WTR pixels are valid.",
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
                "priority_reason": "Current optical observations lead the SAR acquisitions by about 1.8–2.8 days and are not pixel matched.",
            }
        )
    follow_up_items.append(
        {
            "follow_up_id": "F3_ALTERNATIVE_SURFACE_DRIVERS",
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
    ) -> dict[str, Any]:
        evaluation = evaluate_hypothesis(assessments, known_evidence_ids=evidence_ids)
        return {
            "id": hypothesis_id,
            "statement": statement,
            "state": evaluation["disposition"],
            "evidence_refs": [item.evidence_id for item in assessments],
            "evidence_assessments": evaluation["evidence_assessments"],
            "scope_limit": scope_limit,
        }

    summary = (
        "The records establish a diagnostic Sentinel-1-derived backscatter ratio and a decline in DSWx-HLS water-class counts over the same WGS84 AOI."
        " They do not establish a pixel-level relationship, a causal explanation, or a validated flood boundary."
    )
    if nearer_context is not None:
        summary += (
            " The temporally nearer DSWx-HLS comparison does not resolve the interpretation: its WTR layer has no common valid AOI pixels, and all earlier WTR-2 water-coded cells are cloud/snow flagged."
        )

    return {
        "record_type": "ECHO_CROSS_SENSOR_INVESTIGATION_ASSESSMENT",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": "rio-grande-do-sul-cross-sensor-diagnostic-2024",
        "status": "CAUSAL_INTERPRETATION_UNRESOLVED",
        "question": "Do the available same-AOI observations establish that changing surface water caused the measured SAR backscatter response?",
        "evidence_artifacts": evidence,
        "observations": {
            "sar_diagnostic_measurement": sar,
            "optical_product_classifications": optical_context,
            "nearer_optical_quality_context": nearer_context,
            "relative_acquisition_offsets_days": {
                "optical_before_minus_sar_before": temporal.get("optical_before_minus_rtc_before_days"),
                "optical_after_minus_sar_after": temporal.get("optical_after_minus_rtc_after_days"),
            },
        },
        "hypotheses": [
            hypothesis(
                "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
                "In the original retained DSWx-HLS pair, the later products classify fewer AOI cells as water than the earlier products.",
                [EvidenceAssessment(
                    "NASA-OPERA-DSWX-HLS",
                    EvidenceRelation.SUPPORTS,
                    "The retained WTR counts change 36 to 27 and WTR-2 counts change 135 to 59 on their respective common-valid cells.",
                )],
                scope_limit="Supported only as a change in product class counts; this is not ground-truth water extent.",
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
                        "The optical observations precede the SAR acquisitions by about 1.8–2.8 days and use different native grids; no pixel-wise comparison was performed.",
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
                ],
                scope_limit="No causal attribution; RTC-S1 also lacks a consolidated provider QA verdict.",
            ),
            hypothesis(
                "H3_OTHER_LAND_SURFACE_OR_ACQUISITION_EFFECTS",
                "Soil moisture, vegetation, or acquisition-condition changes contributed to the SAR response.",
                [],
                scope_limit="Not evaluated because corresponding measurements or controls are absent.",
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
            ),
        ],
        "assessment": {
            "summary": summary,
            "physical_cause": "UNRESOLVED",
            "event_extent": "NOT_ESTABLISHED",
            "nisar_measurement_present": False,
        },
        "follow_up_evidence": follow_up_evidence,
        "processing": {
            "method": "Read the exact retained source records; verify their record types, shared WGS84 AOI, measurement-mask shapes and counts; summarize only the stored valid log-ratio values; link optical product transitions without raster resampling or pixel matching.",
            "software": {"numpy": np.__version__},
            "script": "tools/research/build_cross_sensor_investigation.py",
            "no_statistical_significance_claim": True,
            "no_probability_or_confidence_score": True,
        },
        "interpretation_limits": [
            "OPERA RTC-S1 is Sentinel-1-derived and is not NISAR.",
            "The SAR result remains diagnostic because provider QA metadata contain no consolidated verdict.",
            "DSWx-HLS water classes are optical algorithm outputs, not ground truth.",
            "The two products share a WGS84 AOI but are not pixel matched; aggregate temporal agreement does not establish a causal relationship.",
            "No event boundary, damage, or physical cause is inferred.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sar-record", required=True, type=Path)
    parser.add_argument("--optical-record", required=True, type=Path)
    parser.add_argument("--nearer-optical-record", type=Path)
    parser.add_argument("--catalog-screen-record", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = build_assessment(
        args.sar_record,
        args.optical_record,
        args.nearer_optical_record,
        args.catalog_screen_record,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"status={record['status']}")
    print(f"evidence_artifacts={len(record['evidence_artifacts'])}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
