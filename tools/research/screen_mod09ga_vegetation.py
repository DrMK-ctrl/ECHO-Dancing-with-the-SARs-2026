#!/usr/bin/env python3
"""Screen paired native-grid MOD09GA support from authenticated LP DAAC granules."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import tempfile
from typing import Any

import numpy as np
import requests
import rasterio
from pyproj import Transformer

from echo.modis_ga import (
    decode_mod09ga_band_qa,
    decode_mod09ga_state_qa,
    mod09ga_vegetation_sample_accepted,
    normalized_difference_vegetation_index,
)


CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
LPDAAC_HOST = "data.lpdaac.earthdatacloud.nasa.gov"
LAADS_OPENDAP = "https://ladsweb.modaps.eosdis.nasa.gov/opendap/RemoteResources/laads/allData"
RADIUS_M = 6371007.181
COLLECTION = "61"
SHORT_NAME = "MOD09GA"
VERSION = "061"
MAX_GRANULE_BYTES = 256 * 1024 * 1024
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
    body = response.content
    evidence.append({
        "granule_id": granule_id,
        "constraint": selector,
        "http_status": response.status_code,
        "response_bytes": len(body),
        "response_sha256": sha256(body).hexdigest(),
    })
    if response.status_code >= 400:
        response.close()
    response.raise_for_status()
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
) -> dict[str, Any]:
    params = {
        "short_name": SHORT_NAME,
        "version": VERSION,
        "temporal": f"{date}T00:00:00Z,{date}T23:59:59Z",
        "bounding_box": ",".join(str(value) for value in bounds),
        "page_size": 200,
    }
    entries: list[dict[str, Any]] = []
    query_pages: list[dict[str, Any]] = []
    reported_total: int | None = None
    for page_num in range(1, 21):
        response = requests.get(CMR_URL, params={**params, "page_num": page_num}, timeout=45)
        response.raise_for_status()
        feed = response.json().get("feed", {})
        page_entries = feed.get("entry", [])
        page_hits_header = response.headers.get("CMR-Hits")
        try:
            page_hits = int(page_hits_header)
        except (TypeError, ValueError):
            page_hits = -1
        if page_hits < 0:
            raise ScreenError(f"CMR did not report a valid result count for {date}")
        if reported_total is not None and page_hits != reported_total:
            raise ScreenError(f"CMR result count changed during pagination for {date}")
        reported_total = page_hits
        query_pages.append({
            "page_num": page_num,
            "page_size": params["page_size"],
            "reported_total": page_hits,
            "returned_count": len(page_entries),
            "response_url": response.url,
            "response_bytes": len(response.content),
            "response_sha256": sha256(response.content).hexdigest(),
        })
        entries.extend(page_entries)
        if len(entries) >= reported_total:
            break
        if not page_entries:
            raise ScreenError(f"CMR pagination stopped before all {reported_total} granules were retrieved")
    else:
        raise ScreenError(f"CMR query exceeded the 20-page retrieval bound for {date}")
    if reported_total != len(entries):
        raise ScreenError(f"CMR returned {len(entries)} of {reported_total} granules for {date}")
    matches = [
        entry for entry in entries
        if entry.get("producer_granule_id", "").startswith(f"{SHORT_NAME}.A")
        and f".{tile_id}." in entry.get("producer_granule_id", "")
    ]
    if len(matches) != 1:
        raise ScreenError(f"CMR returned {len(matches)} {SHORT_NAME} granules for {date} and {tile_id}")
    entry = matches[0]
    granule_id = entry["producer_granule_id"]
    data_links = [
        item.get("href") for item in entry.get("links", [])
        if item.get("rel", "").endswith("data#")
        and isinstance(item.get("href"), str)
        and item["href"].endswith(".hdf")
    ]
    if len(data_links) != 1:
        raise ScreenError(f"CMR returned {len(data_links)} HDF data links for {granule_id}")
    year = granule_id.split(".")[1][1:5]
    day_of_year = granule_id.split(".")[1][5:]
    return {
        "query_url": query_pages[0]["response_url"],
        "query_response_sha256": query_pages[0]["response_sha256"],
        "query_response_bytes": query_pages[0]["response_bytes"],
        "cmr_reported_hits": reported_total,
        "cmr_returned_count": len(entries),
        "query_pages": query_pages,
        "collection_concept_id": entry.get("collection_concept_id"),
        "cmr_granule_concept_id": entry.get("id"),
        "granule_id": granule_id,
        "period_start_utc": entry.get("time_start"),
        "period_end_utc": entry.get("time_end"),
        "cmr_updated_at_utc": entry.get("updated"),
        "data_url": data_links[0],
        "opendap_subset_base_url": f"{LAADS_OPENDAP}/{COLLECTION}/{SHORT_NAME}/{year}/{day_of_year}/{granule_id}.hdf.ascii",
    }


def _download_granule(
    session: requests.Session,
    *,
    granule: dict[str, Any],
    destination: Path,
) -> dict[str, Any]:
    """Download one named product from the protected LP DAAC Earthdata Cloud path."""
    from urllib.parse import urlparse

    url = granule.get("data_url")
    parsed = urlparse(url) if isinstance(url, str) else None
    granule_id = granule["granule_id"]
    expected_prefix = f"/lp-prod-protected/{SHORT_NAME}.{VERSION}/{granule_id}/"
    if (
        parsed is None
        or parsed.scheme != "https"
        or parsed.hostname != LPDAAC_HOST
        or not parsed.path.startswith(expected_prefix)
        or not parsed.path.endswith(f"/{granule_id}.hdf")
    ):
        raise ScreenError(f"CMR data link is outside the expected LP DAAC product path: {granule_id}")

    digest = sha256()
    byte_count = 0
    with session.get(url, timeout=(20, 120), stream=True) as response:
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_GRANULE_BYTES:
            raise ScreenError(f"LP DAAC granule exceeds the {MAX_GRANULE_BYTES}-byte retrieval bound")
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                byte_count += len(chunk)
                if byte_count > MAX_GRANULE_BYTES:
                    raise ScreenError(f"LP DAAC granule exceeded the {MAX_GRANULE_BYTES}-byte retrieval bound")
                output.write(chunk)
                digest.update(chunk)
        status = response.status_code
    return {
        "granule_id": granule_id,
        "source_url": url,
        "http_status": status,
        "response_bytes": byte_count,
        "response_sha256": digest.hexdigest(),
        "temporary_file_only": True,
    }


def _retrieve_date_opendap(
    session: requests.Session,
    *,
    granule: dict[str, Any],
    bounds: list[float],
    transformed_bounds: list[tuple[float, float]],
    evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Use LAADS server-side constraints when the exact granule is available there."""
    granule_id = granule["granule_id"]
    base_url = granule["opendap_subset_base_url"]

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


def _sds_window(
    hdf_path: Path,
    *,
    grid_name: str,
    variable: str,
    transformed_bounds: list[tuple[float, float]],
    expected_size: tuple[int, int],
    output_path: Path,
) -> tuple[np.ndarray, Any, tuple[int, int]]:
    """Read a bounded native-grid window with GDAL; no reprojection or resampling."""
    subdataset = f'HDF4_EOS:EOS_GRID:"{hdf_path}":{grid_name}:{variable}'
    try:
        metadata = subprocess.run(
            ["gdalinfo", "-json", subdataset], check=True, capture_output=True,
            text=True, timeout=45,
        )
        info = json.loads(metadata.stdout)
        if tuple(info.get("size", ())) != expected_size:
            raise ScreenError(f"MOD09GA {variable} has unexpected native dimensions")
        gt = info["geoTransform"]
        inverse_grid = np.linalg.inv(np.array([[gt[1], gt[2]], [gt[4], gt[5]]], dtype=np.float64))
        pixels = [
            inverse_grid @ np.array([x - gt[0], y - gt[3]], dtype=np.float64)
            for x, y in transformed_bounds
        ]
        pixel_size = min(abs(gt[1]), abs(gt[5]))
        padding = math.ceil(max(abs(gt[1]), abs(gt[5])) * 1.5 / pixel_size)
        col0 = max(0, math.floor(min(point[0] for point in pixels)) - padding)
        col1 = min(expected_size[0], math.ceil(max(point[0] for point in pixels)) + padding + 1)
        row0 = max(0, math.floor(min(point[1] for point in pixels)) - padding)
        row1 = min(expected_size[1], math.ceil(max(point[1] for point in pixels)) + padding + 1)
        if col1 <= col0 or row1 <= row0:
            raise ScreenError(f"MOD09GA native grid does not cover the AOI for {variable}")
        subprocess.run(
            ["gdal_translate", "-q", "-of", "GTiff", "-srcwin", str(col0), str(row0),
             str(col1 - col0), str(row1 - row0), subdataset, str(output_path)],
            check=True, capture_output=True, text=True, timeout=60,
        )
        with rasterio.open(output_path) as dataset:
            return dataset.read(1), dataset.transform, (row0, col0)
    except FileNotFoundError as exc:
        raise ScreenError("MOD09GA extraction requires the GDAL gdalinfo and gdal_translate commands") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()[:300]
        raise ScreenError(f"GDAL could not read the bounded MOD09GA subdataset {variable}: {detail}") from exc
    except (KeyError, ValueError, np.linalg.LinAlgError, rasterio.errors.RasterioError) as exc:
        if isinstance(exc, ScreenError):
            raise
        raise ScreenError(f"MOD09GA subdataset metadata is invalid for {variable}: {exc}") from exc


def _retrieve_date(
    session: requests.Session,
    *,
    granule: dict[str, Any],
    bounds: list[float],
    transformed_bounds: list[tuple[float, float]],
    temporary_dir: Path,
    retrieval_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    granule_id = granule["granule_id"]
    hdf_path = temporary_dir / f"{granule_id}.hdf"
    retrieval_evidence.append(_download_granule(session, granule=granule, destination=hdf_path))
    arrays: dict[str, tuple[np.ndarray, Any, tuple[int, int]]] = {}
    for grid, variable, size in (
        ("MODIS_Grid_500m_2D", "sur_refl_b01_1", (2400, 2400)),
        ("MODIS_Grid_500m_2D", "sur_refl_b02_1", (2400, 2400)),
        ("MODIS_Grid_500m_2D", "QC_500m_1", (2400, 2400)),
        ("MODIS_Grid_1km_2D", "state_1km_1", (1200, 1200)),
    ):
        arrays[variable] = _sds_window(
            hdf_path, grid_name=grid, variable=variable,
            transformed_bounds=transformed_bounds, expected_size=size,
            output_path=temporary_dir / f"{granule_id}-{variable}.tif",
        )
    red, grid_transform, (row0, col0) = arrays["sur_refl_b01_1"]
    nir, nir_transform, nir_offsets = arrays["sur_refl_b02_1"]
    quality, quality_transform, quality_offsets = arrays["QC_500m_1"]
    state, state_transform, (state_row0, state_col0) = arrays["state_1km_1"]
    if (
        red.shape != nir.shape or red.shape != quality.shape
        or (row0, col0) != nir_offsets or (row0, col0) != quality_offsets
        or not grid_transform.almost_equals(nir_transform)
        or not grid_transform.almost_equals(quality_transform)
    ):
        raise ScreenError("MOD09GA reflectance and band-QA subsets do not share one native grid")

    inverse = Transformer.from_crs(
        f"+proj=sinu +R={RADIUS_M} +nadgrids=@null +wktext +units=m +no_defs",
        "EPSG:4326", always_xy=True,
    )
    state_x = state_transform.c + (np.arange(state.shape[1]) + 0.5) * state_transform.a
    state_y = state_transform.f + (np.arange(state.shape[0]) + 0.5) * state_transform.e
    pixels = []
    for local_row, local_col in np.ndindex(red.shape):
        x = grid_transform.c + (local_col + 0.5) * grid_transform.a + (local_row + 0.5) * grid_transform.b
        y = grid_transform.f + (local_col + 0.5) * grid_transform.d + (local_row + 0.5) * grid_transform.e
        lon, lat = inverse.transform(x, y)
        if not (bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3]):
            continue
        row, column = row0 + local_row, col0 + local_col
        state_row = state_row0 + int(np.argmin(np.abs(state_y - y)))
        state_column = state_col0 + int(np.argmin(np.abs(state_x - x)))
        red_raw, nir_raw = int(red[local_row, local_col]), int(nir[local_row, local_col])
        band_qa_raw = int(quality[local_row, local_col])
        state_qa_raw = int(state[state_row - state_row0, state_column - state_col0])
        accepted = mod09ga_vegetation_sample_accepted(red_raw, nir_raw, band_qa_raw, state_qa_raw)
        pixels.append({
            "row": row, "column": column, "center_lon_lat": [lon, lat],
            "reflectance_red_raw": red_raw, "reflectance_nir_raw": nir_raw,
            "reflectance_scale_factor": 0.0001, "qc_500m_raw": band_qa_raw,
            "qc_500m_decoded": decode_mod09ga_band_qa(band_qa_raw),
            "state_1km_row": state_row, "state_1km_column": state_column,
            "state_1km_raw": state_qa_raw,
            "state_1km_decoded": decode_mod09ga_state_qa(state_qa_raw),
            "state_flag_support_m": 1000, "strict_vegetation_accepted": accepted,
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
    retrieval_evidence: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="echo-mod09ga-") as temporary_path:
        temporary_dir = Path(temporary_path)
        for role in ("before", "after"):
            date = source_products[role]["acquisition_start_utc"][:10]
            granule = _query_granule(date=date, bounds=bounds, tile_id=tile_id)
            granule["role"] = role
            granule["tile_id"] = tile_id
            granules.append(granule)
            try:
                pixel_sets[role] = _retrieve_date_opendap(
                    session,
                    granule=granule,
                    bounds=bounds,
                    transformed_bounds=transformed_bounds,
                    evidence=subset_evidence,
                )
                granule["retrieval_method"] = "LAADS_OPENDAP_BOUNDED_SUBSETS"
            except requests.HTTPError as exc:
                if exc.response is None or exc.response.status_code != 404:
                    raise
                granule["opendap_unavailable_status"] = 404
                granule["retrieval_method"] = "LPDAAC_FULL_GRANULE_NATIVE_WINDOW_FALLBACK"
                pixel_sets[role] = _retrieve_date(
                    session,
                    granule=granule,
                    bounds=bounds,
                    transformed_bounds=transformed_bounds,
                    temporary_dir=temporary_dir,
                    retrieval_evidence=retrieval_evidence,
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
            "retrieval_service": "NASA LAADS OPeNDAP bounded reads with exact CMR-linked LP DAAC fallback on HTTP 404",
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
            "name": "MOD09GA native-grid red/NIR and state-QA screen",
            "version": "2",
            "qa_policy_reference": QA_REFERENCE,
            "variables": ["sur_refl_b01_1", "sur_refl_b02_1", "QC_500m_1", "state_1km_1", "Latitude_1", "Longitude_1"],
            "state_qa_association": "nearest 1 km native-grid cell center to each 500 m measurement center, in the product's shared sinusoidal grid",
            "retrieval_strategy": "Use LAADS OPeNDAP server-side constraints; on HTTP 404 retrieve the exact protected LP DAAC CMR-linked HDF granule and crop native HDF4 windows with GDAL, without reprojection or resampling.",
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
            "downloaded_product_count": len(retrieval_evidence),
            "downloaded_bytes_total": sum(item["response_bytes"] for item in retrieval_evidence),
            "product_checksums": retrieval_evidence,
            "full_products_retained": False,
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
            "No common 500 m centers pass the paired MOD09GA reflectance and 1 km state-QA gate. Paired NDVI change is not computed, so this candidate does not test the vegetation hypothesis."
        ) if not strict_keys else (
            "A paired strict vegetation support set was retrieved. The screen reports native-support NDVI only and does not establish a vegetation cause or validate the SAR measurement."
        ),
        "limitations": [
            "MOD09GA state QA is 1 km while red/NIR reflectance is 500 m; each 500 m sample is associated with its nearest 1 km native state cell, and that support mismatch is retained.",
            "The MODIS source period is daily; CMR's granule time interval does not provide a per-pixel overpass timestamp for this subset.",
            "The paired MODIS window contains few native 500 m centers and is limited to the linked OPERA case window.",
            "No NDVI change is calculated unless both dates pass the declared strict land and QA gates on the same native cells.",
            "This is NASA optical context, not SAR measurement validation or independent confirmation of an SAR-derived water boundary.",
            "Complete HDF granules are temporarily downloaded from LP DAAC and removed after native-grid extraction; size limits and full-file SHA-256 values are retained.",
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
    print(f"source_products_downloaded={record['retrieval_evidence']['downloaded_product_count']}")
    print(f"source_bytes={record['retrieval_evidence']['downloaded_bytes_total']}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
