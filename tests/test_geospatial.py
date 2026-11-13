import numpy as np
import pytest
from pyproj import Transformer

from echo.geospatial import select_geographic_bbox_window


def _grid():
    forward = Transformer.from_crs(4326, 32736, always_xy=True)
    inverse = Transformer.from_crs(32736, 4326, always_xy=True)
    center_x, center_y = forward.transform(33.0, -24.0)
    x = center_x + np.arange(7, dtype=np.float64) * 100 - 300
    y = center_y + np.arange(7, dtype=np.float64) * 100 - 300
    xx, yy = np.meshgrid(x, y)
    lon, lat = inverse.transform(xx, yy)
    return x, y, lon, lat


def test_select_geographic_bbox_returns_enclosing_window_and_exact_center_mask():
    x, y, lon, lat = _grid()
    bounds = (32.998, -24.002, 33.002, -23.998)
    selected = select_geographic_bbox_window(
        x, y, epsg_code=32736, bounds_wgs84=bounds, max_samples=512 * 512
    )

    expected = (
        (lon[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] >= bounds[0])
        & (lon[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] <= bounds[2])
        & (lat[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] >= bounds[1])
        & (lat[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] <= bounds[3])
    )
    np.testing.assert_array_equal(selected.mask, expected)
    assert selected.metadata["source_crs"] == "EPSG:4326"
    assert selected.metadata["grid_crs"] == "EPSG:32736"
    assert selected.metadata["selected_pixel_center_count"] == int(np.count_nonzero(expected))
    assert selected.mask.any()


def test_selection_supports_descending_gcov_coordinate_axes():
    x, y, lon, lat = _grid()
    bounds = (32.998, -24.002, 33.002, -23.998)
    selected = select_geographic_bbox_window(
        x[::-1], y[::-1], epsg_code=32736, bounds_wgs84=bounds, max_samples=512 * 512
    )
    lon = lon[::-1, ::-1]
    lat = lat[::-1, ::-1]
    expected = (
        (lon[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] >= bounds[0])
        & (lon[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] <= bounds[2])
        & (lat[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] >= bounds[1])
        & (lat[selected.row_start : selected.row_stop, selected.column_start : selected.column_stop] <= bounds[3])
    )
    np.testing.assert_array_equal(selected.mask, expected)


@pytest.mark.parametrize(
    "epsg,center,bounds",
    [
        (32636, (33.86, 35.54), (33.81, 35.49, 33.91, 35.59)),
        (3413, (10.0, 86.0), (9.96, 85.96, 10.04, 86.04)),
        (3031, (0.0, -86.0), (-0.04, -86.04, 0.04, -85.96)),
    ],
)
def test_geographic_selection_in_utm_and_polar_crs(epsg, center, bounds):
    forward = Transformer.from_crs(4326, epsg, always_xy=True)
    center_x, center_y = forward.transform(*center)
    x = center_x + np.arange(-100, 101, dtype=np.float64) * 250
    y = center_y + np.arange(-100, 101, dtype=np.float64) * 250

    selected = select_geographic_bbox_window(
        x, y, epsg_code=epsg, bounds_wgs84=bounds, max_samples=512 * 512
    )

    assert selected.mask.any()
    assert selected.metadata["grid_crs"] == f"EPSG:{epsg}"
    assert selected.metadata["selected_pixel_center_count"] == int(selected.mask.sum())
    accuracy = selected.metadata["transform_expected_accuracy_m"]
    assert accuracy is None or accuracy >= 0
    assert selected.metadata["transform_expected_accuracy_status"] == (
        "UNKNOWN" if accuracy is None else "REPORTED"
    )


@pytest.mark.parametrize(
    "bounds, message",
    [
        ((170, -1, -170, 1), "antimeridian crossing is unsupported"),
        ((0, 2, 1, 1), "must be ordered"),
        ((181, -1, 182, 1), "must be ordered"),
    ],
)
def test_rejects_invalid_geographic_bounds(bounds, message):
    x, y, *_ = _grid()
    with pytest.raises(ValueError, match=message):
        select_geographic_bbox_window(
            x, y, epsg_code=32736, bounds_wgs84=bounds, max_samples=512 * 512
        )


def test_rejects_nonmonotonic_grid_and_oversized_selection():
    x, y, *_ = _grid()
    with pytest.raises(ValueError, match="strictly monotonic"):
        select_geographic_bbox_window(
            x[[0, 1, 3, 2, 4, 5, 6]],
            y,
            epsg_code=32736,
            bounds_wgs84=(32.998, -24.002, 33.002, -23.998),
            max_samples=512 * 512,
        )
    with pytest.raises(ValueError, match="sample limit"):
        select_geographic_bbox_window(
            x,
            y,
            epsg_code=32736,
            bounds_wgs84=(32.998, -24.002, 33.002, -23.998),
            max_samples=1,
        )
