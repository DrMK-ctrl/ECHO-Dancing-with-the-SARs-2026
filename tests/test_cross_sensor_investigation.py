import json

import pytest

from tools.research.build_cross_sensor_investigation import AssessmentError, build_assessment


def _source_records(tmp_path):
    bounds = [-51.24, -30.04, -51.23, -30.03]
    pair = {
        "record_type": "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS",
        "status": "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON",
        "grid": {"window": {"bounds_wgs84": bounds}, "crs": "EPSG:32722"},
        "measurement": {
            "quantity": "signed_gamma0_log_ratio_db",
            "equation": "10 * log10(after / before)",
            "polarization": "VV",
            "units": "dB",
            "values_db": [[-2.0, 1.0, 99.0]],
            "valid_mask": [[True, True, False]],
            "common_clear_mask": [[True, True, True]],
            "measured_pixel_count": 2,
            "common_clear_pixel_count": 2,
            "aoi_pixel_count": 3,
        },
        "source_products": {
            "before": {"scene_id": "before", "acquisition_start_utc": "2024-05-11T08:49:47Z"},
            "after": {"scene_id": "after", "acquisition_start_utc": "2024-06-04T08:49:46Z"},
        },
        "provider_qa": {"status": "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"},
    }
    optical = {
        "record_type": "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON",
        "status": "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION",
        "aoi": {"bounds_west_south_east_north": bounds},
        "source_products": {
            "before": {"granule_id": "optical-before", "acquisition_time_utc": "2024-05-08T00:00:00Z"},
            "after": {"granule_id": "optical-after", "acquisition_time_utc": "2024-06-02T00:00:00Z"},
        },
        "transitions": {
            "WTR": {"common_valid_pixel_count": 2, "water_class_pixels_before_on_common_valid": 2, "water_class_pixels_after_on_common_valid": 1},
            "WTR-2": {"common_valid_pixel_count": 3, "water_class_pixels_before_on_common_valid": 2, "water_class_pixels_after_on_common_valid": 1},
        },
        "wtr2_confidence_quality_overlap": {
            "before": {"wtr2_water_pixels_with_conf_cloud_or_snow_flag": 1},
            "after": {"wtr2_water_pixels_with_conf_cloud_or_snow_flag": 0},
        },
        "temporal_relationship": {
            "optical_before_minus_rtc_before_days": -3.0,
            "optical_after_minus_rtc_after_days": -2.0,
        },
    }
    pair_path = tmp_path / "sar.json"
    optical_path = tmp_path / "optical.json"
    pair_path.write_text(json.dumps(pair), encoding="utf-8")
    optical_path.write_text(json.dumps(optical), encoding="utf-8")
    return pair_path, optical_path, pair, optical


def test_assessment_summarizes_only_valid_measurements_and_keeps_cause_unresolved(tmp_path):
    pair_path, optical_path, _, _ = _source_records(tmp_path)

    result = build_assessment(pair_path, optical_path)

    assert result["status"] == "CAUSAL_INTERPRETATION_UNRESOLVED"
    assert result["observations"]["sar_diagnostic_measurement"]["mean_db"] == pytest.approx(-0.5)
    assert result["observations"]["sar_diagnostic_measurement"]["common_clear_pixel_count"] == 2
    assert result["hypotheses"][0]["state"] == "SUPPORTED_WITHIN_SCOPE"
    assert result["hypotheses"][1]["state"] == "UNRESOLVED"
    assert result["hypotheses"][2]["state"] == "NOT_EVALUATED"
    assert result["hypotheses"][1]["evidence_assessments"][0]["relationship"] == "DOES_NOT_DISTINGUISH"
    assert result["hypotheses"][1]["evidence_assessments"][1]["relationship"] == "LIMITS_INTERPRETATION"
    water_hypothesis = result["hypotheses"][1]
    assert water_hypothesis["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert "documented common-support pixel-wise cross-sensor test" in water_hypothesis["testability_reason"].lower()
    assert "-3.00" in water_hypothesis["evidence_assessments"][1]["rationale"]
    assert water_hypothesis["expected_observation"]
    assert water_hypothesis["would_weaken_if"]
    assert water_hypothesis["required_evidence"]
    assert result["hypotheses"][2]["testability_state"] == "NOT_TESTED"
    hypothesis_ids = {item["id"] for item in result["hypotheses"]}
    assert len(result["follow_up_evidence"]) == 3
    assert all(set(item["target_hypothesis_ids"]) <= hypothesis_ids for item in result["follow_up_evidence"])
    assert result["follow_up_evidence"][0]["availability_state"] == "PROVIDER_RESPONSE_REQUIRED"
    assert result["follow_up_evidence"][1]["availability_state"] == "NOT_SEARCHED"
    assert result["assessment"]["nisar_measurement_present"] is False
    assert result["evidence_artifacts"][0]["sha256"]
    assert result["evidence_artifacts"][1]["sha256"]
    assert "-3.00 and -2.00 days" in result["follow_up_evidence"][1]["priority_reason"]


def test_assessment_rejects_different_geographic_areas(tmp_path):
    pair_path, optical_path, _, optical = _source_records(tmp_path)
    optical["aoi"]["bounds_west_south_east_north"][0] += 0.01
    optical_path.write_text(json.dumps(optical), encoding="utf-8")

    with pytest.raises(AssessmentError, match="same WGS84 AOI"):
        build_assessment(pair_path, optical_path)


def test_assessment_rejects_non_diagnostic_or_qa_relabelled_sar_record(tmp_path):
    pair_path, optical_path, pair, _ = _source_records(tmp_path)
    pair["status"] = "VALIDATED"
    pair_path.write_text(json.dumps(pair), encoding="utf-8")

    with pytest.raises(AssessmentError, match="not the expected diagnostic"):
        build_assessment(pair_path, optical_path)


def test_assessment_rejects_mask_and_measurement_count_mismatch(tmp_path):
    pair_path, optical_path, pair, _ = _source_records(tmp_path)
    pair["measurement"]["measured_pixel_count"] = 1
    pair_path.write_text(json.dumps(pair), encoding="utf-8")

    with pytest.raises(AssessmentError, match="count does not match"):
        build_assessment(pair_path, optical_path)


def test_assessment_links_a_catalog_selected_optical_pair_with_quality_limits(tmp_path):
    pair_path, optical_path, _, optical = _source_records(tmp_path)
    bounds = optical["aoi"]["bounds_west_south_east_north"]
    nearer = {
        **optical,
        "source_products": {
            "before": {"granule_id": "near-before", "acquisition_time_utc": "2024-05-13T13:30:50Z"},
            "after": {"granule_id": "near-after", "acquisition_time_utc": "2024-06-02T13:30:52Z"},
        },
        "transitions": {
            "WTR": {"common_valid_pixel_count": 0},
            "WTR-2": {
                "water_class_pixels_before_on_common_valid": 3,
                "water_class_pixels_after_on_common_valid": 1,
            },
        },
        "wtr2_confidence_quality_overlap": {
            "before": {"wtr2_water_pixels_with_conf_cloud_or_snow_flag": 3},
            "after": {"wtr2_water_pixels_with_conf_cloud_or_snow_flag": 0},
        },
        "temporal_relationship": {
            "optical_before_minus_rtc_before_days": 2.19,
            "optical_after_minus_rtc_after_days": -1.81,
        },
    }
    nearer_path = tmp_path / "nearer.json"
    nearer_path.write_text(json.dumps(nearer), encoding="utf-8")
    screen = {
        "record_type": "ECHO_DSWX_HLS_TEMPORAL_CONTEXT_CATALOG_SCREEN",
        "status": "METADATA_ONLY_NO_PIXEL_QA",
        "bounds_wgs84": bounds,
        "query_results": [
            {"reference_label": "before", "nearest_candidate": {"granule_id": "near-before"}},
            {"reference_label": "after", "nearest_candidate": {"granule_id": "near-after"}},
        ],
    }
    screen_path = tmp_path / "screen.json"
    screen_path.write_text(json.dumps(screen), encoding="utf-8")

    result = build_assessment(pair_path, optical_path, nearer_path, screen_path)

    assert result["observations"]["nearer_optical_quality_context"]["wtr_common_valid_count"] == 0
    assert result["hypotheses"][1]["state"] == "UNRESOLVED"
    assert result["hypotheses"][1]["evidence_assessments"][-1]["relationship"] == "LIMITS_INTERPRETATION"
    assert "zero common valid AOI pixels" in result["hypotheses"][1]["testability_reason"]
    follow_up = result["follow_up_evidence"][1]
    assert follow_up["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert set(follow_up["evidence_refs"]) == {
        "NASA-CMR-DSWX-FOLLOWUP-SCREEN",
        "NASA-OPERA-DSWX-NEARER-CONTEXT",
    }


def test_assessment_records_a_temporal_catalog_screen_without_claiming_pixel_validation(tmp_path):
    pair_path, optical_path, _, optical = _source_records(tmp_path)
    screen = {
        "record_type": "ECHO_DSWX_HLS_TEMPORAL_CONTEXT_CATALOG_SCREEN",
        "status": "METADATA_ONLY_NO_PIXEL_QA",
        "bounds_wgs84": optical["aoi"]["bounds_west_south_east_north"],
        "unique_candidate_count": 12,
        "query_results": [
            {"reference_label": "before", "nearest_candidate": {"granule_id": "before-nearest"}},
            {"reference_label": "after", "nearest_candidate": {"granule_id": "after-nearest"}},
        ],
    }
    screen_path = tmp_path / "screen.json"
    screen_path.write_text(json.dumps(screen), encoding="utf-8")

    result = build_assessment(pair_path, optical_path, catalog_screen_path=screen_path)

    follow_up = result["follow_up_evidence"][1]
    assert follow_up["availability_state"] == "CATALOG_SCREENED_CONTEXT_RETRIEVED"
    assert "12 candidates" in follow_up["priority_reason"]
    assert "Nearest before: before-nearest" in follow_up["priority_reason"]
    assert set(follow_up["evidence_refs"]) == {"NASA-CMR-DSWX-TEMPORAL-SCREEN", "NASA-OPERA-DSWX-HLS"}
    assert result["hypotheses"][1]["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"


def test_assessment_rejects_nearer_products_that_are_not_the_screened_nearest(tmp_path):
    pair_path, optical_path, _, optical = _source_records(tmp_path)
    nearer = json.loads(json.dumps(optical))
    nearer["source_products"]["before"]["granule_id"] = "not-nearest"
    nearer_path = tmp_path / "nearer.json"
    nearer_path.write_text(json.dumps(nearer), encoding="utf-8")
    screen = {
        "record_type": "ECHO_DSWX_HLS_TEMPORAL_CONTEXT_CATALOG_SCREEN",
        "status": "METADATA_ONLY_NO_PIXEL_QA",
        "bounds_wgs84": optical["aoi"]["bounds_west_south_east_north"],
        "query_results": [
            {"reference_label": "before", "nearest_candidate": {"granule_id": "closest-before"}},
            {"reference_label": "after", "nearest_candidate": {"granule_id": "optical-after"}},
        ],
    }
    screen_path = tmp_path / "screen.json"
    screen_path.write_text(json.dumps(screen), encoding="utf-8")

    with pytest.raises(AssessmentError, match="do not match the nearest CMR candidates"):
        build_assessment(pair_path, optical_path, nearer_path, screen_path)
