#!/usr/bin/env python3
"""Retrieve and quality-screen bounded NASA SPL2SMAP_S 3 km context."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import earthaccess
import h5py
import numpy as np
from pyproj import Transformer
from shapely import transform as shapely_transform
from shapely.geometry import box as shapely_box


COLLECTION_ID = "C2938663471-NSIDC_CPRD"
SHORT_NAME = "SPL2SMAP_S"
VERSION = "003"
CELL_SIZE_3KM_M = 3002.69
HARMONY_URL = (
    "https://harmony.earthdata.nasa.gov/ogc-api-edr/1.1.0/collections/"
    f"{COLLECTION_ID}/cube"
)
VARIABLES = (
    "Soil_Moisture_Retrieval_Data_3km/disagg_soil_moisture_3km",
    "Soil_Moisture_Retrieval_Data_3km/retrieval_qual_flag_3km",
    "Soil_Moisture_Retrieval_Data_3km/surface_flag_3km",
    "Soil_Moisture_Retrieval_Data_3km/SMAP_Sentinel_overpass_timediff_hr_3km",
    "Soil_Moisture_Retrieval_Data_3km/latitude_3km",
    "Soil_Moisture_Retrieval_Data_3km/longitude_3km",
)
GROUP = "Soil_Moisture_Retrieval_Data_3km"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _plain(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.generic):
        return value.item()
    return value


def _find_cmr_granule(day: date, bbox: tuple[float, float, float, float], granule_id: str) -> dict[str, Any]:
    matches = earthaccess.search_data(
        short_name=SHORT_NAME,
        version=VERSION,
        temporal=(day.isoformat(), day.isoformat()),
        bounding_box=bbox,
        count=100,
    )
    for item in matches:
        umm = item.get("umm", {})
        if umm.get("GranuleUR") == granule_id:
            collection = umm.get("CollectionReference", {})
            if collection.get("ShortName") != SHORT_NAME or collection.get("Version") != VERSION:
                raise ValueError("CMR granule collection identity differs from the requested product")
            return {
                "granule_id": granule_id,
                "concept_id": item.get("meta", {}).get("concept-id"),
                "temporal_extent": umm.get("TemporalExtent"),
                "provider_dates": umm.get("ProviderDates", []),
                "collection_id": COLLECTION_ID,
                "version": collection.get("Version"),
                "short_name": collection.get("ShortName"),
            }
    raise ValueError(f"requested granule is absent from the bounded CMR search: {granule_id}")


def _summarize_subset(
    path: Path,
    expected_granule_id: str,
    bbox: tuple[float, float, float, float],
) -> dict[str, Any]:
    payload = path.read_bytes()
    with h5py.File(path, "r") as source:
        history = json.loads(source.attrs["history_json"])
        request_url = history[0]["parameters"][0]["request_url"]
        returned_granule_id = request_url.split("/granules/")[-1].split(".h5")[0] + ".h5"
        if returned_granule_id != expected_granule_id:
            raise ValueError(
                f"Harmony returned {returned_granule_id}, expected {expected_granule_id}"
            )
        group = source[GROUP]
        moisture = np.asarray(group["disagg_soil_moisture_3km"][()], dtype=np.float64)
        retrieval_flags = np.asarray(group["retrieval_qual_flag_3km"][()], dtype=np.uint16)
        surface_flags = np.asarray(group["surface_flag_3km"][()], dtype=np.uint16)
        time_difference = np.asarray(
            group["SMAP_Sentinel_overpass_timediff_hr_3km"][()], dtype=np.float64
        )
        latitude = np.asarray(group["latitude_3km"][()], dtype=np.float64)
        longitude = np.asarray(group["longitude_3km"][()], dtype=np.float64)
        row_index = np.asarray(group["EASE_row_index_3km"][()], dtype=np.uint16)
        column_index = np.asarray(group["EASE_column_index_3km"][()], dtype=np.uint16)
        x = np.asarray(group["x"][()], dtype=np.float64)
        y = np.asarray(group["y"][()], dtype=np.float64)
        if not (
            moisture.shape == retrieval_flags.shape == surface_flags.shape
            == time_difference.shape == latitude.shape == longitude.shape
            == row_index.shape == column_index.shape
        ):
            raise ValueError("Harmony subset variables have incompatible grid shapes")
        fill = float(group["disagg_soil_moisture_3km"].attrs.get("_FillValue", -9999.0))
        valid_min = float(group["disagg_soil_moisture_3km"].attrs["valid_min"])
        valid_max = float(group["disagg_soil_moisture_3km"].attrs["valid_max"])
        finite_values = np.isfinite(moisture) & (moisture != fill)
        in_range = finite_values & (moisture >= valid_min) & (moisture <= valid_max)
        # NSIDC defines retrieval_qual_flag == 0 as good overall retrieval quality.
        quality_eligible = in_range & (retrieval_flags == 0) & (surface_flags == 0)
        grid_identity = sha256(
            b"".join(
                np.ascontiguousarray(array).tobytes()
                for array in (latitude, longitude, row_index, column_index)
            )
        ).hexdigest()
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True)
        aoi = shapely_transform(
            shapely_box(bbox[0], bbox[1], bbox[2], bbox[3]),
            transformer.transform,
            interleaved=False,
        )
        cell_support = []
        for row in range(moisture.shape[0]):
            for column in range(moisture.shape[1]):
                cell = shapely_box(
                    x[column] - CELL_SIZE_3KM_M / 2,
                    y[row] - CELL_SIZE_3KM_M / 2,
                    x[column] + CELL_SIZE_3KM_M / 2,
                    y[row] + CELL_SIZE_3KM_M / 2,
                )
                intersection_area = aoi.intersection(cell).area
                if intersection_area > 0:
                    cell_support.append({
                        "ease_row_index": int(row_index[row, column]),
                        "ease_column_index": int(column_index[row, column]),
                        "center_longitude": float(longitude[row, column]),
                        "center_latitude": float(latitude[row, column]),
                        "aoi_intersection_fraction": float(intersection_area / aoi.area),
                        "cell_intersection_fraction": float(intersection_area / cell.area),
                    })
        history_summary = [
            {
                "program": step.get("program"),
                "version": step.get("version"),
                "date_time": step.get("date_time"),
            }
            for step in history
        ]
        try:
            relative_asset_path = path.resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError as exc:
            raise ValueError("bounded source subset must be stored inside the ECHO project") from exc
        return {
            "granule_id": returned_granule_id,
            "harmony_request_url": HARMONY_URL,
            "history": history_summary,
            "grid_shape": list(moisture.shape),
            "grid_identity_sha256": grid_identity,
            "quality_eligible_flat_indices": np.flatnonzero(quality_eligible).astype(int).tolist(),
            "grid_centers_wgs84": {
                "longitude_min": float(np.nanmin(longitude)),
                "longitude_max": float(np.nanmax(longitude)),
                "latitude_min": float(np.nanmin(latitude)),
                "latitude_max": float(np.nanmax(latitude)),
            },
            "aoi_cell_support": {
                "method": "Transform the requested WGS84 rectangle to EPSG:6933 and intersect each posted 3002.69 m square EASE-Grid cell polygon; no resampling.",
                "cell_size_m": CELL_SIZE_3KM_M,
                "intersecting_cells": cell_support,
                "total_aoi_area_coverage_fraction": float(
                    sum(item["aoi_intersection_fraction"] for item in cell_support)
                ),
            },
            "soil_moisture": {
                "variable": f"{GROUP}/disagg_soil_moisture_3km",
                "units": _plain(group["disagg_soil_moisture_3km"].attrs["units"]),
                "valid_min": valid_min,
                "valid_max": valid_max,
                "fill_value": fill,
                "finite_nonfill_cell_count": int(finite_values.sum()),
                "in_range_cell_count": int(in_range.sum()),
                "out_of_range_cell_count": int((finite_values & ~in_range).sum()),
                "quality_eligible_cell_count": int(quality_eligible.sum()),
                "interpretation": "algorithm-derived SMAP/Sentinel-1 soil-moisture estimate; no accepted ECHO measurement",
            },
            "quality_flags": {
                "retrieval_flag_variable": f"{GROUP}/retrieval_qual_flag_3km",
                "retrieval_flag_zero_good_cell_count": int((retrieval_flags == 0).sum()),
                "retrieval_quality_compromised_bit_0_cell_count": int(((retrieval_flags & 1) != 0).sum()),
                "retrieval_attempt_failed_bit_1_cell_count": int(((retrieval_flags & 2) != 0).sum()),
                "retrieval_failed_bit_2_cell_count": int(((retrieval_flags & 4) != 0).sum()),
                "disaggregated_brightness_temperature_bad_bit_6_cell_count": int(((retrieval_flags & 64) != 0).sum()),
                "saturated_water_content_bit_7_cell_count": int(((retrieval_flags & 128) != 0).sum()),
                "surface_flag_variable": f"{GROUP}/surface_flag_3km",
                "surface_flag_zero_cell_count": int((surface_flags == 0).sum()),
            },
            "smap_sentinel_time_difference_field": {
                "variable": f"{GROUP}/SMAP_Sentinel_overpass_timediff_hr_3km",
                "minimum_raw_value": float(np.nanmin(time_difference[time_difference != -9999.0])),
                "maximum_raw_value": float(np.nanmax(time_difference[time_difference != -9999.0])),
                "field_name_unit_semantics": "field name and NSIDC documentation indicate hours while the returned NetCDF units attribute says seconds; the raw value is retained without conversion",
            },
            "asset": {
                "relative_path": relative_asset_path,
                "size_bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
            },
        }


def retrieve_screen(
    *,
    case_id: str,
    bbox: tuple[float, float, float, float],
    before_date: date,
    after_date: date,
    before_granule: str,
    after_granule: str,
    output_dir: Path,
    output_record: Path,
) -> dict[str, Any]:
    if not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
        raise ValueError("bbox bounds are invalid")
    if after_date <= before_date:
        raise ValueError("after_date must follow before_date")
    if not earthaccess.login(strategy="netrc", persist=False):
        raise RuntimeError("Earthdata Login authentication failed")
    observations = []
    session = earthaccess.get_requests_https_session()
    for label, day, granule_id in (
        ("before", before_date, before_granule),
        ("after", after_date, after_granule),
    ):
        cmr = _find_cmr_granule(day, bbox, granule_id)
        day_text = day.isoformat()
        params = {
            "bbox": ",".join(str(value) for value in bbox),
            "datetime": f"{day_text}T00:00:00Z/{day_text}T23:59:59Z",
            "parameter-name": ",".join(VARIABLES),
            "f": "application/netcdf",
            "maxResults": "1",
        }
        response = session.get(HARMONY_URL, params=params, timeout=(20, 120))
        response.raise_for_status()
        if "netcdf" not in response.headers.get("content-type", "").lower():
            raise RuntimeError(f"Harmony did not return a NetCDF subset for {day_text}")
        if len(response.content) > 2 * 1024 * 1024:
            raise RuntimeError("Harmony response exceeded the bounded-subset size limit")
        output_dir.mkdir(parents=True, exist_ok=True)
        asset_path = output_dir / f"spl2smap-s-{case_id}-{label}-{day_text}-bounded.nc4"
        asset_path.write_bytes(response.content)
        subset = _summarize_subset(asset_path, granule_id, bbox)
        subset["harmony_request_parameters"] = params
        subset["query_date_utc"] = day_text
        subset["cmr"] = cmr
        subset["retrieval"] = {
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "query_parameters": params,
        }
        observations.append(subset)

    before, after = observations
    same_grid = (
        before["grid_shape"] == after["grid_shape"]
        and before["grid_identity_sha256"] == after["grid_identity_sha256"]
    )
    eligible_pairs = (
        len(
            set(before["quality_eligible_flat_indices"])
            & set(after["quality_eligible_flat_indices"])
        )
        if same_grid
        else None
    )
    no_valid_paired_cells = eligible_pairs == 0
    record = {
        "record_type": "ECHO_SMAP_SENTINEL_SOIL_MOISTURE_CANDIDATE_SCREEN",
        "schema_version": 1,
        "status": (
            "CANDIDATE_RETRIEVED_QUALITY_LIMITED_NOT_USABLE_FOR_CAUSAL_TEST"
            if no_valid_paired_cells
            else "CANDIDATE_HAS_QA_ELIGIBLE_CELLS_REQUIRES_SCIENTIFIC_REVIEW"
        ),
        "case_id": case_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "NASA NSIDC DAAC",
            "mission_inputs": ["NASA SMAP radiometer", "Copernicus Sentinel-1A/B radar"],
            "product": "SMAP/Sentinel-1 L2 Radiometer/Radar 30-Second Scene 3 km EASE-Grid Soil Moisture",
            "short_name": SHORT_NAME,
            "version": VERSION,
            "collection_concept_id": COLLECTION_ID,
            "doi": "10.5067/ASB0EQO2LYJV",
            "measurement_role": "screened context candidate; not independent Sentinel-1 validation and not an ECHO-accepted measurement",
            "reference_urls": [
                "https://nsidc.org/data/spl2smap_s/versions/3",
                "https://nsidc.org/sites/default/files/spl2smap_s-v003-userguide_0.pdf",
            ],
        },
        "query": {
            "collection": COLLECTION_ID,
            "bbox_west_south_east_north": list(bbox),
            "requested_resolution": "3 km EASE-Grid; source grid cells retained without resampling",
            "coordinate_reference_system": "EPSG:6933 (WGS 84 / NSIDC EASE-Grid 2.0 Global)",
            "requested_variables": [value.split("/")[-1] for value in VARIABLES],
            "same_grid_before_after": same_grid,
        },
        "observations": observations,
        "comparison": {
            "paired_quality_eligible_cells": eligible_pairs if same_grid else None,
            "disposition": (
                "NO_VALID_PAIRED_CELLS; no paired grid cells meet the stated numeric range and product quality-flag criteria"
                if no_valid_paired_cells
                else "QA-eligible paired cells exist; scientific suitability and independence still require review"
            ),
            "not_an_independent_validation": "The retrieval combines SMAP L-band radiometry with Sentinel-1 C-band radar; its Sentinel-1 inputs are not proven to be identical to the OPERA scenes, but it is not an independent SAR-only reference.",
        },
        "processing": {
            "script": "tools/research/screen_smap_s_candidates.py",
            "method": "CMR granule identity check; Harmony AOI subset; range and fill checks; NSIDC retrieval and surface quality flag counts; exact grid identity check; no interpolation or resampling.",
            "quality_eligibility_rule": "in-range finite non-fill values with retrieval_qual_flag_3km == 0 and surface_flag_3km == 0",
            "flag_semantics_source": "NSIDC SPL2SMAP_S V3 User Guide, sections 2.6.4.1 and 2.6.4.3",
        },
        "limitations": [
            "The soil-moisture estimate is produced from SMAP and Sentinel-1 inputs and cannot serve as independent validation of a Sentinel-1 measurement.",
            *(
                ["No paired cell meets the declared quality-eligibility rule; this source cannot test the surface-driver hypothesis."]
                if no_valid_paired_cells
                else ["Passing the product flags does not establish suitability for the case or causal relevance."]
            ),
            "The returned Harmony crop is small and is not a scientific estimate of the complete event area.",
            "The field name and NSIDC documentation indicate an overpass time difference in hours while the returned NetCDF units attribute says seconds; raw values are preserved without conversion.",
        ],
    }
    output_record.parent.mkdir(parents=True, exist_ok=True)
    output_record.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def _parse_bbox(text: str) -> tuple[float, float, float, float]:
    values = tuple(float(item) for item in text.split(","))
    if len(values) != 4:
        raise argparse.ArgumentTypeError("bbox must be west,south,east,north")
    west, south, east, north = values
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise argparse.ArgumentTypeError("bbox coordinates are invalid")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--bbox", required=True, type=_parse_bbox)
    parser.add_argument("--before-date", required=True, type=date.fromisoformat)
    parser.add_argument("--after-date", required=True, type=date.fromisoformat)
    parser.add_argument("--before-granule", required=True)
    parser.add_argument("--after-granule", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--output-record", required=True, type=Path)
    args = parser.parse_args()
    record = retrieve_screen(
        case_id=args.case_id,
        bbox=args.bbox,
        before_date=args.before_date,
        after_date=args.after_date,
        before_granule=args.before_granule,
        after_granule=args.after_granule,
        output_dir=args.output_dir,
        output_record=args.output_record,
    )
    print(f"status={record['status']}")
    print(f"before_cells={record['observations'][0]['soil_moisture']['quality_eligible_cell_count']}")
    print(f"after_cells={record['observations'][1]['soil_moisture']['quality_eligible_cell_count']}")
    print(f"output={args.output_record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
