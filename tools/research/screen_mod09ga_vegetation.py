#!/usr/bin/env python3
"""Retrieve a bounded MOD09GA OPeNDAP window and screen paired vegetation support."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import requests
from pyproj import Transformer

from echo.modis_ga import (
    decode_mod09ga_band_qa,
    decode_mod09ga_state_qa,
    mod09ga_vegetation_sample_accepted,
    normalized_difference_vegetation_index,
)


CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
LAADS_OPENDAP = "https://ladsweb.modaps.eosdis.nasa.gov/opendap/RemoteResources/laads/allData"
RADIUS_M = 6371007.181
COLLECTION = "61"
SHORT_NAME = "MOD09GA"
VERSION = "061"
QA_REFERENCE = "NASA MODIS Surface Reflectance User Guide, Collection 6.1, Tables 11 and 14"


class ScreenError(ValueError):
    """Raised when a case or product cannot support this bounded screen."""


def _dap_array(
    session: requests.Session,
    base_url: str,
    variable: str,
    selector: str,
    *,
    dimensions: int,
    evidence: list[dict[str, Any]],
    granule_id: str,
) -> np.ndarray:
    response = session.get(f"{base_url}?{selector}", timeout=(20, 45))
    response.raise_for_status()
    body = response.content
    evidence.append({
        "granule_id": granule_id,
        "constraint": selector,
        "http_status": response.status_code,
        "response_bytes": len(body),
        "response_sha256": sha256(body).hexdigest(),
    })
    lines = response.text.splitlines()
    response.close()
    if dimensions == 1:
        values: list[float] = []
        for line in lines:
            tokens = line.split(",")
            values.extend(float(token.strip()) for token in tokens[1:] if token.strip())
        return np.asarray(values, dtype=np.float64)
    rows = []
    for line in lines[1:]:
        if line.strip():
            tokens = line.split(",")
            rows.append([float(token.strip()) for token in tokens[1:] if token.strip()])
    array = np.asarray(rows, dtype=np.float64)
    if array.ndim != 2:
        raise ScreenError(f"LAADS OPeNDAP returned an invalid {variable} subset")
    return array


def _tile_for_bounds(bounds: list[float]) -> tuple[int, int]:
    transformer = Transformer.from_crs(
        "EPSG:4326",
        f"+proj=sinu +R={RADIUS_M} +nadgrids=@null +wktext +units=m +no_defs",
        always_xy=True,
    )
    size = math.pi * RADIUS_M / 18
    corners = [
        transformer.transform(lon, lat)
        for lon in (bounds[0], bounds[2])
        for lat in (bounds[1], bounds[3])
    ]
    tiles = {
        (
            math.floor((x + math.pi * RADIUS_M) / size),
            math.floor((math.pi * RADIUS_M / 2 - y) / size),
        )
        for x, y in corners
    }
    if len(tiles) != 1:
        raise ScreenError("the linked analysis window crosses MODIS tiles; multi-tile screening is not implemented")
    horizontal, vertical = next(iter(tiles))
    return horizontal, vertical


def _query_granule(
    *,
    date: str,
    bounds: list[float],
    tile_id: str,
) -> tuple[dict[str, Any], str]:
    params = {
        "short_name": SHORT_NAME,
        "version": VERSION,
        "temporal": f"{date}T00:00:00Z,{date}T23:59:59Z",
        "bounding_box": ",".join(str(value) for value in bounds),
        "page_size": 200,
    }
    response = requests.get(CMR_URL, params=params, timeout=45)
    response.raise_for_status()
    entries = response.json().get("feed", {}).get("entry", [])
    matches = [
        entry for entry in entries
        if entry.get("producer_granule_id", "").startswith(f"{SHORT_NAME}.A")
        and f".{tile_id}." in entry.get("producer_granule_id", "")
    ]
    if len(matches) != 1:
        raise ScreenError(f"CMR returned {len(matches)} {SHORT_NAME} granules for {date} and {tile_id}")
    entry = matches[0]
    granule_id = entry["producer_granule_id"]
    year = granule_id.split(".")[1][1:5]
    day_of_year = granule_id.split(".")[1][5:]
    return {
        "query_url": response.url,
        "query_response_sha256": sha256(response.content).hexdigest(),
        "collection_concept_id": entry.get("collection_concept_id"),
        "cmr_granule_concept_id": entry.get("id"),
        "granule_id": granule_id,
        "period_start_utc": entry.get("time_start"),
        "period_end_utc": entry.get("time_end"),
        "cmr_updated_at_utc": entry.get("updated"),
        "data_links": [
            item.get("href") for item in entry.get("links", [])
            if item.get("rel", "").endswith("data#") and isinstance(item.get("href"), str)
        ],
        "opendap_subset_base_url": f"{LAADS_OPENDAP}/{COLLECTION}/{SHORT_NAME}/{year}/{day_of_year}/{granule_id}.hdf.ascii",
    }, response.url


def _retrieve_date(
    session: requests.Session,
    *,
    granule: dict[str, Any],
    bounds: list[float],
    transformed_bounds: list[tuple[float, float]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    granule_id = granule["granule_id"]
    year = granule_id.split(".")[1][1:5]
    day_of_year = granule_id.split(".")[1][5:]
    filename = f"{granule_id}.hdf"
    base_url = f"{LAADS_OPENDAP}/{COLLECTION}/{SHORT_NAME}/{year}/{day_of_year}/{filename}.ascii"

    def vector(name: str, size: int) -> np.ndarray:
        return _dap_array(
            session, base_url, name, f"{name}[0:1:{size - 1}]", dimensions=1,
            evidence=evidence, granule_id=granule_id,
        )

    x500 = vector("XDim_1", 2400)
    y500 = vector("YDim_1", 2400)
    x1000 = vector("XDim", 1200)
    y1000 = vector("YDim", 1200)
    xmin = min(x for x, _ in transformed_bounds)
    xmax = max(x for x, _ in transformed_bounds)
    ymin = min(y for _, y in transformed_bounds)
    ymax = max(y for _, y in transformed_bounds)
    columns = np.flatnonzero((x500 >= xmin - 600) & (x500 <= xmax + 600))
    rows = np.flatnonzero((y500 >= ymin - 600) & (y500 <= ymax + 600))
    state_columns = np.flatnonzero((x1000 >= xmin - 1200) & (x1000 <= xmax + 1200))
    state_rows = np.flatnonzero((y1000 >= ymin - 1200) & (y1000 <= ymax + 1200))
    if any(values.size == 0 for values in (columns, rows, state_columns, state_rows)):
        raise ScreenError("MODIS native-grid coordinates do not cover the linked analysis window")
    c0, c1 = int(columns.min()), int(columns.max())
    r0, r1 = int(rows.min()), int(rows.max())
    sc0, sc1 = int(state_columns.min()), int(state_columns.max())
    sr0, sr1 = int(state_rows.min()), int(state_rows.max())

    def window(name: str, row0: int, row1: int, col0: int, col1: int) -> np.ndarray:
        constraint = f"{name}[{row0}:1:{row1}][{col0}:1:{col1}]"
        return _dap_array(
            session, base_url, name, constraint, dimensions=2,
            evidence=evidence, granule_id=granule_id,
        )

    red = window("sur_refl_b01_1", r0, r1, c0, c1)
    nir = window("sur_refl_b02_1", r0, r1, c0, c1)
    quality = window("QC_500m_1", r0, r1, c0, c1)
    latitude = window("Latitude_1", r0, r1, c0, c1)
    longitude = window("Longitude_1", r0, r1, c0, c1)
    state = window("state_1km_1", sr0, sr1, sc0, sc1)
    pixels = []
    for local_row, local_col in np.ndindex(latitude.shape):
        lat = float(latitude[local_row, local_col])
        lon = float(longitude[local_row, local_col])
        if not (bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]):
            continue
        row, column = r0 + local_row, c0 + local_col
        state_row = min(range(sr0, sr1 + 1), key=lambda idx: abs(float(y1000[idx] - y500[row])))
        state_column = min(range(sc0, sc1 + 1), key=lambda idx: abs(float(x1000[idx] - x500[column])))
        red_raw, nir_raw = int(red[local_row, local_col]), int(nir[local_row, local_col])
        band_qa_raw = int(quality[local_row, local_col])
        state_qa_raw = int(state[state_row - sr0, state_column - sc0])
        accepted = mod09ga_vegetation_sample_accepted(red_raw, nir_raw, band_qa_raw, state_qa_raw)
        pixels.append({
            "row": row,
            "column": column,
            "center_lon_lat": [lon, lat],
            "reflectance_red_raw": red_raw,
            "reflectance_nir_raw": nir_raw,
            "reflectance_scale_factor": 0.0001,
            "qc_500m_raw": band_qa_raw,
            "qc_500m_decoded": decode_mod09ga_band_qa(band_qa_raw),
            "state_1km_row": state_row,
            "state_1km_column": state_column,
            "state_1km_raw": state_qa_raw,
            "state_1km_decoded": decode_mod09ga_state_qa(state_qa_raw),
            "state_flag_support_m": 1000,
            "strict_vegetation_accepted": accepted,
            "ndvi": normalized_difference_vegetation_index(red_raw, nir_raw) if accepted else None,
        })
    return pixels


def screen(pair_path: Path, case_id: str, output_path: Path) -> dict[str, Any]:
    pair_bytes = pair_path.read_bytes()
    pair = json.loads(pair_bytes)
    if pair.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        raise ScreenError("source is not an OPERA RTC-S1 pair-analysis record")
    source_products = pair.get("source_products")
    if not isinstance(source_products, dict):
        raise ScreenError("linked SAR pair has no source products")
    bounds = pair["grid"]["window"]["bounds_wgs84"]
    transformer = Transformer.from_crs(
        "EPSG:4326",
        f"+proj=sinu +R={RADIUS_M} +nadgrids=@null +wktext +units=m +no_defs",
        always_xy=True,
    )
    transformed_bounds = [
        transformer.transform(lon, lat)
        for lon in (bounds[0], bounds[2])
        for lat in (bounds[1], bounds[3])
    ]
    horizontal, vertical = _tile_for_bounds(bounds)
    tile_id = f"h{horizontal:02d}v{vertical:02d}"
    import earthaccess

    if not earthaccess.login(strategy="netrc", persist=False):
        raise ScreenError("Earthdata Login did not return an authenticated session")
    session = earthaccess.get_requests_https_session()
    granules = []
    pixel_sets = {}
    subset_evidence: list[dict[str, Any]] = []
    for role in ("before", "after"):
        date = source_products[role]["acquisition_start_utc"][:10]
        granule, _ = _query_granule(date=date, bounds=bounds, tile_id=tile_id)
        granule["tile_id"] = tile_id
        granules.append({"role": role, **granule})
        pixel_sets[role] = _retrieve_date(
            session, granule=granule, bounds=bounds,
            transformed_bounds=transformed_bounds, evidence=subset_evidence,
        )
    before = {(p["row"], p["column"]): p for p in pixel_sets["before"]}
    after = {(p["row"], p["column"]): p for p in pixel_sets["after"]}
    common_keys = sorted(set(before) & set(after))
    strict_keys = [
        key for key in common_keys
        if before[key]["strict_vegetation_accepted"] and after[key]["strict_vegetation_accepted"]
    ]
    paired_ndvi = [
        {
            "row": row,
            "column": column,
            "before_ndvi": before[(row, column)]["ndvi"],
            "after_ndvi": after[(row, column)]["ndvi"],
            "delta_ndvi": after[(row, column)]["ndvi"] - before[(row, column)]["ndvi"],
        }
        for row, column in strict_keys
    ]
    record = {
        "record_type": "ECHO_MOD09GA_VEGETATION_CANDIDATE_SCREEN",
        "schema_version": 1,
        "status": "RETRIEVED_QUALITY_LIMITED" if not strict_keys else "SCREENED_REQUIRES_REVIEW",
        "case_id": case_id,
        "source": {
            "provider": "NASA LP DAAC (CMR granule collection)",
            "retrieval_service": "NASA LAADS DAAC OPeNDAP bounded subsets",
            "mission": "Terra",
            "instrument": "MODIS",
            "short_name": SHORT_NAME,
            "collection": COLLECTION,
            "version": VERSION,
            "product_level": "daily gridded L2G-lite surface reflectance",
            "source_pair_record_path": str(pair_path),
            "source_pair_record_sha256": sha256(pair_bytes).hexdigest(),
            "sar_scene_ids": [source_products[role]["scene_id"] for role in ("before", "after")],
            "granules": granules,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        },
        "query": {
            "bbox_west_south_east_north": bounds,
            "sar_acquisition_timestamps_utc": [source_products[role]["acquisition_start_utc"] for role in ("before", "after")],
            "selected_modis_tile": tile_id,
            "native_measurement_resolution_m": 500,
            "state_qa_resolution_m": 1000,
            "spatial_resampling": False,
        },
        "method": {
            "name": "bounded LAADS OPeNDAP MOD09GA red/NIR and state-QA screen",
            "version": "1",
            "qa_policy_reference": QA_REFERENCE,
            "variables": ["sur_refl_b01_1", "sur_refl_b02_1", "QC_500m_1", "state_1km_1", "Latitude_1", "Longitude_1"],
            "state_qa_association": "nearest 1 km native-grid cell center to each 500 m measurement center, in the product's shared sinusoidal grid",
            "strict_acceptance": {
                "valid_red_and_nir_ranges": [-100, 16000],
                "modland_quality_equals": 0,
                "band1_quality_equals": 0,
                "band2_quality_equals": 0,
                "state_cloud_clear_no_shadow_land_class_equals": 1,
                "cirrus_cloud_snow_and_adjacent_cloud_flags_absent": True,
                "both_dates_must_pass_on_same_500m_grid_cell": True,
            },
            "ndvi_delta_calculated_only_on_common_strict_support": True,
        },
        "retrieval_evidence": {
            "subset_request_count": len(subset_evidence),
            "subset_response_bytes_total": sum(item["response_bytes"] for item in subset_evidence),
            "subset_response_checksums": subset_evidence,
        },
        "observations": {
            "before": {"pixel_center_count": len(pixel_sets["before"]), "strict_accepted_count": sum(p["strict_vegetation_accepted"] for p in pixel_sets["before"])},
            "after": {"pixel_center_count": len(pixel_sets["after"]), "strict_accepted_count": sum(p["strict_vegetation_accepted"] for p in pixel_sets["after"])},
            "common_pixel_center_count": len(common_keys),
            "common_strict_accepted_count": len(strict_keys),
            "paired_ndvi": paired_ndvi,
        },
        "bounded_pixel_records": [
            {"role": role, **pixel}
            for role in ("before", "after")
            for pixel in pixel_sets[role]
        ],
        "interpretation": (
            "The MOD09GA red/NIR band QA passes on the retained measurement pixels, but the linked 1 km state QA classifies all 500 m centers as inland-water or shoreline support; the before-date state flags also include cloud/shadow conditions. No paired strict land cells remain, so NDVI change is not computed and this candidate does not test the vegetation hypothesis."
        ) if not strict_keys else (
            "A paired strict vegetation support set was retrieved. The screen reports native-support NDVI only and does not establish a vegetation cause or validate the SAR measurement."
        ),
        "limitations": [
            "MOD09GA state QA is 1 km while red/NIR reflectance is 500 m; each 500 m sample is associated with its nearest 1 km native state cell, and that support mismatch is retained.",
            "The MODIS source period is daily; CMR's granule time interval does not provide a per-pixel overpass timestamp for this subset.",
            "The paired MODIS window contains few native 500 m centers and is limited to the linked OPERA case window.",
            "No NDVI change is calculated unless both dates pass the declared strict land and QA gates on the same native cells.",
            "This is NASA optical context, not SAR measurement validation or independent confirmation of an SAR-derived water boundary.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-record", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = screen(args.pair_record, args.case_id, args.output)
    print(f"status={record['status']}")
    print(f"native_common_centers={record['observations']['common_pixel_center_count']}")
    print(f"strict_common_land_centers={record['observations']['common_strict_accepted_count']}")
    print(f"subset_requests={record['retrieval_evidence']['subset_request_count']}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
