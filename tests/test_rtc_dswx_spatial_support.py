import copy
import json
from pathlib import Path

import pytest
from pyproj import Transformer

from tools.research.evaluate_rtc_dswx_spatial_support import (
    SpatialSupportError,
    evaluate_spatial_support,
)


def _synthetic_records():
    forward = Transformer.from_crs("EPSG:32631", "EPSG:4326", always_xy=True)

    def ring(points):
        return [list(forward.transform(x, y)) for x, y in points]

    upper_left = [500000.0, 10.0]
    upper_right = [500010.0, 10.0]
    lower_right = [500010.0, 0.0]
    lower_left = [500000.0, 0.0]
    left_mid_top = [500005.0, 10.0]
    left_mid_bottom = [500005.0, 0.0]
    sar_corners = [
        [list(forward.transform(*upper_left)), list(forward.transform(*upper_right))],
        [list(forward.transform(*lower_left)), list(forward.transform(*lower_right))],
    ]
    grid = {
        "crs": "EPSG:32631",
        "transform": [10, 0, 500000, 0, -10, 10],
        "window_shape": [1, 1],
        "selected_pixel_center_count": 2,
    }
    bounds = [-1.0, -1.0, 1.0, 1.0]
    pair = {
        "record_type": "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS",
        "status": "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON",
        "provider_qa": {"status": "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"},
        "grid": {
            "crs": "EPSG:32631",
            "window": {"shape": [1, 1], "bounds_wgs84": bounds},
            "pixel_corners_wgs84": sar_corners,
        },
        "measurement": {
            "values_db": [[-3.0]],
            "common_clear_mask": [[True]],
            "valid_mask": [[True]],
            "quantity": "signed_gamma0_log_ratio_db",
            "equation": "10*log10(after/before)",
            "units": "dB",
        },
        "source_products": {
            "before": {"scene_id": "SAR_BEFORE", "acquisition_start_utc": "2024-01-01T00:00:00Z"},
            "after": {"scene_id": "SAR_AFTER", "acquisition_start_utc": "2024-01-25T00:00:00Z"},
        },
    }
    optical = {
        "record_type": "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON",
        "status": "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION",
        "processing": {"valid_transition_classes": [0, 1, 2], "water_class_codes": [1, 2]},
        "aoi": {"bounds_west_south_east_north": bounds},
        "source_products": {
            role: {
                "granule_id": f"OPTICAL_{role.upper()}",
                "acquisition_time_utc": f"2024-01-{day:02d}T12:00:00Z",
                "assets": {
                    layer: {"grid": copy.deepcopy(grid), "access": {"sha256": f"sha-{role}-{layer}"}}
                    for layer in ("WTR", "WTR-2", "CLOUD")
                },
            }
            for role, day in (("before", 1), ("after", 25))
        },
        "map_samples": [
            {
                "corners_wgs84": ring([upper_left, left_mid_top, left_mid_bottom, lower_left, upper_left]),
                "before": {"WTR": 0, "WTR-2": 0, "CLOUD": 1},
                "after": {"WTR": 1, "WTR-2": 1, "CLOUD": 0},
            },
            {
                "corners_wgs84": ring([left_mid_top, upper_right, lower_right, left_mid_bottom, left_mid_top]),
                "before": {"WTR": 0, "WTR-2": 0, "CLOUD": 0},
                "after": {"WTR": 0, "WTR-2": 0, "CLOUD": 8},
            },
        ],
    }
    return pair, optical


def test_exact_area_overlay_preserves_fractional_classes_without_resampling():
    pair, optical = _synthetic_records()

    record = evaluate_spatial_support(pair, optical, coverage_thresholds=(0.75,))

    assert record["status"] == "DIAGNOSTIC_SPATIAL_ASSOCIATION"
    assert record["method"]["resampling"] == "NONE"
    assert record["per_sar_cell"][0]["common_valid_wtr_area_fraction"] == pytest.approx(1.0)
    assert record["per_sar_cell"][0]["water_fraction_before_on_common_area"] == pytest.approx(0.0)
    assert record["per_sar_cell"][0]["water_fraction_after_on_common_area"] == pytest.approx(0.5)
    assert record["per_sar_cell"][0]["water_fraction_change_after_minus_before"] == pytest.approx(0.5)
    assert record["summary"]["coverage_sensitivity"][0]["sar_cells"] == 1
    assert "causal" in record["scope"]


def test_overlay_refuses_provider_qa_failure_or_changed_qa_contract():
    pair, optical = _synthetic_records()
    pair["provider_qa"]["status"] = "FAIL"

    with pytest.raises(SpatialSupportError, match="provider QA state"):
        evaluate_spatial_support(pair, optical)


def test_overlay_refuses_incompatible_optical_grids():
    pair, optical = _synthetic_records()
    optical["source_products"]["after"]["assets"]["WTR"]["grid"] = copy.deepcopy(
        optical["source_products"]["after"]["assets"]["WTR"]["grid"]
    )
    optical["source_products"]["after"]["assets"]["WTR"]["grid"]["transform"][2] += 30

    with pytest.raises(SpatialSupportError, match="grids are not identical"):
        evaluate_spatial_support(pair, optical)


def test_overlay_refuses_incomplete_retained_optical_samples():
    pair, optical = _synthetic_records()
    optical["map_samples"].pop()

    with pytest.raises(SpatialSupportError, match="AOI-center counts"):
        evaluate_spatial_support(pair, optical)


def test_invalid_wtr_classes_are_excluded_from_both_date_fractions():
    pair, optical = _synthetic_records()
    optical["map_samples"][0]["before"]["WTR"] = 253

    result = evaluate_spatial_support(pair, optical, coverage_thresholds=(0.01,))

    cell = result["per_sar_cell"][0]
    assert cell["common_valid_wtr_area_fraction"] == pytest.approx(0.5)
    assert cell["water_fraction_before_on_common_area"] == pytest.approx(0.0)
    assert cell["water_fraction_after_on_common_area"] == pytest.approx(0.0)


def test_wtr2_cloud_mask_sensitivity_excludes_obscured_change_and_keeps_clear_codes():
    pair, optical = _synthetic_records()

    result = evaluate_spatial_support(pair, optical, coverage_thresholds=(0.49,))

    cell = result["per_sar_cell"][0]
    assert cell["common_valid_wtr2_area_fraction"] == pytest.approx(1.0)
    assert cell["wtr2_water_fraction_change_after_minus_before"] == pytest.approx(0.5)
    assert cell["common_clear_cloud_wtr2_area_fraction"] == pytest.approx(0.5)
    assert cell["wtr2_clear_cloud_water_fraction_change_after_minus_before"] == pytest.approx(0.0)
    assert result["summary"]["wtr2_cells_common_cloud_clear_at_both_dates"] == 1
    assert result["method"]["wtr2_cloud_clear_classes"] == [0, 8]
    matched = result["summary"]["wtr2_matched_mask_sensitivity"][0]
    assert matched["sar_cells_on_identical_clear_supported_cohort"] == 1
    assert matched["unmasked_wtr2_cells_changed_by_more_than_0_05"] == 1
    assert matched["clear_masked_wtr2_cells_changed_by_more_than_0_05"] == 0
    assert matched["cells_with_absolute_change_difference_over_0_05"] == 1
    count_summary = result["summary"]["wtr2_clear_mask_class_counts"]
    assert count_summary["cloud_clear_sample_count"] == 1
    assert count_summary["WTR"]["water_class_counts_before_after"] == [0, 0]
    assert count_summary["WTR-2"]["transition_matrix_classes_0_1_2"] == [[1, 0, 0], [0, 0, 0], [0, 0, 0]]


def test_overlay_refuses_misaligned_cloud_mask_grid():
    pair, optical = _synthetic_records()
    optical["source_products"]["after"]["assets"]["CLOUD"]["grid"]["transform"][2] += 30

    with pytest.raises(SpatialSupportError, match="after DSWx-HLS CLOUD grid does not align"):
        evaluate_spatial_support(pair, optical)


def test_overlay_does_not_mutate_source_masks():
    pair, optical = _synthetic_records()
    before = copy.deepcopy(pair)

    evaluate_spatial_support(pair, optical, coverage_thresholds=(0.75,))

    assert pair == before


def test_retained_t163_wtr2_mask_sensitivity_reproduces_on_real_records():
    root = Path(__file__).resolve().parents[1]
    pair = json.loads((root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json").read_text())
    optical = json.loads((root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json").read_text())

    result = evaluate_spatial_support(pair, optical)

    counts = result["summary"]["wtr2_clear_mask_class_counts"]
    assert counts["cloud_clear_sample_count"] == 837
    assert counts["WTR"]["water_class_counts_before_after"] == [36, 27]
    assert counts["WTR-2"]["water_class_counts_before_after"] == [36, 27]
    assert counts["wtr_and_wtr2_transition_matrices_match"] is True
    unmasked = next(item for item in result["summary"]["wtr2_unmasked_coverage_sensitivity"] if item["minimum_common_valid_wtr2_area_fraction"] == 0.75)
    clear = next(item for item in result["summary"]["wtr2_cloud_clear_coverage_sensitivity"] if item["minimum_common_clear_cloud_wtr2_area_fraction"] == 0.75)
    matched = next(item for item in result["summary"]["wtr2_matched_mask_sensitivity"] if item["minimum_common_clear_cloud_wtr2_area_fraction"] == 0.75)
    assert (unmasked["sar_cells"], unmasked["water_fraction_increased_by_more_than_0_05"] + unmasked["water_fraction_decreased_by_more_than_0_05"]) == (1166, 141)
    assert (clear["sar_cells"], clear["water_fraction_increased_by_more_than_0_05"] + clear["water_fraction_decreased_by_more_than_0_05"]) == (738, 28)
    assert matched["sar_cells_on_identical_clear_supported_cohort"] == 738
    assert matched["cells_with_absolute_change_difference_over_0_05"] == 0
    partition = next(item for item in result["summary"]["wtr2_support_partition_sensitivity"] if item["minimum_common_area_fraction"] == 0.75)
    assert partition["unmasked_only_sar_cells"] == 428
    assert partition["unmasked_only_cells_increased_by_more_than_0_05"] == 1
    assert partition["unmasked_only_cells_decreased_by_more_than_0_05"] == 112
