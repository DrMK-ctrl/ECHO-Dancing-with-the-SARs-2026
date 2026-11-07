import copy

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
                "assets": {"WTR": {"grid": grid, "access": {"sha256": f"sha-{role}"}}},
            }
            for role, day in (("before", 1), ("after", 25))
        },
        "map_samples": [
            {
                "corners_wgs84": ring([upper_left, left_mid_top, left_mid_bottom, lower_left, upper_left]),
                "before": {"WTR": 0},
                "after": {"WTR": 1},
            },
            {
                "corners_wgs84": ring([left_mid_top, upper_right, lower_right, left_mid_bottom, left_mid_top]),
                "before": {"WTR": 0},
                "after": {"WTR": 0},
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


def test_overlay_does_not_mutate_source_masks():
    pair, optical = _synthetic_records()
    before = copy.deepcopy(pair)

    evaluate_spatial_support(pair, optical, coverage_thresholds=(0.75,))

    assert pair == before
