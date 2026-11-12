"""Deterministic, source-linked challenge views for retained investigations."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import fmean, median
from typing import Any
from urllib.parse import urlsplit


_SENSITIVITY_TERMS = ("SENSITIVITY", "SPATIAL-SUPPORT", "MASK-SUPPORT")


def _read_linked_json_artifact(
    artifact: dict[str, Any], *, evidence_root: Path, label: str
) -> tuple[dict[str, Any], str]:
    """Read one checksum-linked JSON evidence artifact under the case root."""
    relative_path = artifact.get("relative_path")
    if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
        raise ValueError(f"linked {label} path is invalid")
    root = evidence_root.resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"linked {label} path escapes the project root")
    try:
        content = path.read_bytes()
        record = json.loads(content)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"linked {label} cannot be read") from exc
    digest = sha256(content).hexdigest()
    if digest != artifact.get("sha256"):
        raise ValueError(f"linked {label} checksum does not match")
    if not isinstance(record, dict):
        raise ValueError(f"linked {label} is not a JSON object")
    if (
        record.get("record_type") != artifact.get("record_type")
        or record.get("status") != artifact.get("status")
    ):
        raise ValueError(f"linked {label} identity or status does not match its assessment link")
    return record, digest


def _finite_summary_number(summary: dict[str, Any], key: str) -> float:
    value = summary.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"linked sensitivity summary has an invalid {key}")
    return float(value)


def _finite_cell_number(cell: dict[str, Any], key: str) -> float | None:
    value = cell.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"retained per-cell sensitivity has an invalid {key}")
    return float(value)


def _qa_artifact_provenance(
    *, scene_id: Any, collection: Any, artifact: dict[str, Any], suffix: str, label: str
) -> dict[str, Any]:
    """Validate a product-specific ASF QA artifact link before exposing it."""
    uri = artifact.get("artifact_uri")
    digest = artifact.get("artifact_sha256")
    size = artifact.get("artifact_size_bytes")
    if (
        not isinstance(scene_id, str)
        or not scene_id
        or any(character in scene_id for character in "/\\?#")
        or not isinstance(collection, str)
        or not collection
        or any(character in collection for character in "/\\?#")
        or not isinstance(uri, str)
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or size is not None
        and (
            isinstance(size, bool)
            or not isinstance(size, int)
            or size <= 0
        )
    ):
        raise ValueError(f"case review {label} provenance is incomplete")
    parsed = urlsplit(uri)
    parts = tuple(part for part in parsed.path.split("/") if part)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "nisar.asf.earthdatacloud.nasa.gov"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or len(parts) != 4
        or parts[0] != "NISAR"
        or parts[1] != collection
        or parts[2] != scene_id
        or parts[3] != f"{scene_id}{suffix}"
    ):
        raise ValueError(f"case review {label} URI does not identify its ASF product")
    return {
        "uri": uri,
        "sha256": digest,
        "size_bytes": size,
        "retrieved_at_utc": artifact.get("retrieved_at_utc"),
    }


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError("cannot summarize an empty sensitivity cohort")
    return fmean(values)


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 3:
        return None
    left_mean, right_mean = _mean(left), _mean(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_ss = math.fsum(value * value for value in left_centered)
    right_ss = math.fsum(value * value for value in right_centered)
    if left_ss == 0 or right_ss == 0:
        return None
    result = math.fsum(a * b for a, b in zip(left_centered, right_centered, strict=True)) / math.sqrt(left_ss * right_ss)
    return result if math.isfinite(result) else None


def _require_reproduced_number(actual: Any, expected: float | None, label: str) -> None:
    if expected is None:
        if actual is not None:
            raise ValueError(f"linked sensitivity summary {label} does not reproduce")
    elif (
        isinstance(actual, bool)
        or not isinstance(actual, (int, float))
        or not math.isfinite(actual)
        or not math.isclose(float(actual), expected, rel_tol=1e-9, abs_tol=1e-9)
    ):
        raise ValueError(f"linked sensitivity summary {label} does not reproduce")


def _reproduce_spatial_coverage_variants(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Recompute the displayed WTR sensitivity from retained per-cell values."""
    cells = record.get("per_sar_cell")
    variants = record.get("summary", {}).get("coverage_sensitivity")
    if not isinstance(cells, list) or not cells or not isinstance(variants, list) or not variants:
        raise ValueError("linked spatial sensitivity lacks per-cell values or coverage variants")
    cell_ids: set[tuple[int, int]] = set()
    for cell in cells:
        if not isinstance(cell, dict):
            raise ValueError("linked spatial sensitivity contains an invalid per-cell record")
        row, column = cell.get("sar_row"), cell.get("sar_column")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (row, column)):
            raise ValueError("linked spatial sensitivity contains an invalid SAR cell index")
        if (row, column) in cell_ids:
            raise ValueError("linked spatial sensitivity contains duplicate SAR cells")
        cell_ids.add((row, column))

    reproduced: list[dict[str, Any]] = []
    previous_threshold = 0.0
    for variant in variants:
        if not isinstance(variant, dict):
            raise ValueError("linked spatial sensitivity contains an invalid coverage variant")
        threshold = _finite_summary_number(variant, "minimum_common_valid_wtr_area_fraction")
        if not previous_threshold < threshold <= 1:
            raise ValueError("linked spatial sensitivity thresholds are not ordered and valid")
        previous_threshold = threshold
        water_changes: list[float] = []
        sar_changes: list[float] = []
        for cell in cells:
            if cell.get("sar_measurement_valid") is not True:
                continue
            coverage = _finite_cell_number(cell, "common_valid_wtr_area_fraction")
            change = _finite_cell_number(cell, "water_fraction_change_after_minus_before")
            if coverage is None or change is None or coverage < threshold:
                continue
            sar_change = _finite_cell_number(cell, "sar_log_ratio_db")
            if sar_change is None:
                raise ValueError("valid spatial sensitivity cell lacks a SAR measurement")
            water_changes.append(change)
            sar_changes.append(sar_change)
        if not water_changes:
            raise ValueError("linked spatial sensitivity variant has no supported cells")
        increases = sum(value > 0.05 for value in water_changes)
        decreases = sum(value < -0.05 for value in water_changes)
        expected = {
            "minimum_common_valid_wtr_area_fraction": threshold,
            "sar_cells": len(water_changes),
            "water_fraction_increased_by_more_than_0_05": increases,
            "water_fraction_decreased_by_more_than_0_05": decreases,
            "water_fraction_changed_by_at_most_0_05": len(water_changes) - increases - decreases,
            "median_water_fraction_change": float(median(water_changes)),
            "mean_signed_sar_log_ratio_db": _mean(sar_changes),
            "median_signed_sar_log_ratio_db": float(median(sar_changes)),
            "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db": _pearson(water_changes, sar_changes),
        }
        for key, value in expected.items():
            actual = variant.get(key)
            if key == "sar_cells" or key.startswith("water_fraction_") and key.endswith("_0_05"):
                if isinstance(actual, bool) or not isinstance(actual, int) or actual != value:
                    raise ValueError(f"linked spatial sensitivity summary {key} does not reproduce")
            else:
                _require_reproduced_number(actual, value, key)
        reproduced.append(expected)
    return reproduced


def _spatial_coverage_sweep(cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Calculate a fixed descriptive support sweep from retained per-cell measurements."""
    results: list[dict[str, Any]] = []
    # This range extends the thresholds already documented in the source record.
    # It is a sensitivity display, not an optimized or scientifically preferred cutoff.
    for step in range(10, 20):
        threshold = step / 20
        water_changes: list[float] = []
        sar_changes: list[float] = []
        for cell in cells:
            if cell.get("sar_measurement_valid") is not True:
                continue
            coverage = _finite_cell_number(cell, "common_valid_wtr_area_fraction")
            change = _finite_cell_number(cell, "water_fraction_change_after_minus_before")
            sar_change = _finite_cell_number(cell, "sar_log_ratio_db")
            if coverage is None:
                raise ValueError("valid spatial sensitivity cell lacks optical support coverage")
            if sar_change is None:
                raise ValueError("valid spatial sensitivity cell lacks a SAR measurement")
            if change is None or coverage < threshold:
                continue
            water_changes.append(change)
            sar_changes.append(sar_change)
        if not water_changes:
            results.append({
                "minimum_common_valid_wtr_area_fraction": threshold,
                "sar_cells": 0,
                "mean_signed_sar_log_ratio_db": None,
                "median_signed_sar_log_ratio_db": None,
                "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db": None,
            })
            continue
        results.append({
            "minimum_common_valid_wtr_area_fraction": threshold,
            "sar_cells": len(water_changes),
            "mean_signed_sar_log_ratio_db": _mean(sar_changes),
            "median_signed_sar_log_ratio_db": float(median(sar_changes)),
            "descriptive_pearson_r_water_fraction_change_vs_sar_log_ratio_db": _pearson(
                water_changes, sar_changes
            ),
        })
    return results


def _build_spatial_sensitivity_map(
    record: dict[str, Any], pair_record: dict[str, Any]
) -> dict[str, Any]:
    """Link per-cell sensitivity values to their exact checked SAR measurements and WGS84 corners."""
    grid = pair_record.get("grid")
    window = grid.get("window") if isinstance(grid, dict) else None
    dimensions = window.get("shape") if isinstance(window, dict) else None
    if (
        not isinstance(dimensions, list) or len(dimensions) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in dimensions)
    ):
        raise ValueError("spatial sensitivity pair grid dimensions are invalid")
    rows, columns = dimensions
    corners = grid.get("pixel_corners_wgs84")
    if not isinstance(corners, list) or len(corners) != rows + 1:
        raise ValueError("spatial sensitivity WGS84 corner grid does not match the SAR window")
    normalized_corners: list[list[list[float]]] = []
    for row in corners:
        if not isinstance(row, list) or len(row) != columns + 1:
            raise ValueError("spatial sensitivity WGS84 corner row does not match the SAR window")
        normalized_row: list[list[float]] = []
        for point in row:
            if (
                not isinstance(point, list) or len(point) != 2
                or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in point)
                or not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90
            ):
                raise ValueError("spatial sensitivity contains an invalid WGS84 corner")
            normalized_row.append([float(point[0]), float(point[1])])
        normalized_corners.append(normalized_row)

    measurement = pair_record.get("measurement")
    values = measurement.get("values_db") if isinstance(measurement, dict) else None
    valid_mask = measurement.get("valid_mask") if isinstance(measurement, dict) else None
    common_clear_mask = measurement.get("common_clear_mask") if isinstance(measurement, dict) else None
    for name, matrix in (("values", values), ("validity mask", valid_mask), ("common-clear mask", common_clear_mask)):
        if (
            not isinstance(matrix, list) or len(matrix) != rows
            or any(not isinstance(line, list) or len(line) != columns for line in matrix)
        ):
            raise ValueError(f"spatial sensitivity pair {name} does not match the SAR window")

    source_cells = record.get("per_sar_cell")
    if not isinstance(source_cells, list) or len(source_cells) != rows * columns:
        raise ValueError("spatial sensitivity cells do not cover the SAR window")
    indexed: dict[tuple[int, int], dict[str, Any]] = {}
    for cell in source_cells:
        if not isinstance(cell, dict):
            raise ValueError("spatial sensitivity contains an invalid SAR cell")
        row, column = cell.get("sar_row"), cell.get("sar_column")
        if (
            isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < rows
            or isinstance(column, bool) or not isinstance(column, int) or not 0 <= column < columns
            or (row, column) in indexed
        ):
            raise ValueError("spatial sensitivity contains a duplicate or out-of-window SAR cell")
        indexed[(row, column)] = cell
    if len(indexed) != rows * columns:
        raise ValueError("spatial sensitivity does not identify every SAR window cell")

    output_cells: list[dict[str, Any]] = []
    for row in range(rows):
        for column in range(columns):
            cell = indexed[(row, column)]
            pair_valid = valid_mask[row][column]
            pair_clear = common_clear_mask[row][column]
            if not isinstance(pair_valid, bool) or not isinstance(pair_clear, bool):
                raise ValueError("spatial sensitivity pair masks contain non-boolean values")
            is_valid = pair_valid and pair_clear
            if cell.get("sar_measurement_valid") is not is_valid:
                raise ValueError("spatial sensitivity SAR validity does not match the linked pair masks")
            sar_value = _finite_cell_number(cell, "sar_log_ratio_db")
            pair_value = values[row][column]
            if is_valid:
                if (
                    sar_value is None
                    or isinstance(pair_value, bool)
                    or not isinstance(pair_value, (int, float))
                    or not math.isfinite(pair_value)
                    or not math.isclose(sar_value, float(pair_value), rel_tol=1e-10, abs_tol=1e-10)
                ):
                    raise ValueError("spatial sensitivity SAR value does not match the linked pair measurement")
            elif sar_value is not None:
                raise ValueError("spatial sensitivity exposes SAR values outside the linked pair masks")

            coverage = _finite_cell_number(cell, "common_valid_wtr_area_fraction")
            if coverage is None or not 0 <= coverage <= 1:
                raise ValueError("spatial sensitivity optical coverage is invalid")
            water_change = _finite_cell_number(cell, "water_fraction_change_after_minus_before")
            if water_change is not None and not -1 <= water_change <= 1:
                raise ValueError("spatial sensitivity optical water-fraction change is invalid")
            output_cells.append({
                "row": row,
                "column": column,
                "sar_measurement_valid": is_valid,
                "common_valid_wtr_area_fraction": coverage,
                "sar_log_ratio_db": sar_value,
                "water_fraction_change_after_minus_before": water_change,
            })

    aoi_bounds = window.get("bounds_wgs84") if isinstance(window, dict) else None
    if (
        not isinstance(aoi_bounds, list) or len(aoi_bounds) != 4
        or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in aoi_bounds)
        or aoi_bounds[0] >= aoi_bounds[2] or aoi_bounds[1] >= aoi_bounds[3]
    ):
        raise ValueError("spatial sensitivity AOI bounds are invalid")
    all_points = [point for corner_row in normalized_corners for point in corner_row]
    bounds = [
        min(point[0] for point in all_points),
        min(point[1] for point in all_points),
        max(point[0] for point in all_points),
        max(point[1] for point in all_points),
    ]
    if bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise ValueError("spatial sensitivity pixel-corner extent is degenerate")
    return {
        "status": "DIAGNOSTIC_SPATIAL_ASSOCIATION",
        "coordinate_reference_system": "WGS84 longitude, latitude",
        "bounds_wgs84": bounds,
        "aoi_bounds_wgs84": [float(value) for value in aoi_bounds],
        "rows": rows,
        "columns": columns,
        "pixel_corners_wgs84": normalized_corners,
        "pair_record_sha256": record.get("sources", {}).get("sar_pair_record_sha256"),
        "optical_context_record_sha256": record.get("sources", {}).get("optical_context_record_sha256"),
        "cells": output_cells,
        "interpretation_limit": "Cell locations come from the linked pair's WGS84 pixel corners. SAR response and NASA OPERA DSWx-HLS optical context are shown on common support; this descriptive view does not establish cause, flood extent, or validated product QA.",
    }


def _reproduce_polarization_summary(
    record: dict[str, Any], *, artifacts_by_id: dict[str, dict[str, Any]], evidence_root: Path
) -> dict[str, Any]:
    """Recompute VV/VH summaries from linked common-support cell records."""
    method = record.get("method")
    if not isinstance(method, dict):
        raise ValueError("linked polarization sensitivity lacks its method parameters")
    threshold = _finite_summary_number(method, "minimum_common_valid_wtr_area_fraction")
    if not 0 < threshold <= 1:
        raise ValueError("linked polarization sensitivity threshold is invalid")
    loaded: dict[str, dict[str, Any]] = {}
    for role, evidence_id, checksum_key in (
        ("vv", "NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT", "vv_spatial_record_sha256"),
        ("vh", "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT", "vh_spatial_record_sha256"),
    ):
        artifact = artifacts_by_id.get(evidence_id)
        if artifact is None:
            raise ValueError("polarization sensitivity is missing a linked spatial-support artifact")
        cells_record, _ = _read_linked_json_artifact(
            artifact, evidence_root=evidence_root, label="polarization spatial-support record"
        )
        if record.get("sources", {}).get(checksum_key) != artifact.get("sha256"):
            raise ValueError("polarization sensitivity spatial-support lineage does not match")
        sources = cells_record.get("sources", {})
        if (
            cells_record.get("record_type") != "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC"
            or sources.get("sar_polarization") != role.upper()
            or sources.get("sar_pair_record_sha256") != record.get("sources", {}).get(f"{role}_pair_record_sha256")
        ):
            raise ValueError("polarization sensitivity linked spatial-support identity is invalid")
        loaded[role] = cells_record

    def index_cells(cells_record: dict[str, Any], role: str) -> dict[tuple[int, int], dict[str, Any]]:
        cells = cells_record.get("per_sar_cell")
        if not isinstance(cells, list) or not cells:
            raise ValueError(f"{role} spatial-support record has no retained cell values")
        indexed: dict[tuple[int, int], dict[str, Any]] = {}
        for cell in cells:
            if not isinstance(cell, dict):
                raise ValueError(f"{role} spatial-support record contains an invalid cell")
            row, column = cell.get("sar_row"), cell.get("sar_column")
            if any(isinstance(value, bool) or not isinstance(value, int) for value in (row, column)):
                raise ValueError(f"{role} spatial-support record contains an invalid cell index")
            key = (row, column)
            if key in indexed:
                raise ValueError(f"{role} spatial-support record contains duplicate cells")
            indexed[key] = cell
        return indexed

    vv_cells, vh_cells = index_cells(loaded["vv"], "VV"), index_cells(loaded["vh"], "VH")
    if vv_cells.keys() != vh_cells.keys():
        raise ValueError("linked VV and VH spatial-support cell grids differ")
    water: list[float] = []
    vv_values: list[float] = []
    vh_values: list[float] = []
    for key in sorted(vv_cells):
        vv_cell, vh_cell = vv_cells[key], vh_cells[key]
        coverage = _finite_cell_number(vv_cell, "common_valid_wtr_area_fraction")
        if coverage != _finite_cell_number(vh_cell, "common_valid_wtr_area_fraction"):
            raise ValueError("linked VV and VH optical support differs")
        water_change = _finite_cell_number(vv_cell, "water_fraction_change_after_minus_before")
        if water_change != _finite_cell_number(vh_cell, "water_fraction_change_after_minus_before"):
            raise ValueError("linked VV and VH water-context values differ")
        if (
            vv_cell.get("sar_measurement_valid") is not True
            or vh_cell.get("sar_measurement_valid") is not True
            or coverage is None
            or coverage < threshold
            or water_change is None
        ):
            continue
        vv_change = _finite_cell_number(vv_cell, "sar_log_ratio_db")
        vh_change = _finite_cell_number(vh_cell, "sar_log_ratio_db")
        if vv_change is None or vh_change is None:
            raise ValueError("valid polarization cell lacks a SAR measurement")
        water.append(water_change)
        vv_values.append(vv_change)
        vh_values.append(vh_change)
    if len(water) < 3:
        raise ValueError("linked polarization sensitivity has fewer than three supported cells")
    difference = [vh - vv for vv, vh in zip(vv_values, vh_values, strict=True)]
    difference_median = float(median(difference))
    expected = {
        "common_cells": len(water),
        "water_fraction_change_median": float(median(water)),
        "vv_mean_log_ratio_db": _mean(vv_values),
        "vv_median_log_ratio_db": float(median(vv_values)),
        "vv_pearson_r_water_change_vs_log_ratio": _pearson(water, vv_values),
        "vh_mean_log_ratio_db": _mean(vh_values),
        "vh_median_log_ratio_db": float(median(vh_values)),
        "vh_pearson_r_water_change_vs_log_ratio": _pearson(water, vh_values),
        "vv_vh_pearson_r_log_ratio": _pearson(vv_values, vh_values),
        "vh_minus_vv_mean_db": _mean(difference),
        "vh_minus_vv_median_db": difference_median,
        "vh_minus_vv_median_absolute_deviation_db": float(median([abs(value - difference_median) for value in difference])),
    }
    retained = record.get("summary")
    if not isinstance(retained, dict):
        raise ValueError("linked polarization sensitivity summary is missing")
    for key, value in expected.items():
        if key == "common_cells":
            if isinstance(retained.get(key), bool) or retained.get(key) != value:
                raise ValueError("linked polarization sensitivity common_cells does not reproduce")
        else:
            _require_reproduced_number(retained.get(key), value, key)
    return expected


def _summarize_linked_sensitivity(
    artifact: dict[str, Any], *, artifacts_by_id: dict[str, dict[str, Any]],
    evidence_root: Path, pair_record: dict[str, Any], pair_record_sha256: str,
) -> dict[str, Any]:
    """Expose selected recorded sensitivity outcomes without pooling their metrics."""
    record, digest = _read_linked_json_artifact(
        artifact, evidence_root=evidence_root, label="sensitivity record"
    )
    sources = record.get("sources")
    summary = record.get("summary")
    if not isinstance(sources, dict) or not isinstance(summary, dict):
        raise ValueError("linked sensitivity record lacks sources or summary")
    pair_products = pair_record.get("source_products", {})
    expected_scenes = [
        pair_products.get(role, {}).get("scene_id")
        for role in ("before", "after")
    ] if isinstance(pair_products, dict) else []
    if len(expected_scenes) != 2 or any(not isinstance(scene, str) for scene in expected_scenes):
        raise ValueError("selected SAR pair has no valid scene identity for sensitivity checks")

    record_type = record["record_type"]
    if record_type == "ECHO_RTC_POLARIZATION_SENSITIVITY_DIAGNOSTIC":
        if (
            sources.get("sar_scene_ids") != expected_scenes
            or sources.get("vv_pair_record_sha256") != pair_record_sha256
        ):
            raise ValueError("polarization sensitivity does not identify the selected SAR pair")
        vh_artifact = artifacts_by_id.get("NASA-OPERA-RTC-S1-VH-PAIR")
        vh_spatial = artifacts_by_id.get("NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT")
        vv_spatial = artifacts_by_id.get("NASA-OPERA-RTC-DSWX-SPATIAL-SUPPORT")
        optical = artifacts_by_id.get("NASA-OPERA-DSWX-HLS")
        if (
            vh_artifact is None or vh_spatial is None or vv_spatial is None or optical is None
            or sources.get("vh_pair_record_sha256") != vh_artifact.get("sha256")
            or sources.get("vh_spatial_record_sha256") != vh_spatial.get("sha256")
            or sources.get("vv_spatial_record_sha256") != vv_spatial.get("sha256")
            or sources.get("optical_context_record_sha256") != optical.get("sha256")
        ):
            raise ValueError("polarization sensitivity source lineage does not match the assessment")
        reproduced_summary = _reproduce_polarization_summary(
            record, artifacts_by_id=artifacts_by_id, evidence_root=evidence_root
        )
        cells = reproduced_summary.get("common_cells")
        if isinstance(cells, bool) or not isinstance(cells, int) or cells <= 0:
            raise ValueError("polarization sensitivity common-cell count is invalid")
        return {
            "evidence_id": artifact["evidence_id"],
            "record_type": record_type,
            "source_status": artifact.get("status"),
            "scope": record.get("scope"),
            "result_kind": "RECORDED_POLARIZATION_COMPARISON",
            "summary_basis": "RECOMPUTED_FROM_CHECKSUM_VALIDATED_VV_VH_PER_CELL_RECORDS",
            "summary": reproduced_summary,
            "interpretation_limits": record.get("interpretation_limits", []),
            "sha256": digest,
        }

    if record_type == "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC":
        if (
            sources.get("sar_pair_record_sha256") != pair_record_sha256
            or sources.get("sar_pair_status") != pair_record.get("status")
        ):
            raise ValueError("spatial-support sensitivity does not identify the selected SAR pair")
        optical = artifacts_by_id.get("NASA-OPERA-DSWX-HLS")
        if optical is None or sources.get("optical_context_record_sha256") != optical.get("sha256"):
            raise ValueError("spatial-support sensitivity optical source does not match the assessment")
        variants = _reproduce_spatial_coverage_variants(record)
        return {
            "evidence_id": artifact["evidence_id"],
            "record_type": record_type,
            "source_status": artifact.get("status"),
            "scope": record.get("scope"),
            "result_kind": "RECORDED_OPTICAL_SUPPORT_THRESHOLD_VARIANTS",
            "summary_basis": "RECORDED_VARIANTS_REPRODUCED_AND_FIXED_SWEEP_COMPUTED_FROM_CHECKSUM_VALIDATED_CELLS",
            "summary": {
                "coverage_sensitivity": variants,
                "exploratory_threshold_sweep": _spatial_coverage_sweep(record["per_sar_cell"]),
            },
            "spatial_map": _build_spatial_sensitivity_map(record, pair_record),
            "interpretation_limits": record.get("interpretation_limits", []),
            "sha256": digest,
        }
    return {
        "evidence_id": artifact["evidence_id"],
        "record_type": record_type,
        "source_status": artifact.get("status"),
        "scope": record.get("scope"),
        "result_kind": "SOURCE_LINKED_RECORD_NOT_SUMMARIZED",
        "summary_basis": "CHECKSUM_VALIDATED_RETAINED_RECORD",
        "summary": None,
        "interpretation_limits": record.get("interpretation_limits", []),
        "sha256": digest,
    }


def build_adversarial_challenge(
    assessment: dict[str, Any], *, hypothesis_id: str, assessment_sha256: str,
    evidence_root: Path,
) -> dict[str, Any]:
    """Assemble a review dossier from an already validated assessment.

    This function reorganizes retained evidence and declared relationships,
    and independently reproduces the linked pair's mean and median from its
    checksummed values and masks. It does not verify analyst interpretations
    or revise the assessment.
    """
    hypotheses = assessment.get("hypotheses")
    artifacts = assessment.get("evidence_artifacts")
    follow_ups = assessment.get("follow_up_evidence", [])
    if not isinstance(hypotheses, list) or not isinstance(artifacts, list):
        raise ValueError("assessment hypotheses and evidence artifacts are required")
    selected = [item for item in hypotheses if isinstance(item, dict) and item.get("id") == hypothesis_id]
    if len(selected) != 1:
        raise ValueError("hypothesis must identify exactly one assessment explanation")
    hypothesis = selected[0]
    by_id = {
        artifact["evidence_id"]: artifact
        for artifact in artifacts
        if isinstance(artifact, dict) and isinstance(artifact.get("evidence_id"), str)
    }
    evidence_refs = hypothesis.get("evidence_refs", [])
    relations = hypothesis.get("evidence_assessments", [])
    if not isinstance(evidence_refs, list) or not isinstance(relations, list):
        raise ValueError("hypothesis evidence references are invalid")
    relation_ids = [item.get("evidence_id") for item in relations if isinstance(item, dict)]
    if len(relation_ids) != len(relations) or len(relation_ids) != len(set(relation_ids)):
        raise ValueError("hypothesis evidence relationships are invalid or duplicated")
    if set(evidence_refs) - set(by_id):
        raise ValueError("hypothesis references missing evidence artifacts")

    reviewed_evidence = []
    for relation in relations:
        artifact = by_id.get(relation["evidence_id"])
        if artifact is None or relation["evidence_id"] not in evidence_refs:
            raise ValueError("hypothesis relationship is not linked to a cited source")
        reviewed_evidence.append({
            "evidence_id": relation["evidence_id"],
            "relationship": relation.get("relationship", "UNASSESSED"),
            "rationale": relation.get("rationale", ""),
            "relationship_basis": "RECORDED_ANALYST_ASSESSMENT",
            "role": artifact.get("role", "ROLE_NOT_RECORDED"),
            "source_status": artifact.get("status", "STATUS_NOT_RECORDED"),
            "record_type": artifact.get("record_type", "RECORD_TYPE_NOT_RECORDED"),
            "sha256": artifact.get("sha256"),
            "lineage": artifact.get("lineage", {}),
        })

    observations = assessment.get("observations", {})
    sar = observations.get("sar_diagnostic_measurement", {}) if isinstance(observations, dict) else {}
    scene_ids = sar.get("scene_ids") if isinstance(sar, dict) else None
    if scene_ids is not None and (
        not isinstance(scene_ids, list)
        or len(scene_ids) != 2
        or any(not isinstance(scene_id, str) or not scene_id for scene_id in scene_ids)
        or scene_ids[0] == scene_ids[1]
    ):
        raise ValueError("SAR comparison must identify two distinct acquisition records")
    pair_artifact = by_id.get("SAR-RTC-S1-PAIR")
    measurement_reproduction: dict[str, Any] | None = None
    pair_record: dict[str, Any] | None = None
    pair_record_sha256: str | None = None
    if sar and pair_artifact is None:
        raise ValueError("SAR measurement has no linked comparison source")
    if sar and pair_artifact is not None:
        relative_path = pair_artifact.get("relative_path")
        if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
            raise ValueError("linked SAR comparison source path is invalid")
        root = evidence_root.resolve()
        pair_path = (root / relative_path).resolve()
        if not pair_path.is_relative_to(root):
            raise ValueError("linked SAR comparison source escapes the project root")
        try:
            pair_bytes = pair_path.read_bytes()
            pair_record = json.loads(pair_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("linked SAR comparison source cannot be read") from exc
        pair_record_sha256 = sha256(pair_bytes).hexdigest()
        if pair_record_sha256 != pair_artifact.get("sha256"):
            raise ValueError("linked SAR comparison source checksum does not match")
        if not isinstance(pair_record, dict):
            raise ValueError("linked SAR comparison source is not a JSON object")
        source_products = pair_record.get("source_products", {})
        if not isinstance(source_products, dict) or any(
            not isinstance(source_products.get(role), dict) for role in ("before", "after")
        ):
            raise ValueError("linked SAR comparison source product metadata is invalid")
        source_scene_ids = [
            source_products.get(role, {}).get("scene_id")
            for role in ("before", "after")
        ]
        if (
            pair_record.get("record_type") != pair_artifact.get("record_type")
            or pair_record.get("status") != pair_artifact.get("status")
            or source_scene_ids != scene_ids
        ):
            raise ValueError("SAR comparison identity does not match its linked measurement record")
        pair_measurement = pair_record.get("measurement", {})
        if not isinstance(pair_measurement, dict):
            raise ValueError("linked SAR comparison has no measurement record")
        before_source = source_products.get("before", {})
        after_source = source_products.get("after", {})
        if (
            pair_measurement.get("quantity") != sar.get("quantity")
            or pair_measurement.get("units") != sar.get("units")
            or pair_measurement.get("polarization") != sar.get("polarization")
            or before_source.get("acquisition_start_utc") != sar.get("acquisition_before_utc")
            or after_source.get("acquisition_start_utc") != sar.get("acquisition_after_utc")
            or pair_measurement.get("aoi_pixel_count") != sar.get("aoi_pixel_count")
            or pair_measurement.get("common_clear_pixel_count") != sar.get("common_clear_pixel_count")
        ):
            raise ValueError("SAR measurement metadata or support does not match the linked comparison")
        values = pair_measurement.get("values_db")
        valid_mask = pair_measurement.get("valid_mask")
        common_clear_mask = pair_measurement.get("common_clear_mask")
        if (
            not isinstance(values, list) or not values
            or not isinstance(valid_mask, list) or len(valid_mask) != len(values)
            or not isinstance(common_clear_mask, list) or len(common_clear_mask) != len(values)
        ):
            raise ValueError("linked SAR comparison values and masks are incompatible")
        samples: list[float] = []
        clear_count = 0
        for value_row, valid_row, clear_row in zip(values, valid_mask, common_clear_mask, strict=True):
            if (
                not isinstance(value_row, list) or not isinstance(valid_row, list)
                or not isinstance(clear_row, list)
                or len(value_row) != len(valid_row) or len(value_row) != len(clear_row)
            ):
                raise ValueError("linked SAR comparison rows have incompatible shapes")
            for value, is_valid, is_clear in zip(value_row, valid_row, clear_row, strict=True):
                if is_clear is True:
                    clear_count += 1
                if is_valid is True:
                    if is_clear is not True or not isinstance(value, (int, float)) or not math.isfinite(value):
                        raise ValueError("SAR comparison validity mask admits an invalid or non-clear value")
                    samples.append(float(value))
        if clear_count != sar.get("common_clear_pixel_count") or not samples:
            raise ValueError("SAR comparison common support does not reproduce")
        reproduced_mean = fmean(samples)
        reproduced_median = median(samples)
        for key, reproduced in (("mean_db", reproduced_mean), ("median_db", reproduced_median)):
            observed = sar.get(key)
            if not isinstance(observed, (int, float)) or not math.isclose(
                float(observed), reproduced, rel_tol=1e-10, abs_tol=1e-10
            ):
                raise ValueError(f"SAR {key} does not reproduce from the checksummed measurement")
        measurement_reproduction = {
            "status": "LINKED_MEAN_MEDIAN_AND_MASK_REPRODUCED",
            "valid_sample_count": len(samples),
            "common_clear_pixel_count": clear_count,
            "mean_db": reproduced_mean,
            "median_db": reproduced_median,
            "method": "Mean and median recomputed from the checksummed pair values_db under its recorded valid_mask and common_clear_mask.",
        }
    provider_qa = sar.get("provider_qa_state") if isinstance(sar, dict) else None
    if provider_qa == "PASS":
        qa_gate = "PROVIDER_QA_PASS_RECORDED"
    elif provider_qa == "FAIL" or (isinstance(provider_qa, str) and "HELD" in provider_qa):
        qa_gate = "PROVIDER_QA_HELD"
    else:
        qa_gate = "PROVIDER_QA_UNRESOLVED"

    sensitivity_sources = [
        {
            "evidence_id": evidence_id,
            "role": by_id[evidence_id].get("role", "ROLE_NOT_RECORDED"),
            "source_status": by_id[evidence_id].get("status", "STATUS_NOT_RECORDED"),
            "record_type": by_id[evidence_id].get("record_type", "RECORD_TYPE_NOT_RECORDED"),
            "sha256": by_id[evidence_id].get("sha256"),
        }
        for evidence_id in evidence_refs
        if any(term in evidence_id.upper() for term in _SENSITIVITY_TERMS)
    ]
    if not sensitivity_sources:
        sensitivity_state = "NO_LINKED_SENSITIVITY_RECORD"
    else:
        sensitivity_state = "LINKED_VARIANT_RECORDS_NO_AGGREGATE_STABILITY_VERDICT"
    sensitivity_results = []
    if sensitivity_sources:
        if pair_record is None or pair_record_sha256 is None:
            raise ValueError("linked sensitivity records have no checksummed SAR comparison")
        for source in sensitivity_sources:
            artifact = by_id[source["evidence_id"]]
            sensitivity_results.append(_summarize_linked_sensitivity(
                artifact,
                artifacts_by_id=by_id,
                evidence_root=evidence_root,
                pair_record=pair_record,
                pair_record_sha256=pair_record_sha256,
            ))

    comparability_review: dict[str, Any] | None = None
    comparability_artifact = by_id.get("NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW")
    if comparability_artifact is not None:
        relative_path = comparability_artifact.get("relative_path")
        if not isinstance(relative_path, str) or Path(relative_path).is_absolute():
            raise ValueError("linked acquisition-condition review path is invalid")
        root = evidence_root.resolve()
        review_path = (root / relative_path).resolve()
        if not review_path.is_relative_to(root):
            raise ValueError("linked acquisition-condition review path escapes the project root")
        try:
            review_bytes = review_path.read_bytes()
            review_record = json.loads(review_bytes)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("linked acquisition-condition review cannot be read") from exc
        review_sha256 = sha256(review_bytes).hexdigest()
        if review_sha256 != comparability_artifact.get("sha256"):
            raise ValueError("linked acquisition-condition review checksum does not match")
        if not isinstance(review_record, dict):
            raise ValueError("linked acquisition-condition review is not a JSON object")
        if pair_record is None or pair_record_sha256 is None:
            raise ValueError("acquisition-condition review has no checksummed SAR pair")
        from .opera_rtc_conditions import validate_acquisition_condition_review

        try:
            validate_acquisition_condition_review(
                review_record,
                pair_record=pair_record,
                pair_record_sha256=pair_record_sha256,
                case_id=assessment.get("case_id"),
            )
        except ValueError as exc:
            raise ValueError("linked acquisition-condition review does not reproduce") from exc
        comparability_review = {
            "state": review_record["status"],
            "evidence_id": comparability_artifact["evidence_id"],
            "source_status": comparability_artifact.get("status"),
            "sha256": review_sha256,
            "scope": (
                "LINKED_TO_SELECTED_HYPOTHESIS"
                if comparability_artifact["evidence_id"] in evidence_refs
                else "CASE_WIDE_NOT_LINKED_TO_SELECTED_HYPOTHESIS"
            ),
            "summary": review_record["summary"],
            "comparisons": review_record["comparisons"],
            "interpretation": review_record["interpretation"],
            "limitations": review_record["limitations"],
        }

    alternatives = [
        {
            "hypothesis_id": item.get("id"),
            "statement": item.get("statement"),
            "recorded_state": item.get("state"),
            "testability_state": item.get("testability_state"),
            "would_weaken_if": item.get("would_weaken_if"),
            "required_evidence": item.get("required_evidence", []),
        }
        for item in hypotheses
        if isinstance(item, dict) and item.get("id") != hypothesis_id
    ]
    relevant_follow_ups = [
        {
            "follow_up_id": item.get("follow_up_id"),
            "purpose": item.get("purpose"),
            "availability_state": item.get("availability_state"),
            "action_track": item.get("action_track"),
            "action": item.get("action"),
            "discriminating_question": item.get("discriminating_question"),
            "priority_reason": item.get("priority_reason"),
            "test_design": item.get("test_design"),
            "evidence_refs": item.get("evidence_refs", []),
        }
        for item in follow_ups
        if isinstance(item, dict) and hypothesis_id in item.get("target_hypothesis_ids", [])
    ] if isinstance(follow_ups, list) else []

    return {
        "record_type": "ECHO_ADVERSARIAL_EVIDENCE_CHALLENGE",
        "schema_version": 1,
        "status": "REVIEWABLE_WITH_RECORDED_LIMITS",
        "case_id": assessment.get("case_id"),
        "assessment_sha256": assessment_sha256,
        "assessment_status": assessment.get("status"),
        "hypothesis": {
            "hypothesis_id": hypothesis_id,
            "statement": hypothesis.get("statement"),
            "recorded_state": hypothesis.get("state"),
            "testability_state": hypothesis.get("testability_state"),
            "scope_limit": hypothesis.get("scope_limit"),
            "expected_observation": hypothesis.get("expected_observation"),
            "would_weaken_if": hypothesis.get("would_weaken_if"),
            "testability_reason": hypothesis.get("testability_reason"),
            "required_evidence": hypothesis.get("required_evidence", []),
        },
        "observation": {
            "measurement_recorded": bool(sar),
            "measurement": {
                key: sar[key]
                for key in (
                    "scene_ids", "acquisition_before_utc", "acquisition_after_utc",
                    "sensor", "polarization", "quantity", "equation", "units", "grid_crs",
                    "mean_db", "median_db", "common_clear_pixel_count", "aoi_pixel_count",
                    "common_clear_fraction", "analysis_disposition",
                )
                if isinstance(sar, dict) and key in sar
            },
            "measurement_evidence_id": next((
                artifact.get("evidence_id") for artifact in artifacts
                if isinstance(artifact, dict) and artifact.get("role") == "DIAGNOSTIC_SAR_MEASUREMENT"
            ), None),
            "measurement_reproduction": measurement_reproduction,
            "provider_qa_state": provider_qa or "NOT_RECORDED",
            "qa_gate": qa_gate,
            "interpretation_limit": (
                "A recorded radar-response difference does not identify its physical cause. "
                "Diagnostic or unresolved QA does not permit a validated change claim."
            ),
        },
        "evidence_review": {
            "recorded_relationships": reviewed_evidence,
            "unassessed_referenced_evidence_ids": sorted(set(evidence_refs) - set(relation_ids)),
            "relationship_limit": (
                "Relationships are retained analyst assessments. They are not independently "
                "verified by assembling this challenge view."
            ),
        },
        "sensitivity_review": {
            "state": sensitivity_state,
            "linked_sources": sensitivity_sources,
            "recorded_results": sensitivity_results,
            "interpretation_limit": (
                "Only source-linked variants already present in the assessment are listed. "
                "ECHO does not combine unlike metrics into a stability score or infer a probability."
            ),
        },
        "comparability_review": comparability_review,
        "alternatives": alternatives,
        "next_observations": relevant_follow_ups,
        "reproducibility": {
            "assessment_sha256": assessment_sha256,
            "source_artifacts": [
                {key: source.get(key) for key in ("evidence_id", "sha256", "record_type", "status")}
                for source in reviewed_evidence
            ],
        },
        "interpretation_limit": (
            "This is a deterministic challenge view of one retained assessment, not a new scientific "
            "analysis. It does not alter evidence relationships, QA, measurements, or findings."
        ),
    }


def build_qa_held_observation_challenge(
    case_review: dict[str, Any], *, review_sha256: str,
    preview_record: dict[str, Any], preview_sha256: str,
) -> dict[str, Any]:
    """Return a fail-closed challenge record when a case has no finding to test."""
    candidate = case_review.get("candidate_pair")
    preview = case_review.get("diagnostic_single_observation_preview")
    products = case_review.get("products")
    if (
        not isinstance(candidate, dict) or not isinstance(preview, dict)
        or not isinstance(products, list) or not isinstance(preview_record, dict)
    ):
        raise ValueError("case review does not contain a challengeable observation record")
    preview_source = preview_record.get("source")
    if (
        preview_record.get("record_type") != preview.get("record_type")
        or preview_record.get("scientific_disposition") != preview.get("scientific_disposition")
        or not isinstance(preview_source, dict)
        or preview_source.get("scene_id") != preview.get("scene_id")
        or preview_source.get("provider_qa_status") not in {"FAIL", "QA_FAIL"}
    ):
        raise ValueError("diagnostic preview source does not match the case review and provider QA hold")
    product_records = []
    for product in products:
        if not isinstance(product, dict) or not isinstance(product.get("qa_summary"), dict):
            raise ValueError("case review product QA record is missing")
        qa = product["qa_summary"]
        scene_id = product.get("scene_id")
        collection = candidate.get("collection")
        summary_provenance = _qa_artifact_provenance(
            scene_id=scene_id,
            collection=collection,
            artifact=qa,
            suffix="_QA_SUMMARY.csv",
            label="QA summary",
        )
        report = product.get("qa_report")
        report_provenance = None
        if report is not None:
            if not isinstance(report, dict):
                raise ValueError("case review QA report record is invalid")
            report_provenance = _qa_artifact_provenance(
                scene_id=scene_id,
                collection=collection,
                artifact=report,
                suffix="_QA_REPORT.pdf",
                label="QA report",
            )
        product_records.append({
            "scene_id": scene_id,
            "acquisition_time_utc": product.get("acquisition_time_utc"),
            "provider_qa_state": qa.get("identification_group", "NOT_RECORDED"),
            "qa_summary_uri": summary_provenance["uri"],
            "qa_summary_sha256": summary_provenance["sha256"],
            "qa_summary_size_bytes": summary_provenance["size_bytes"],
            "qa_summary_retrieved_at_utc": summary_provenance["retrieved_at_utc"],
            "qa_report_uri": report_provenance["uri"] if report_provenance else None,
            "qa_report_sha256": report_provenance["sha256"] if report_provenance else None,
            "qa_report_size_bytes": report_provenance["size_bytes"] if report_provenance else None,
            "qa_report_retrieved_at_utc": report_provenance["retrieved_at_utc"] if report_provenance else None,
        })
    failures = [item for item in product_records if item["provider_qa_state"] == "FAIL"]
    preview_product = next((item for item in product_records if item["scene_id"] == preview.get("scene_id")), None)
    if preview_product is None or preview_product["provider_qa_state"] != preview_source.get("provider_qa_status"):
        raise ValueError("diagnostic preview QA does not match its case product record")
    qa_held = candidate.get("qa_status") == "QA_HOLD" or bool(failures)
    return {
        "record_type": "ECHO_ADVERSARIAL_EVIDENCE_CHALLENGE",
        "schema_version": 1,
        "status": "QA_HELD_NO_CHANGE_FINDING" if qa_held else "NO_INVESTIGATION_ASSESSMENT",
        "case_id": case_review.get("case_id"),
        "case_review_sha256": review_sha256,
        "finding": None,
        "observation": {
            "record_type": preview.get("record_type"),
            "scientific_disposition": preview.get("scientific_disposition"),
            "scene_id": preview.get("scene_id"),
            "acquired_at_utc": preview.get("acquired_at_utc"),
            "measurement": preview.get("measurement"),
            "units": preview.get("units"),
            "selected_pixel_center_count": preview.get("selected_pixel_center_count"),
            "source_record_sha256": preview.get("record_sha256"),
            "verified_record_sha256": preview_sha256,
        },
        "candidate_pair": {
            "status": candidate.get("status"),
            "qa_status": candidate.get("qa_status"),
            "interval_days": candidate.get("interval_days"),
            "products": product_records,
        },
        "challenge_result": {
            "change_conclusion": None,
            "change_computation_permitted": False,
            "reason": (
                "No change finding exists to challenge: the available single-scene preview is diagnostic, "
                "and provider QA FAIL on one or more candidate-pair products holds temporal analysis."
                if qa_held else "No retained investigation assessment or change finding is available."
            ),
            "next_step": (
                "Use provider-cleared or corrected products, then repeat compatibility and QA checks before "
                "computing any temporal measurement."
                if qa_held else "Create and assess a source-linked investigation before challenging an interpretation."
            ),
        },
        "interpretation_limit": (
            "A diagnostic single-observation preview is not a temporal change measurement, physical explanation, "
            "event boundary, or validation result."
        ),
    }
