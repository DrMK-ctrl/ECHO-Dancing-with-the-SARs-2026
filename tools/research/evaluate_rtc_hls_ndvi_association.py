#!/usr/bin/env python3
"""Area-weight HLS L30/S30 NDVI changes onto diagnostic OPERA RTC-S1 cells."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
from affine import Affine
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.strtree import STRtree


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_THRESHOLDS = (0.25, 0.50, 0.75)
SCALE = 0.0001


class AssociationError(ValueError):
    """Raised when source records do not support the requested overlay."""


def _read_json(path: Path, expected_type: str) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    record = json.loads(payload)
    if record.get("record_type") != expected_type:
        raise AssociationError(f"unexpected record type in {path}")
    return record, payload


def _load_hls_pixels(record: dict[str, Any]) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray]:
    observations = record.get("observations")
    if not isinstance(observations, list) or len(observations) != 2:
        raise AssociationError("HLS record must contain an ordered before/after pair")
    arrays_by_date = []
    masks_by_date = []
    nir_band = record.get("processing", {}).get("nir_band") or record.get("query", {}).get("nir_band") or "B05"
    for observation in observations:
        asset = observation.get("asset", {})
        relative = asset.get("relative_path")
        expected_hash = asset.get("sha256")
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise AssociationError("HLS subset path must be project-relative")
        path = (PROJECT_ROOT / relative).resolve()
        if not path.is_relative_to(PROJECT_ROOT) or not path.is_file():
            raise AssociationError("HLS bounded subset is unavailable or escapes the project")
        payload = path.read_bytes()
        if sha256(payload).hexdigest() != expected_hash or len(payload) != asset.get("size_bytes"):
            raise AssociationError("HLS bounded subset checksum or size validation failed")
        with np.load(path, allow_pickle=False) as subset:
            if set(subset.files) != {"B04", nir_band, "Fmask", "AOI"}:
                raise AssociationError("HLS subset does not contain the declared bands and AOI pixel mask")
            arrays = {
                "B04": subset["B04"].copy(),
                "NIR": subset[nir_band].copy(),
                "Fmask": subset["Fmask"].copy(),
                "AOI": subset["AOI"].copy(),
            }
        grid = observation.get("grid", {})
        window = grid.get("window", {})
        expected_shape = (window.get("height"), window.get("width"))
        if any(array.shape != expected_shape for array in arrays.values()):
            raise AssociationError("HLS array shape does not match the recorded pixel window")
        arrays_by_date.append(arrays)
        masks_by_date.append(_clear_land_ndvi_mask(arrays))
    before_grid, after_grid = (item.get("grid", {}) for item in observations)
    if (
        before_grid.get("crs") != after_grid.get("crs")
        or before_grid.get("transform") != after_grid.get("transform")
        or before_grid.get("window") != after_grid.get("window")
    ):
        raise AssociationError("HLS pair must share exact CRS, affine transform, and native pixel window")
    before_mask, after_mask = masks_by_date
    if before_mask.shape != after_mask.shape:
        raise AssociationError("HLS paired masks have different shapes")
    ndvi_before = _ndvi(arrays_by_date[0])
    ndvi_after = _ndvi(arrays_by_date[1])
    common = before_mask & after_mask
    delta = np.full(common.shape, np.nan, dtype=np.float64)
    delta[common] = ndvi_after[common] - ndvi_before[common]
    return observations, delta, common


def _clear_land_ndvi_mask(arrays: dict[str, np.ndarray]) -> np.ndarray:
    red = arrays["B04"].astype(np.float64)
    nir = arrays["NIR"].astype(np.float64)
    fmask = arrays["Fmask"].astype(np.uint8)
    valid = (
        arrays["AOI"].astype(bool)
        &
        (red != -9999)
        & (nir != -9999)
        & (fmask != 255)
        & ((fmask & 0b00011110) == 0)
        & ((fmask & 0b00100000) == 0)
        & (((fmask >> 6) & 0b11) != 0b11)
        & ((red + nir) > 0)
    )
    return valid


def _ndvi(arrays: dict[str, np.ndarray]) -> np.ndarray:
    red = arrays["B04"].astype(np.float64) * SCALE
    nir = arrays["NIR"].astype(np.float64) * SCALE
    denominator = red + nir
    result = np.full(red.shape, np.nan, dtype=np.float64)
    valid = _clear_land_ndvi_mask(arrays)
    result[valid] = (nir[valid] - red[valid]) / denominator[valid]
    return result


def _checked_polygon(points: list[list[float]], transform: Any, label: str) -> Polygon:
    polygon = Polygon([transform(float(point[0]), float(point[1])) for point in points])
    if not polygon.is_valid or polygon.is_empty or polygon.area <= 0:
        raise AssociationError(f"{label} has invalid or zero-area geometry")
    return polygon


def _correlation(x: np.ndarray, y: np.ndarray) -> float | None:
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def _offset_hours(optical_timestamp: str, sar_timestamp: str) -> float:
    optical = datetime.fromisoformat(optical_timestamp.replace("Z", "+00:00"))
    sar = datetime.fromisoformat(sar_timestamp.replace("Z", "+00:00"))
    if optical.tzinfo is None or sar.tzinfo is None:
        raise AssociationError("acquisition timestamps must include a timezone")
    return (optical - sar).total_seconds() / 3600


def evaluate_association(
    pair: dict[str, Any],
    hls: dict[str, Any],
    pair_payload: bytes,
    hls_payload: bytes,
    *,
    thresholds: tuple[float, ...] = DEFAULT_THRESHOLDS,
) -> dict[str, Any]:
    if pair.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        raise AssociationError("unexpected RTC-S1 record type")
    if pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON":
        raise AssociationError("RTC-S1 pair is not an eligible diagnostic comparison")
    if pair.get("provider_qa", {}).get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION":
        raise AssociationError("RTC-S1 provider QA state is missing or unexpected")
    product_variant = hls.get("source", {}).get("product_variant", "L30")
    if product_variant not in {"L30", "S30"} or hls.get("record_type") != f"ECHO_HLS_{product_variant}_VEGETATION_CONTEXT_SCREEN":
        raise AssociationError("unexpected HLS vegetation-context record type")
    if hls.get("status") != "DESCRIPTIVE_OPTICAL_CONTEXT_NOT_CAUSAL_TEST":
        raise AssociationError("HLS L30 record is not labeled as descriptive context")
    if pair.get("case_id") and hls.get("case_id") != pair.get("case_id"):
        raise AssociationError("HLS and SAR records refer to different investigation cases")
    if len(thresholds) == 0 or any(not 0 < threshold <= 1 for threshold in thresholds):
        raise AssociationError("coverage thresholds must be in (0, 1]")

    pair_grid = pair.get("grid", {})
    window = pair_grid.get("window", {})
    shape = window.get("shape")
    if not isinstance(shape, list) or len(shape) != 2:
        raise AssociationError("RTC-S1 pixel window shape is missing")
    rows, columns = shape
    measurement = pair.get("measurement", {})
    sar_values = np.asarray(measurement.get("values_db"), dtype=np.float64)
    sar_common = np.asarray(measurement.get("common_clear_mask"), dtype=bool)
    sar_valid = np.asarray(measurement.get("valid_mask"), dtype=bool)
    if any(array.shape != (rows, columns) for array in (sar_values, sar_common, sar_valid)):
        raise AssociationError("RTC-S1 arrays do not match the recorded source grid window")
    if measurement.get("quantity") != "signed_gamma0_log_ratio_db" or measurement.get("units") != "dB":
        raise AssociationError("RTC-S1 record does not contain the declared log-ratio measurement")
    sar_valid &= sar_common & np.isfinite(sar_values)

    hls_observations, ndvi_delta, common_hls = _load_hls_pixels(hls)
    sar_observations = [pair.get("source_products", {}).get(role, {}) for role in ("before", "after")]
    optical_times = [item.get("temporal_extent_utc", {}).get("BeginningDateTime") for item in hls_observations]
    sar_times = [item.get("acquisition_start_utc") for item in sar_observations]
    if any(not isinstance(value, str) for value in optical_times + sar_times):
        raise AssociationError("paired optical and SAR acquisition timestamps are required")
    hls_grid = hls_observations[0]["grid"]
    hls_window = hls_grid["window"]
    hls_transform = Affine(*hls_grid["transform"])
    hls_crs = CRS.from_user_input(hls_grid["crs"])
    sar_crs = CRS.from_user_input(pair_grid["crs"])
    hls_to_sar = Transformer.from_crs(hls_crs, sar_crs, always_xy=True).transform
    sar_to_sar = Transformer.from_crs("EPSG:4326", sar_crs, always_xy=True).transform

    optical_polygons: list[Polygon] = []
    optical_delta: list[float] = []
    if pair_grid.get("window", {}).get("bounds_wgs84") != hls.get("query", {}).get("bbox_west_south_east_north"):
        raise AssociationError("RTC-S1 and HLS records do not share the same WGS84 AOI")
    row_offset = hls_window["row_offset"]
    column_offset = hls_window["column_offset"]
    for row, column in zip(*np.nonzero(common_hls)):
        grid_row = int(row + row_offset)
        grid_column = int(column + column_offset)
        corners = [
            hls_transform @ (grid_column, grid_row),
            hls_transform @ (grid_column + 1, grid_row),
            hls_transform @ (grid_column + 1, grid_row + 1),
            hls_transform @ (grid_column, grid_row + 1),
            hls_transform @ (grid_column, grid_row),
        ]
        polygon = Polygon([hls_to_sar(x, y) for x, y in corners])
        if not polygon.is_valid or polygon.is_empty or polygon.area <= 0:
            raise AssociationError(f"HLS cell ({row}, {column}) has invalid transformed geometry")
        optical_polygons.append(polygon)
        optical_delta.append(float(ndvi_delta[row, column]))
    if not optical_polygons:
        raise AssociationError("no common clear-land HLS pixels remain for spatial comparison")

    tree = STRtree(optical_polygons)
    corner_rows = pair_grid.get("pixel_corners_wgs84")
    if not isinstance(corner_rows, list) or len(corner_rows) != rows + 1:
        raise AssociationError("RTC-S1 cell-corner rows are missing or invalid")
    if any(not isinstance(row, list) or len(row) != columns + 1 for row in corner_rows):
        raise AssociationError("RTC-S1 cell-corner columns are missing or invalid")
    projected_corners = [
        [sar_to_sar(float(point[0]), float(point[1])) for point in row]
        for row in corner_rows
    ]

    per_cell: list[dict[str, Any]] = []
    for row in range(rows):
        for column in range(columns):
            ring = [
                projected_corners[row][column],
                projected_corners[row][column + 1],
                projected_corners[row + 1][column + 1],
                projected_corners[row + 1][column],
                projected_corners[row][column],
            ]
            sar_polygon = Polygon(ring)
            if not sar_polygon.is_valid or sar_polygon.area <= 0:
                raise AssociationError(f"RTC-S1 cell ({row}, {column}) has invalid geometry")
            represented_area = 0.0
            weighted_delta = 0.0
            for raw_index in tree.query(sar_polygon):
                index = int(raw_index)
                area = sar_polygon.intersection(optical_polygons[index]).area
                if area <= sar_polygon.area * 1e-12:
                    continue
                represented_area += area
                weighted_delta += area * optical_delta[index]
            fraction = min(1.0, represented_area / sar_polygon.area)
            ndvi_change = weighted_delta / represented_area if represented_area else None
            per_cell.append({
                "row": row,
                "column": column,
                "sar_valid": bool(sar_valid[row, column]),
                "sar_log_ratio_db": float(sar_values[row, column]) if sar_valid[row, column] else None,
                "common_clear_land_ndvi_area_fraction": fraction,
                "area_weighted_ndvi_change_after_minus_before": ndvi_change,
            })

    summaries = []
    for threshold in thresholds:
        selected = [
            cell for cell in per_cell
            if cell["sar_valid"]
            and cell["common_clear_land_ndvi_area_fraction"] >= threshold
            and cell["area_weighted_ndvi_change_after_minus_before"] is not None
        ]
        ndvi_changes = np.asarray([cell["area_weighted_ndvi_change_after_minus_before"] for cell in selected])
        sar_changes = np.asarray([cell["sar_log_ratio_db"] for cell in selected])
        summaries.append({
            "minimum_common_clear_land_ndvi_area_fraction": threshold,
            "sar_cells": len(selected),
            "median_area_weighted_ndvi_change": float(np.median(ndvi_changes)) if len(selected) else None,
            "mean_signed_sar_log_ratio_db": float(np.mean(sar_changes)) if len(selected) else None,
            "median_signed_sar_log_ratio_db": float(np.median(sar_changes)) if len(selected) else None,
            "descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db": _correlation(ndvi_changes, sar_changes),
            "inferential_statistics": "NOT_COMPUTED; neighboring cells are spatially dependent and RTC-S1 provider QA is diagnostic",
        })

    return {
        "record_type": f"ECHO_RTC_HLS_{product_variant}_NDVI_SPATIAL_ASSOCIATION",
        "schema_version": 1,
        "status": "DIAGNOSTIC_SPATIAL_ASSOCIATION",
        "case_id": hls.get("case_id"),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "sar_pair_record_sha256": sha256(pair_payload).hexdigest(),
            "hls_vegetation_record_sha256": sha256(hls_payload).hexdigest(),
            "sar_scene_ids": [item.get("scene_id") for item in pair.get("source_products", {}).values()],
            "optical_granule_ids": [item.get("granule_id") for item in hls_observations],
            "optical_acquisition_times_utc": optical_times,
            "sar_acquisition_times_utc": sar_times,
            "optical_minus_sar_offsets_hours": [
                _offset_hours(optical_times[index], sar_times[index]) for index in range(2)
            ],
            "optical_input_sensor": f"{product_variant} optical inputs via NASA/USGS HLS {product_variant}",
            "optical_derived_quantity": "NDVI change on common clear, non-water HLS pixels",
            "sar_quantity": measurement.get("quantity"),
            "sar_polarization": measurement.get("polarization"),
            "sar_provider_qa": pair.get("provider_qa"),
        },
        "method": {
            "spatial_join": "Transform HLS native 30 m pixel polygons and RTC-S1 pixel corner rings into the SAR projected CRS, then intersect polygons and area-weight NDVI change onto SAR cells; no resampling.",
            "common_optical_support": "Only HLS pixel centers inside the AOI with valid red/NIR/Fmask, no cloud/adjacency/shadow/snow/water flags, and no high-aerosol flag on both dates contribute.",
            "coverage_thresholds": list(thresholds),
            "association_metric": "Pearson correlation between area-weighted NDVI change and signed SAR gamma-zero log-ratio; descriptive only.",
            "software": {"numpy": np.__version__, "shapely": __import__("shapely").__version__, "pyproj": __import__("pyproj").__version__},
        },
        "per_cell": per_cell,
        "coverage_sensitivity": summaries,
        "interpretation_limits": [
            "The per-cell association is observational and descriptive; it does not demonstrate that vegetation change caused the SAR response.",
            "Only common clear-land pixels contribute, so the result does not represent cloud-, water-, snow-, or high-aerosol-masked areas.",
            "The RTC-S1 pair lacks a consolidated provider QA verdict and remains diagnostic.",
            "NDVI is a vegetation spectral index, not a direct biomass or soil-moisture measurement.",
            "The association is not an independent SAR validation or a calibrated predictive model.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sar-record", type=Path, required=True)
    parser.add_argument("--hls-record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pair, pair_payload = _read_json(args.sar_record, "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS")
    hls_payload = args.hls_record.read_bytes()
    hls = json.loads(hls_payload)
    record = evaluate_association(pair, hls, pair_payload, hls_payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"status={record['status']}")
    for item in record["coverage_sensitivity"]:
        print(f"threshold={item['minimum_common_clear_land_ndvi_area_fraction']} cells={item['sar_cells']} correlation={item['descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db']}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
