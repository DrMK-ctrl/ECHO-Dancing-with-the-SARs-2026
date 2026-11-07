"""Geographic selection of pixel-center grids used by NISAR products."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np


@dataclass(frozen=True)
class GeographicWindowSelection:
    """An enclosing raster window plus an exact pixel-center AOI mask."""

    row_start: int
    row_stop: int
    column_start: int
    column_stop: int
    mask: np.ndarray
    metadata: dict[str, Any]


def _coordinate_axis(
    values: np.ndarray, *, name: str, product_label: str
) -> np.ndarray:
    axis = np.asarray(values)
    if axis.ndim != 1 or axis.size < 2 or not np.issubdtype(axis.dtype, np.number):
        raise ValueError(
            f"{product_label} {name} coordinates must be a numeric one-dimensional axis"
        )
    if not np.isfinite(axis).all():
        raise ValueError(f"{product_label} {name} coordinates contain non-finite values")
    delta = np.diff(axis)
    if not (np.all(delta > 0) or np.all(delta < 0)):
        raise ValueError(f"{product_label} {name} coordinates must be strictly monotonic")
    return axis


def select_geographic_bbox_window(
    x_coordinates: np.ndarray,
    y_coordinates: np.ndarray,
    *,
    epsg_code: int,
    bounds_wgs84: tuple[float, float, float, float],
    max_samples: int,
    product_label: str = "GCOV",
) -> GeographicWindowSelection:
    """Map a WGS84 bbox to a bounded NISAR window and pixel-center mask.

    Bounds use ``(west, south, east, north)``. The returned index window is
    the smallest axis-aligned window enclosing candidate pixel centers; its
    Boolean mask selects only centers that transform back inside the WGS84
    bbox. This distinction avoids analyzing the corners of a projected
    envelope that lie outside a geographic rectangle.
    """
    try:
        import pyproj
        from pyproj import CRS, Transformer
    except ImportError as exc:
        raise ValueError("geographic NISAR selection requires the optional pyproj dependency") from exc

    if isinstance(epsg_code, bool) or not isinstance(epsg_code, int) or epsg_code <= 0:
        raise ValueError(f"{product_label} EPSG code must be a positive integer")
    if not isinstance(bounds_wgs84, tuple) or len(bounds_wgs84) != 4:
        raise ValueError("geographic bounds must be a (west, south, east, north) tuple")
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in bounds_wgs84
    ):
        raise ValueError("geographic bounds must contain four finite numbers")
    west, south, east, north = map(float, bounds_wgs84)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("geographic bounds must be ordered within WGS84; antimeridian crossing is unsupported")
    if isinstance(max_samples, bool) or not isinstance(max_samples, int) or max_samples < 1:
        raise ValueError("max_samples must be a positive integer")

    if not isinstance(product_label, str) or not product_label.isidentifier():
        raise ValueError("product_label must be a simple identifier")
    x_axis = _coordinate_axis(x_coordinates, name="x", product_label=product_label)
    y_axis = _coordinate_axis(y_coordinates, name="y", product_label=product_label)
    try:
        grid_crs = CRS.from_epsg(epsg_code)
        if not grid_crs.is_projected:
            raise ValueError(f"{product_label} grid CRS must be projected")
        forward = Transformer.from_crs("EPSG:4326", grid_crs, always_xy=True)
        inverse = Transformer.from_crs(grid_crs, "EPSG:4326", always_xy=True)
        projected_bounds = forward.transform_bounds(
            west, south, east, north, densify_pts=64, errcheck=True
        )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"could not transform the WGS84 AOI to EPSG:{epsg_code}") from exc

    if not all(math.isfinite(value) for value in projected_bounds):
        raise ValueError(
            f"WGS84 AOI does not transform to finite coordinates in the {product_label} CRS"
        )
    min_x, min_y, max_x, max_y = projected_bounds
    selected_columns = np.flatnonzero((x_axis >= min_x) & (x_axis <= max_x))
    selected_rows = np.flatnonzero((y_axis >= min_y) & (y_axis <= max_y))
    if selected_columns.size == 0 or selected_rows.size == 0:
        raise ValueError(f"WGS84 AOI contains no {product_label} pixel centers")
    column_start, column_stop = int(selected_columns[0]), int(selected_columns[-1]) + 1
    row_start, row_stop = int(selected_rows[0]), int(selected_rows[-1]) + 1
    sample_count = (row_stop - row_start) * (column_stop - column_start)
    if sample_count > max_samples:
        raise ValueError(
            f"geographic AOI window exceeds the {max_samples}-sample limit"
        )

    xx, yy = np.meshgrid(
        x_axis[column_start:column_stop], y_axis[row_start:row_stop], indexing="xy"
    )
    try:
        longitude, latitude = inverse.transform(xx, yy, errcheck=True)
    except Exception as exc:
        raise ValueError(
            f"could not transform {product_label} pixel centers back to WGS84"
        ) from exc
    aoi_mask = (
        np.isfinite(longitude)
        & np.isfinite(latitude)
        & (longitude >= west)
        & (longitude <= east)
        & (latitude >= south)
        & (latitude <= north)
    )
    if not np.any(aoi_mask):
        raise ValueError(f"WGS84 AOI contains no {product_label} pixel centers")

    metadata = {
        "bounds_wgs84": [west, south, east, north],
        "source_crs": "EPSG:4326",
        "grid_crs": f"EPSG:{epsg_code}",
        "projected_envelope": [float(value) for value in projected_bounds],
        "transform_operation": forward.description,
        "transform_expected_accuracy_m": forward.accuracy,
        "pyproj_version": pyproj.__version__,
        "proj_version": pyproj.proj_version_str,
        "envelope_edge_densification_points": 64,
        "pixel_selection": "pixel-center inverse transform inside closed WGS84 bbox",
        "rows": [row_start, row_stop],
        "columns": [column_start, column_stop],
        "window_sample_count": sample_count,
        "selected_pixel_center_count": int(np.count_nonzero(aoi_mask)),
    }
    return GeographicWindowSelection(
        row_start=row_start,
        row_stop=row_stop,
        column_start=column_start,
        column_stop=column_stop,
        mask=aoi_mask,
        metadata=metadata,
    )
