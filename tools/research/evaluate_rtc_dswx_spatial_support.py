#!/usr/bin/env python3
"""Area-weight NASA DSWx-HLS classes onto retained OPERA RTC-S1 cells.

This is a diagnostic common-support analysis, not a flood classifier or causal
test. It uses exact polygon intersections between native-grid cell footprints;
it does not resample either product.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from shapely.strtree import STRtree


class SpatialSupportError(ValueError):
    """Raised when source records cannot support a spatial overlay."""


VALID_WTR_CLASSES = {0, 1, 2}
WATER_CLASSES = {1, 2}
DEFAULT_COVERAGE_THRESHOLDS = (0.50, 0.75, 0.90, 0.95)


def _polygon_wgs84(points: Any, project: Any, label: str) -> Polygon:
    if not isinstance(points, list) or len(points) < 4:
        raise SpatialSupportError(f"{label} must contain a closed cell ring")
    try:
        polygon = Polygon([project(float(point[0]), float(point[1])) for point in points])
    except (TypeError, ValueError, IndexError) as exc:
        raise SpatialSupportError(f"{label} has invalid coordinates") from exc
    if not polygon.is_valid or polygon.is_empty or polygon.area <= 0:
        raise SpatialSupportError(f"{label} is not a valid non-zero-area cell")
    return polygon


def evaluate_spatial_support(
    pair: dict[str, Any],
    optical: dict[str, Any],
    *,
    coverage_thresholds: tuple[float, ...] = DEFAULT_COVERAGE_THRESHOLDS,
) -> dict[str, Any]:
    """Summarize common WTR area and its descriptive relationship to SAR change."""
    if pair.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        raise SpatialSupportError("unexpected RTC-S1 record type")
    if optical.get("record_type") != "ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON":
        raise SpatialSupportError("unexpected DSWx-HLS record type")
    if pair.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON":
        raise SpatialSupportError("RTC-S1 pair is not an eligible diagnostic comparison")
    qa = pair.get("provider_qa", {})
    if qa.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION":
        raise SpatialSupportError("RTC-S1 provider QA state is missing or unexpected")
    if optical.get("status") != "NASA_OPTICAL_CONTEXT_ONLY_NOT_SAR_VALIDATION":
        raise SpatialSupportError("DSWx-HLS record is not labeled as optical context only")
    if len(coverage_thresholds) == 0 or any(not 0 < value <= 1 for value in coverage_thresholds):
        raise SpatialSupportError("coverage thresholds must be in (0, 1]")

    pair_grid = pair.get("grid", {})
    window = pair_grid.get("window", {})
    shape = window.get("shape")
    if not isinstance(shape, list) or len(shape) != 2:
        raise SpatialSupportError("RTC-S1 window shape is missing")
    rows, columns = shape
    sar_values = np.asarray(pair.get("measurement", {}).get("values_db"), dtype=np.float64)
    sar_common = np.asarray(pair.get("measurement", {}).get("common_clear_mask"), dtype=bool)
    sar_valid = np.asarray(pair.get("measurement", {}).get("valid_mask"), dtype=bool)
    if any(array.shape != (rows, columns) for array in (sar_values, sar_common, sar_valid)):
        raise SpatialSupportError("RTC-S1 value and mask shapes do not match its grid window")
    sar_valid &= sar_common & np.isfinite(sar_values)
    measurement = pair.get("measurement", {})
    if measurement.get("quantity") != "signed_gamma0_log_ratio_db" or measurement.get("units") != "dB":
        raise SpatialSupportError("RTC-S1 measurement is not the expected signed gamma-zero log-ratio in dB")
    if pair_grid.get("window", {}).get("bounds_wgs84") != optical.get("aoi", {}).get("bounds_west_south_east_north"):
        raise SpatialSupportError("RTC-S1 and DSWx-HLS records do not share the same WGS84 AOI")

    corner_rows = pair_grid.get("pixel_corners_wgs84")
    if not isinstance(corner_rows, list) or len(corner_rows) != rows + 1:
        raise SpatialSupportError("RTC-S1 pixel-corner grid has an invalid row count")
    if any(not isinstance(row, list) or len(row) != columns + 1 for row in corner_rows):
        raise SpatialSupportError("RTC-S1 pixel-corner grid has an invalid column count")

    before_product = optical.get("source_products", {}).get("before", {})
    after_product = optical.get("source_products", {}).get("after", {})
    before_asset = before_product.get("assets", {}).get("WTR", {})
    after_asset = after_product.get("assets", {}).get("WTR", {})
    before_grid = before_asset.get("grid", {})
    after_grid = after_asset.get("grid", {})
    if not before_product.get("granule_id") or not after_product.get("granule_id"):
        raise SpatialSupportError("DSWx-HLS source granule identifiers are missing")
    if before_grid.get("crs") != after_grid.get("crs") or before_grid.get("transform") != after_grid.get("transform"):
        raise SpatialSupportError("before and after DSWx-HLS WTR grids are not identical")
    if before_grid.get("window_shape") != after_grid.get("window_shape"):
        raise SpatialSupportError("before and after DSWx-HLS WTR windows differ")
    samples = optical.get("map_samples")
    if not isinstance(samples, list) or not samples:
        raise SpatialSupportError("DSWx-HLS record has no retained cell geometries")
    expected_sample_count = before_grid.get("selected_pixel_center_count")
    if (
        not isinstance(expected_sample_count, int)
        or expected_sample_count != len(samples)
        or after_grid.get("selected_pixel_center_count") != expected_sample_count
    ):
        raise SpatialSupportError("retained DSWx-HLS cells do not match both products' AOI-center counts")
    processing = optical.get("processing", {})
    if set(processing.get("valid_transition_classes", [])) != VALID_WTR_CLASSES:
        raise SpatialSupportError("DSWx-HLS valid WTR class contract does not match the retained record")
    if set(processing.get("water_class_codes", [])) != WATER_CLASSES:
        raise SpatialSupportError("DSWx-HLS water-class contract does not match the retained record")

    try:
        target_crs = CRS.from_user_input(pair_grid["crs"])
        transformer = Transformer.from_crs("EPSG:4326", target_crs, always_xy=True)
    except (KeyError, ValueError) as exc:
        raise SpatialSupportError("RTC-S1 grid CRS is missing or invalid") from exc
    project = transformer.transform

    optical_polygons: list[Polygon] = []
    before_classes: list[int] = []
    after_classes: list[int] = []
    for index, sample in enumerate(samples):
        polygon = _polygon_wgs84(sample.get("corners_wgs84"), project, f"DSWx cell {index}")
        try:
            before_class = sample["before"]["WTR"]
            after_class = sample["after"]["WTR"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SpatialSupportError(f"DSWx cell {index} has no valid WTR class values") from exc
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (before_class, after_class)):
            raise SpatialSupportError(f"DSWx cell {index} has non-integer WTR classes")
        optical_polygons.append(polygon)
        before_classes.append(before_class)
        after_classes.append(after_class)

    tree = STRtree(optical_polygons)
    rows_of_corners = [[None] * (columns + 1) for _ in range(rows + 1)]
    for row in range(rows + 1):
        for column in range(columns + 1):
            point = corner_rows[row][column]
            try:
                rows_of_corners[row][column] = project(float(point[0]), float(point[1]))
            except (TypeError, ValueError, IndexError) as exc:
                raise SpatialSupportError("RTC-S1 grid contains invalid WGS84 corner coordinates") from exc

    per_cell: list[dict[str, Any]] = []
    for row in range(rows):
        for column in range(columns):
            ring = [
                rows_of_corners[row][column],
                rows_of_corners[row][column + 1],
                rows_of_corners[row + 1][column + 1],
                rows_of_corners[row + 1][column],
                rows_of_corners[row][column],
            ]
            sar_polygon = Polygon(ring)
            if not sar_polygon.is_valid or sar_polygon.area <= 0:
                raise SpatialSupportError(f"RTC-S1 cell ({row}, {column}) has invalid geometry")
            total_area = sar_polygon.area
            represented_area = 0.0
            common_area = 0.0
            water_before_area = 0.0
            water_after_area = 0.0
            for raw_index in tree.query(sar_polygon):
                index = int(raw_index)
                intersection_area = sar_polygon.intersection(optical_polygons[index]).area
                if intersection_area <= total_area * 1e-12:
                    continue
                represented_area += intersection_area
                if before_classes[index] not in VALID_WTR_CLASSES or after_classes[index] not in VALID_WTR_CLASSES:
                    continue
                common_area += intersection_area
                if before_classes[index] in WATER_CLASSES:
                    water_before_area += intersection_area
                if after_classes[index] in WATER_CLASSES:
                    water_after_area += intersection_area
            if represented_area > total_area * 1.01:
                raise SpatialSupportError(f"overlapping DSWx cells exceed RTC-S1 cell area at ({row}, {column})")
            cell = {
                "sar_row": row,
                "sar_column": column,
                "sar_log_ratio_db": float(sar_values[row, column]) if sar_valid[row, column] else None,
                "sar_measurement_valid": bool(sar_valid[row, column]),
                "represented_optical_area_fraction": min(1.0, represented_area / total_area),
                "common_valid_wtr_area_fraction": min(1.0, common_area / total_area),
                "water_fraction_before_on_common_area": water_before_area / common_area if common_area else None,
                "water_fraction_after_on_common_area": water_after_area / common_area if common_area else None,
                "water_fraction_change_after_minus_before": (water_after_area - water_before_area) / common_area if common_area else None,
            }
            per_cell.append(cell)

    summaries = []
    for threshold in coverage_thresholds:
        selected = [
            cell for cell in per_cell
            if cell["sar_measurement_valid"]
            and cell["common_valid_wtr_area_fraction"] >= threshold
            and cell["water_fraction_change_after_minus_before"] is not None
        ]
        water_delta = np.asarray([cell["water_fraction_change_after_minus_before"] for cell in selected])
        sar_delta = np.asarray([cell["sar_log_ratio_db"] for cell in selected])
        changed_up = int(np.count_nonzero(water_delta > 0.05))
        changed_down = int(np.count_nonzero(water_delta < -0.05))
        unchanged = len(selected) - changed_up - changed_down
        correlation = None
        if len(selected) >= 3 and np.std(water_delta) > 0 and np.std(sar_delta) > 0:
            correlation = float(np.corrcoef(water_delta, sar_delta)[0, 1])
        summaries.append({
            "minimum_common_valid_wtr_area_fraction": threshold,
            "sar_cells": len(selected),
            "water_fraction_increased_by_more_than_0_05": changed_up,
            "water_fraction_decreased_by_more_than_0_05": changed_down,
            "water_fraction_changed_by_at_most_0_05": unchanged,
            "median_water_fraction_change": float(np.median(water_delta)) if len(selected) else None,
            "mean_signed_sar_log_ratio_db": float(np.mean(sar_delta)) if len(selected) else None,
            "median_signed_sar_log_ratio_db": float(np.median(sar_delta)) if len(selected) else None,
            "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db": correlation,
            "inferential_statistics": "NOT_COMPUTED; neighboring cells are spatially dependent and RTC-S1 QA remains diagnostic",
        })

    return {
        "record_type": "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC",
        "schema_version": 1,
        "status": "DIAGNOSTIC_SPATIAL_ASSOCIATION",
        "scope": "Exact area-weighted spatial overlay of NASA OPERA DSWx-HLS WTR classes onto NASA OPERA RTC-S1 30 m cells; not a flood boundary, causal test, or validated finding.",
        "sources": {
            "sar_pair_status": pair["status"],
            "sar_provider_qa": qa,
            "sar_scene_ids": [item.get("scene_id") for item in pair.get("source_products", {}).values()],
            "sar_acquisition_times_utc": [item.get("acquisition_start_utc") for item in pair.get("source_products", {}).values()],
            "sar_pair_record_sha256": None,
            "sar_quantity": pair.get("measurement", {}).get("quantity"),
            "sar_equation": pair.get("measurement", {}).get("equation"),
            "sar_grid_crs": pair_grid.get("crs"),
            "optical_product": "NASA OPERA L3 DSWx-HLS WTR classification; Sentinel-2 HLS-derived optical context",
            "optical_granule_ids": [before_product["granule_id"], after_product["granule_id"]],
            "optical_acquisition_times_utc": [before_product.get("acquisition_time_utc"), after_product.get("acquisition_time_utc")],
            "optical_wtr_source_sha256": [
                before_asset.get("access", {}).get("sha256"),
                after_asset.get("access", {}).get("sha256"),
            ],
            "optical_grid_crs": before_grid.get("crs"),
        },
        "method": {
            "spatial_join": "Transform native cell corner rings to the RTC-S1 projected CRS and intersect polygons; use exact overlap area to calculate DSWx class fractions per SAR cell.",
            "resampling": "NONE",
            "common_optical_support": "Only DSWx cells whose before and after WTR codes are both in the retained valid class set [0, 1, 2] contribute to either date's fractions.",
            "water_classes": sorted(WATER_CLASSES),
            "coverage_fraction_denominator": "Full RTC-S1 cell area; DSWx samples are the retained AOI display cells, so edge coverage may be incomplete.",
            "sar_validity": "The retained common-clear and finite-value masks are both required.",
            "sensitivity": "Descriptive summaries repeated at multiple minimum common-valid optical area coverage thresholds.",
            "association_metric": "Pearson correlation of per-cell optical water-fraction change with signed RTC-S1 gamma-zero log-ratio; descriptive only.",
            "software": {"numpy": np.__version__, "shapely": __import__("shapely").__version__, "pyproj": __import__("pyproj").__version__},
        },
        "references": [
            {
                "provider": "NASA PO.DAAC",
                "title": "OPERA Dynamic Surface Water Extent from Harmonized Landsat Sentinel-2 product (Version 1)",
                "doi": "10.5067/OPDSW-PL3V1",
                "url": "https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-HLS_V1",
            },
        ],
        "summary": {
            "sar_window_cells": rows * columns,
            "sar_valid_cells": int(np.count_nonzero(sar_valid)),
            "dswx_retained_cells": len(samples),
            "dswx_cells_valid_at_both_dates": sum(
                before_class in VALID_WTR_CLASSES and after_class in VALID_WTR_CLASSES
                for before_class, after_class in zip(before_classes, after_classes, strict=True)
            ),
            "overlap_cells_with_any_common_valid_wtr_area": sum(cell["common_valid_wtr_area_fraction"] > 0 for cell in per_cell),
            "coverage_sensitivity": summaries,
        },
        "per_sar_cell": per_cell,
        "interpretation_limits": [
            "RTC-S1 has no consolidated provider PASS/FAIL disposition; this result cannot promote the pair beyond diagnostic status.",
            "DSWx-HLS is optical product context derived from HLS, not independent field truth or SAR validation.",
            "Acquisition proximity and spatial association do not establish causation; the retained pair spans about 24 days.",
            "No inferential statistic is reported because neighboring pixels are spatially dependent and no evaluation design was specified.",
            "Optical common-area fractions summarize categorical product output; they do not estimate subpixel water area.",
            "The retained DSWx cells were selected for AOI display, so incomplete edge coverage is reported rather than imputed.",
        ],
    }


def evaluate_files(pair_path: Path, optical_path: Path, output_path: Path) -> dict[str, Any]:
    pair = json.loads(pair_path.read_text(encoding="utf-8"))
    optical = json.loads(optical_path.read_text(encoding="utf-8"))
    result = evaluate_spatial_support(pair, optical)
    result["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["sources"]["sar_pair_record_sha256"] = sha256(pair_path.read_bytes()).hexdigest()
    result["sources"]["sar_pair_record"] = str(pair_path)
    result["sources"]["optical_context_record_sha256"] = sha256(optical_path.read_bytes()).hexdigest()
    result["sources"]["optical_context_record"] = str(optical_path)
    result["processing"] = {
        "script": "tools/research/evaluate_rtc_dswx_spatial_support.py",
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "created_at_utc": result["created_at_utc"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", type=Path, default=root / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json")
    parser.add_argument("--optical", type=Path, default=root / "data/research/dswx-hls-context-T163-349925-2026-11-07.json")
    parser.add_argument("--output", type=Path, default=root / "data/research/opera-rtc-dswx-spatial-support-T163-349925-2026-11-08.json")
    args = parser.parse_args()
    result = evaluate_files(args.pair, args.optical, args.output)
    print(json.dumps({"status": result["status"], "summary": result["summary"], "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
