"""Bounded, authenticated inspection and window reads of NISAR GCOV products."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Iterator
from urllib.parse import urlsplit

import numpy as np

from echo.geospatial import select_geographic_bbox_window


REMOTE_BLOCK_BYTES = 1024 * 1024
MAX_METADATA_RANGE_BYTES = 64 * 1024 * 1024
MAX_WINDOW_RANGE_BYTES = 64 * 1024 * 1024
MAX_WINDOW_SAMPLES = 512 * 512
MAX_WINDOW_ARRAY_BYTES = 16 * 1024 * 1024
MAX_FULL_GRID_COORDINATE_BYTES = 16 * 1024 * 1024
IDENTIFICATION_FIELDS = (
    "instrumentName",
    "listOfObservationModes",
    "missionId",
    "productVersion",
    "productSpecificationVersion",
    "absoluteOrbitNumber",
    "trackNumber",
    "frameNumber",
    "isUrgentObservation",
    "isJointObservation",
    "lookDirection",
    "listOfFrequencies",
)
_SCENE_ID = re.compile(r"^NISAR_([LS])2_PR_GCOV_[A-Z0-9_]+$")
_ASF_HOST = "nisar.asf.earthdatacloud.nasa.gov"
_ASF_COLLECTIONS = {
    "NISAR_L2_GCOV_BETA_V1",
    "NISAR_L2_GCOV_PROVISIONAL_V1",
    "NISAR_L2_GCOV_V1",
}
_WINDOW_LAYERS = {
    "HHHH",
    "HVHV",
    "HHHV",
    "HHVH",
    "HHVV",
    "HVVH",
    "HVVV",
    "VVVV",
    "VHVH",
    "VHVV",
    "RHRH",
    "RVRV",
    "RHRV",
    "mask",
    "numberOfLooks",
    "rtcGammaToSigmaFactor",
    "inputDataExceptionMask",
}

_WINDOW_LAYER_ATTRIBUTES = {
    "_FillValue",
    "description",
    "flag_meanings",
    "flag_masks",
    "flag_values",
    "long_name",
    "units",
    "valid_max",
    "valid_min",
}


@dataclass(frozen=True)
class GcovWindow:
    """Small selected GCOV arrays and the access record for their source scene."""

    scene_id: str
    frequency: str
    row_start: int
    row_stop: int
    column_start: int
    column_stop: int
    layers: dict[str, np.ndarray]
    product_url: str
    grid_metadata: dict[str, Any]
    catalog_metadata: dict[str, Any]
    access: dict[str, Any]
    selection_mask: np.ndarray | None = None
    selection_metadata: dict[str, Any] | None = None
    layer_attributes: dict[str, dict[str, Any]] | None = None


class NisarAccessError(ValueError):
    """Raised for invalid catalog entries or failed remote metadata access."""


def _install_read_budget(
    remote_file: Any, *, limit_bytes: int = MAX_METADATA_RANGE_BYTES
) -> Any:
    cache = getattr(remote_file, "cache", None)
    original_fetcher = getattr(cache, "fetcher", None)
    if cache is None or not callable(original_fetcher):
        raise NisarAccessError("remote byte-range cache does not support read budgeting")

    def fetch_with_budget(start: int, end: int) -> bytes:
        range_bytes = max(0, end - start)
        if cache.total_requested_bytes + range_bytes > limit_bytes:
            raise NisarAccessError(
                "remote range-read budget exceeded "
                f"({limit_bytes} bytes; requested_so_far={cache.total_requested_bytes}; "
                f"next_range_bytes={range_bytes})"
            )
        return original_fetcher(start, end)

    cache.fetcher = fetch_with_budget
    return cache


def _validated_product(feature: dict[str, Any]) -> tuple[str, str, str]:
    properties = feature.get("properties", {})
    if not isinstance(properties, dict):
        raise NisarAccessError("catalog feature properties must be an object")
    scene_id = properties.get("fileID")
    url = properties.get("url")
    collection = properties.get("collectionName")
    match = _SCENE_ID.fullmatch(scene_id or "")
    if not match:
        raise NisarAccessError("catalog feature is not a NISAR L2 GCOV production scene")
    if properties.get("processingLevel") != "GCOV":
        raise NisarAccessError("catalog feature processing level must be GCOV")
    if collection not in _ASF_COLLECTIONS:
        raise NisarAccessError("catalog feature collection must be a supported ASF GCOV collection")
    if not isinstance(url, str):
        raise NisarAccessError("catalog feature has no product URL")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        netloc = parsed.netloc
        path_parts = tuple(part for part in parsed.path.split("/") if part)
    except ValueError as exc:
        raise NisarAccessError("catalog product URL is malformed") from exc
    if (
        parsed.scheme != "https"
        or hostname != _ASF_HOST
        or netloc not in {_ASF_HOST, f"{_ASF_HOST}:443"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or path_parts != ("NISAR", collection, scene_id, f"{scene_id}.h5")
    ):
        raise NisarAccessError("catalog product URL is not a plain ASF NISAR HTTPS product URL")

    instrument = "LSAR" if match.group(1) == "L" else "SSAR"
    return scene_id, url, instrument


def _json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "tolist"):
        return _json_value(value.tolist())
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if hasattr(value, "item"):
        return _json_value(value.item())
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise NisarAccessError(f"unsupported HDF5 metadata value type: {type(value).__name__}")


@contextmanager
def _open_remote_product(
    url: str, *, max_range_bytes: int
) -> Iterator[tuple[Any, Any]]:
    try:
        import earthaccess
        import h5py
        from aiohttp import ClientTimeout
    except ImportError as exc:
        raise NisarAccessError(
            "remote NISAR access requires the 'nisar' optional dependencies"
        ) from exc

    try:
        auth = earthaccess.login(strategy="netrc", persist=False)
        if not auth.authenticated:
            raise NisarAccessError(
                "Earthdata Login failed; configure credentials in the local netrc file"
            )

        filesystem = earthaccess.get_fsspec_https_session()
        client_kwargs = dict(filesystem.client_kwargs)
        client_kwargs["timeout"] = ClientTimeout(total=25, connect=10, sock_read=20)
        filesystem.client_kwargs = client_kwargs

        with filesystem.open(
            url,
            "rb",
            block_size=REMOTE_BLOCK_BYTES,
            cache_type="bytes",
        ) as remote_file:
            cache = _install_read_budget(remote_file, limit_bytes=max_range_bytes)
            with h5py.File(remote_file, "r") as product:
                yield product, cache
    except NisarAccessError:
        raise
    except Exception as exc:
        raise NisarAccessError(
            f"remote NISAR product read failed ({type(exc).__name__})"
        ) from exc


def inspect_identification(
    feature: dict[str, Any], *, inspected_at: datetime | None = None
) -> dict[str, Any]:
    """Read a small allowlist from a remote HDF5 identification group.

    Authentication is read from Earthdata Login's local netrc configuration.
    Only the named identification datasets are accessed; no radar arrays are
    read, and the complete product is not downloaded.
    """
    scene_id, url, instrument = _validated_product(feature)

    try:
        group_path = f"/science/{instrument}/identification"
        with _open_remote_product(url, max_range_bytes=MAX_METADATA_RANGE_BYTES) as (
            product,
            cache,
        ):
            group = product[group_path]
            metadata = {
                name: _json_value(group[name][()])
                for name in IDENTIFICATION_FIELDS
                if name in group
            }
            missing = [name for name in IDENTIFICATION_FIELDS if name not in group]
        requested_bytes = getattr(cache, "total_requested_bytes", None)
    except NisarAccessError:
        raise
    except (KeyError, TypeError) as exc:
        raise NisarAccessError(
            f"remote identification metadata read failed ({type(exc).__name__})"
        ) from exc

    inspected_at = inspected_at or datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "inspected_at_utc": inspected_at.astimezone(timezone.utc).isoformat(),
        "product": {
            "scene_id": scene_id,
            "identification_group": group_path,
            "metadata": metadata,
            "fields_not_present": missing,
        },
        "access": {
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "HTTPS byte-range streaming",
            "fsspec_read_ahead_block_bytes": REMOTE_BLOCK_BYTES,
            "max_fsspec_range_bytes_requested": MAX_METADATA_RANGE_BYTES,
            "fsspec_range_bytes_requested": requested_bytes,
            "complete_product_download_requested": False,
            "radar_measurement_arrays_read": False,
        },
        "interpretation_limit": (
            "This command inspects product identification metadata only. It does not "
            "evaluate product QA, inspect radar measurements, or validate a scientific result."
        ),
    }


def _bounded_slice(value: slice, *, name: str) -> tuple[int, int]:
    if not isinstance(value, slice) or value.step not in (None, 1):
        raise NisarAccessError(f"{name} must be a unit-step slice")
    if (
        isinstance(value.start, bool)
        or isinstance(value.stop, bool)
        or not isinstance(value.start, int)
        or not isinstance(value.stop, int)
        or value.start < 0
        or value.stop <= value.start
    ):
        raise NisarAccessError(f"{name} must have explicit non-negative bounds")
    return value.start, value.stop


def read_gcov_window(
    feature: dict[str, Any],
    *,
    frequency: str,
    rows: slice | None = None,
    columns: slice | None = None,
    bounds_wgs84: tuple[float, float, float, float] | None = None,
    layers: tuple[str, ...] = ("HHHH", "mask", "numberOfLooks", "inputDataExceptionMask"),
    max_samples: int = MAX_WINDOW_SAMPLES,
) -> GcovWindow:
    """Read selected, allowlisted arrays from a bounded GCOV index window.

    Supply either explicit row/column slices or a WGS84 bbox. Geographic mode
    reads the full 1-D grid coordinate vectors within a separate byte budget,
    then returns an exact pixel-center selection mask for the enclosing window.
    This reader does not evaluate product QA or authorize scientific use.
    """
    scene_id, url, instrument = _validated_product(feature)
    if (
        isinstance(max_samples, bool)
        or not isinstance(max_samples, int)
        or not 1 <= max_samples <= MAX_WINDOW_SAMPLES
    ):
        raise NisarAccessError(
            f"max_samples must be between 1 and {MAX_WINDOW_SAMPLES}"
        )
    if not isinstance(frequency, str) or frequency not in {"A", "B"}:
        raise NisarAccessError("frequency must be A or B")
    if not layers or len(set(layers)) != len(layers):
        raise NisarAccessError("layers must be a non-empty list without duplicates")
    if any(layer not in _WINDOW_LAYERS for layer in layers):
        raise NisarAccessError("requested GCOV layer is not allowlisted")
    index_mode = rows is not None or columns is not None
    geographic_mode = bounds_wgs84 is not None
    if index_mode == geographic_mode or (rows is None) != (columns is None):
        raise NisarAccessError(
            "supply either both row/column slices or one geographic WGS84 bbox"
        )
    if index_mode:
        row_start, row_stop = _bounded_slice(rows, name="rows")
        column_start, column_stop = _bounded_slice(columns, name="columns")
        sample_count = (row_stop - row_start) * (column_stop - column_start)
        if sample_count > max_samples:
            raise NisarAccessError(
                f"window exceeds the {max_samples}-sample limit"
            )
    else:
        row_start = row_stop = column_start = column_stop = 0
        sample_count = 0
    selection_mask = None
    selection_metadata = None
    full_grid_coordinate_bytes = 0

    group_path = f"/science/{instrument}/GCOV/grids/frequency{frequency}"
    try:
        with _open_remote_product(url, max_range_bytes=MAX_WINDOW_RANGE_BYTES) as (
            product,
            cache,
        ):
            group = product[group_path]
            datasets = {}
            layer_attributes = {}
            for layer in layers:
                if layer not in group:
                    raise NisarAccessError(
                        f"requested GCOV layer is absent: {layer}"
                    )
                dataset = group[layer]
                if len(dataset.shape) != 2:
                    raise NisarAccessError(f"GCOV layer is not two-dimensional: {layer}")
                datasets[layer] = dataset
                layer_attributes[layer] = {
                    key: _json_value(value)
                    for key, value in getattr(dataset, "attrs", {}).items()
                    if key in _WINDOW_LAYER_ATTRIBUTES
                }

            shapes = {tuple(dataset.shape) for dataset in datasets.values()}
            if len(shapes) != 1:
                raise NisarAccessError("requested GCOV layers have different grid shapes")
            height, width = next(iter(shapes))
            if row_stop > height or column_stop > width:
                raise NisarAccessError("requested window exceeds the GCOV grid bounds")

            required_grid_datasets = {"projection", "xCoordinates", "yCoordinates"}
            missing_grid_datasets = required_grid_datasets.difference(group)
            if missing_grid_datasets:
                raise NisarAccessError(
                    "GCOV grid metadata is incomplete: "
                    + ", ".join(sorted(missing_grid_datasets))
                )
            projection_dataset = group["projection"]
            projection_value = _json_value(projection_dataset[()])
            projection_attribute_names = {
                "ellipsoid",
                "epsg_code",
                "false_easting",
                "false_northing",
                "grid_mapping_name",
                "inverse_flattening",
                "latitude_of_projection_origin",
                "longitude_of_projection_origin",
                "semi_major_axis",
                "spatial_ref",
                "utm_zone_number",
                "scale_factor_at_central_meridian",
                "longitude_of_central_meridian",
                "straight_vertical_longitude_from_pole",
                "standard_parallel",
            }
            projection_attributes = {
                key: _json_value(value)
                for key, value in projection_dataset.attrs.items()
                if key in projection_attribute_names
            }
            if "epsg_code" not in projection_attributes:
                raise NisarAccessError("GCOV projection is missing its EPSG code")
            if projection_value != projection_attributes["epsg_code"]:
                raise NisarAccessError(
                    "GCOV projection value and EPSG attribute do not agree"
                )

            x_dataset = group["xCoordinates"]
            y_dataset = group["yCoordinates"]
            if tuple(x_dataset.shape) != (width,) or tuple(y_dataset.shape) != (height,):
                raise NisarAccessError("GCOV coordinate vectors do not match the data grid")

            if geographic_mode:
                full_grid_coordinate_bytes = (
                    int(np.dtype(x_dataset.dtype).itemsize) * width
                    + int(np.dtype(y_dataset.dtype).itemsize) * height
                )
                if full_grid_coordinate_bytes > MAX_FULL_GRID_COORDINATE_BYTES:
                    raise NisarAccessError(
                        "full GCOV coordinate vectors exceed the geographic-selection memory limit"
                    )
                try:
                    selection = select_geographic_bbox_window(
                        np.asarray(x_dataset[:]),
                        np.asarray(y_dataset[:]),
                        epsg_code=int(projection_attributes["epsg_code"]),
                        bounds_wgs84=bounds_wgs84,
                        max_samples=max_samples,
                    )
                except (TypeError, ValueError) as exc:
                    raise NisarAccessError(f"geographic AOI selection failed: {exc}") from exc
                row_start, row_stop = selection.row_start, selection.row_stop
                column_start, column_stop = selection.column_start, selection.column_stop
                sample_count = (row_stop - row_start) * (column_stop - column_start)
                selection_mask = selection.mask
                selection_metadata = selection.metadata
            else:
                row_start, row_stop = _bounded_slice(rows, name="rows")
                column_start, column_stop = _bounded_slice(columns, name="columns")
                sample_count = (row_stop - row_start) * (column_stop - column_start)
                if sample_count > max_samples:
                    raise NisarAccessError(
                        f"window exceeds the {max_samples}-sample limit"
                    )
            if row_stop > height or column_stop > width:
                raise NisarAccessError("requested window exceeds the GCOV grid bounds")

            estimated_bytes = sum(
                int(np.dtype(dataset.dtype).itemsize) * sample_count
                for dataset in datasets.values()
            )
            if selection_mask is not None:
                estimated_bytes += int(selection_mask.nbytes)
            x_coordinate_bytes = int(np.dtype(x_dataset.dtype).itemsize) * (
                column_stop - column_start
            )
            y_coordinate_bytes = int(np.dtype(y_dataset.dtype).itemsize) * (
                row_stop - row_start
            )
            total_output_bytes = estimated_bytes + x_coordinate_bytes + y_coordinate_bytes
            if total_output_bytes > MAX_WINDOW_ARRAY_BYTES:
                raise NisarAccessError(
                    f"window output exceeds the {MAX_WINDOW_ARRAY_BYTES}-byte memory limit"
                )
            arrays = {
                layer: np.asarray(
                    dataset[row_start:row_stop, column_start:column_stop]
                )
                for layer, dataset in datasets.items()
            }
            x_coordinates = np.asarray(x_dataset[column_start:column_stop])
            y_coordinates = np.asarray(y_dataset[row_start:row_stop])
            x_steps = np.diff(x_coordinates)
            y_steps = np.diff(y_coordinates)
            if (
                not np.isfinite(x_coordinates).all()
                or not np.isfinite(y_coordinates).all()
                or (
                    x_steps.size > 0
                    and not (np.all(x_steps > 0) or np.all(x_steps < 0))
                )
                or (
                    y_steps.size > 0
                    and not (np.all(y_steps > 0) or np.all(y_steps < 0))
                )
            ):
                raise NisarAccessError(
                    "GCOV grid coordinates are non-finite or not monotonic"
                )
        requested_bytes = getattr(cache, "total_requested_bytes", None)
    except NisarAccessError:
        raise
    except (KeyError, TypeError, IndexError) as exc:
        raise NisarAccessError(
            f"remote GCOV window read failed ({type(exc).__name__})"
        ) from exc

    return GcovWindow(
        scene_id=scene_id,
        frequency=frequency,
        row_start=row_start,
        row_stop=row_stop,
        column_start=column_start,
        column_stop=column_stop,
        layers=arrays,
        product_url=url,
        grid_metadata={
            "projection_value": projection_value,
            "projection_attributes": projection_attributes,
            "x_coordinates": x_coordinates,
            "y_coordinates": y_coordinates,
            "coordinate_convention": "pixel centers per GCOV product specification",
        },
        catalog_metadata={
            key: _json_value(value)
            for key, value in feature["properties"].items()
            if key
            in {
                "fileID",
                "collectionName",
                "processingLevel",
                "startTime",
                "stopTime",
                "crid",
                "orbit",
                "productionConfiguration",
                "pathNumber",
                "frameNumber",
                "frameCoverage",
                "flightDirection",
                "mainBandPolarization",
                "sideBandPolarization",
                "rangeBandwidth",
            }
        },
        access={
            "read_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "HTTPS byte-range streaming",
            "fsspec_read_ahead_block_bytes": REMOTE_BLOCK_BYTES,
            "fsspec_range_bytes_requested": requested_bytes,
            "max_fsspec_range_bytes_requested": MAX_WINDOW_RANGE_BYTES,
            "complete_product_download_requested": False,
            "window_sample_count": sample_count,
            "window_array_bytes_estimated": estimated_bytes,
            "grid_coordinate_bytes_estimated": x_coordinate_bytes + y_coordinate_bytes,
            "full_grid_coordinate_bytes_read_for_selection": full_grid_coordinate_bytes,
            "grid_epsg_code": projection_attributes["epsg_code"],
            "layers_read": list(layers),
            "geographic_selection": selection_metadata,
            "interpretation_limit": (
                "Bounded data access only; product QA, geospatial alignment, and "
                "scientific validity are not assessed."
            ),
        },
        selection_mask=selection_mask,
        selection_metadata=selection_metadata,
        layer_attributes=layer_attributes,
    )
