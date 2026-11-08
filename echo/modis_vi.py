"""Bounded, quality-first screening for NASA MODIS MOD13Q1 vegetation indices."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np


RECORD_TYPE = "ECHO_MOD13Q1_VEGETATION_CANDIDATE_SCREEN"
RECORD_STATUS = "QUALITY_AND_TEMPORAL_SUPPORT_LIMITED_NOT_A_VEGETATION_TEST"
NDVI_FILL = -3000
NDVI_SCALE = 0.0001


class ModisScreenError(ValueError):
    """Raised when MOD13Q1 source windows cannot support a linked screen."""


def _date_from_utc(value: str) -> date:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ModisScreenError("linked acquisition timestamps must include a timezone")
    return parsed.astimezone(timezone.utc).date()


def _date_from_doy(year: int, day_of_year: int) -> date:
    return date(year, 1, 1) + timedelta(days=day_of_year - 1)


def _decode_quality(value: int) -> dict[str, int]:
    raw = int(value)
    return {
        "vi_quality": raw & 0b11,
        "vi_usefulness": (raw >> 2) & 0b1111,
        "aerosol_quantity": (raw >> 6) & 0b11,
        "adjacent_cloud": (raw >> 8) & 1,
        "mixed_cloud": (raw >> 10) & 1,
        "land_water_class": (raw >> 11) & 0b111,
        "possible_snow_ice": (raw >> 14) & 1,
        "possible_shadow": (raw >> 15) & 1,
    }


def build_mod13q1_candidate_screen(
    *,
    pair_record: dict[str, Any],
    case_id: str,
    pair_record_sha256: str,
    source_pair_record_path: str,
    before_arrays: dict[str, np.ndarray],
    after_arrays: dict[str, np.ndarray],
    grid: dict[str, Any],
    source_granules: list[dict[str, Any]],
    qa_policy_reference: str,
    processed_at_utc: str,
) -> dict[str, Any]:
    """Screen MOD13Q1 data by exact native-grid cell centers and source QA.

    The acceptance mask is intentionally strict: valid NDVI, MODLAND detailed
    QA class 0, pixel reliability 0 (NASA says "Good Data / Use with
    confidence"), land mask class 1, and no adjacent-cloud, mixed-cloud,
    snow/ice, or shadow flags on both dates. This creates a suitability screen,
    not a claim that the product is a vegetation measurement at SAR acquisition
    instants; the per-pixel composite day remains explicit.
    """
    if pair_record.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        raise ModisScreenError("source is not an OPERA RTC-S1 pair-analysis record")
    source_products = pair_record.get("source_products")
    if not isinstance(source_products, dict):
        raise ModisScreenError("linked SAR pair has no source products")
    required_arrays = {"ndvi", "detailed_qa", "summary_qa", "composite_doy", "aoi_center_mask"}
    if set(before_arrays) != required_arrays or set(after_arrays) != required_arrays:
        raise ModisScreenError("both MODIS dates must supply the five declared native-grid arrays")
    shapes = {np.asarray(values).shape for arrays in (before_arrays, after_arrays) for values in arrays.values()}
    if len(shapes) != 1 or len(next(iter(shapes))) != 2:
        raise ModisScreenError("MODIS date arrays must share one two-dimensional native grid")
    if not isinstance(grid.get("crs"), str) or not isinstance(grid.get("transform"), list) or len(grid["transform"]) != 6:
        raise ModisScreenError("MODIS native-grid CRS and affine transform are required")
    if len(source_granules) != 4:
        raise ModisScreenError("the paired screen requires two temporal composites across two source tiles")
    if any(not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64 for item in source_granules):
        raise ModisScreenError("each source granule must have a SHA-256 checksum")

    sar_dates = [
        _date_from_utc(source_products[role]["acquisition_start_utc"])
        for role in ("before", "after")
    ]
    arrays_by_role = {"before": before_arrays, "after": after_arrays}
    counts: dict[str, Any] = {}
    pixel_rows: list[dict[str, Any]] = []
    selected_masks: dict[str, np.ndarray] = {}
    rows, columns = next(iter(shapes))
    a, b, c, d, e, f = (float(value) for value in grid["transform"])
    for role, sar_date in zip(("before", "after"), sar_dates):
        arrays = arrays_by_role[role]
        ndvi = np.asarray(arrays["ndvi"], dtype=np.int32)
        detailed = np.asarray(arrays["detailed_qa"], dtype=np.uint16)
        reliability = np.asarray(arrays["summary_qa"], dtype=np.int16)
        doy = np.asarray(arrays["composite_doy"], dtype=np.int16)
        inside = np.asarray(arrays["aoi_center_mask"], dtype=bool)
        valid_ndvi = inside & (ndvi != NDVI_FILL) & (ndvi >= -2000) & (ndvi <= 10000)
        usable_day = inside & (doy >= 1) & (doy <= 366)
        if not np.any(inside):
            raise ModisScreenError(f"no MODIS pixel centers fall inside the linked AOI for {role}")
        q = np.zeros(ndvi.shape, dtype=bool)
        decoded = np.zeros((*ndvi.shape, 8), dtype=np.uint8)
        for row, column in zip(*np.nonzero(inside)):
            fields = _decode_quality(int(detailed[row, column]))
            decoded[row, column] = [
                fields["vi_quality"], fields["vi_usefulness"], fields["aerosol_quantity"],
                fields["adjacent_cloud"], fields["mixed_cloud"], fields["land_water_class"],
                fields["possible_snow_ice"], fields["possible_shadow"],
            ]
        q = (
            valid_ndvi
            & (reliability == 0)
            & (decoded[:, :, 0] == 0)
            & (decoded[:, :, 5] == 1)
            & (decoded[:, :, 3] == 0)
            & (decoded[:, :, 4] == 0)
            & (decoded[:, :, 6] == 0)
            & (decoded[:, :, 7] == 0)
        )
        selected_masks[role] = q
        observed_dates = [
            _date_from_doy(sar_date.year, int(doy[row, column]))
            for row, column in zip(*np.nonzero(usable_day))
        ]
        date_offsets = [int((observed - sar_date).days) for observed in observed_dates]
        counts[role] = {
            "aoi_pixel_center_count": int(inside.sum()),
            "valid_ndvi_count": int(valid_ndvi.sum()),
            "good_summary_qa_count": int((inside & (reliability == 0)).sum()),
            "marginal_summary_qa_count": int((inside & (reliability == 1)).sum()),
            "snow_or_cloud_summary_qa_count": int((inside & (reliability == 2)).sum()),
            "cloudy_summary_qa_count": int((inside & (reliability == 3)).sum()),
            "valid_land_class_count": int((inside & (decoded[:, :, 5] == 1)).sum()),
            "strict_accepted_count": int(q.sum()),
            "composite_day_of_year_counts": {
                str(int(day)): int(count)
                for day, count in zip(*np.unique(doy[usable_day], return_counts=True))
            },
            "composite_observation_offset_days_min_max": (
                [min(date_offsets), max(date_offsets)] if date_offsets else None
            ),
            "composite_observation_dates": sorted({value.isoformat() for value in observed_dates}),
            "all_pixel_centers_accepted": bool(q[inside].all()),
        }
        for row, column in zip(*np.nonzero(inside)):
            fields = _decode_quality(int(detailed[row, column]))
            observed = (
                _date_from_doy(sar_date.year, int(doy[row, column])).isoformat()
                if 1 <= int(doy[row, column]) <= 366 else None
            )
            pixel_rows.append({
                "role": role,
                "row": int(row),
                "column": int(column),
                "center_native_crs": [
                    float(c + a * (column + 0.5) + b * (row + 0.5)),
                    float(f + d * (column + 0.5) + e * (row + 0.5)),
                ],
                "ndvi_raw": int(ndvi[row, column]),
                "ndvi_scaled": (
                    float(ndvi[row, column] * NDVI_SCALE) if valid_ndvi[row, column] else None
                ),
                "detailed_qa_raw": int(detailed[row, column]),
                "detailed_qa_decoded": fields,
                "summary_qa": int(reliability[row, column]),
                "composite_observation_date": observed,
                "offset_from_sar_acquisition_days": (
                    int((_date_from_doy(sar_date.year, int(doy[row, column])) - sar_date).days)
                    if observed else None
                ),
                "strictly_accepted": bool(q[row, column]),
            })

    common = selected_masks["before"] & selected_masks["after"]
    temporal_offsets = [
        row["offset_from_sar_acquisition_days"]
        for row in pixel_rows if row["offset_from_sar_acquisition_days"] is not None
    ]
    return {
        "record_type": RECORD_TYPE,
        "schema_version": 1,
        "status": RECORD_STATUS,
        "case_id": case_id,
        "source": {
            "provider": "NASA LP DAAC",
            "mission": "Terra",
            "instrument": "MODIS",
            "short_name": "MOD13Q1",
            "version": "061",
            "doi": "10.5067/MODIS/MOD13Q1.061",
            "collection_concept_id": "C1748066515-LPCLOUD",
            "source_pair_record_path": source_pair_record_path,
            "source_pair_record_sha256": pair_record_sha256,
            "sar_scene_ids": [source_products[role]["scene_id"] for role in ("before", "after")],
            "granules": source_granules,
            "retrieved_at_utc": processed_at_utc,
        },
        "query": {
            "bbox_west_south_east_north": pair_record["grid"]["window"]["bounds_wgs84"],
            "sar_acquisition_dates_utc": [value.isoformat() for value in sar_dates],
            "selected_composite_periods": sorted(
                {
                    (item["period_start_date_utc"], item["period_end_date_utc"])
                    for item in source_granules
                }
            ),
            "native_grid": grid,
            "spatial_resampling": False,
        },
        "method": {
            "name": "native-grid MOD13Q1 NDVI and per-pixel QA/date suitability screen",
            "version": "1",
            "ndvi_scale_factor": NDVI_SCALE,
            "qa_policy_reference": qa_policy_reference,
            "strict_acceptance": {
                "ndvi_in_product_valid_range": True,
                "summary_pixel_reliability_equals": 0,
                "detailed_modland_vi_quality_equals": 0,
                "land_water_class_equals_land": 1,
                "adjacent_cloud_mixed_cloud_snow_shadow_absent": True,
                "both_dates_must_pass": True,
            },
            "no_sar_association_computed": True,
            "no_vegetation_change_conclusion": True,
        },
        "observations": {
            "before": counts["before"],
            "after": counts["after"],
            "common_strictly_accepted_pixel_count": int(common.sum()),
            "all_retained_composite_observation_offsets_days_min_max": (
                [min(temporal_offsets), max(temporal_offsets)] if temporal_offsets else None
            ),
            "paired_timing_suitable_for_sar_date_comparison": bool(
                temporal_offsets and all(value == 0 for value in temporal_offsets)
            ),
            "strict_common_support_suitable_for_test": bool(common.any()),
        },
        "bounded_pixel_records": pixel_rows,
        "interpretation": (
            "MOD13Q1 offers finer native posting than the previously screened coarse soil-moisture products, but its values are per-pixel selections from 16-day composites, not measurements at the SAR acquisition instants. The retained AOI window has no pixels passing the declared strict paired vegetation QA and land-support gates, and the selected per-pixel composite days are not all aligned with the SAR acquisition dates. No NDVI difference or NDVI/SAR association is computed; this product does not test H4 or validate the diagnostic SAR response."
        ),
        "limitations": [
            "The MOD13Q1 composite selects a source observation within a 16-day interval; per-pixel composite days are not interchangeable with nominal composite start dates.",
            "The strict screen requires NASA summary reliability 0, DetailedQA MODLAND class 0, land mask class 1, and no adjacent cloud, mixed cloud, snow/ice, or shadow flags.",
            "No native-grid pixels pass both temporal QA gates on accepted land support; zero common accepted cells means change and association are not calculated.",
            "At least one retained early-period pixel observation occurs after the earlier SAR acquisition, so nominal temporal proximity alone would misrepresent alignment.",
            "This candidate screen does not clear the Sentinel-1/OPERA provider QA state or establish a vegetation driver.",
        ],
    }


def validate_mod13q1_candidate_screen(
    record: dict[str, Any],
    *,
    pair_record: dict[str, Any],
    pair_record_sha256: str,
    case_id: str,
) -> None:
    """Validate identity, provenance, and internally reported screen counts."""
    source = record.get("source", {})
    pair_products = pair_record.get("source_products", {})
    expected_scenes = [pair_products.get(role, {}).get("scene_id") for role in ("before", "after")]
    if (
        record.get("record_type") != RECORD_TYPE
        or record.get("schema_version") != 1
        or record.get("status") != RECORD_STATUS
        or record.get("case_id") != case_id
        or source.get("provider") != "NASA LP DAAC"
        or source.get("short_name") != "MOD13Q1"
        or source.get("version") != "061"
        or source.get("source_pair_record_sha256") != pair_record_sha256
        or source.get("sar_scene_ids") != expected_scenes
    ):
        raise ModisScreenError("MOD13Q1 screen identity or linked SAR source is invalid")
    if record.get("query", {}).get("bbox_west_south_east_north") != pair_record.get("grid", {}).get("window", {}).get("bounds_wgs84"):
        raise ModisScreenError("MOD13Q1 screen does not use the linked SAR AOI")
    granules = source.get("granules")
    if (
        not isinstance(granules, list)
        or len(granules) != 4
        or len({item.get("granule_id") for item in granules if isinstance(item, dict)}) != 4
        or any(
            not isinstance(item, dict)
            or item.get("provider") != "NASA LP DAAC"
            or item.get("collection_concept_id") != "C1748066515-LPCLOUD"
            or not isinstance(item.get("sha256"), str)
            or len(item["sha256"]) != 64
            or not isinstance(item.get("source_url"), str)
            for item in granules
        )
    ):
        raise ModisScreenError("MOD13Q1 screen source granule provenance is incomplete")
    pixels = record.get("bounded_pixel_records")
    if not isinstance(pixels, list) or not pixels:
        raise ModisScreenError("MOD13Q1 bounded AOI pixels are missing")
    by_role = {role: [item for item in pixels if item.get("role") == role] for role in ("before", "after")}
    if not all(by_role.values()) or len(by_role["before"]) != len(by_role["after"]):
        raise ModisScreenError("MOD13Q1 before/after bounded AOI support is inconsistent")
    observations = record.get("observations", {})
    for role, rows in by_role.items():
        summary = observations.get(role, {})
        if (
            summary.get("aoi_pixel_center_count") != len(rows)
            or summary.get("strict_accepted_count") != sum(bool(item.get("strictly_accepted")) for item in rows)
            or summary.get("valid_ndvi_count") != sum(item.get("ndvi_scaled") is not None for item in rows)
            or summary.get("good_summary_qa_count") != sum(item.get("summary_qa") == 0 for item in rows)
            or summary.get("valid_land_class_count") != sum(item.get("detailed_qa_decoded", {}).get("land_water_class") == 1 for item in rows)
        ):
            raise ModisScreenError(f"MOD13Q1 {role} counts do not reproduce from bounded pixel records")
    strict_by_cell = {
        role: {(item["row"], item["column"]) for item in rows if item.get("strictly_accepted")}
        for role, rows in by_role.items()
    }
    common = strict_by_cell["before"] & strict_by_cell["after"]
    if (
        observations.get("common_strictly_accepted_pixel_count") != len(common)
        or observations.get("strict_common_support_suitable_for_test") is not bool(common)
    ):
        raise ModisScreenError("MOD13Q1 common-support count does not reproduce from pixel records")
    if record.get("method", {}).get("no_sar_association_computed") is not True:
        raise ModisScreenError("MOD13Q1 screen must not claim an uncomputed SAR association")
