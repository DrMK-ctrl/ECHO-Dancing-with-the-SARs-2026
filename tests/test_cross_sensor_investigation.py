import json
from hashlib import sha256
from pathlib import Path

import pytest

from tools.research.build_cross_sensor_investigation import AssessmentError, build_assessment
from echo.hls_candidate_screen import validate_hls_candidate_screen
from echo.soil_moisture_sources import (
    validate_ecostress_availability_screen,
    validate_ismn_station_screen,
)


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


def _guaiba_context_record(case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024"):
    return {
        "record_type": "ECHO_ANA_GUAIBA_FLOOD_STAGE_CONTEXT",
        "schema_version": 1,
        "status": "OFFICIAL_NARRATIVE_CONTEXT_NOT_PRIMARY_STATION_MEASUREMENTS",
        "case_id": case_id,
        "source": {
            "provider": "Agência Nacional de Águas e Saneamento Básico (ANA)",
            "url": "https://conjuntura2025.ana.gov.br/agua-e-clima.html",
        },
        "reported_context": {
            "station_code": "87444000",
            "station_name": "Usina do Gasômetro (CHEIA 2024)",
            "above_flood_stage": True,
            "period_local_dates": {"start_date": "2024-05-02", "end_date": "2024-06-01"},
            "reported_duration_days": 30,
            "timestamped_readings_retrieved": False,
        },
        "interpretation_limits": [
            "This official narrative is not the primary timestamped gauge series.",
            "It is not a measurement of water extent in the SAR AOI.",
        ],
    }


def _smap_screen_record(tmp_path, bounds):
    project = tmp_path
    asset_dir = project / "data" / "research" / "source-artifacts"
    asset_dir.mkdir(parents=True)
    observations = []
    for label in ("before", "after"):
        asset = asset_dir / f"{label}.nc4"
        asset.write_bytes(f"bounded {label} subset".encode())
        observations.append({
            "granule_id": f"granule-{label}",
            "grid_shape": [1, 1],
            "grid_identity_sha256": "a" * 64,
            "quality_eligible_flat_indices": [],
            "soil_moisture": {"quality_eligible_cell_count": 0},
            "quality_flags": {
                "retrieval_flag_zero_good_cell_count": 0,
                "retrieval_quality_compromised_bit_0_cell_count": 1,
                "disaggregated_brightness_temperature_bad_bit_6_cell_count": 1,
            },
            "asset": {
                "relative_path": str(asset.relative_to(project)),
                "sha256": sha256(asset.read_bytes()).hexdigest(),
            },
        })
    record = {
        "record_type": "ECHO_SMAP_SENTINEL_SOIL_MOISTURE_CANDIDATE_SCREEN",
        "status": "CANDIDATE_RETRIEVED_QUALITY_LIMITED_NOT_USABLE_FOR_CAUSAL_TEST",
        "case_id": "rio-grande-do-sul-cross-sensor-diagnostic-2024",
        "source": {
            "provider": "NASA NSIDC DAAC",
            "product": "SMAP/Sentinel-1 L2 3 km soil moisture",
            "short_name": "SPL2SMAP_S",
            "version": "003",
            "doi": "10.5067/ASB0EQO2LYJV",
        },
        "query": {"bbox_west_south_east_north": bounds, "same_grid_before_after": True},
        "observations": observations,
        "comparison": {"paired_quality_eligible_cells": 0},
    }
    screen_path = project / "data" / "research" / "screen.json"
    screen_path.write_text(json.dumps(record), encoding="utf-8")
    return screen_path, observations[0]["asset"]["relative_path"]


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
    hypothesis_ids = {item["id"] for item in result["hypotheses"]}
    assert len(result["follow_up_evidence"]) == 5
    assert {item["id"] for item in result["hypotheses"]} >= {
        "H3_SOIL_MOISTURE_CHANGE",
        "H4_VEGETATION_STATE_CHANGE",
        "H5_ACQUISITION_CONDITIONS_EFFECT",
        "H6_SAR_PRODUCT_QUALITY_EFFECT",
    }
    assert all(set(item["target_hypothesis_ids"]) <= hypothesis_ids for item in result["follow_up_evidence"])
    assert result["follow_up_evidence"][0]["availability_state"] == "PROVIDER_RESPONSE_REQUIRED"
    assert result["follow_up_evidence"][1]["availability_state"] == "NOT_SEARCHED"
    assert result["assessment"]["nisar_measurement_present"] is False
    assert result["evidence_artifacts"][0]["sha256"]
    assert result["evidence_artifacts"][1]["sha256"]
    assert "-3.00 and -2.00 days" in result["follow_up_evidence"][1]["priority_reason"]


def test_real_t024_temporal_series_and_hls_vegetation_are_nondistinguishing():
    root = Path(__file__).parents[1]
    result = build_assessment(
        root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json",
        root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json",
        nearer_optical_path=root / "data/research/dswx-hls-nearer-rtc-context-2026-11-07.json",
        catalog_screen_path=root / "data/research/dswx-hls-followup-screen-2026-11-07.json",
        acquisition_conditions_path=root / "data/research/opera-rtc-acquisition-conditions-T024-050661-2026-11-08.json",
        sar_temporal_series_path=root / "data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json",
        gpm_before_path=root / "data/research/gpm-imerg-context-T024-050661-before-2024-05-11.json",
        gpm_after_path=root / "data/research/gpm-imerg-context-T024-050661-before-2024-06-04.json",
        gpm_intervening_path=root / "data/research/gpm-imerg-intervening-T024-050661-2024-05-12-05-27.json",
        gpm_interacquisition_path=root / "data/research/gpm-imerg-interacquisition-T024-050661-2024-05-11-06-04.json",
        smap_l4_context_path=root / "data/research/smap-l4-regional-context-T024-050661-2026-11-08.json",
        hls_vegetation_path=root / "data/research/hls-l30-vegetation-T024-050661-2026-11-09.json",
        hls_association_path=root / "data/research/hls-l30-ndvi-sar-association-T024-050661-2026-11-09.json",
    )

    series = result["observations"]["sar_temporal_series"]
    assert series["common_support_count"] == 1034
    assert result["schema_version"] == 3
    assert series["temporal_direction_screen"]["pixel_counts"]["direction_reversal"] == 650
    assert series["temporal_direction_screen"]["interval_days"] == pytest.approx([24, 384], abs=0.001)
    assert series["shares_source_observations_with"] == ["SAR-RTC-S1-PAIR"]
    artifact = next(item for item in result["evidence_artifacts"] if item["evidence_id"] == "NASA-OPERA-RTC-S1-TEMPORAL-SERIES")
    assert artifact["lineage"]["shares_source_observations_with"] == ["SAR-RTC-S1-PAIR"]
    assert artifact["lineage"]["derived_from_evidence_ids"] == []

    vegetation = result["observations"]["hls_l30_vegetation_context"]
    assert vegetation["common_clear_land_aoi_fraction"] == pytest.approx(0.23003472)
    assert vegetation["association_at_75_percent_common_support"]["sar_cells"] == 218
    assert vegetation["association_at_75_percent_common_support"]["descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db"] == pytest.approx(-0.2717353)
    assert [item["sar_cells"] for item in vegetation["association_coverage_sensitivity"]] == [312, 265, 218]
    assert [item["minimum_common_clear_land_ndvi_area_fraction"] for item in vegetation["association_coverage_sensitivity"]] == [0.25, 0.5, 0.75]
    h4 = next(item for item in result["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    assert h4["state"] == "UNRESOLVED"
    assert h4["testability_state"] == "DESCRIPTIVE_ASSOCIATION_ONLY"
    assert h4["evidence_assessments"][0]["relationship"] == "DOES_NOT_DISTINGUISH"
    vegetation_follow_up = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F8_VEGETATION_STATE_SCREEN")
    assert vegetation_follow_up["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert vegetation_follow_up["evidence_refs"] == [
        "NASA-HLS-L30-VEGETATION-SCREEN", "NASA-HLS-L30-NDVI-SAR-ASSOCIATION"
    ]

    rainfall = result["observations"]["gpm_precipitation_context"]["interacquisition"]
    assert rainfall["complete_days"] == 23
    assert rainfall["complete_day_sum_mm"] == pytest.approx(181.385, abs=0.001)
    assert rainfall["peak_date_utc"] == "2024-05-23"
    rainfall_artifact = next(
        item for item in result["evidence_artifacts"]
        if item["evidence_id"] == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"
    )
    assert rainfall_artifact["sha256"]

    smap_l4 = result["observations"]["smap_l4_regional_soil_moisture_context"]
    assert smap_l4["before_granule"].startswith("SMAP_L4_SM_aup_20240511T090000")
    assert smap_l4["after_granule"].startswith("SMAP_L4_SM_aup_20240604T090000")
    assert smap_l4["nearest_cell_center_distance_from_aoi_center_km"] == pytest.approx(2.7035, abs=0.001)
    assert smap_l4["after_minus_before_model_analysis_m3_m3"] == pytest.approx(0.003538, abs=1e-6)
    smap_l4_artifact = next(
        item for item in result["evidence_artifacts"]
        if item["evidence_id"] == "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN"
    )
    assert smap_l4_artifact["role"] == "NASA_MODEL_ASSIMILATED_REGIONAL_SOIL_MOISTURE_CONTEXT"
    assert smap_l4_artifact["lineage"]["derived_from_evidence_ids"] == ["SAR-RTC-S1-PAIR"]
    assert smap_l4_artifact["sha256"]

    h3 = next(item for item in result["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
    smap_l4_relation = next(
        item for item in h3["evidence_assessments"]
        if item["evidence_id"] == "NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN"
    )
    assert h3["state"] == "UNRESOLVED"
    assert h3["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert smap_l4_relation["relationship"] == "DOES_NOT_DISTINGUISH"
    soil_moisture_search = next(
        item for item in result["follow_up_evidence"]
        if item["follow_up_id"] == "F6_INDEPENDENT_SOIL_MOISTURE_SEARCH"
    )
    assert soil_moisture_search["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    assert soil_moisture_search["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert soil_moisture_search["evidence_refs"] == ["NASA-SMAP-L4-REGIONAL-CONTEXT-SCREEN"]
    assert soil_moisture_search["test_design"]["hypothesis_under_test_id"] == "H3_SOIL_MOISTURE_CHANGE"

    water = next(item for item in result["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    relation = next(item for item in water["evidence_assessments"] if item["evidence_id"] == "NASA-OPERA-RTC-S1-TEMPORAL-SERIES")
    assert relation["relationship"] == "DOES_NOT_DISTINGUISH"
    rainfall_relation = next(
        item for item in water["evidence_assessments"]
        if item["evidence_id"] == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"
    )
    assert rainfall_relation["relationship"] == "DOES_NOT_DISTINGUISH"
    assert water["state"] == "UNRESOLVED"
    assert result["status"] == "CAUSAL_INTERPRETATION_UNRESOLVED"
    assert "shares the primary pair's first two scenes" in result["assessment"]["summary"]
    assert "remains diagnostic" in result["assessment"]["summary"]


def test_t024_hls_association_rejects_changed_cutoff_metric(tmp_path):
    root = Path(__file__).parents[1]
    association = json.loads(
        (root / "data/research/hls-l30-ndvi-sar-association-T024-050661-2026-11-09.json").read_text()
    )
    association["coverage_sensitivity"][0]["descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db"] = 0.99
    altered_path = tmp_path / "altered-hls-association.json"
    altered_path.write_text(json.dumps(association), encoding="utf-8")
    with pytest.raises(AssessmentError, match="does not reproduce from its linked source observations"):
        build_assessment(
            root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json",
            root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json",
            case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024",
            hls_vegetation_path=root / "data/research/hls-l30-vegetation-T024-050661-2026-11-09.json",
            hls_association_path=altered_path,
        )


def test_official_gauge_narrative_is_linked_as_non_discriminating_context(tmp_path):
    pair_path, optical_path, pair, _ = _source_records(tmp_path)
    pair["source_products"]["before"]["acquisition_start_utc"] = "2024-05-08T22:07:19Z"
    pair["source_products"]["after"]["acquisition_start_utc"] = "2024-06-01T22:07:19Z"
    pair_path.write_text(json.dumps(pair), encoding="utf-8")
    context_path = tmp_path / "ana-guaiba-context.json"
    context_path.write_text(json.dumps(_guaiba_context_record()), encoding="utf-8")

    result = build_assessment(pair_path, optical_path, guaiba_context_path=context_path)

    context = result["observations"]["official_hydrologic_event_context"]
    assert context["station_code"] == "87444000"
    assert context["timestamped_readings_retrieved"] is False
    assert "not a primary gauge series" in context["interpretation_role"]
    h2 = next(item for item in result["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    relation = next(item for item in h2["evidence_assessments"] if item["evidence_id"] == "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY")
    assert relation["relationship"] == "DOES_NOT_DISTINGUISH"
    assert h2["state"] == "UNRESOLVED"
    artifact = next(item for item in result["evidence_artifacts"] if item["evidence_id"] == "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY")
    assert artifact["role"] == "OFFICIAL_HYDROLOGIC_EVENT_CONTEXT"
    assert artifact["sha256"] == sha256(context_path.read_bytes()).hexdigest()


def test_t163_primary_gauge_followup_exposes_authorization_requirement_without_promoting_context():
    root = Path(__file__).parents[1]
    case_id = "rio-grande-do-sul-t163-349925-diagnostic-2024"
    result = build_assessment(
        root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json",
        root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json",
        case_id=case_id,
        guaiba_context_path=root / "data/research/ana-guaiba-official-flood-stage-context-2026-11-08.json",
        guaiba_access_screen_path=root / "data/research/ana-guaiba-primary-series-access-screen-2026-11-09.json",
    )

    followup = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F11_GUAIBA_PRIMARY_SERIES")
    evidence_ids = {item["evidence_id"] for item in result["evidence_artifacts"]}
    assert followup["availability_state"] == "ACCESS_REQUIRED"
    assert followup["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert set(followup["evidence_refs"]) <= evidence_ids
    assert followup["test_design"]["hypothesis_under_test_id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE"
    assert "cannot establish water extent" in followup["possible_interpretation"]
    h2 = next(item for item in result["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    assert h2["state"] == "UNRESOLVED"
    assert result["observations"]["official_hydrologic_event_context"]["timestamped_readings_retrieved"] is False


def test_t163_gauge_access_screen_rejects_claimed_auth_or_retrieval():
    root = Path(__file__).parents[1]
    access = json.loads((root / "data/research/ana-guaiba-primary-series-access-screen-2026-11-09.json").read_text())
    access["access_review"]["credentials_or_tokens_collected"] = True
    altered = root / "data/research/.tmp-ana-access-screen-test.json"
    try:
        altered.write_text(json.dumps(access), encoding="utf-8")
        with pytest.raises(AssessmentError, match="access screen identity or limits are invalid"):
            build_assessment(
                root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json",
                root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json",
                case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
                guaiba_context_path=root / "data/research/ana-guaiba-official-flood-stage-context-2026-11-08.json",
                guaiba_access_screen_path=altered,
            )
    finally:
        altered.unlink(missing_ok=True)


def test_official_gauge_context_must_cover_both_sar_dates(tmp_path):
    pair_path, optical_path, pair, _ = _source_records(tmp_path)
    pair["source_products"]["before"]["acquisition_start_utc"] = "2024-05-08T22:07:19Z"
    pair["source_products"]["after"]["acquisition_start_utc"] = "2024-06-02T22:07:19Z"
    pair_path.write_text(json.dumps(pair), encoding="utf-8")
    context_path = tmp_path / "ana-guaiba-context.json"
    context_path.write_text(json.dumps(_guaiba_context_record()), encoding="utf-8")

    with pytest.raises(AssessmentError, match="does not cover both SAR acquisition dates"):
        build_assessment(pair_path, optical_path, guaiba_context_path=context_path)


def test_official_gauge_context_rejects_claims_as_primary_measurements(tmp_path):
    pair_path, optical_path, pair, _ = _source_records(tmp_path)
    pair["source_products"]["before"]["acquisition_start_utc"] = "2024-05-08T22:07:19Z"
    pair["source_products"]["after"]["acquisition_start_utc"] = "2024-06-01T22:07:19Z"
    pair_path.write_text(json.dumps(pair), encoding="utf-8")
    context = _guaiba_context_record()
    context["reported_context"]["timestamped_readings_retrieved"] = True
    context_path = tmp_path / "ana-guaiba-context.json"
    context_path.write_text(json.dumps(context), encoding="utf-8")

    with pytest.raises(AssessmentError, match="narrative-only boundary is invalid"):
        build_assessment(pair_path, optical_path, guaiba_context_path=context_path)


def test_smap_screen_is_retained_as_quality_limitation_and_keeps_independent_search_open(tmp_path):
    pair_path, optical_path, pair, _ = _source_records(tmp_path)
    screen_path, _ = _smap_screen_record(tmp_path, pair["grid"]["window"]["bounds_wgs84"])

    result = build_assessment(pair_path, optical_path, smap_screen_path=screen_path)

    h3 = next(item for item in result["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
    assert h3["state"] == "UNRESOLVED"
    assert h3["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert h3["evidence_assessments"][0]["evidence_id"] == "NASA-SPL2SMAP-S-CANDIDATE-SCREEN"
    assert h3["evidence_assessments"][0]["relationship"] == "LIMITS_INTERPRETATION"
    assert result["observations"]["smap_sentinel_soil_moisture_screen"]["paired_quality_eligible_cells"] == 0
    failed_screen_followup = next(
        item for item in result["follow_up_evidence"]
        if item["follow_up_id"] == "F3_SOIL_MOISTURE_SEARCH"
    )
    assert failed_screen_followup["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert failed_screen_followup["target_hypothesis_ids"] == ["H3_SOIL_MOISTURE_CHANGE"]


def test_smap_screen_source_subset_checksum_is_required(tmp_path):
    pair_path, optical_path, pair, _ = _source_records(tmp_path)
    screen_path, asset_relative = _smap_screen_record(
        tmp_path, pair["grid"]["window"]["bounds_wgs84"]
    )
    (tmp_path / asset_relative).write_bytes(b"changed source subset")

    with pytest.raises(AssessmentError, match="checksum or size validation failed"):
        build_assessment(pair_path, optical_path, smap_screen_path=screen_path)


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


def test_assessment_links_exact_spatial_overlay_but_keeps_water_cause_unresolved(tmp_path):
    pair_path, optical_path, pair, optical = _source_records(tmp_path)
    spatial = {
        "record_type": "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC",
        "status": "DIAGNOSTIC_SPATIAL_ASSOCIATION",
        "sources": {
            "sar_pair_record_sha256": sha256(pair_path.read_bytes()).hexdigest(),
            "optical_context_record_sha256": sha256(optical_path.read_bytes()).hexdigest(),
            "sar_scene_ids": [item["scene_id"] for item in pair["source_products"].values()],
            "optical_granule_ids": [item["granule_id"] for item in optical["source_products"].values()],
        },
        "summary": {
            "coverage_sensitivity": [{
                "minimum_common_valid_wtr_area_fraction": 0.75,
                "sar_cells": 738,
                "water_fraction_increased_by_more_than_0_05": 14,
                "water_fraction_decreased_by_more_than_0_05": 14,
                "water_fraction_changed_by_at_most_0_05": 710,
                "median_water_fraction_change": 0.0,
                "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db": -0.108,
            }],
        },
    }
    spatial_path = tmp_path / "spatial.json"
    spatial_path.write_text(json.dumps(spatial), encoding="utf-8")

    result = build_assessment(pair_path, optical_path, spatial_support_path=spatial_path)

    water = result["hypotheses"][1]
    assert result["observations"]["spatial_support_diagnostic"]["status"] == "DIAGNOSTIC_SPATIAL_ASSOCIATION"
    assert water["state"] == "UNRESOLVED"
    assert water["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert water["evidence_assessments"][-1]["relationship"] == "DOES_NOT_DISTINGUISH"
    assert result["evidence_artifacts"][2]["evidence_id"] == "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"
    assert result["follow_up_evidence"][1]["availability_state"] == "NOT_SEARCHED"
    assert result["follow_up_evidence"][2]["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert result["follow_up_evidence"][2]["evidence_refs"] == ["NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT"]
    assert "descriptive Pearson r was -0.108" in result["assessment"]["summary"]


def test_assessment_links_real_polarization_sensitivity_without_promoting_cause():
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
    optical = root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
    result = build_assessment(
        pair,
        optical,
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        spatial_support_path=root / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-2026-11-08.json",
        polarization_vh_pair_path=root / "data/research/opera-rtc-live-pair-T163-349925-IW2-VH-2024-11-08.json",
        polarization_vh_spatial_path=root / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VH-2026-11-08.json",
        polarization_sensitivity_path=root / "data/research/opera-rtc-polarization-sensitivity-T163-349925-2026-11-08.json",
    )
    water = next(item for item in result["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    ids = {item["evidence_id"] for item in result["evidence_artifacts"]}
    assert {
        "NASA-OPERA-RTC-S1-VH-PAIR",
        "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT",
        "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY",
    } <= ids
    assert water["state"] == "UNRESOLVED"
    assert water["evidence_assessments"][-1]["relationship"] == "DOES_NOT_DISTINGUISH"
    assert result["observations"]["polarization_sensitivity_diagnostic"]["summary"]["common_cells"] == 738
    artifacts = {item["evidence_id"]: item for item in result["evidence_artifacts"]}
    assert artifacts["NASA-OPERA-RTC-S1-VH-PAIR"]["lineage"]["shares_source_observations_with"] == [
        "SAR-RTC-S1-PAIR",
    ]
    assert artifacts["NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"]["lineage"]["derived_from_evidence_ids"] == [
        "SAR-RTC-S1-PAIR",
        "NASA-OPERA-RTC-S1-VH-PAIR",
        "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT",
        "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT",
    ]


def test_assessment_uses_gpm_as_traceable_context_without_resolving_surface_cause():
    root = Path(__file__).parents[1]
    result = build_assessment(
        root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json",
        root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json",
        catalog_screen_path=root / "data/research/dswx-hls-screen-T163-349925-2026-11-07.json",
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        spatial_support_path=root / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-2026-11-08.json",
        polarization_vh_pair_path=root / "data/research/opera-rtc-live-pair-T163-349925-IW2-VH-2024-11-08.json",
        polarization_vh_spatial_path=root / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VH-2026-11-08.json",
        polarization_sensitivity_path=root / "data/research/opera-rtc-polarization-sensitivity-T163-349925-2026-11-08.json",
        gpm_before_path=root / "data/research/gpm-imerg-context-T163-349925-before-2024-05-08.json",
        gpm_after_path=root / "data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json",
        gpm_intervening_path=root / "data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json",
        gpm_interacquisition_path=root / "data/research/gpm-imerg-interacquisition-T163-349925-2024-05-08-06-01.json",
        smap_screen_path=root / "data/research/smap-sentinel-soil-moisture-screen-T163-349925-2026-11-08.json",
        smap_radiometer_screen_path=root / "data/research/smap-radiometer-candidate-screen-T163-349925-2026-11-08.json",
    )
    h3 = next(item for item in result["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
    follow_up = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F5_SOIL_MOISTURE_CONTEXT")
    next_observation = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F6_SMAP_SOIL_MOISTURE_QUALITY_SCREEN")
    independent_search = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F7_INDEPENDENT_SOIL_MOISTURE_SEARCH")
    quality_prerequisite = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F1_RTC_QA_RESOLUTION")
    gpm = result["observations"]["gpm_precipitation_context"]
    ids = {item["evidence_id"] for item in result["evidence_artifacts"]}

    assert h3["state"] == "UNRESOLVED"
    assert h3["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert {item["relationship"] for item in h3["evidence_assessments"]} == {
        "DOES_NOT_DISTINGUISH",
        "LIMITS_INTERPRETATION",
    }
    assert gpm["before"]["complete_days"] == gpm["after"]["complete_days"] == 7
    assert gpm["before"]["complete_day_sum_mm"] == pytest.approx(219.87, abs=0.01)
    assert gpm["after"]["complete_day_sum_mm"] == pytest.approx(14.33, abs=0.01)
    assert gpm["interacquisition"]["complete_days"] == 23
    assert gpm["interacquisition"]["complete_day_sum_mm"] == pytest.approx(214.93, abs=0.01)
    assert gpm["interacquisition"]["peak_date_utc"] == "2024-05-23"
    radiometer = result["observations"]["smap_radiometer_spatial_suitability_screen"]
    assert radiometer["independent_of_sentinel1"] is True
    assert radiometer["pixel_data_retrieved"] is False
    assert radiometer["grid_posting_km"] == 9
    assert radiometer["native_radiometer_footprint_km_approx"] == 36
    assert follow_up["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert next_observation["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert quality_prerequisite["action_track"] == "QUALITY_PREREQUISITE"
    assert next_observation["action_track"] == "REVIEWED_RESULT"
    assert follow_up["action_track"] == "REVIEWED_RESULT"
    assert "soil-moisture" in next_observation["action"]
    assert independent_search["test_design"]["hypothesis_under_test_id"] == "H3_SOIL_MOISTURE_CHANGE"
    assert independent_search["test_design"]["does_not_test_hypothesis_ids"] == [
        "H1_OPTICAL_PRODUCT_CLASS_COUNTS_DECLINED",
        "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        "H4_VEGETATION_STATE_CHANGE",
        "H5_ACQUISITION_CONDITIONS_EFFECT",
        "H6_SAR_PRODUCT_QUALITY_EFFECT",
    ]
    assert len(independent_search["test_design"]["acceptance_gates"]) == 5
    assert {"NASA-GPM-IMERG-BEFORE-PRE-SAR", "NASA-GPM-IMERG-AFTER-PRE-SAR", "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"} <= ids
    assert any(item["evidence_id"] == "NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY" for item in h3["evidence_assessments"])
    assert any(item["evidence_id"] == "NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN" and item["relationship"] == "DOES_NOT_DISTINGUISH" for item in h3["evidence_assessments"])


def test_hls_land_satellite_association_is_traceable_and_does_not_resolve_driver():
    root = Path(__file__).parents[1]
    result = build_assessment(
        root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json",
        root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json",
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        hls_vegetation_path=root / "data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json",
        hls_association_path=root / "data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json",
    )
    hypothesis = next(item for item in result["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    artifacts = {item["evidence_id"]: item for item in result["evidence_artifacts"]}
    context = result["observations"]["hls_l30_vegetation_context"]

    assert result["schema_version"] == 3
    assert hypothesis["state"] == "UNRESOLVED"
    assert hypothesis["testability_state"] == "DESCRIPTIVE_ASSOCIATION_ONLY"
    assert hypothesis["evidence_assessments"][-1]["relationship"] == "DOES_NOT_DISTINGUISH"
    assert context["common_clear_land_aoi_fraction"] == pytest.approx(0.2300347)
    assert context["association_at_75_percent_common_support"]["sar_cells"] == 218
    assert [item["sar_cells"] for item in context["association_coverage_sensitivity"]] == [312, 265, 218]
    assert artifacts["NASA-HLS-L30-NDVI-SAR-ASSOCIATION"]["lineage"]["derived_from_evidence_ids"] == [
        "SAR-RTC-S1-PAIR",
        "NASA-HLS-L30-VEGETATION-SCREEN",
    ]


def test_hls_sentinel2_candidate_is_linked_but_remains_insufficient_to_test_vegetation():
    root = Path(__file__).parents[1]
    result = build_assessment(
        root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json",
        root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json",
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        hls_vegetation_path=root / "data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json",
        hls_association_path=root / "data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json",
        hls_s30_vegetation_path=root / "data/research/hls-s30-vegetation-screen-T163-349925-2026-11-08.json",
        hls_s30_association_path=root / "data/research/hls-s30-rtc-ndvi-association-T163-349925-2026-11-08.json",
        smap_screen_path=root / "data/research/smap-sentinel-soil-moisture-screen-T163-349925-2026-11-08.json",
        smap_radiometer_screen_path=root / "data/research/smap-radiometer-candidate-screen-T163-349925-2026-11-08.json",
    )
    h3 = next(item for item in result["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
    h4 = next(item for item in result["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    context = result["observations"]["hls_s30_vegetation_context"]
    artifacts = {item["evidence_id"]: item for item in result["evidence_artifacts"]}
    completed_screen = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F8_VEGETATION_STATE_SCREEN")
    next_search = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION")

    assert h3["state"] == "UNRESOLVED"
    assert h3["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert all(not item["evidence_id"].startswith("NASA-HLS-") for item in h3["evidence_assessments"])
    assert h4["testability_state"] == "DESCRIPTIVE_ASSOCIATION_ONLY"
    s30_relation = next(item for item in h4["evidence_assessments"] if item["evidence_id"] == "NASA-HLS-S30-NDVI-SAR-ASSOCIATION")
    assert s30_relation["relationship"] == "DOES_NOT_DISTINGUISH"
    assert context["common_clear_land_pixel_count"] == 25
    assert context["aoi_center_pixel_count"] == 1152
    assert context["common_clear_land_aoi_fraction"] == pytest.approx(25 / 1152)
    assert context["association_at_75_percent_common_support"]["sar_cells"] == 11
    assert [item["sar_cells"] for item in context["association_coverage_sensitivity"]] == [39, 25, 11]
    assert artifacts["NASA-HLS-S30-NDVI-SAR-ASSOCIATION"]["lineage"]["derived_from_evidence_ids"] == [
        "SAR-RTC-S1-PAIR",
        "NASA-HLS-S30-VEGETATION-SCREEN",
    ]
    assert completed_screen["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert completed_screen["evidence_refs"] == [
        "NASA-HLS-L30-VEGETATION-SCREEN",
        "NASA-HLS-L30-NDVI-SAR-ASSOCIATION",
        "NASA-HLS-S30-VEGETATION-SCREEN",
        "NASA-HLS-S30-NDVI-SAR-ASSOCIATION",
    ]
    assert next_search["availability_state"] == "NOT_SEARCHED"
    assert result["assessment"]["physical_cause"] == "UNRESOLVED"


def test_hls_association_rejects_mismatched_source_hash(tmp_path):
    root = Path(__file__).parents[1]
    hls_path = root / "data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json"
    association = json.loads((root / "data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json").read_text())
    association["sources"]["hls_vegetation_record_sha256"] = "0" * 64
    association_path = tmp_path / "association.json"
    association_path.write_text(json.dumps(association), encoding="utf-8")

    with pytest.raises(AssessmentError, match="source-record links"):
        build_assessment(
            root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json",
            root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json",
            case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
            hls_vegetation_path=hls_path,
            hls_association_path=association_path,
        )


def test_hls_s30_association_rejects_mismatched_source_hash(tmp_path):
    root = Path(__file__).parents[1]
    association = json.loads((root / "data/research/hls-s30-rtc-ndvi-association-T163-349925-2026-11-08.json").read_text())
    association["sources"]["hls_vegetation_record_sha256"] = "0" * 64
    association_path = tmp_path / "association.json"
    association_path.write_text(json.dumps(association), encoding="utf-8")

    with pytest.raises(AssessmentError, match="source-record links"):
        build_assessment(
            root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json",
            root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json",
            case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
            hls_s30_vegetation_path=root / "data/research/hls-s30-vegetation-screen-T163-349925-2026-11-08.json",
            hls_s30_association_path=association_path,
        )


def test_assessment_rejects_spatial_overlay_from_different_source_records(tmp_path):
    pair_path, optical_path, pair, optical = _source_records(tmp_path)
    spatial = {
        "record_type": "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC",
        "status": "DIAGNOSTIC_SPATIAL_ASSOCIATION",
        "sources": {
            "sar_pair_record_sha256": "0" * 64,
            "optical_context_record_sha256": sha256(optical_path.read_bytes()).hexdigest(),
            "sar_scene_ids": [item["scene_id"] for item in pair["source_products"].values()],
            "optical_granule_ids": [item["granule_id"] for item in optical["source_products"].values()],
        },
        "summary": {"coverage_sensitivity": [{"minimum_common_valid_wtr_area_fraction": 0.75}]},
    }
    spatial_path = tmp_path / "spatial.json"
    spatial_path.write_text(json.dumps(spatial), encoding="utf-8")

    with pytest.raises(AssessmentError, match="different source records"):
        build_assessment(pair_path, optical_path, spatial_support_path=spatial_path)


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


def test_t163_assessment_links_partial_soil_moisture_source_search():
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
    optical = root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
    result = build_assessment(
        pair,
        optical,
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        gpm_before_path=root / "data/research/gpm-imerg-context-T163-349925-before-2024-05-08.json",
        gpm_after_path=root / "data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json",
        gpm_intervening_path=root / "data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json",
        gpm_interacquisition_path=root / "data/research/gpm-imerg-interacquisition-T163-349925-2024-05-08-06-01.json",
        smap_screen_path=root / "data/research/smap-sentinel-soil-moisture-screen-T163-349925-2026-11-08.json",
        smap_radiometer_screen_path=root / "data/research/smap-radiometer-candidate-screen-T163-349925-2026-11-08.json",
        ecostress_sm_screen_path=root / "data/research/ecostress-soil-moisture-catalog-screen-T163-2026-11-08.json",
        ismn_station_screen_path=root / "data/research/ismn-station-coverage-screen-T163-2026-11-08.json",
    )

    follow_up = next(
        item for item in result["follow_up_evidence"]
        if item["follow_up_id"] == "F7_INDEPENDENT_SOIL_MOISTURE_SEARCH"
    )
    artifact_ids = {item["evidence_id"] for item in result["evidence_artifacts"]}
    assert follow_up["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    assert follow_up["action_track"] == "NEW_EVIDENCE_SEARCH"
    assert {
        "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN",
        "ISMN-SOIL-MOISTURE-STATION-COVERAGE",
    } <= set(follow_up["evidence_refs"])
    assert {
        "NASA-SPL2SMAP-S-CANDIDATE-SCREEN",
        "NASA-SMAP-SPL3SMP-E-RESOLUTION-SCREEN",
    } <= set(follow_up["evidence_refs"])
    assert set(follow_up["evidence_refs"]) <= artifact_ids
    assert result["hypotheses"][2]["state"] == "UNRESOLVED"
    assert result["hypotheses"][2]["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"


def test_t163_availability_screen_rejects_other_case_pair():
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
    optical = root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
    with pytest.raises(AssessmentError, match="different case"):
        build_assessment(
            pair,
            optical,
            case_id="another-case",
            ecostress_sm_screen_path=root / "data/research/ecostress-soil-moisture-catalog-screen-T163-2026-11-08.json",
        )


def test_t163_availability_screen_rejects_mismatched_acquisition_times(tmp_path):
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
    optical = root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
    screen = json.loads((root / "data/research/ecostress-soil-moisture-catalog-screen-T163-2026-11-08.json").read_text())
    screen["target"]["sar_acquisitions"][0] = "2024-05-09T22:07:19Z/2024-05-10T08:24:03Z"
    screen_path = tmp_path / "ecostress-screen.json"
    screen_path.write_text(json.dumps(screen), encoding="utf-8")

    with pytest.raises(AssessmentError, match="acquisition times do not match"):
        build_assessment(
            pair,
            optical,
            case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
            ecostress_sm_screen_path=screen_path,
        )


def test_t163_assessment_links_daily_mod09ga_quality_limited_screen():
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
    optical = root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
    record = root / "data/research/mod09ga-vegetation-candidate-T163-349925-2026-11-08.json"
    hls = root / "data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json"
    association = root / "data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json"
    result = build_assessment(
        pair,
        optical,
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        hls_vegetation_path=hls,
        hls_association_path=association,
        mod09ga_screen_path=record,
    )

    follow_up = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION")
    hypothesis = next(item for item in result["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    artifact_ids = {item["evidence_id"] for item in result["evidence_artifacts"]}
    assert follow_up["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN" in follow_up["evidence_refs"]
    assert "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN" in artifact_ids
    assert "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN" in hypothesis["evidence_refs"]
    assert any(item["evidence_id"] == "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN" for item in hypothesis["evidence_assessments"])
    assert result["observations"]["mod09ga_vegetation_candidate_screen"]["common_pixel_center_count"] == 6
    assert result["observations"]["mod09ga_vegetation_candidate_screen"]["common_strict_accepted_count"] == 0
    assert result["status"] == "CAUSAL_INTERPRETATION_UNRESOLVED"


def test_t163_assessment_rejects_mod09ga_screen_from_another_pair(tmp_path):
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
    optical = root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
    record = json.loads((root / "data/research/mod09ga-vegetation-candidate-T163-349925-2026-11-08.json").read_text())
    record["source"]["sar_scene_ids"][0] = "OTHER_SCENE"
    record_path = tmp_path / "mod09ga-other-pair.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(AssessmentError, match="MOD09GA candidate screen is not linked"):
        build_assessment(
            pair,
            optical,
            case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
            mod09ga_screen_path=record_path,
        )


def test_t024_lpdaac_mod09ga_screen_remains_quality_limited_and_linked():
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json"
    optical = root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json"
    record = root / "data/research/mod09ga-vegetation-candidate-T024-050661-2026-11-09.json"
    hls = root / "data/research/hls-l30-vegetation-T024-050661-2026-11-09.json"
    association = root / "data/research/hls-l30-ndvi-sar-association-T024-050661-2026-11-09.json"
    hls_candidate = root / "data/research/hls-l30-vegetation-T024-050661-2026-11-09-jun09.json"
    result = build_assessment(
        pair,
        optical,
        case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024",
        mod09ga_screen_path=record,
        hls_vegetation_path=hls,
        hls_association_path=association,
        hls_candidate_screen_path=hls_candidate,
    )

    evidence_id = "NASA-MOD09GA-VEGETATION-CANDIDATE-SCREEN"
    evidence = next(item for item in result["evidence_artifacts"] if item["evidence_id"] == evidence_id)
    hypothesis = next(item for item in result["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    follow_up = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION")
    summary = result["observations"]["mod09ga_vegetation_candidate_screen"]

    assert evidence["role"] == "NASA_DAILY_SURFACE_REFLECTANCE_QUALITY_LIMITED_SCREEN"
    assert summary["common_pixel_center_count"] == 6
    assert summary["common_strict_accepted_count"] == 0
    assert summary["land_water_class_codes"] == [2, 3]
    assert summary["cloud_state_codes"] == [1]
    assert hypothesis["state"] == "UNRESOLVED"
    assert evidence_id in hypothesis["evidence_refs"]
    assert evidence_id in follow_up["evidence_refs"]
    assert follow_up["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    assert result["status"] == "CAUSAL_INTERPRETATION_UNRESOLVED"


def test_t024_lpdaac_mod09ga_screen_rejects_broken_download_provenance(tmp_path):
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json"
    optical = root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json"
    record = json.loads((root / "data/research/mod09ga-vegetation-candidate-T024-050661-2026-11-09.json").read_text())
    record["retrieval_evidence"]["product_checksums"][0]["response_sha256"] = "not-a-sha256"
    record_path = tmp_path / "mod09ga-broken-download-provenance.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(AssessmentError, match="LP DAAC download provenance is incomplete"):
        build_assessment(
            pair,
            optical,
            case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024",
            mod09ga_screen_path=record_path,
        )


def test_t024_extended_hls_candidate_is_linked_as_nondirectional_limit():
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json"
    optical = root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json"
    screen = root / "data/research/hls-l30-vegetation-T024-050661-2026-11-09-jun09.json"
    result = build_assessment(
        pair,
        optical,
        case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024",
        hls_vegetation_path=root / "data/research/hls-l30-vegetation-T024-050661-2026-11-09.json",
        hls_association_path=root / "data/research/hls-l30-ndvi-sar-association-T024-050661-2026-11-09.json",
        hls_candidate_screen_path=screen,
    )
    followup = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION")
    h4 = next(item for item in result["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    assessment = next(item for item in h4["evidence_assessments"] if item["evidence_id"] == "NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN")
    assert result["schema_version"] == 4
    assert followup["availability_state"] == "SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE"
    assert "NASA-HLS-L30-EXTENDED-CANDIDATE-SCREEN" in followup["evidence_refs"]
    assert assessment["relationship"] == "LIMITS_INTERPRETATION"
    assert h4["state"] == "UNRESOLVED"
    assert result["observations"]["hls_l30_extended_candidate_screen"]["common_clear_land_ndvi_pixel_count"] == 0


def test_t024_soil_moisture_availability_screens_are_verified_and_keep_h3_open():
    root = Path(__file__).parents[1]
    pair = root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json"
    optical = root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json"
    case_id = "rio-grande-do-sul-cross-sensor-diagnostic-2024"
    ecostress_path = root / "data/research/ecostress-soil-moisture-catalog-screen-T024-050661-2026-11-09.json"
    ismn_path = root / "data/research/ismn-station-coverage-screen-T024-050661-2026-11-09.json"
    pair_record, optical_record = json.loads(pair.read_text()), json.loads(optical.read_text())
    ecostress = json.loads(ecostress_path.read_text())
    ismn = json.loads(ismn_path.read_text())
    ecostress_summary = validate_ecostress_availability_screen(
        ecostress, pair_record=pair_record, optical_record=optical_record, case_id=case_id, evidence_root=root
    )
    ismn_summary = validate_ismn_station_screen(
        ismn, pair_record=pair_record, optical_record=optical_record, case_id=case_id, evidence_root=root
    )
    result = build_assessment(
        pair, optical, case_id=case_id,
        ecostress_sm_screen_path=ecostress_path,
        ismn_station_screen_path=ismn_path,
    )
    followup = next(item for item in result["follow_up_evidence"] if item["target_hypothesis_ids"] == ["H3_SOIL_MOISTURE_CHANGE"])
    h3 = next(item for item in result["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
    artifact_ids = {item["evidence_id"] for item in result["evidence_artifacts"]}
    assert ecostress_summary["target_interval_cmr_hits"] == 0
    assert ecostress_summary["positive_control_cmr_hits"] == 377
    assert ismn_summary["station_count"] == 3347
    assert ismn_summary["soil_moisture_stations_within_100_km"] == 0
    assert followup["evidence_refs"] == [
        "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN",
        "ISMN-SOIL-MOISTURE-STATION-COVERAGE",
    ]
    assert set(followup["evidence_refs"]) <= artifact_ids
    assert h3["state"] == "NOT_EVALUATED"
    assert h3["testability_state"] == "NOT_TESTED"


def test_t024_soil_moisture_screen_rejects_changed_inventory_summary():
    root = Path(__file__).parents[1]
    pair = json.loads((root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json").read_text())
    optical = json.loads((root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json").read_text())
    record = json.loads((root / "data/research/ismn-station-coverage-screen-T024-050661-2026-11-09.json").read_text())
    record["inventory"]["station_count"] += 1
    with pytest.raises(ValueError, match="summary does not reproduce"):
        validate_ismn_station_screen(
            record,
            pair_record=pair,
            optical_record=optical,
            case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024",
            evidence_root=root,
        )


def test_t024_ecostress_screen_rejects_changed_retained_response_hash():
    root = Path(__file__).parents[1]
    pair = json.loads((root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json").read_text())
    optical = json.loads((root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json").read_text())
    record = json.loads((root / "data/research/ecostress-soil-moisture-catalog-screen-T024-050661-2026-11-09.json").read_text())
    record["catalog"]["queries"][0]["response_pages"][0]["response_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum or size does not match"):
        validate_ecostress_availability_screen(
            record,
            pair_record=pair,
            optical_record=optical,
            case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024",
            evidence_root=root,
        )
def test_t024_extended_hls_candidate_rejects_tampered_fmask_summary(tmp_path):
    root = Path(__file__).parents[1]
    screen = json.loads((root / "data/research/hls-l30-vegetation-T024-050661-2026-11-09-jun09.json").read_text())
    screen["observations"][1]["fmask_class_counts_in_aoi"] = {"194": 1151}
    screen_path = tmp_path / "tampered-hls-candidate.json"
    screen_path.write_text(json.dumps(screen), encoding="utf-8")
    pair = json.loads((root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json").read_text())
    optical = json.loads((root / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json").read_text())
    with pytest.raises(ValueError, match="Fmask counts do not reproduce"):
        validate_hls_candidate_screen(
            screen,
            pair_record=pair,
            case_id="rio-grande-do-sul-cross-sensor-diagnostic-2024",
            aoi_bounds=optical["aoi"]["bounds_west_south_east_north"],
            evidence_root=root,
        )
