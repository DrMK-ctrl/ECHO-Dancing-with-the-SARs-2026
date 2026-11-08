#!/usr/bin/env python3
"""Screen matched-time NASA SMAP L4 soil-moisture context for an AOI."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
from typing import Any

import earthaccess
import h5py
import numpy as np
import requests


CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
HARMONY_URL = (
    "https://harmony.earthdata.nasa.gov/SPL4SMAU/ogc-api-coverages/1.0.0/"
    "collections/parameter_vars/coverage/rangeset"
)
SHORT_NAME = "SPL4SMAU"
VERSION = "008"
COLLECTION_ID = "C3480440639-NSIDC_CPRD"
PRODUCT_URL = "https://nsidc.org/data/spl4smgp/versions/8"
USER_GUIDE_URL = "https://nsidc.org/sites/default/files/documents/user-guide/multi_spl4smau-v008-userguide.pdf"
DOI = "10.5067/02LGW4DGJYRX"
CELL_SIZE_M = 9000.0
MAX_SUBSET_BYTES = 2 * 1024 * 1024
PROJECT_ROOT = Path(__file__).resolve().parents[2]
GRANULE_TIME = re.compile(r"T(\d{6})")
VARIABLES = (
    "Analysis_Data/sm_surface_analysis",
    "Analysis_Data/sm_surface_analysis_ensstd",
    "Observations_Data/tb_h_obs_assim",
    "Observations_Data/tb_v_obs_assim",
    "Observations_Data/tb_h_obs_time_sec",
    "Observations_Data/tb_v_obs_time_sec",
)


def _iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def _query_day(
    session: requests.Session,
    *,
    day: str,
    bbox: tuple[float, float, float, float],
) -> dict[str, Any]:
    params = {
        "short_name": SHORT_NAME,
        "version": VERSION,
        "temporal": f"{day}T00:00:00Z,{day}T23:59:59Z",
        "bounding_box": ",".join(str(item) for item in bbox),
        "page_size": 2000,
        "page_num": 1,
    }
    response = session.get(CMR_URL, params=params, timeout=(15, 45))
    response.raise_for_status()
    payload = response.content
    body = response.json()
    hits = int(response.headers.get("CMR-Hits", "0"))
    items = body.get("items", [])
    if hits != len(items):
        raise ValueError(f"CMR page is incomplete for {day}: received {len(items)} of {hits}")
    if not items:
        raise ValueError(f"CMR returned no {SHORT_NAME} Version {VERSION} granules for {day}")
    if any(item.get("meta", {}).get("collection-concept-id") != COLLECTION_ID for item in items):
        raise ValueError("CMR granule collection identity does not match the pinned SPL4SMAU Version 8 collection")
    return {
        "query_url": response.url,
        "response_sha256": sha256(payload).hexdigest(),
        "hit_count": hits,
        "granules": items,
    }


def _granule_timestamp(item: dict[str, Any]) -> datetime:
    granule_id = item.get("umm", {}).get("GranuleUR", "")
    match = GRANULE_TIME.search(granule_id)
    if not match:
        raise ValueError(f"cannot read UTC timestamp from SMAP L4 granule id: {granule_id}")
    timestamp = datetime.strptime(match.group(1), "%H%M%S").time()
    day = _iso_datetime(item["umm"]["TemporalExtent"]["RangeDateTime"]["BeginningDateTime"]).date()
    return datetime.combine(day, timestamp, tzinfo=timezone.utc)


def _select_granule(
    query: dict[str, Any],
    *,
    target_time: datetime,
    max_offset_minutes: int,
) -> dict[str, Any]:
    candidates = []
    for item in query["granules"]:
        umm = item.get("umm", {})
        collection = umm.get("CollectionReference", {})
        if (
            collection.get("ShortName") != SHORT_NAME
            or collection.get("Version") != VERSION
            or umm.get("GranuleUR", "").startswith("SMAP_L4_SM_aup_") is False
        ):
            continue
        timestamp = _granule_timestamp(item)
        candidates.append((abs((timestamp - target_time).total_seconds()), timestamp, item))
    if not candidates:
        raise ValueError("CMR results contain no matching analysis-update granules")
    offset_seconds, timestamp, selected = min(candidates, key=lambda value: value[0])
    if offset_seconds > max_offset_minutes * 60:
        raise ValueError(
            f"nearest SMAP L4 analysis is {offset_seconds / 60:.1f} minutes from the target; "
            f"limit is {max_offset_minutes}"
        )
    return {
        "granule_id": selected["umm"]["GranuleUR"],
        "concept_id": selected.get("meta", {}).get("concept-id"),
        "acquisition_time_utc": timestamp.isoformat().replace("+00:00", "Z"),
        "target_time_utc": target_time.isoformat().replace("+00:00", "Z"),
        "offset_minutes": offset_seconds / 60,
        "temporal_extent": selected["umm"].get("TemporalExtent"),
        "provider_dates": selected["umm"].get("ProviderDates", []),
        "short_name": selected["umm"].get("CollectionReference", {}).get("ShortName"),
        "collection_version": selected["umm"].get("CollectionReference", {}).get("Version"),
    }


def summarize_subset(
    path: Path,
    granule_id: str,
    *,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    payload = path.read_bytes()
    with h5py.File(path, "r") as source:
        lat = np.asarray(source["cell_lat"], dtype=np.float64)
        lon = np.asarray(source["cell_lon"], dtype=np.float64)
        if lat.shape != lon.shape or lat.ndim != 2 or not lat.size:
            raise ValueError("Harmony response has invalid native grid coordinates")
        fields: dict[str, dict[str, Any]] = {}
        arrays: dict[str, np.ndarray] = {}
        for name in VARIABLES:
            if name not in source:
                raise ValueError(f"Harmony response omitted required variable {name}")
            dataset = source[name]
            values = np.asarray(dataset, dtype=np.float64)
            if values.shape != lat.shape:
                raise ValueError(f"Harmony response grid differs for {name}")
            fill = float(dataset.attrs.get("_FillValue", -9999.0))
            valid = np.isfinite(values) & (values != fill)
            arrays[name] = values
            unit_value = dataset.attrs.get("units", "")
            if isinstance(unit_value, bytes):
                unit_value = unit_value.decode("utf-8", errors="replace")
            fields[name] = {
                "valid_cell_count": int(valid.sum()),
                "fill_value": fill,
                "units": str(unit_value),
                "values": values.tolist(),
            }
        history = source.attrs.get("history_json", "")
        if isinstance(history, bytes):
            history = history.decode("utf-8", errors="replace")
        try:
            history_json = json.loads(history)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Harmony response is missing its transformation history") from exc
        request_parameters = history_json[0].get("parameters", []) if history_json else []
        request_text = json.dumps(request_parameters)
        if granule_id not in request_text:
            raise ValueError("Harmony transformation history identifies a different source granule")
        try:
            relative_asset_path = path.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("bounded source subsets must be stored inside the ECHO project") from exc
        return {
            "granule_id": granule_id,
            "asset": {
                "relative_path": relative_asset_path,
                "size_bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
                "format": "NetCDF-4",
            },
            "grid": {
                "crs": "WGS 84 / NSIDC EASE-Grid 2.0 Global",
                "cell_size_m": CELL_SIZE_M,
                "shape": list(lat.shape),
                "cell_lat": lat.tolist(),
                "cell_lon": lon.tolist(),
                "coordinate_grid_sha256": sha256(
                    np.ascontiguousarray(lat).tobytes() + np.ascontiguousarray(lon).tobytes()
                ).hexdigest(),
            },
            "variables": fields,
            "harmony_history": history_json,
        }


def retrieve_screen(
    *,
    case_id: str,
    bbox: tuple[float, float, float, float],
    before_time: str,
    after_time: str,
    output_dir: Path,
    output_record: Path,
    max_offset_minutes: int = 90,
) -> dict[str, Any]:
    if not (-180 <= bbox[0] < bbox[2] <= 180 and -90 <= bbox[1] < bbox[3] <= 90):
        raise ValueError("invalid WGS84 bbox")
    if (bbox[2] - bbox[0]) > 1 or (bbox[3] - bbox[1]) > 1:
        raise ValueError("SMAP L4 retrieval is limited to a one-degree AOI window")
    before_target, after_target = _iso_datetime(before_time), _iso_datetime(after_time)
    if after_target <= before_target:
        raise ValueError("after_time must be later than before_time")
    if max_offset_minutes < 1 or max_offset_minutes > 90:
        raise ValueError("maximum time offset must be between 1 and 90 minutes")
    if not earthaccess.login(strategy="netrc", persist=False):
        raise RuntimeError("Earthdata Login did not authenticate with the local netrc")
    session = earthaccess.get_requests_https_session()
    west, south, east, north = bbox
    padding = 0.1
    harmony_params = [
        ("subset", f"lat({south - padding:.6f}:{north + padding:.6f})"),
        ("subset", f"lon({west - padding:.6f}:{east + padding:.6f})"),
        *(('variable', item) for item in VARIABLES),
        ("format", "application/netcdf"),
    ]
    observations = []
    cmr_queries = []
    for label, target_time in (("before", before_target), ("after", after_target)):
        day = target_time.date().isoformat()
        query = _query_day(session, day=day, bbox=bbox)
        granule = _select_granule(
            query,
            target_time=target_time,
            max_offset_minutes=max_offset_minutes,
        )
        cmr_queries.append({
            "date_utc": day,
            "url": query["query_url"],
            "response_sha256": query["response_sha256"],
            "hit_count": query["hit_count"],
            "result_count": len(query["granules"]),
            "selected_granule_id": granule["granule_id"],
        })
        params = [("granuleName", granule["granule_id"]), *harmony_params]
        response = session.get(HARMONY_URL, params=params, timeout=(20, 120))
        response.raise_for_status()
        if "netcdf" not in response.headers.get("content-type", "").lower():
            raise RuntimeError("Harmony did not return a NetCDF subset")
        if not response.content or len(response.content) > MAX_SUBSET_BYTES:
            raise RuntimeError("Harmony subset is empty or exceeds the 2 MiB transfer limit")
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_case_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", case_id).strip("-")
        asset_path = output_dir / f"smap-l4-{safe_case_id}-{label}-{day}-bounded.nc4"
        asset_path.write_bytes(response.content)
        observation = summarize_subset(asset_path, granule["granule_id"])
        observation["catalog"] = granule
        observation["retrieval"] = {
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "service": HARMONY_URL,
            "http_status": response.status_code,
            "content_type": response.headers.get("content-type"),
            "request_parameters": params,
        }
        observations.append(observation)
    before, after = observations
    if (
        before["grid"]["shape"] != after["grid"]["shape"]
        or before["grid"]["coordinate_grid_sha256"] != after["grid"]["coordinate_grid_sha256"]
    ):
        raise ValueError("before and after Harmony subsets do not share the same native grid")
    center_lat = (bbox[1] + bbox[3]) / 2
    center_lon = (bbox[0] + bbox[2]) / 2
    grid_lat = np.asarray(before["grid"]["cell_lat"], dtype=np.float64)
    grid_lon = np.asarray(before["grid"]["cell_lon"], dtype=np.float64)
    lat1, lat2 = np.radians(center_lat), np.radians(grid_lat)
    delta_lon = np.radians(grid_lon - center_lon)
    haversine = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(delta_lon / 2) ** 2
    nearest_flat = int(np.nanargmin(haversine))
    nearest = np.unravel_index(nearest_flat, grid_lat.shape)
    key = "Analysis_Data/sm_surface_analysis"
    uncertainty_key = "Analysis_Data/sm_surface_analysis_ensstd"
    before_value = before["variables"][key]["values"][nearest[0]][nearest[1]]
    after_value = after["variables"][key]["values"][nearest[0]][nearest[1]]
    before_uncertainty = before["variables"][uncertainty_key]["values"][nearest[0]][nearest[1]]
    after_uncertainty = after["variables"][uncertainty_key]["values"][nearest[0]][nearest[1]]
    tb_keys = ["Observations_Data/tb_h_obs_assim", "Observations_Data/tb_v_obs_assim"]
    tb_valid_by_date = [
        sum(observation["variables"][name]["valid_cell_count"] for name in tb_keys)
        for observation in observations
    ]
    def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
        dlat, dlon = lat2_r - lat1_r, math.radians(lon2 - lon1)
        value = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
        return 6371.0088 * 2 * math.asin(math.sqrt(value))

    aoi_width_km = distance_km(center_lat, bbox[0], center_lat, bbox[2])
    aoi_height_km = distance_km(bbox[1], center_lon, bbox[3], center_lon)
    aoi_is_smaller_than_cell = max(aoi_width_km, aoi_height_km) < CELL_SIZE_M / 1000
    status = (
        "SCREENED_REGIONAL_MODEL_CONTEXT_NOT_SUITABLE_FOR_AOI_SCALE_DISCRIMINATION"
        if aoi_is_smaller_than_cell
        else "SCREENED_MODEL_DERIVED_REGIONAL_CONTEXT_REQUIRES_CASE_REVIEW"
    )
    record = {
        "record_type": "ECHO_SMAP_L4_REGIONAL_SOIL_MOISTURE_CONTEXT_SCREEN",
        "schema_version": 1,
        "status": status,
        "case_id": case_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "NASA National Snow and Ice Data Center DAAC",
            "mission": "Soil Moisture Active Passive (SMAP)",
            "instrument": "L-band radiometer; observations are assimilated by the Level 4 land-surface modeling system",
            "product": "SMAP L4 Global 3-hourly 9 km EASE-Grid Surface and Root Zone Soil Moisture Analysis Update, Version 8",
            "short_name": SHORT_NAME,
            "version": VERSION,
            "collection_concept_id": COLLECTION_ID,
            "doi": DOI,
            "product_url": PRODUCT_URL,
            "user_guide_url": USER_GUIDE_URL,
            "measurement_role": "model-assimilated regional context; not direct soil-moisture measurement or ECHO-accepted evidence for the AOI-scale hypothesis test",
        },
        "query": {
            "bounds_wgs84": list(bbox),
            "coordinate_reference_system": "WGS 84 / NSIDC EASE-Grid 2.0 Global",
            "grid_posting_m": CELL_SIZE_M,
            "aoi_width_km_approx": aoi_width_km,
            "aoi_height_km_approx": aoi_height_km,
            "aoi_smaller_than_one_grid_cell": aoi_is_smaller_than_cell,
            "cmr_queries": cmr_queries,
            "harmony_subset_parameters": harmony_params,
            "max_temporal_offset_minutes": max_offset_minutes,
            "same_native_grid_before_after": True,
        },
        "observations": observations,
        "comparison": {
            "nearest_cell_index_row_column": [int(nearest[0]), int(nearest[1])],
            "nearest_cell_center_wgs84": {
                "longitude": float(grid_lon[nearest]),
                "latitude": float(grid_lat[nearest]),
            },
            "nearest_cell_center_distance_from_aoi_center_km": distance_km(
                center_lat,
                center_lon,
                float(grid_lat[nearest]),
                float(grid_lon[nearest]),
            ),
            "before_surface_soil_moisture_model_analysis_m3_m3": before_value,
            "after_surface_soil_moisture_model_analysis_m3_m3": after_value,
            "after_minus_before_model_analysis_m3_m3": after_value - before_value,
            "before_ensemble_standard_deviation_m3_m3": before_uncertainty,
            "after_ensemble_standard_deviation_m3_m3": after_uncertainty,
            "valid_assimilated_brightness_temperature_values_by_date": tb_valid_by_date,
            "provider_quality_gate": "No product QA flags were exposed in the bounded subset; ensemble spread is retained as model uncertainty and is not treated as a QA pass or significance test.",
            "disposition": "Regional model context only. The nearest 9 km grid cell cannot resolve the approximately 1 km AOI; the analysis is model-derived, matching local assimilated brightness-temperature fields are fill values, and uncertainty covariance is unavailable. No hypothesis test or significance claim is made.",
        },
        "upstream_dependencies": {
            "potential_input_overlap": ["NASA-GPM-IMERG-INTERACQUISITION-CHRONOLOGY"],
            "reason": "NSIDC documents IMERG Final V07 precipitation as an input to SPL4SMGP outside North America and high latitudes. ECHO's local GPM chronology therefore cannot be treated as independent corroboration of this model-derived context.",
        },
        "processing": {
            "script": "tools/research/screen_smap_l4_context.py",
            "method": "CMR exact-day search with pagination completeness check; select the closest same-day analysis update within a declared time limit; bounded Harmony OGC Coverages retrieval; retain native grid; nearest-cell context summary; checksum and source-lineage capture.",
            "resampling": False,
            "causal_inference": False,
            "statistical_significance_test": False,
        },
        "limitations": [
            *(
                ["The 9 km product grid and model support are much coarser than the AOI and cannot resolve within-AOI variation."]
                if aoi_is_smaller_than_cell
                else ["The 9 km product grid may still be too coarse for the SAR analysis cells; compare native support before any cross-sensor inference."]
            ),
            "SMAP L4 is a model-assimilated estimate; it is not a direct in-situ soil-moisture measurement.",
            *(
                ["No valid assimilated brightness-temperature values were returned for any selected grid cells at either matched analysis time."]
                if all(value == 0 for value in tb_valid_by_date)
                else ["Some assimilated brightness-temperature values are present; their support and timing still require scientific review."]
            ),
            "IMERG precipitation is an upstream forcing input in this region, so this context is not independent of the GPM chronology.",
            "Ensemble standard deviation is not a QA status or a significance threshold; temporal covariance was not available.",
            "The screen does not validate the diagnostic OPERA RTC-S1 observations or establish flood extent, mechanism, or cause.",
        ],
    }
    output_record.parent.mkdir(parents=True, exist_ok=True)
    output_record.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def _parse_bbox(value: str) -> tuple[float, float, float, float]:
    try:
        parts = tuple(float(item) for item in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bbox must be west,south,east,north") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be west,south,east,north")
    return parts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--bbox", required=True, type=_parse_bbox)
    parser.add_argument("--before-time", required=True, help="ISO 8601 SAR acquisition timestamp")
    parser.add_argument("--after-time", required=True, help="ISO 8601 SAR acquisition timestamp")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--output-record", required=True, type=Path)
    parser.add_argument("--max-offset-minutes", type=int, default=90)
    args = parser.parse_args()
    record = retrieve_screen(
        case_id=args.case_id,
        bbox=args.bbox,
        before_time=args.before_time,
        after_time=args.after_time,
        output_dir=args.output_dir,
        output_record=args.output_record,
        max_offset_minutes=args.max_offset_minutes,
    )
    print(f"status={record['status']}")
    print(f"before_granule={record['observations'][0]['granule_id']}")
    print(f"after_granule={record['observations'][1]['granule_id']}")
    print(f"regional_context_delta_m3_m3={record['comparison']['after_minus_before_model_analysis_m3_m3']:.6f}")
    print(f"output={args.output_record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
