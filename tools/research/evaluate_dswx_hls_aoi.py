#!/usr/bin/env python3
"""Compare two OPERA DSWx-HLS class windows over one bounded WGS84 AOI.

The script keeps source COGs in memory, verifies CMR MD5 checksums, records
SHA-256 provenance, and compares only native-grid pixel centers selected by
the AOI. It does not produce a flood boundary or cross-sensor pixel match.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import md5, sha256
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

import numpy as np
import requests


COLLECTION_CONCEPT_ID = "C2617126679-POCLOUD"
CMR_GRANULE_URL = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
PRODUCT_SPEC_URL = (
    "https://d2pn8kiwq2w21t.cloudfront.net/documents/"
    "OPERA_DSWx-HLS_ProductSpec_v1.0.0_D-107395_RevB.pdf"
)
ASSET_HOST = "archive.podaac.earthdata.nasa.gov"
MAX_ASSET_BYTES = 16 * 1024 * 1024
LAYERS = {
    "B01_WTR.tif": "WTR",
    "B03_CONF.tif": "CONF",
    "B06_WTR-2.tif": "WTR-2",
    "B09_CLOUD.tif": "CLOUD",
}
METADATA_TAGS = (
    "PRODUCT_ID",
    "PRODUCT_VERSION",
    "SOFTWARE_VERSION",
    "PRODUCT_LEVEL",
    "PRODUCT_TYPE",
    "PRODUCT_SOURCE",
    "PROCESSING_DATETIME",
    "SPACECRAFT_NAME",
    "SENSOR",
    "HLS_DATASET",
    "DEM_SOURCE",
    "LANDCOVER_SOURCE",
    "WORLDCOVER_SOURCE",
)


class EvaluationError(ValueError):
    """Raised when a source product or bounded AOI cannot be evaluated."""


def _parse_bounds(value: list[float]) -> tuple[float, float, float, float]:
    if len(value) != 4:
        raise EvaluationError("bounds must be west,south,east,north")
    west, south, east, north = value
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise EvaluationError("bounds are not an ordered WGS84 rectangle")
    return west, south, east, north


def _cmr_product(granule_id: str, session: requests.Session) -> tuple[dict[str, Any], dict[str, Any]]:
    response = session.get(
        CMR_GRANULE_URL,
        params={
            "collection_concept_id": COLLECTION_CONCEPT_ID,
            "granule_ur": granule_id,
            "page_size": 10,
        },
        timeout=(10, 30),
    )
    if response.status_code != 200:
        raise EvaluationError(f"CMR granule lookup returned HTTP {response.status_code}")
    items = response.json().get("items", [])
    matches = [item for item in items if item.get("umm", {}).get("GranuleUR") == granule_id]
    if len(matches) != 1:
        raise EvaluationError(f"CMR did not return exactly one record for {granule_id}")
    return matches[0]["umm"], matches[0].get("meta", {})


def _asset_metadata(umm: dict[str, Any], filename: str) -> tuple[str, int, str]:
    distribution = {
        item.get("Name"): item
        for item in umm.get("DataGranule", {}).get("ArchiveAndDistributionInformation", [])
    }
    details = distribution.get(filename)
    if not isinstance(details, dict):
        raise EvaluationError(f"CMR has no size/checksum metadata for {filename}")
    size = details.get("SizeInBytes")
    checksum = details.get("Checksum", {})
    if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= MAX_ASSET_BYTES:
        raise EvaluationError(f"CMR asset size is invalid or exceeds the cap: {filename}")
    if checksum.get("Algorithm", "").upper() != "MD5" or not isinstance(checksum.get("Value"), str):
        raise EvaluationError(f"CMR MD5 checksum is unavailable for {filename}")
    links = [
        item.get("URL")
        for item in umm.get("RelatedUrls", [])
        if item.get("Type") == "GET DATA"
        and isinstance(item.get("URL"), str)
        and item["URL"].rsplit("/", 1)[-1] == filename
    ]
    if len(links) != 1:
        raise EvaluationError(f"CMR has no unique HTTPS data URL for {filename}")
    parsed = urlsplit(links[0])
    if parsed.scheme != "https" or parsed.hostname != ASSET_HOST or parsed.username or parsed.password:
        raise EvaluationError(f"CMR returned an asset URL outside the PO.DAAC HTTPS host: {filename}")
    return links[0], size, checksum["Value"].lower()


def _read_asset(
    session: Any,
    url: str,
    size: int,
    expected_md5: str,
) -> tuple[bytes, dict[str, Any]]:
    with session.get(
        url,
        headers={"Range": f"bytes=0-{size - 1}"},
        stream=True,
        timeout=(10, 45),
    ) as response:
        if response.status_code != 206:
            raise EvaluationError(f"PO.DAAC did not honor the bounded range (HTTP {response.status_code})")
        expected_range = f"bytes 0-{size - 1}/{size}"
        if response.headers.get("Content-Range", "").strip() != expected_range:
            raise EvaluationError("PO.DAAC Content-Range does not match CMR size metadata")
        chunks: list[bytes] = []
        received = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            received += len(chunk)
            if received > size:
                raise EvaluationError("PO.DAAC asset exceeded the requested byte range")
            chunks.append(chunk)
    payload = b"".join(chunks)
    if len(payload) != size:
        raise EvaluationError("PO.DAAC returned an incomplete product layer")
    actual_md5 = md5(payload).hexdigest()
    if actual_md5 != expected_md5:
        raise EvaluationError("retrieved asset MD5 does not match CMR")
    return payload, {
        "url": url,
        "bytes": len(payload),
        "cmr_md5": expected_md5,
        "retrieved_md5": actual_md5,
        "sha256": sha256(payload).hexdigest(),
        "http_status": 206,
        "content_range": expected_range,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _read_window(
    payload: bytes,
    bounds: tuple[float, float, float, float],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    try:
        import rasterio
        from pyproj import CRS, Transformer
        from rasterio.io import MemoryFile
        from rasterio.windows import from_bounds
    except ImportError as exc:
        raise EvaluationError("bounded DSWx-HLS evaluation requires rasterio and pyproj") from exc

    try:
        with MemoryFile(payload) as memory_file:
            with memory_file.open() as dataset:
                if dataset.count != 1 or dataset.dtypes[0] != "uint8":
                    raise EvaluationError("DSWx-HLS class layer must be single-band UInt8")
                if dataset.crs is None:
                    raise EvaluationError("DSWx-HLS class layer has no CRS")
                crs = CRS.from_user_input(dataset.crs)
                forward = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
                inverse = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                projected_bounds = forward.transform_bounds(*bounds, densify_pts=64, errcheck=True)
                candidate = from_bounds(*projected_bounds, transform=dataset.transform)
                col0 = max(0, int(np.floor(candidate.col_off)))
                row0 = max(0, int(np.floor(candidate.row_off)))
                col1 = min(dataset.width, int(np.ceil(candidate.col_off + candidate.width)))
                row1 = min(dataset.height, int(np.ceil(candidate.row_off + candidate.height)))
                if col0 >= col1 or row0 >= row1:
                    raise EvaluationError("WGS84 AOI does not intersect the DSWx-HLS raster")
                values = dataset.read(1, window=((row0, row1), (col0, col1)))
                rows = np.arange(row0, row1, dtype=np.float64) + 0.5
                cols = np.arange(col0, col1, dtype=np.float64) + 0.5
                col_mesh, row_mesh = np.meshgrid(cols, rows)
                x = dataset.transform.a * col_mesh + dataset.transform.b * row_mesh + dataset.transform.c
                y = dataset.transform.d * col_mesh + dataset.transform.e * row_mesh + dataset.transform.f
                longitude, latitude = inverse.transform(x, y, errcheck=True)
                west, south, east, north = bounds
                selected = (
                    (longitude >= west)
                    & (longitude <= east)
                    & (latitude >= south)
                    & (latitude <= north)
                )
                if not np.any(selected):
                    raise EvaluationError("WGS84 AOI contains no DSWx-HLS pixel centers")
                tags = dataset.tags()
                return values, selected, {
                    "crs": dataset.crs.to_string(),
                    "epsg": dataset.crs.to_epsg(),
                    "transform": [float(value) for value in tuple(dataset.transform)[:6]],
                    "raster_shape": [dataset.height, dataset.width],
                    "window": {"row_start": row0, "row_stop": row1, "column_start": col0, "column_stop": col1},
                    "window_shape": list(values.shape),
                    "selected_pixel_center_count": int(np.count_nonzero(selected)),
                    "nodata": dataset.nodata,
                    "metadata_tags": {key: tags[key] for key in METADATA_TAGS if key in tags},
                }
    except EvaluationError:
        raise
    except Exception as exc:
        raise EvaluationError(f"DSWx-HLS window could not be read ({type(exc).__name__})") from exc


def _histogram(values: np.ndarray, selected: np.ndarray) -> dict[str, int]:
    return {str(code): int(count) for code, count in sorted(Counter(values[selected].ravel().tolist()).items())}


def _transition(
    before: np.ndarray,
    after: np.ndarray,
    selected: np.ndarray,
    *,
    valid_classes: tuple[int, ...] = (0, 1, 2),
    water_classes: tuple[int, ...] = (1, 2),
) -> dict[str, Any]:
    valid = selected & np.isin(before, valid_classes) & np.isin(after, valid_classes)
    matrix = [
        [int(np.count_nonzero(valid & (before == old) & (after == new))) for new in valid_classes]
        for old in valid_classes
    ]
    return {
        "class_order": list(valid_classes),
        "rows_before_columns_after": matrix,
        "common_valid_pixel_count": int(np.count_nonzero(valid)),
        "water_class_codes": list(water_classes),
        "water_class_pixels_before_on_common_valid": int(np.count_nonzero(valid & np.isin(before, water_classes))),
        "water_class_pixels_after_on_common_valid": int(np.count_nonzero(valid & np.isin(after, water_classes))),
    }


def _wtr2_confidence_quality_overlap(
    wtr2: np.ndarray,
    confidence: np.ndarray,
    selected: np.ndarray,
) -> dict[str, Any]:
    water = selected & np.isin(wtr2, (1, 2))
    flagged = water & np.isin(confidence, tuple(range(10, 15)) + tuple(range(20, 25)))
    return {
        "wtr2_water_class_codes": [1, 2],
        "wtr2_water_pixel_count": int(np.count_nonzero(water)),
        "conf_cloud_or_snow_flag_codes": list(range(10, 15)) + list(range(20, 25)),
        "wtr2_water_pixels_with_conf_cloud_or_snow_flag": int(np.count_nonzero(flagged)),
    }


def _map_samples(
    products: dict[str, Any],
    raw_windows: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]],
) -> list[dict[str, Any]]:
    """Serialize bounded native-grid class cells for a provenance-linked map."""
    try:
        from pyproj import CRS, Transformer
    except ImportError as exc:
        raise EvaluationError("map sample serialization requires pyproj") from exc

    grid = products["before"]["assets"]["WTR"]["grid"]
    row0 = grid["window"]["row_start"]
    col0 = grid["window"]["column_start"]
    a, b, c, d, e, f = grid["transform"]
    source_crs = CRS.from_user_input(grid["crs"])
    inverse = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
    selected = raw_windows["before"]["WTR"][1]
    rows, cols = np.nonzero(selected)
    samples: list[dict[str, Any]] = []
    layer_names = ("WTR", "WTR-2", "CONF", "CLOUD")
    for row, col in zip(rows.tolist(), cols.tolist(), strict=True):
        raster_row, raster_col = row0 + row, col0 + col

        def coordinate(pixel_row: float, pixel_col: float) -> list[float]:
            x = a * pixel_col + b * pixel_row + c
            y = d * pixel_col + e * pixel_row + f
            lon, lat = inverse.transform(x, y, errcheck=True)
            return [round(float(lon), 8), round(float(lat), 8)]

        corners = [
            coordinate(raster_row, raster_col),
            coordinate(raster_row, raster_col + 1),
            coordinate(raster_row + 1, raster_col + 1),
            coordinate(raster_row + 1, raster_col),
            coordinate(raster_row, raster_col),
        ]
        sample: dict[str, Any] = {
            "row": int(raster_row),
            "column": int(raster_col),
            "center_wgs84": coordinate(raster_row + 0.5, raster_col + 0.5),
            "corners_wgs84": corners,
        }
        for role in ("before", "after"):
            sample[role] = {
                name: int(raw_windows[role][name][0][row, col])
                for name in layer_names
            }
        samples.append(sample)
    return samples


def _validate_shared_native_grid(
    products: dict[str, Any],
    raw_windows: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]],
) -> None:
    """Require every compared layer to describe the same selected native pixels."""
    grid_fields = ("crs", "transform", "raster_shape", "window", "selected_pixel_center_count")
    reference_grid = products["before"]["assets"]["WTR"]["grid"]
    reference_selection = raw_windows["before"]["WTR"][1]
    for role in ("before", "after"):
        for layer in LAYERS.values():
            grid = products[role]["assets"][layer]["grid"]
            if any(grid[field] != reference_grid[field] for field in grid_fields):
                raise EvaluationError(f"{role} {layer} grid differs from the shared native comparison grid")
            selection = raw_windows[role][layer][1]
            if not np.array_equal(selection, reference_selection):
                raise EvaluationError(f"{role} {layer} AOI pixel-center selection differs from the shared grid")


def _parse_acquisition_time(granule_id: str) -> datetime:
    match = re.search(r"_(\d{8}T\d{6}Z)_\d{8}T\d{6}Z_", granule_id)
    if match is None:
        raise EvaluationError("granule identifier has no supported acquisition timestamp")
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _parse_utc_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvaluationError("RTC-S1 reference times must be ISO timestamps with timezone") from exc
    if parsed.tzinfo is None:
        raise EvaluationError("RTC-S1 reference times must include timezone information")
    return parsed.astimezone(timezone.utc)


def evaluate(
    before_id: str,
    after_id: str,
    bounds: tuple[float, float, float, float],
    rtc_before_time: datetime,
    rtc_after_time: datetime,
) -> dict[str, Any]:
    try:
        import earthaccess
        import rasterio
        import pyproj
    except ImportError as exc:
        raise EvaluationError("install the NISAR optional dependencies for Earthdata/raster access") from exc

    cmr = requests.Session()
    products: dict[str, Any] = {}
    raw_windows: dict[str, dict[str, tuple[np.ndarray, np.ndarray]]] = {}
    auth = earthaccess.login(strategy="netrc", persist=False)
    if not auth.authenticated:
        raise EvaluationError("Earthdata Login did not authenticate with the local netrc")
    session = earthaccess.get_requests_https_session()

    for role, granule_id in (("before", before_id), ("after", after_id)):
        umm, cmr_meta = _cmr_product(granule_id, cmr)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        assets: dict[str, Any] = {}
        raw_windows[role] = {}
        for suffix, layer in LAYERS.items():
            filename = f"{granule_id}_{suffix}"
            url, size, expected_md5 = _asset_metadata(umm, filename)
            payload, access = _read_asset(session, url, size, expected_md5)
            values, selected, grid = _read_window(payload, bounds)
            raw_windows[role][layer] = (values, selected)
            assets[layer] = {
                "filename": filename,
                "access": access,
                "grid": grid,
                "aoi_class_histogram": _histogram(values, selected),
            }
        products[role] = {
            "provider": "NASA PO.DAAC",
            "mission_product": "NASA OPERA L3 DSWx-HLS",
            "collection_concept_id": COLLECTION_CONCEPT_ID,
            "cmr_concept_id": cmr_meta.get("concept-id"),
            "granule_id": umm.get("GranuleUR"),
            "acquisition_time_utc": umm.get("TemporalExtent", {}).get("RangeDateTime", {}).get("BeginningDateTime"),
            "retrieved_at_utc": retrieved_at,
            "assets": assets,
        }

    optical_before_time = _parse_acquisition_time(before_id)
    optical_after_time = _parse_acquisition_time(after_id)
    if optical_after_time <= optical_before_time:
        raise EvaluationError("optical DSWx-HLS acquisitions must be chronologically ordered")

    _validate_shared_native_grid(products, raw_windows)
    before_selection = raw_windows["before"]["WTR"][1]
    after_selection = raw_windows["after"]["WTR"][1]
    if not np.array_equal(before_selection, after_selection):
        raise EvaluationError("before/after DSWx-HLS AOI pixel-center selections differ")

    transitions: dict[str, Any] = {}
    for layer in ("WTR", "WTR-2"):
        before_values = raw_windows["before"][layer][0]
        after_values = raw_windows["after"][layer][0]
        transitions[layer] = _transition(before_values, after_values, before_selection)
    conf_quality_overlap: dict[str, Any] = {}
    for role in ("before", "after"):
        conf_quality_overlap[role] = _wtr2_confidence_quality_overlap(
            raw_windows[role]["WTR-2"][0],
            raw_windows[role]["CONF"][0],
            raw_windows[role]["WTR-2"][1],
        )
    try:
        software = {
            "numpy": np.__version__,
            "rasterio": rasterio.__version__,
            "gdal": rasterio.__gdal_version__,
            "pyproj": pyproj.__version__,
        }
    except Exception:
        software = {"numpy": np.__version__}

    try:
        script_version = version("echo-sar-investigation")
    except PackageNotFoundError:
        script_version = "source-checkout"
    return {
        "record_type": "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION",
        "analysis_question": "How do NASA OPERA DSWx-HLS water-class outputs differ at optical acquisitions bracketing the two nearby OPERA RTC-S1 acquisition dates?",
        "aoi": {"crs": "EPSG:4326", "bounds_west_south_east_north": list(bounds)},
        "source_products": products,
        "temporal_relationship": {
            "optical_before_minus_rtc_before_days": (optical_before_time - rtc_before_time).total_seconds() / 86400,
            "optical_after_minus_rtc_after_days": (optical_after_time - rtc_after_time).total_seconds() / 86400,
            "optical_interval_days": (optical_after_time - optical_before_time).total_seconds() / 86400,
            "rtc_s1_interval_days": (rtc_after_time - rtc_before_time).total_seconds() / 86400,
            "rtc_s1_before_acquisition_utc": rtc_before_time.isoformat(),
            "rtc_s1_after_acquisition_utc": rtc_after_time.isoformat(),
        },
        "processing": {
            "method": "CMR identity lookup; Earthdata-authenticated full COG byte-range reads; CMR MD5 verification; in-memory native-grid AOI pixel-center extraction; no resampling; common-valid class transitions for WTR and WTR-2; bounded WGS84 display-cell serialization.",
            "water_class_codes": [1, 2],
            "valid_transition_classes": [0, 1, 2],
            "software": software,
            "script": "tools/research/evaluate_dswx_hls_aoi.py",
            "script_version": script_version,
        },
        "transitions": transitions,
        "wtr2_confidence_quality_overlap": conf_quality_overlap,
        "map_samples": _map_samples(products, raw_windows),
        "interpretation_limits": [
            "DSWx-HLS is NASA Level-3 classification derived from optical HLS observations, not SAR and not field ground truth.",
            "The AOI is spatially the same WGS84 rectangle as the RTC-S1 sample, but this comparison does not co-register or compare individual optical and SAR pixels.",
            "The WTR layer includes HLS cloud and snow/ice exclusions; a large excluded fraction limits its coverage.",
            "WTR-2 uses different masking and has no WTR cloud mask. CONF describes confidence classes and embeds cloud/snow flags; it is not an independent WTR classification. CLOUD is a separate HLS mask layer.",
            "Water-class counts are product classifications only; they do not establish a flood extent, cause, damage, or SAR validation.",
            "This context record does not alter NISAR product QA or the OPERA RTC-S1 diagnostic disposition.",
        ],
        "references": [
            {"title": "NASA JPL OPERA DSWx-HLS Product Specification v1.0.1", "url": PRODUCT_SPEC_URL},
            {"title": "NASA PO.DAAC OPERA DSWx-HLS Version 1 collection", "url": "https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-HLS_V1"},
        ],
        "source_arrays_written_to_disk": False,
        "bounded_map_samples_written": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, help="Exact CMR GranuleUR for earlier DSWx-HLS product")
    parser.add_argument("--after", required=True, help="Exact CMR GranuleUR for later DSWx-HLS product")
    parser.add_argument("--bounds", required=True, nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--rtc-before-time", required=True, help="ISO8601 acquisition time for the preceding RTC-S1 observation")
    parser.add_argument("--rtc-after-time", required=True, help="ISO8601 acquisition time for the following RTC-S1 observation")
    parser.add_argument("--output", required=True, type=Path, help="Write the JSON evidence record to this path")
    args = parser.parse_args()
    bounds = _parse_bounds(args.bounds)
    record = evaluate(
        args.before,
        args.after,
        bounds,
        _parse_utc_time(args.rtc_before_time),
        _parse_utc_time(args.rtc_after_time),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"status={record['status']}")
    print(f"output={args.output}")
    for layer, result in record["transitions"].items():
        print(
            f"{layer}: common={result['common_valid_pixel_count']} "
            f"water_before={result['water_class_pixels_before_on_common_valid']} "
            f"water_after={result['water_class_pixels_after_on_common_valid']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
