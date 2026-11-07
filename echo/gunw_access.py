"""Bounded, authenticated reads of geocoded NISAR GUNW windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlsplit

import numpy as np

from echo.geospatial import select_geographic_bbox_window
from echo.nisar_access import (
    MAX_WINDOW_ARRAY_BYTES,
    MAX_WINDOW_SAMPLES,
    REMOTE_BLOCK_BYTES,
    NisarAccessError,
    _json_value,
    _open_remote_product,
)


# Product header/metadata probes alone requested about 66 MB across two opens.
# Allow one open for metadata plus a few compressed 512x512 chunks, still capped.
MAX_GUNW_WINDOW_RANGE_BYTES = 96 * 1024 * 1024
MAX_FULL_GUNW_COORDINATE_BYTES = 16 * 1024 * 1024
_ASF_HOST = "nisar.asf.earthdatacloud.nasa.gov"
_GUNW_COLLECTIONS = {
    "NISAR_L2_GUNW_PROVISIONAL_V1",
    "NISAR_L2_GUNW_V1",
}
_SCENE_ID = re.compile(r"^NISAR_L2_PR_GUNW_[A-Z0-9_]+$")
_IDENTIFICATION_FIELDS = (
    "compositeReleaseId",
    "frameNumber",
    "instrumentName",
    "listOfFrequencies",
    "lookDirection",
    "missionId",
    "orbitPassDirection",
    "productSpecificationVersion",
    "productType",
    "productVersion",
    "radarBand",
    "referenceAbsoluteOrbitNumber",
    "referenceHasInputDataException",
    "referenceListOfObservationModes",
    "referenceZeroDopplerEndTime",
    "referenceZeroDopplerStartTime",
    "secondaryAbsoluteOrbitNumber",
    "secondaryHasInputDataException",
    "secondaryListOfObservationModes",
    "secondaryZeroDopplerEndTime",
    "secondaryZeroDopplerStartTime",
    "trackNumber",
)
_REQUIRED_IDENTIFICATION_FIELDS = frozenset(
    {
        "compositeReleaseId",
        "frameNumber",
        "instrumentName",
        "listOfFrequencies",
        "lookDirection",
        "missionId",
        "orbitPassDirection",
        "productSpecificationVersion",
        "productType",
        "productVersion",
        "radarBand",
        "referenceAbsoluteOrbitNumber",
        "referenceHasInputDataException",
        "referenceListOfObservationModes",
        "referenceZeroDopplerEndTime",
        "referenceZeroDopplerStartTime",
        "secondaryAbsoluteOrbitNumber",
        "secondaryHasInputDataException",
        "secondaryListOfObservationModes",
        "secondaryZeroDopplerEndTime",
        "secondaryZeroDopplerStartTime",
        "trackNumber",
    }
)
_PHASE_ROOT = "science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram"
_MANDATORY_LAYERS = frozenset(
    {"unwrappedPhase", "coherenceMagnitude", "connectedComponents", "mask"}
)
_OPTIONAL_LAYERS = frozenset(
    {"ionospherePhaseScreen", "ionospherePhaseScreenUncertainty"}
)
_LAYERS = _MANDATORY_LAYERS | _OPTIONAL_LAYERS


@dataclass(frozen=True)
class GunwWindow:
    """Selected GUNW source arrays and their grid/access provenance."""

    scene_id: str
    polarization: str
    row_start: int
    row_stop: int
    column_start: int
    column_stop: int
    arrays: dict[str, np.ndarray]
    x_coordinates: np.ndarray
    y_coordinates: np.ndarray
    selection_mask: np.ndarray | None
    identification: dict[str, Any]
    catalog_metadata: dict[str, Any]
    grid_metadata: dict[str, Any]
    provider_qa: dict[str, Any]
    access: dict[str, Any]


class GunwAccessError(NisarAccessError):
    """Raised for invalid GUNW catalog entries or bounded-read failures."""


def _validated_gunw_product(feature: dict[str, Any]) -> tuple[str, str]:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise GunwAccessError("catalog feature properties must be an object")
    scene_id = properties.get("fileID")
    product_url = properties.get("url")
    collection = properties.get("collectionName")
    if (
        not isinstance(scene_id, str)
        or not _SCENE_ID.fullmatch(scene_id)
        or properties.get("processingLevel") != "GUNW"
        or collection not in _GUNW_COLLECTIONS
    ):
        raise GunwAccessError("catalog feature is not a supported ASF NISAR L2 GUNW product")
    if not isinstance(product_url, str):
        raise GunwAccessError("catalog feature has no GUNW product URL")
    try:
        parsed = urlsplit(product_url)
        parts = tuple(part for part in parsed.path.split("/") if part)
    except ValueError as exc:
        raise GunwAccessError("catalog GUNW URL is malformed") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != _ASF_HOST
        or parsed.netloc not in {_ASF_HOST, f"{_ASF_HOST}:443"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parts != ("NISAR", collection, scene_id, f"{scene_id}.h5")
    ):
        raise GunwAccessError("catalog URL is not a canonical ASF NISAR GUNW product")
    return scene_id, product_url


def _bounded_axis_slice(value: slice, *, name: str) -> tuple[int, int]:
    if not isinstance(value, slice) or value.step not in (None, 1):
        raise GunwAccessError(f"{name} must be a unit-step slice")
    if (
        isinstance(value.start, bool)
        or isinstance(value.stop, bool)
        or not isinstance(value.start, int)
        or not isinstance(value.stop, int)
        or value.start < 0
        or value.stop <= value.start
    ):
        raise GunwAccessError(f"{name} must have explicit non-negative bounds")
    return value.start, value.stop


def _array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(value.dtype.str.encode("ascii"))
    digest.update(json.dumps(value.shape).encode("ascii"))
    digest.update(value.view(np.uint8))
    return digest.hexdigest()


def _provider_qa_reference(
    scene_id: str, collection: str, qa_summary: dict[str, Any] | None
) -> dict[str, Any]:
    if qa_summary is None:
        return {"status": "NOT_PROVIDED"}
    status = qa_summary.get("observed_provider_status")
    artifact_uri = qa_summary.get("artifact_uri")
    artifact_sha256 = qa_summary.get("artifact_sha256")
    if status not in {"PASS", "FAIL", "INDETERMINATE", "NO_FAIL_REPORTED"}:
        raise GunwAccessError("provider QA status is missing or unrecognized")
    if (
        not isinstance(artifact_uri, str)
        or not isinstance(artifact_sha256, str)
        or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256)
    ):
        raise GunwAccessError("provider QA summary requires a canonical artifact and SHA-256")
    try:
        parsed = urlsplit(artifact_uri)
        parts = tuple(part for part in parsed.path.split("/") if part)
    except ValueError as exc:
        raise GunwAccessError("provider QA summary URI is malformed") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != _ASF_HOST
        or parsed.netloc != _ASF_HOST
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or len(parts) != 4
        or parts[0] != "NISAR"
        or parts[1] != collection
        or parts[1] not in _GUNW_COLLECTIONS
        or parts[2] != scene_id
        or parts[3] != f"{scene_id}_QA_SUMMARY.csv"
    ):
        raise GunwAccessError("provider QA summary URI does not identify this GUNW scene")
    return {
        "status": status,
        "artifact_uri": artifact_uri,
        "artifact_sha256": artifact_sha256,
        "retrieved_at_utc": qa_summary.get("retrieved_at_utc"),
    }


def read_gunw_window(
    feature: dict[str, Any],
    *,
    polarization: str,
    rows: slice | None = None,
    columns: slice | None = None,
    bounds_wgs84: tuple[float, float, float, float] | None = None,
    layers: tuple[str, ...] = (
        "unwrappedPhase",
        "coherenceMagnitude",
        "connectedComponents",
        "mask",
    ),
    provider_qa_summary: dict[str, Any] | None = None,
) -> GunwWindow:
    """Read a small, allowlisted GUNW window without changing QA disposition.

    Use either explicit row/column slices or one WGS84 rectangle. Geographic
    selection includes only pixel centers that transform back inside the AOI.
    Arrays remain in product units; this reader performs no correction,
    thresholding, phase-to-displacement conversion, or scientific finding.
    """
    scene_id, product_url = _validated_gunw_product(feature)
    if polarization not in {"HH", "VV"}:
        raise GunwAccessError("polarization must be HH or VV")
    if not isinstance(layers, tuple) or not layers or len(set(layers)) != len(layers):
        raise GunwAccessError("layers must be a non-empty tuple without duplicates")
    if not _MANDATORY_LAYERS.issubset(layers) or not set(layers).issubset(_LAYERS):
        raise GunwAccessError("layers must include the mandatory GUNW quality and phase layers")
    index_mode = rows is not None or columns is not None
    geographic_mode = bounds_wgs84 is not None
    if index_mode == geographic_mode or (rows is None) != (columns is None):
        raise GunwAccessError(
            "supply either both row/column slices or one geographic WGS84 bbox"
        )
    selection = None
    full_coordinate_bytes = 0
    if index_mode:
        row_start, row_stop = _bounded_axis_slice(rows, name="rows")
        column_start, column_stop = _bounded_axis_slice(columns, name="columns")
        sample_count = (row_stop - row_start) * (column_stop - column_start)
        if sample_count > MAX_WINDOW_SAMPLES:
            raise GunwAccessError(
                f"window exceeds the {MAX_WINDOW_SAMPLES}-sample limit"
            )
    else:
        row_start = row_stop = column_start = column_stop = sample_count = 0

    try:
        with _open_remote_product(
            product_url, max_range_bytes=MAX_GUNW_WINDOW_RANGE_BYTES
        ) as (product, cache):
            identification_path = "/science/LSAR/identification"
            if identification_path not in product:
                raise GunwAccessError("GUNW identification group is absent")
            identification_group = product[identification_path]
            identification = {
                name: _json_value(identification_group[name][()])
                for name in _IDENTIFICATION_FIELDS
                if name in identification_group
            }
            missing_identification = sorted(
                _REQUIRED_IDENTIFICATION_FIELDS - identification.keys()
            )
            if missing_identification:
                raise GunwAccessError(
                    "GUNW 1.5.0 identification fields are missing: "
                    + ", ".join(missing_identification)
                )
            if (
                identification["productType"] != "GUNW"
                or identification["productSpecificationVersion"] != "1.5.0"
                or identification["listOfFrequencies"] != ["A"]
            ):
                raise GunwAccessError(
                    "GUNW product type, specification version, or frequency is unsupported"
                )

            base_path = f"/{_PHASE_ROOT}"
            data_group_path = f"{base_path}/{polarization}"
            grid_group = product[base_path]
            data_group = product[data_group_path]
            projection = data_group.get("projection")
            if projection is None or "epsg_code" not in projection.attrs:
                raise GunwAccessError("GUNW map projection metadata is missing its EPSG code")
            epsg_code = int(projection.attrs["epsg_code"])
            if int(projection[()]) != epsg_code:
                raise GunwAccessError("GUNW projection value and EPSG attribute do not agree")

            data_datasets = {}
            for layer in layers:
                parent = grid_group if layer == "mask" else data_group
                if layer not in parent:
                    raise GunwAccessError(f"requested GUNW layer is absent: {layer}")
                data_datasets[layer] = parent[layer]
            shapes = {tuple(dataset.shape) for dataset in data_datasets.values()}
            if len(shapes) != 1 or len(next(iter(shapes))) != 2:
                raise GunwAccessError("requested GUNW window layers have incompatible grids")
            height, width = next(iter(shapes))
            if tuple(grid_group["xCoordinates"].shape) != (width,) or tuple(
                grid_group["yCoordinates"].shape
            ) != (height,):
                raise GunwAccessError("GUNW coordinate vectors do not match the phase grid")
            if str(_json_value(data_datasets["unwrappedPhase"].attrs.get("units", ""))) != "radians":
                raise GunwAccessError("GUNW unwrapped phase units are not radians")
            required_dtypes = {
                "unwrappedPhase": np.dtype("float32"),
                "coherenceMagnitude": np.dtype("float32"),
                "connectedComponents": np.dtype("uint16"),
                "mask": np.dtype("uint32"),
            }
            for layer, expected_dtype in required_dtypes.items():
                if np.dtype(data_datasets[layer].dtype) != expected_dtype:
                    raise GunwAccessError(
                        f"GUNW 1.5.0 {layer} dtype does not match its product specification"
                    )
            if str(_json_value(data_datasets["coherenceMagnitude"].attrs.get("units", ""))) != "1":
                raise GunwAccessError("GUNW coherence units are not dimensionless")
            if int(data_datasets["mask"].attrs.get("_FillValue", -1)) != 255:
                raise GunwAccessError("GUNW 1.5.0 mask fill value is not 255")
            if int(data_datasets["connectedComponents"].attrs.get("_FillValue", -1)) != 65535:
                raise GunwAccessError("GUNW connected-component fill value is not 65535")

            x_dataset = grid_group["xCoordinates"]
            y_dataset = grid_group["yCoordinates"]
            if geographic_mode:
                full_coordinate_bytes = (
                    int(np.dtype(x_dataset.dtype).itemsize) * width
                    + int(np.dtype(y_dataset.dtype).itemsize) * height
                )
                if full_coordinate_bytes > MAX_FULL_GUNW_COORDINATE_BYTES:
                    raise GunwAccessError(
                        "full GUNW coordinate vectors exceed the memory limit"
                    )
                try:
                    selection = select_geographic_bbox_window(
                        np.asarray(x_dataset[:]),
                        np.asarray(y_dataset[:]),
                        epsg_code=epsg_code,
                        bounds_wgs84=bounds_wgs84,
                        max_samples=MAX_WINDOW_SAMPLES,
                        product_label="GUNW",
                    )
                except (TypeError, ValueError) as exc:
                    raise GunwAccessError(f"geographic GUNW selection failed: {exc}") from exc
                row_start, row_stop = selection.row_start, selection.row_stop
                column_start, column_stop = selection.column_start, selection.column_stop
                sample_count = (row_stop - row_start) * (column_stop - column_start)
            if row_stop > height or column_stop > width:
                raise GunwAccessError("requested window exceeds the GUNW grid bounds")

            estimated_array_bytes = sum(
                int(np.dtype(dataset.dtype).itemsize) * sample_count
                for dataset in data_datasets.values()
            )
            selection_bytes = int(selection.mask.nbytes) if selection is not None else 0
            output_coordinate_bytes = (
                int(np.dtype(x_dataset.dtype).itemsize) * (column_stop - column_start)
                + int(np.dtype(y_dataset.dtype).itemsize) * (row_stop - row_start)
            )
            if estimated_array_bytes + selection_bytes + output_coordinate_bytes > MAX_WINDOW_ARRAY_BYTES:
                raise GunwAccessError(
                    f"window output exceeds the {MAX_WINDOW_ARRAY_BYTES}-byte memory limit"
                )
            arrays = {
                name: np.asarray(dataset[row_start:row_stop, column_start:column_stop])
                for name, dataset in data_datasets.items()
            }
            x_coordinates = np.asarray(x_dataset[column_start:column_stop])
            y_coordinates = np.asarray(y_dataset[row_start:row_stop])
            for axis_name, axis in (("x", x_coordinates), ("y", y_coordinates)):
                if (
                    not np.isfinite(axis).all()
                    or not (
                        np.all(np.diff(axis) > 0)
                        or np.all(np.diff(axis) < 0)
                    )
                ):
                    raise GunwAccessError(
                        f"GUNW {axis_name} coordinate window is not finite and monotonic"
                    )
            grid_metadata = {
                "epsg_code": epsg_code,
                "projection_attributes": {
                    key: _json_value(value)
                    for key, value in projection.attrs.items()
                    if key in {"grid_mapping_name", "spatial_ref", "utm_zone_number"}
                },
                "x_coordinate_convention": "pixel centers per GUNW product specification",
                "y_coordinate_convention": "pixel centers per GUNW product specification",
                "phase_units": "radians",
                "raster_shape": [height, width],
            }
        requested_range_bytes = int(cache.total_requested_bytes)
    except NisarAccessError:
        raise
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise GunwAccessError(f"remote GUNW window read failed ({type(exc).__name__})") from exc

    provenance = {
        "scene_id": scene_id,
        "product_url": product_url,
        "polarization": polarization,
        "frequency": "A",
        "window": [row_start, row_stop, column_start, column_stop],
        "layers": {
            name: {"sha256": _array_sha256(array), "dtype": str(array.dtype), "shape": list(array.shape)}
            for name, array in arrays.items()
        },
        "coordinates": {
            "x_sha256": _array_sha256(x_coordinates),
            "y_sha256": _array_sha256(y_coordinates),
        },
    }
    provider_qa = _provider_qa_reference(
        scene_id, feature["properties"]["collectionName"], provider_qa_summary
    )
    return GunwWindow(
        scene_id=scene_id,
        polarization=polarization,
        row_start=row_start,
        row_stop=row_stop,
        column_start=column_start,
        column_stop=column_stop,
        arrays=arrays,
        x_coordinates=x_coordinates,
        y_coordinates=y_coordinates,
        selection_mask=selection.mask if selection is not None else None,
        identification=identification,
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
                "pathNumber",
                "frameNumber",
                "flightDirection",
            }
        },
        grid_metadata=grid_metadata,
        provider_qa=provider_qa,
        access={
            "read_at_utc": datetime.now(timezone.utc).isoformat(),
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "HTTPS byte-range streaming",
            "fsspec_read_ahead_block_bytes": REMOTE_BLOCK_BYTES,
            "fsspec_range_bytes_requested": requested_range_bytes,
            "maximum_range_bytes": MAX_GUNW_WINDOW_RANGE_BYTES,
            "complete_product_download_requested": False,
            "measurement_values_read": True,
            "output_array_bytes": estimated_array_bytes,
            "full_coordinate_bytes_read_for_geographic_selection": full_coordinate_bytes,
            "window_sample_count": sample_count,
            "geographic_selection": (
                selection.metadata if selection is not None else None
            ),
            "interpretation_limit": (
                "Window access only. This function does not apply phase corrections, "
                "interpret phase as displacement, select coherence thresholds, decode "
                "quality decisions, or make a scientific finding."
            ),
            "window_provenance": provenance,
        },
    )


def decode_gunw_mask(mask: np.ndarray) -> dict[str, np.ndarray]:
    """Expose GUNW 1.5.0 mask fields without imposing analysis thresholds.

    The low byte encodes the water flag and reference/secondary subswaths as
    a three-digit decimal value. Higher bytes carry reference/secondary
    anomaly flags, an ionospheric interpolation flag, and reserved bits.
    """
    values = np.asarray(mask)
    if values.ndim != 2 or values.dtype != np.dtype("uint32"):
        raise GunwAccessError("GUNW 1.5.0 mask must be a two-dimensional uint32 array")
    low_byte = values & np.uint32(0xFF)
    secondary_anomaly = (values >> np.uint32(8)) & np.uint32(0xFF)
    reference_anomaly = (values >> np.uint32(16)) & np.uint32(0xFF)
    return {
        "fill": values == np.uint32(255),
        "water_flag": low_byte // np.uint32(100),
        "reference_subswath": (low_byte // np.uint32(10)) % np.uint32(10),
        "secondary_subswath": low_byte % np.uint32(10),
        "secondary_anomaly_flags": secondary_anomaly,
        "reference_anomaly_flags": reference_anomaly,
        "ionosphere_interpolated": ((values >> np.uint32(24)) & np.uint32(1)) != 0,
        "reserved_bits": (values >> np.uint32(25)) & np.uint32(0x7F),
    }
