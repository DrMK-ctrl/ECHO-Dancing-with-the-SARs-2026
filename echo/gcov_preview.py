"""QA-explicit, bounded single-observation GCOV raster previews."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any

import numpy as np

from echo.science import decode_gcov_exception_mask
from echo.nisar_access import (
    FALLBACK_REMOTE_BLOCK_BYTES,
    MAX_WINDOW_RANGE_BYTES,
    MAX_WINDOW_SAMPLES,
    NisarAccessError,
    REMOTE_BLOCK_BYTES,
    _is_retryable_remote_range_failure,
    _validated_product,
    read_gcov_window,
)
from echo.qa import QASummaryError, read_qa_summary


MAX_PREVIEW_SAMPLES = 65_536
_DISPLAY_LAYERS = {"HHHH", "HVHV", "VVVV", "VHVH", "RHRH", "RVRV"}
_QUALITY_LAYERS = ("mask", "numberOfLooks", "inputDataExceptionMask")


class GcovPreviewError(ValueError):
    """Raised when a single-observation preview cannot be built safely."""


def _validate_bounds(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        raise GcovPreviewError("bounds_wgs84 must be west, south, east, north")
    if any(
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(item)
        for item in value
    ):
        raise GcovPreviewError("bounds_wgs84 must contain four finite numbers")
    west, south, east, north = (float(item) for item in value)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise GcovPreviewError("bounds_wgs84 must be ordered within WGS84")
    return west, south, east, north


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(str(value.shape).encode("ascii"))
    digest.update(value.view(np.uint8))
    return digest.hexdigest()


def _array_values(array: np.ndarray) -> list[Any]:
    values = np.asarray(array)
    if np.issubdtype(values.dtype, np.floating):
        return [
            [float(value) if np.isfinite(value) else None for value in row]
            for row in values
        ]
    return [[int(value) for value in row] for row in values]


def _selected_code_counts(array: np.ndarray, selection: np.ndarray) -> dict[str, int]:
    """Count source quality codes in the exact AOI, without assigning meaning."""
    codes, counts = np.unique(array[selection], return_counts=True)
    return {str(int(code)): int(count) for code, count in zip(codes, counts, strict=True)}


def _center_edges(coordinates: np.ndarray, *, axis: str) -> np.ndarray:
    values = np.asarray(coordinates, dtype=np.float64)
    if values.ndim != 1 or values.size < 2:
        raise GcovPreviewError(
            f"the selected preview needs at least two {axis} pixel centers"
        )
    differences = np.diff(values)
    if not np.isfinite(values).all() or not (
        np.all(differences > 0) or np.all(differences < 0)
    ):
        raise GcovPreviewError(f"{axis} pixel centers are not finite and monotonic")
    edges = np.empty(values.size + 1, dtype=np.float64)
    edges[1:-1] = (values[:-1] + values[1:]) / 2
    edges[0] = values[0] - differences[0] / 2
    edges[-1] = values[-1] + differences[-1] / 2
    return edges


def _pixel_corners_wgs84(window: Any) -> list[list[list[float]]]:
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise GcovPreviewError("pyproj is required to locate preview pixels") from exc
    projection = window.grid_metadata.get("projection_attributes", {})
    epsg = projection.get("epsg_code")
    if isinstance(epsg, bool) or not isinstance(epsg, int):
        raise GcovPreviewError("GCOV grid has no valid EPSG code")
    x_edges = _center_edges(window.grid_metadata["x_coordinates"], axis="x")
    y_edges = _center_edges(window.grid_metadata["y_coordinates"], axis="y")
    x_grid, y_grid = np.meshgrid(x_edges, y_edges)
    transformer = Transformer.from_crs(
        f"EPSG:{epsg}", "EPSG:4326", always_xy=True
    )
    longitude, latitude = transformer.transform(x_grid, y_grid)
    if not np.isfinite(longitude).all() or not np.isfinite(latitude).all():
        raise GcovPreviewError("GCOV pixel corners could not be transformed to WGS84")
    return [
        [[float(lon), float(lat)] for lon, lat in zip(lon_row, lat_row, strict=True)]
        for lon_row, lat_row in zip(longitude, latitude, strict=True)
    ]


def build_gcov_preview(
    feature: dict[str, Any],
    *,
    bounds_wgs84: tuple[float, float, float, float] | list[float],
    frequency: str,
    layer: str,
) -> dict[str, Any]:
    """Read one real GCOV layer and its quality context for display only.

    Provider QA is retrieved first and preserved unchanged. A `FAIL` result
    does not prevent an explicitly QA-held diagnostic preview, but this record
    never authorizes temporal measurement or physical interpretation.
    """
    scene_id, product_url, _instrument = _validated_product(feature)
    if frequency not in {"A", "B"}:
        raise GcovPreviewError("frequency must be A or B")
    if layer not in _DISPLAY_LAYERS:
        raise GcovPreviewError("requested layer is not a supported real-valued diagonal term")
    bounds = _validate_bounds(bounds_wgs84)

    try:
        qa = read_qa_summary(feature, product_metadata={})
    except QASummaryError as exc:
        raise GcovPreviewError(f"provider QA could not be retrieved: {exc}") from exc

    read_options = {
        "frequency": frequency,
        "bounds_wgs84": bounds,
        "layers": (layer, *_QUALITY_LAYERS),
        "max_samples": MAX_PREVIEW_SAMPLES,
    }
    try:
        window = read_gcov_window(feature, **read_options)
    except NisarAccessError as exc:
        if (
            not _is_retryable_remote_range_failure(exc)
            or REMOTE_BLOCK_BYTES <= FALLBACK_REMOTE_BLOCK_BYTES
        ):
            raise GcovPreviewError(str(exc)) from exc
        first_attempt_bytes = int(exc.remote_range_bytes_requested)
        remaining_budget = MAX_WINDOW_RANGE_BYTES - first_attempt_bytes
        if remaining_budget <= 0:
            raise GcovPreviewError(
                "the first remote read exhausted the bounded range budget"
            ) from exc
        try:
            window = read_gcov_window(
                feature,
                **read_options,
                _remote_block_bytes=FALLBACK_REMOTE_BLOCK_BYTES,
                _max_range_bytes=remaining_budget,
            )
        except NisarAccessError as retry_exc:
            raise GcovPreviewError(
                f"bounded GCOV retry failed after {type(exc.__cause__).__name__}"
            ) from retry_exc
        retry_record = {
            "policy": "retry transport failures once with smaller read-ahead blocks",
            "attempts": [
                {
                    "block_bytes": REMOTE_BLOCK_BYTES,
                    "result": "TRANSPORT_FAILURE",
                    "failure": str(exc),
                    "range_bytes_requested": first_attempt_bytes,
                },
                {
                    "block_bytes": FALLBACK_REMOTE_BLOCK_BYTES,
                    "result": "SUCCEEDED",
                    "range_bytes_requested": window.access[
                        "fsspec_range_bytes_requested"
                    ],
                },
            ],
            "combined_range_bytes_requested": first_attempt_bytes
            + window.access["fsspec_range_bytes_requested"],
            "combined_range_byte_limit": MAX_WINDOW_RANGE_BYTES,
        }
        window.access["fsspec_range_bytes_requested"] = retry_record[
            "combined_range_bytes_requested"
        ]
        window.access["max_fsspec_range_bytes_requested"] = MAX_WINDOW_RANGE_BYTES
        window.access["range_read_retry"] = retry_record
    values = window.layers[layer]
    mask = window.layers["mask"]
    looks = window.layers["numberOfLooks"]
    exceptions = window.layers["inputDataExceptionMask"]
    selection = window.selection_mask
    if selection is None:
        raise GcovPreviewError("geographic preview has no exact pixel-center mask")
    if any(array.shape != values.shape for array in (mask, looks, exceptions, selection)):
        raise GcovPreviewError("measurement and quality arrays do not share one grid")

    valid_codes = (mask >= 1) & (mask <= 5)
    quality_attributes = window.layer_attributes or {}
    exception_description = quality_attributes.get(
        "inputDataExceptionMask", {}
    ).get("description")
    exception_attributes_hash = hashlib.sha256(
        json.dumps(
            quality_attributes.get("inputDataExceptionMask", {}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()
    try:
        exception_flags = decode_gcov_exception_mask(
            exceptions, layer=layer, description=exception_description
        )
    except ValueError:
        exception_flags = None
    exception_valid = (
        exception_flags.valid_mask
        if exception_flags is not None
        else np.zeros(exceptions.shape, dtype=bool)
    )
    finite_positive = np.isfinite(values) & (values > 0)
    display_eligible = selection & valid_codes & exception_valid & finite_positive
    known_mask_codes = {0, 1, 2, 3, 4, 5, 255}
    unknown_quality_codes = int(
        np.count_nonzero(
            selection
            & ~np.isin(mask, tuple(known_mask_codes))
        )
    )
    if exception_flags is None:
        unknown_quality_codes += int(np.count_nonzero(selection))
    else:
        unknown_quality_codes += int(
            np.count_nonzero(selection & exception_flags.unknown_mask)
        )
    display_values_db = 10.0 * np.log10(values[display_eligible].astype(np.float64))
    if display_values_db.size:
        stretch_low_db, stretch_high_db = np.percentile(display_values_db, (2, 98))
    else:
        stretch_low_db = stretch_high_db = None

    checksum_arrays = {
        name: {
            "sha256": _array_sha256(array),
            "dtype": str(array.dtype),
            "shape": list(array.shape),
        }
        for name, array in window.layers.items()
    }
    x_coordinates = np.asarray(window.grid_metadata["x_coordinates"])
    y_coordinates = np.asarray(window.grid_metadata["y_coordinates"])
    checksum_arrays["xCoordinates"] = {
        "sha256": _array_sha256(x_coordinates),
        "dtype": str(x_coordinates.dtype),
        "shape": list(x_coordinates.shape),
    }
    checksum_arrays["yCoordinates"] = {
        "sha256": _array_sha256(y_coordinates),
        "dtype": str(y_coordinates.dtype),
        "shape": list(y_coordinates.shape),
    }
    checksum_arrays["selectionMask"] = {
        "sha256": _array_sha256(selection),
        "dtype": str(selection.dtype),
        "shape": list(selection.shape),
    }

    qa_record = asdict(qa)
    return {
        "record_type": "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "Alaska Satellite Facility DAAC",
            "mission": "NISAR",
            "product": "L2 GCOV",
            "scene_id": scene_id,
            "product_url": product_url,
            "catalog_metadata": window.catalog_metadata,
            "provider_qa_status": qa.evidence.status,
            "provider_qa_summary": qa_record,
        },
        "measurement": {
            "dataset": f"/science/LSAR/GCOV/grids/frequency{frequency}/{layer}",
            "frequency": frequency,
            "layer": layer,
            "units": "linear gamma-zero power",
            "values": _array_values(values),
            "quality": {
                "mask": _array_values(mask),
                "number_of_looks": _array_values(looks),
                "input_data_exception_mask": _array_values(exceptions),
                "exact_aoi_pixel_center_selection": _array_values(selection),
                "mask_code_counts": _selected_code_counts(mask, selection),
                "input_data_exception_code_counts": _selected_code_counts(
                    exceptions, selection
                ),
                "input_data_exception_mask_encoding": (
                    exception_flags.encoding if exception_flags else "UNRECOGNIZED"
                ),
                "input_data_exception_mask_polarization": (
                    exception_flags.polarization if exception_flags else None
                ),
                "input_data_exception_mask_polarization_flag": (
                    exception_flags.polarization_flag if exception_flags else None
                ),
                "input_data_exception_mask_attributes": quality_attributes.get(
                    "inputDataExceptionMask", {}
                ),
                "input_data_exception_mask_attributes_sha256": exception_attributes_hash,
                "display_eligible_pixel_count": int(np.count_nonzero(display_eligible)),
                "aoi_pixel_center_count": int(np.count_nonzero(selection)),
                "excluded_nonvalid_mask_count": int(
                    np.count_nonzero(selection & ~valid_codes)
                ),
                "excluded_exception_count": int(
                    np.count_nonzero(selection & exception_flags.exception_mask)
                    if exception_flags
                    else 0
                ),
                "excluded_unfocused_count": int(
                    np.count_nonzero(selection & exception_flags.unfocused_mask)
                    if exception_flags
                    else 0
                ),
                "excluded_unknown_exception_count": int(
                    np.count_nonzero(selection & exception_flags.unknown_mask)
                    if exception_flags
                    else int(np.count_nonzero(selection))
                ),
                "excluded_nonfinite_or_nonpositive_count": int(
                    np.count_nonzero(selection & ~finite_positive)
                ),
                "unknown_quality_code_count": unknown_quality_codes,
            },
        },
        "grid": {
            "epsg_code": window.grid_metadata["projection_attributes"]["epsg_code"],
            "coordinate_convention": window.grid_metadata["coordinate_convention"],
            "x_pixel_centers": [float(value) for value in x_coordinates],
            "y_pixel_centers": [float(value) for value in y_coordinates],
            "pixel_corners_wgs84": _pixel_corners_wgs84(window),
            "window": {
                "row_start": window.row_start,
                "row_stop": window.row_stop,
                "column_start": window.column_start,
                "column_stop": window.column_stop,
                "shape": list(values.shape),
                "bounds_wgs84": list(bounds),
            },
        },
        "access": window.access,
        "checksums": checksum_arrays,
        "display_transform": {
            "method": "10 * log10(linear gamma-zero power)",
            "units": "dB",
            "purpose": "visualization only; raw product values are retained above",
            "eligible_values_only": True,
            "stretch_method": "2nd to 98th percentile of display-eligible AOI samples",
            "stretch_range_db": (
                [float(stretch_low_db), float(stretch_high_db)]
                if stretch_low_db is not None and stretch_high_db is not None
                else None
            ),
        },
        "scientific_disposition": (
            "QA_HELD_DIAGNOSTIC_PREVIEW"
            if qa.evidence.status != "PASS"
            else "SINGLE_OBSERVATION_PREVIEW_NO_CHANGE_ASSESSMENT"
        ),
        "interpretation_limits": [
            "One source observation only; no temporal change is measured.",
            "Provider QA is displayed unchanged and does not authorize analysis.",
            "Mask and exception flags use product-documented definitions; the display screen does not override provider QA.",
            "No event, cause, damage, or ground condition is inferred from this layer.",
        ],
        "provenance": {
            "provider_qa_artifact_uri": qa.artifact_uri,
            "provider_qa_artifact_sha256": qa.artifact_sha256,
            "provider_qa_retrieved_at_utc": qa.retrieved_at_utc,
            "window_read_at_utc": window.access["read_at_utc"],
            "window_access_method": window.access["method"],
            "fsspec_range_bytes_requested": window.access[
                "fsspec_range_bytes_requested"
            ],
            "maximum_range_bytes": window.access[
                "max_fsspec_range_bytes_requested"
            ],
            "software": {"numpy": np.__version__},
            "sample_count_limit": MAX_PREVIEW_SAMPLES,
            "max_reader_sample_count": MAX_WINDOW_SAMPLES,
        },
    }
