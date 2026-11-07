from copy import deepcopy

import numpy as np
import pytest

from tools.research.evaluate_dswx_hls_aoi import (
    EvaluationError,
    LAYERS,
    _parse_utc_time,
    _map_samples,
    _transition,
    _validate_shared_native_grid,
    _wtr2_confidence_quality_overlap,
)


def test_wtr_transition_excludes_masked_classes_and_counts_partial_water():
    before = np.array([[0, 1, 2, 253]], dtype=np.uint8)
    after = np.array([[1, 0, 2, 0]], dtype=np.uint8)
    result = _transition(before, after, np.ones_like(before, dtype=bool))

    assert result["common_valid_pixel_count"] == 3
    assert result["rows_before_columns_after"] == [[0, 1, 0], [1, 0, 0], [0, 0, 1]]
    assert result["water_class_pixels_before_on_common_valid"] == 2
    assert result["water_class_pixels_after_on_common_valid"] == 2


def _shared_grid_fixture():
    grid = {
        "crs": "EPSG:32622",
        "transform": [30, 0, 500000, 0, -30, 6700000],
        "raster_shape": [100, 100],
        "window": {"row_start": 10, "row_stop": 12, "column_start": 20, "column_stop": 22},
        "selected_pixel_center_count": 4,
    }
    products = {
        role: {"assets": {layer: {"grid": deepcopy(grid)} for layer in LAYERS.values()}}
        for role in ("before", "after")
    }
    selection = np.ones((2, 2), dtype=bool)
    raw_windows = {
        role: {layer: (np.zeros((2, 2), dtype=np.uint8), selection.copy()) for layer in LAYERS.values()}
        for role in ("before", "after")
    }
    return products, raw_windows


def test_shared_grid_gate_accepts_identical_layers_and_selections():
    products, raw_windows = _shared_grid_fixture()
    _validate_shared_native_grid(products, raw_windows)


def test_shared_grid_gate_rejects_cross_layer_transform_mismatch():
    products, raw_windows = _shared_grid_fixture()
    products["after"]["assets"]["CONF"]["grid"]["transform"][2] += 30

    with pytest.raises(EvaluationError, match="after CONF grid differs"):
        _validate_shared_native_grid(products, raw_windows)


def test_shared_grid_gate_rejects_different_layer_aoi_pixel_selection():
    products, raw_windows = _shared_grid_fixture()
    raw_windows["after"]["WTR-2"][1][0, 0] = False

    with pytest.raises(EvaluationError, match="after WTR-2 AOI pixel-center selection differs"):
        _validate_shared_native_grid(products, raw_windows)


def test_confidence_flags_are_counted_as_quality_context_not_water_classes():
    wtr2 = np.array([[1, 2, 1, 0, 2]], dtype=np.uint8)
    confidence = np.array([[1, 14, 21, 24, 4]], dtype=np.uint8)
    selected = np.array([[True, True, True, True, False]])

    result = _wtr2_confidence_quality_overlap(wtr2, confidence, selected)

    assert result["wtr2_water_pixel_count"] == 3
    assert result["wtr2_water_pixels_with_conf_cloud_or_snow_flag"] == 2
    assert result["conf_cloud_or_snow_flag_codes"] == [10, 11, 12, 13, 14, 20, 21, 22, 23, 24]


def test_map_samples_preserve_native_pixel_codes_and_wgs84_cell_geometry():
    products, raw_windows = _shared_grid_fixture()
    for role in ("before", "after"):
        for index, layer in enumerate(LAYERS.values(), start=1):
            raw_windows[role][layer][0][:] = index
    raw_windows["after"]["WTR"][0][0, 1] = 252
    raw_windows["before"]["CONF"][0][1, 0] = 14

    samples = _map_samples(products, raw_windows)

    assert len(samples) == 4
    assert samples[0]["row"] == 10
    assert samples[0]["column"] == 20
    assert len(samples[0]["center_wgs84"]) == 2
    assert len(samples[0]["corners_wgs84"]) == 5
    assert samples[0]["corners_wgs84"][0] == samples[0]["corners_wgs84"][-1]
    assert samples[1]["after"]["WTR"] == 252
    assert samples[2]["before"]["CONF"] == 14


def test_cmr_acquisition_timestamp_is_used_with_millisecond_precision():
    parsed = _parse_utc_time("2024-06-02T13:30:52.554Z")
    assert parsed.isoformat() == "2024-06-02T13:30:52.554000+00:00"


@pytest.mark.parametrize("value", ["2024-05-11T08:49:44", "not-a-time"])
def test_rtc_reference_time_requires_timezone(value):
    with pytest.raises(EvaluationError):
        _parse_utc_time(value)
