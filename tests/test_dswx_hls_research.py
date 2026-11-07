from copy import deepcopy

import numpy as np
import pytest

from tools.research.evaluate_dswx_hls_aoi import (
    EvaluationError,
    LAYERS,
    _parse_acquisition_time,
    _parse_utc_time,
    _transition,
    _validate_shared_native_grid,
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


def test_confidence_transition_uses_only_unmasked_confidence_classes():
    before = np.array([[0, 1, 2, 3, 4, 11, 20]], dtype=np.uint8)
    after = np.array([[1, 0, 4, 3, 0, 1, 1]], dtype=np.uint8)
    result = _transition(
        before,
        after,
        np.ones_like(before, dtype=bool),
        valid_classes=(0, 1, 2, 3, 4),
        water_classes=(1, 2, 3, 4),
    )

    assert result["class_order"] == [0, 1, 2, 3, 4]
    assert result["common_valid_pixel_count"] == 5
    assert result["water_class_pixels_before_on_common_valid"] == 4
    assert result["water_class_pixels_after_on_common_valid"] == 3


def test_granule_acquisition_time_is_parsed_as_utc():
    parsed = _parse_acquisition_time(
        "OPERA_L3_DSWx-HLS_T22JDM_20240508T132241Z_20240510T085001Z_S2A_30_v1.0"
    )
    assert parsed.isoformat() == "2024-05-08T13:22:41+00:00"


@pytest.mark.parametrize("value", ["2024-05-11T08:49:44", "not-a-time"])
def test_rtc_reference_time_requires_timezone(value):
    with pytest.raises(EvaluationError):
        _parse_utc_time(value)
