import json
from hashlib import sha256
from pathlib import Path

import pytest

from echo.adversarial import (
    _reproduce_polarization_summary,
    _reproduce_spatial_coverage_variants,
    _spatial_coverage_sweep,
    _build_spatial_sensitivity_map,
    _summarize_linked_sensitivity,
    build_adversarial_challenge,
    build_qa_held_observation_challenge,
)


ROOT = Path(__file__).resolve().parents[1]


def _t163_assessment():
    case = json.loads((ROOT / "data/cases/rio-grande-do-sul-t163-349925-2024/investigation.json").read_text())
    return json.loads((ROOT / case["evidence_records"]["cross_sensor_assessment"]).read_text())


def _t024_assessment():
    case = json.loads((ROOT / "data/cases/rio-grande-do-sul-t024-2024/investigation.json").read_text())
    return json.loads((ROOT / case["evidence_records"]["cross_sensor_assessment"]).read_text())


@pytest.mark.parametrize(
    "hypothesis_id",
    [
        "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
        "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        "H3_SOIL_MOISTURE_CHANGE",
        "H4_VEGETATION_STATE_CHANGE",
        "H5_ACQUISITION_CONDITIONS_EFFECT",
        "H6_SAR_PRODUCT_QUALITY_EFFECT",
    ],
)
def test_t024_challenge_reproduces_measurement_without_upgrading_diagnostic_case(hypothesis_id):
    assessment = _t024_assessment()
    case = json.loads((ROOT / "data/cases/rio-grande-do-sul-t024-2024/investigation.json").read_text())
    assessment_bytes = (ROOT / case["evidence_records"]["cross_sensor_assessment"]).read_bytes()
    report = build_adversarial_challenge(
        assessment,
        hypothesis_id=hypothesis_id,
        assessment_sha256=sha256(assessment_bytes).hexdigest(),
        evidence_root=ROOT,
    )

    assert report["case_id"] == "rio-grande-do-sul-cross-sensor-diagnostic-2024"
    assert report["status"] == "REVIEWABLE_WITH_RECORDED_LIMITS"
    recorded_hypothesis = next(
        item for item in assessment["hypotheses"] if item["id"] == hypothesis_id
    )
    assert report["hypothesis"]["recorded_state"] == recorded_hypothesis["state"]
    assert assessment["status"] == "CAUSAL_INTERPRETATION_UNRESOLVED"
    assert report["observation"]["qa_gate"] == "PROVIDER_QA_UNRESOLVED"
    assert (
        report["observation"]["measurement_reproduction"]["status"]
        == "LINKED_MEAN_MEDIAN_AND_MASK_REPRODUCED"
    )
    assert report["observation"]["measurement"]["sensor"] == "Sentinel-1A via NASA OPERA RTC-S1; not NISAR"
    assert report["observation"]["measurement"]["analysis_disposition"] == "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
    baseline_review = report["temporal_baseline_review"]
    assert baseline_review["status"] == "REPRODUCED_DIAGNOSTIC_BASELINE_SENSITIVITY"
    assert baseline_review["common_support_count"] == 1034
    assert [item["measured_pixel_count"] for item in baseline_review["adjacent_intervals"]] == [1034, 1034]
    assert baseline_review["reference_baseline"]["comparisons"][0]["interval_days"] == pytest.approx(408, abs=0.001)
    assert baseline_review["reference_baseline"]["comparisons"][0]["summary_db"]["median"] == pytest.approx(-1.2518466562)


def test_t163_challenge_view_keeps_diagnostic_qa_and_surfaces_existing_alternatives():
    assessment = _t163_assessment()
    report = build_adversarial_challenge(
        assessment,
        hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        assessment_sha256="a" * 64,
        evidence_root=ROOT,
    )

    assert report["status"] == "REVIEWABLE_WITH_RECORDED_LIMITS"
    assert report["observation"]["qa_gate"] == "PROVIDER_QA_UNRESOLVED"
    assert report["observation"]["measurement"]["scene_ids"] == assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"]
    assert report["hypothesis"]["recorded_state"] == "UNRESOLVED"
    assert report["temporal_baseline_review"]["status"] == "NOT_AVAILABLE_NO_LINKED_TEMPORAL_SERIES"
    assert any(item["hypothesis_id"] == "H3_SOIL_MOISTURE_CHANGE" for item in report["alternatives"])
    assert "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY" in {
        item["evidence_id"] for item in report["sensitivity_review"]["linked_sources"]
    }
    results = {item["evidence_id"]: item for item in report["sensitivity_review"]["recorded_results"]}
    polarization = results["NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"]
    assert polarization["summary_basis"] == "RECOMPUTED_FROM_CHECKSUM_VALIDATED_VV_VH_PER_CELL_RECORDS"
    assert polarization["summary"]["common_cells"] == 738
    assert polarization["summary"]["vv_median_log_ratio_db"] == pytest.approx(-1.215351641)
    assert polarization["summary"]["vh_median_log_ratio_db"] == pytest.approx(-1.143774748)
    support = results["NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"]["summary"]["coverage_sensitivity"]
    assert [item["sar_cells"] for item in support] == [826, 738, 738, 738]
    assert [item["minimum_common_valid_wtr_area_fraction"] for item in support] == [0.5, 0.75, 0.9, 0.95]
    sweep = results["NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"]["summary"]["exploratory_threshold_sweep"]
    assert [item["minimum_common_valid_wtr_area_fraction"] for item in sweep] == pytest.approx(
        [0.5 + step * 0.05 for step in range(10)]
    )
    assert len(sweep) == 10
    assert [item["sar_cells"] for item in sweep] == sorted(
        (item["sar_cells"] for item in sweep), reverse=True
    )
    assert sweep[0]["sar_cells"] == support[0]["sar_cells"]
    assert sweep[5]["sar_cells"] == support[1]["sar_cells"]
    assert sweep[8]["sar_cells"] == support[2]["sar_cells"]
    assert sweep[9]["sar_cells"] == support[3]["sar_cells"]
    spatial_map = results["NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"]["spatial_map"]
    pair = json.loads((ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json").read_text())
    assert spatial_map["status"] == "DIAGNOSTIC_SPATIAL_ASSOCIATION"
    assert spatial_map["coordinate_reference_system"] == "WGS84 longitude, latitude"
    assert (spatial_map["rows"], spatial_map["columns"], len(spatial_map["cells"])) == (38, 33, 1254)
    assert [
        spatial_map["pixel_corners_wgs84"][0][0],
        spatial_map["pixel_corners_wgs84"][0][1],
        spatial_map["pixel_corners_wgs84"][1][1],
        spatial_map["pixel_corners_wgs84"][1][0],
    ] == [
        pair["grid"]["pixel_corners_wgs84"][0][0],
        pair["grid"]["pixel_corners_wgs84"][0][1],
        pair["grid"]["pixel_corners_wgs84"][1][1],
        pair["grid"]["pixel_corners_wgs84"][1][0],
    ]
    all_points = [point for row in pair["grid"]["pixel_corners_wgs84"] for point in row]
    assert spatial_map["bounds_wgs84"] == [
        min(point[0] for point in all_points),
        min(point[1] for point in all_points),
        max(point[0] for point in all_points),
        max(point[1] for point in all_points),
    ]
    assert spatial_map["aoi_bounds_wgs84"] == pair["grid"]["window"]["bounds_wgs84"]
    assert sum(cell["sar_measurement_valid"] for cell in spatial_map["cells"]) == 1199
    assert spatial_map["pair_record_sha256"] == sha256(
        (ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json").read_bytes()
    ).hexdigest()
    assert "DIAGNOSTIC" in polarization["source_status"]
    assert report["observation"]["qa_gate"] == "PROVIDER_QA_UNRESOLVED"
    reproduction = report["observation"]["measurement_reproduction"]
    assert reproduction["status"] == "LINKED_MEAN_MEDIAN_AND_MASK_REPRODUCED"
    assert reproduction["valid_sample_count"] == report["observation"]["measurement"]["common_clear_pixel_count"]
    assert reproduction["median_db"] == pytest.approx(report["observation"]["measurement"]["median_db"])
    assert report["next_observations"]
    next_steps = {item["follow_up_id"]: item for item in report["next_observations"]}
    assert next_steps["F1_RTC_QA_RESOLUTION"]["action_track"] == "QUALITY_PREREQUISITE"
    assert "no consolidated verdict" in next_steps["F1_RTC_QA_RESOLUTION"]["priority_reason"].lower()
    gauge_follow_up = next_steps["F11_GUAIBA_PRIMARY_SERIES"]
    assert gauge_follow_up["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert gauge_follow_up["evidence_refs"] == [
        "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY",
        "ANA-GUAIBA-PRIMARY-SERIES-ACCESS-SCREEN",
    ]
    assert "do not establish that the archived series is absent" in gauge_follow_up["priority_reason"].lower()
    assert "probability" in report["sensitivity_review"]["interpretation_limit"]


def test_spatial_sensitivity_summary_is_recomputed_from_retained_cells():
    path = ROOT / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-mask-sensitivity-2026-11-09.json"
    record = json.loads(path.read_text())
    record["summary"]["coverage_sensitivity"][0]["sar_cells"] += 1

    with pytest.raises(ValueError, match="sar_cells does not reproduce"):
        _reproduce_spatial_coverage_variants(record)


def test_spatial_sweep_rejects_missing_values_for_cells_marked_sar_valid():
    cells = [{
        "sar_measurement_valid": True,
        "common_valid_wtr_area_fraction": 1.0,
        "water_fraction_change_after_minus_before": 0.0,
        "sar_log_ratio_db": None,
    }]

    with pytest.raises(ValueError, match="lacks a SAR measurement"):
        _spatial_coverage_sweep(cells)


def test_spatial_map_rejects_per_cell_sar_value_that_differs_from_linked_pair():
    record = json.loads((ROOT / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-mask-sensitivity-2026-11-09.json").read_text())
    pair = json.loads((ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json").read_text())
    cell = next(item for item in record["per_sar_cell"] if item["sar_measurement_valid"])
    cell["sar_log_ratio_db"] += 0.1

    with pytest.raises(ValueError, match="does not match the linked pair measurement"):
        _build_spatial_sensitivity_map(record, pair)


def test_spatial_map_rejects_non_boolean_pair_masks_and_invalid_wgs84_corners():
    record = json.loads((ROOT / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-mask-sensitivity-2026-11-09.json").read_text())
    pair = json.loads((ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json").read_text())
    pair["measurement"]["valid_mask"][0][0] = "true"
    with pytest.raises(ValueError, match="non-boolean values"):
        _build_spatial_sensitivity_map(record, pair)

    pair = json.loads((ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json").read_text())
    pair["grid"]["pixel_corners_wgs84"][0][0][0] = 181
    with pytest.raises(ValueError, match="invalid WGS84 corner"):
        _build_spatial_sensitivity_map(record, pair)


def test_polarization_sensitivity_summary_is_recomputed_from_linked_cells():
    assessment = _t163_assessment()
    artifacts = {item["evidence_id"]: item for item in assessment["evidence_artifacts"]}
    artifact = artifacts["NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"]
    record = json.loads((ROOT / artifact["relative_path"]).read_text())
    record["summary"]["vv_median_log_ratio_db"] += 0.1

    with pytest.raises(ValueError, match="vv_median_log_ratio_db does not reproduce"):
        _reproduce_polarization_summary(
            record, artifacts_by_id=artifacts, evidence_root=ROOT
        )


def test_t163_challenge_includes_reproducible_case_wide_comparability_without_promoting_it():
    assessment = _t163_assessment()
    report = build_adversarial_challenge(
        assessment,
        hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        assessment_sha256="a" * 64,
        evidence_root=ROOT,
    )

    review = report["comparability_review"]
    assert review["state"] == "DESCRIPTIVE_METADATA_REVIEW_NOT_CAUSAL_OR_QA_CLEARANCE"
    assert review["scope"] == "CASE_WIDE_NOT_LINKED_TO_SELECTED_HYPOTHESIS"
    assert review["summary"]["causal_disposition"] == "UNRESOLVED"
    assert review["summary"]["hypothesis_relation"] == "DOES_NOT_DISTINGUISH"
    assert review["summary"]["incidence_angle_metadata_available"] is False
    assert review["summary"]["spatially_matched_rfi_evidence_available"] is False
    assert report["observation"]["qa_gate"] == "PROVIDER_QA_UNRESOLVED"
    assert "rfi_burst_report" in {item["field"] for item in review["comparisons"]}


def test_t163_challenge_rejects_tampered_acquisition_comparability_source_checksum():
    assessment = _t163_assessment()
    artifact = next(
        item for item in assessment["evidence_artifacts"]
        if item["evidence_id"] == "NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW"
    )
    artifact["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="acquisition-condition review checksum"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="a" * 64,
            evidence_root=ROOT,
        )


def test_t163_challenge_rejects_tampered_retained_sensitivity_checksum():
    assessment = _t163_assessment()
    artifact = next(
        item for item in assessment["evidence_artifacts"]
        if item["evidence_id"] == "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"
    )
    artifact["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="sensitivity record checksum"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="a" * 64,
            evidence_root=ROOT,
        )


def test_spatial_sensitivity_rejects_negative_coverage_threshold(tmp_path):
    pair_record = {
        "status": "DIAGNOSTIC",
        "source_products": {
            "before": {"scene_id": "before-scene"},
            "after": {"scene_id": "after-scene"},
        },
    }
    optical = {"sha256": "optical-checksum"}
    record = {
        "record_type": "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC",
        "status": "DIAGNOSTIC",
        "scope": "TEST_ONLY",
        "sources": {
            "sar_pair_record_sha256": "pair-checksum",
            "sar_pair_status": "DIAGNOSTIC",
            "optical_context_record_sha256": "optical-checksum",
        },
        "summary": {
            "coverage_sensitivity": [{
                "minimum_common_valid_wtr_area_fraction": -0.01,
                "sar_cells": 1,
                "mean_signed_sar_log_ratio_db": 0.0,
                "median_signed_sar_log_ratio_db": 0.0,
                "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db": 0.0,
            }],
        },
        "per_sar_cell": [{
            "sar_row": 0,
            "sar_column": 0,
            "sar_measurement_valid": True,
            "common_valid_wtr_area_fraction": 1.0,
            "water_fraction_change_after_minus_before": 0.0,
            "sar_log_ratio_db": 0.0,
        }],
    }
    source_path = tmp_path / "sensitivity.json"
    source_bytes = json.dumps(record).encode()
    source_path.write_bytes(source_bytes)
    artifact = {
        "evidence_id": "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
        "record_type": record["record_type"],
        "status": record["status"],
        "relative_path": "sensitivity.json",
        "sha256": sha256(source_bytes).hexdigest(),
    }

    with pytest.raises(ValueError, match="thresholds are not ordered and valid"):
        _summarize_linked_sensitivity(
            artifact,
            artifacts_by_id={"NASA-OPERA-DSWX-HLS": optical},
            evidence_root=tmp_path,
            pair_record=pair_record,
            pair_record_sha256="pair-checksum",
        )


def test_challenge_view_reports_referenced_but_unassessed_sources_as_gaps():
    assessment = _t163_assessment()
    hypothesis = next(item for item in assessment["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    removed = hypothesis["evidence_assessments"].pop()

    report = build_adversarial_challenge(
        assessment,
        hypothesis_id=hypothesis["id"],
        assessment_sha256="b" * 64,
        evidence_root=ROOT,
    )

    assert removed["evidence_id"] in report["evidence_review"]["unassessed_referenced_evidence_ids"]
    assert removed["evidence_id"] not in {
        item["evidence_id"] for item in report["evidence_review"]["recorded_relationships"]
    }


@pytest.mark.parametrize("scene_ids", [[], ["same", "same"], ["only-one"]])
def test_challenge_view_rejects_invalid_sar_comparison_identity(scene_ids):
    assessment = _t163_assessment()
    assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"] = scene_ids

    with pytest.raises(ValueError, match="two distinct acquisition records"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="c" * 64,
            evidence_root=ROOT,
        )


def test_challenge_view_rejects_scene_pair_that_disagrees_with_checksummed_measurement():
    assessment = _t163_assessment()
    scene_ids = assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"]
    assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"] = list(reversed(scene_ids))

    with pytest.raises(ValueError, match="does not match its linked measurement record"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="f" * 64,
            evidence_root=ROOT,
        )


def test_challenge_view_rejects_measurement_summary_that_does_not_reproduce():
    assessment = _t163_assessment()
    assessment["observations"]["sar_diagnostic_measurement"]["median_db"] += 0.25

    with pytest.raises(ValueError, match="median_db does not reproduce"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="9" * 64,
            evidence_root=ROOT,
        )


def test_iraq_challenge_stops_at_provider_qa_hold_without_change_result():
    review_path = ROOT / "data/cases/iraq-2026-nisar-diagnostic/case-review.json"
    review_bytes = review_path.read_bytes()
    review = json.loads(review_bytes)
    preview_bytes = (ROOT / review["diagnostic_single_observation_preview"]["record_path"]).read_bytes()
    report = build_qa_held_observation_challenge(
        review,
        review_sha256=sha256(review_bytes).hexdigest(),
        preview_record=json.loads(preview_bytes),
        preview_sha256=sha256(preview_bytes).hexdigest(),
    )

    assert report["status"] == "QA_HELD_NO_CHANGE_FINDING"
    assert report["finding"] is None
    assert report["challenge_result"]["change_conclusion"] is None
    assert report["challenge_result"]["change_computation_permitted"] is False
    assert [item["provider_qa_state"] for item in report["candidate_pair"]["products"]] == ["FAIL", "FAIL"]
    assert report["observation"]["scientific_disposition"] == "QA_HELD_DIAGNOSTIC_PREVIEW"
    before, after = report["candidate_pair"]["products"]
    assert before["qa_summary_uri"].endswith(f"{before['scene_id']}_QA_SUMMARY.csv")
    assert after["qa_summary_uri"].endswith(f"{after['scene_id']}_QA_SUMMARY.csv")
    assert before["qa_summary_uri"] != after["qa_summary_uri"]
    assert before["qa_summary_sha256"] == after["qa_summary_sha256"]
    assert before["qa_summary_size_bytes"] is after["qa_summary_size_bytes"] is None
    assert before["qa_report_uri"].endswith(f"{before['scene_id']}_QA_REPORT.pdf")
    assert after["qa_report_uri"].endswith(f"{after['scene_id']}_QA_REPORT.pdf")
    assert before["qa_report_sha256"] != after["qa_report_sha256"]


def test_iraq_challenge_rejects_noncanonical_product_qa_links():
    review = json.loads((ROOT / "data/cases/iraq-2026-nisar-diagnostic/case-review.json").read_text())
    review["products"][0]["qa_summary"]["artifact_uri"] = "https://example.invalid/summary.csv"
    preview_path = ROOT / review["diagnostic_single_observation_preview"]["record_path"]
    preview_bytes = preview_path.read_bytes()

    with pytest.raises(ValueError, match="QA summary URI does not identify its ASF product"):
        build_qa_held_observation_challenge(
            review,
            review_sha256="d" * 64,
            preview_record=json.loads(preview_bytes),
            preview_sha256=sha256(preview_bytes).hexdigest(),
        )


def test_iraq_challenge_rejects_preview_that_disagrees_with_provider_qa_record():
    review = json.loads((ROOT / "data/cases/iraq-2026-nisar-diagnostic/case-review.json").read_text())
    preview_path = ROOT / review["diagnostic_single_observation_preview"]["record_path"]
    preview = json.loads(preview_path.read_text())
    preview["source"]["provider_qa_status"] = "PASS"

    with pytest.raises(ValueError, match="provider QA hold"):
        build_qa_held_observation_challenge(
            review,
            review_sha256="d" * 64,
            preview_record=preview,
            preview_sha256="e" * 64,
        )
