#!/usr/bin/env python3
"""Screen nearby NASA SWOT RiverSP reaches for a SAR observation pair.

This command records product access, reach proximity, and provider quality
flags. It does not compare water levels or validate a SAR-derived boundary.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any
from zipfile import ZipFile

import earthaccess
import pyproj
import requests
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import box, shape


CMR_URL = "https://cmr.earthdata.nasa.gov/search/granules.json"
SHORT_NAME = "SWOT_L2_HR_RiverSP_reach_D"
COLLECTION_ID = "C3233942283-POCLOUD"
DOI = "10.5067/SWOT-RIVERSP-D"
DATASET_URL = "https://podaac.jpl.nasa.gov/dataset/SWOT_L2_HR_RiverSP_reach_D"
PDD_URL = (
    "https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-docs/"
    "web-misc/swot_mission_docs/pdd/"
    "D-56413_SWOT_Product_Description_L2_HR_RiverSP_20250224a_RevC_clean_sig_final.pdf"
)
MAX_CMR_PAGES = 20
CMR_PAGE_SIZE = 2000
MAX_GRANULE_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 500 * 1024 * 1024
PGD_SUFFIX = re.compile(r"_PGD0_\d+\.zip$")


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("acquisition times must include a timezone")
    return parsed.astimezone(timezone.utc)


def _read_pair(path: Path) -> tuple[dict[str, Any], str, tuple[float, float, float, float], list[str]]:
    record = json.loads(path.read_text(encoding="utf-8"))
    products = record.get("source_products", {})
    before = products.get("before", {}).get("acquisition_start_utc")
    after = products.get("after", {}).get("acquisition_start_utc")
    bounds = record.get("grid", {}).get("window", {}).get("bounds_wgs84")
    if not before or not after or not isinstance(bounds, list) or len(bounds) != 4:
        raise ValueError("pair record must contain acquisition times and grid.window.bounds_wgs84")
    west, south, east, north = (float(value) for value in bounds)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("pair record contains an invalid WGS84 bounding box")
    times = [_utc(before), _utc(after)]
    if times[1] <= times[0]:
        raise ValueError("pair after acquisition must follow the before acquisition")
    return record, str(record.get("case_id", "")), (west, south, east, north), [
        value.isoformat().replace("+00:00", "Z") for value in times
    ]


def _query_day(session: requests.Session, day: date, bbox: tuple[float, float, float, float]) -> dict[str, Any]:
    params = {
        "short_name": SHORT_NAME,
        "temporal": (
            f"{datetime.combine(day, time.min, timezone.utc).isoformat().replace('+00:00', 'Z')},"
            f"{datetime.combine(day, time.max, timezone.utc).isoformat().replace('+00:00', 'Z')}"
        ),
        "bounding_box": ",".join(f"{value:.10f}" for value in bbox),
        "page_size": CMR_PAGE_SIZE,
    }
    entries: list[dict[str, Any]] = []
    page_evidence: list[dict[str, Any]] = []
    expected_hits: int | None = None
    for page_num in range(1, MAX_CMR_PAGES + 1):
        response = session.get(CMR_URL, params={**params, "page_num": page_num}, timeout=(15, 45))
        response.raise_for_status()
        page_payload = response.content
        page = response.json().get("feed", {})
        page_entries = page.get("entry", [])
        hits = int(response.headers.get("CMR-Hits", "0"))
        if expected_hits is None:
            expected_hits = hits
        elif expected_hits != hits:
            raise ValueError(f"CMR hit count changed while paging {day.isoformat()}")
        page_evidence.append({
            "page": page_num,
            "url": response.url,
            "entry_count": len(page_entries),
            "response_sha256": sha256(page_payload).hexdigest(),
        })
        entries.extend(page_entries)
        if len(entries) >= expected_hits or not page_entries:
            break
    if expected_hits is None or len(entries) != expected_hits:
        raise ValueError(
            f"incomplete CMR response for {day.isoformat()}: "
            f"received {len(entries)} of {expected_hits} entries"
        )
    for entry in entries:
        if entry.get("collection_concept_id") != COLLECTION_ID:
            raise ValueError("CMR returned a granule from an unexpected collection")
    return {"date_utc": day.isoformat(), "hit_count": expected_hits, "pages": page_evidence, "entries": entries}


def _select_unique_passes(queries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for query in queries:
        for entry in query["entries"]:
            producer = entry.get("producer_granule_id", "")
            if not producer.endswith(".zip"):
                continue
            pass_key = PGD_SUFFIX.sub("", producer)
            previous = selected.get(pass_key)
            if previous is None or entry.get("updated", "") > previous.get("updated", ""):
                selected[pass_key] = entry
    return sorted(selected.values(), key=lambda item: item.get("time_start", ""))


def _download_url(entry: dict[str, Any]) -> str:
    links = [
        item.get("href", "")
        for item in entry.get("links", [])
        if item.get("href", "").startswith("https://archive.swot.podaac.earthdata.nasa.gov/")
        and item.get("href", "").lower().endswith(".zip")
    ]
    if len(links) != 1:
        raise ValueError(f"expected one ZIP data link for granule {entry.get('id')}")
    return links[0]


def _download(session: requests.Session, url: str, path: Path, remaining_bytes: int) -> tuple[int, str]:
    response = session.get(url, stream=True, timeout=(20, 120))
    response.raise_for_status()
    declared_size = response.headers.get("Content-Length")
    if declared_size and int(declared_size) > min(MAX_GRANULE_BYTES, remaining_bytes):
        response.close()
        raise ValueError("SWOT granule exceeds the configured transfer budget")
    digest = sha256()
    size = 0
    with path.open("wb") as target:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if not chunk:
                continue
            size += len(chunk)
            if size > min(MAX_GRANULE_BYTES, remaining_bytes):
                response.close()
                raise ValueError("SWOT granule exceeded the configured transfer budget")
            target.write(chunk)
            digest.update(chunk)
    response.close()
    if not size:
        raise ValueError("PO.DAAC returned an empty SWOT granule")
    return size, digest.hexdigest()


def _quality_summary(archive: Path, *, bbox: tuple[float, float, float, float], radius_m: float) -> dict[str, Any]:
    ogr2ogr = shutil.which("ogr2ogr")
    if not ogr2ogr:
        raise RuntimeError("GDAL ogr2ogr is required to read the SWOT reach shapefile")
    with ZipFile(archive) as source_zip:
        shapefiles = [
            item.filename for item in source_zip.infolist()
            if item.filename.lower().endswith(".shp") and "/" not in item.filename
        ]
    if len(shapefiles) != 1:
        raise ValueError("expected exactly one root-level reach shapefile in the SWOT ZIP")
    out_geojson = archive.with_suffix(".geojson")
    virtual_shapefile = f"/vsizip/{archive.resolve()}/{shapefiles[0]}"
    result = subprocess.run(
        [ogr2ogr, "-f", "GeoJSON", "-t_srs", "EPSG:4326", str(out_geojson), virtual_shapefile],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"ogr2ogr could not read SWOT reach data: {result.stderr[-1000:]}")
    features = json.loads(out_geojson.read_text(encoding="utf-8")).get("features", [])
    west, south, east, north = bbox
    center_lon, center_lat = (west + east) / 2, (south + north) / 2
    local_crs = CRS.from_proj4(
        f"+proj=aeqd +lat_0={center_lat:.10f} +lon_0={center_lon:.10f} "
        "+datum=WGS84 +units=m +no_defs"
    )
    to_local = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
    target = shapely.transform(box(west, south, east, north), to_local.transform, interleaved=False)
    nearby: list[dict[str, Any]] = []
    feature_count = 0
    for feature in features:
        if not feature.get("geometry"):
            continue
        feature_count += 1
        properties = feature.get("properties", {})
        geometry = shapely.transform(shape(feature["geometry"]), to_local.transform, interleaved=False)
        distance = float(geometry.distance(target))
        if distance > radius_m:
            continue
        item = {
            "distance_to_window_m": round(distance, 3),
            "reach_id": properties.get("reach_id"),
            "time_utc": properties.get("time_str"),
            "river_name": properties.get("river_name"),
            "wse_m": _finite_or_none(properties.get("wse")),
            "wse_total_uncertainty_m": _finite_or_none(properties.get("wse_u")),
            "reach_q": _int_or_none(properties.get("reach_q")),
            "reach_q_bitfield": _int_or_none(properties.get("reach_q_b")),
            "partial_f": _int_or_none(properties.get("partial_f")),
            "obs_frac_n": _finite_or_none(properties.get("obs_frac_n")),
        }
        nearby.append(item)
    nearby.sort(key=lambda item: item["distance_to_window_m"])
    quality_counts = Counter(str(item["reach_q"]) for item in nearby if item["reach_q"] is not None)
    return {
        "feature_count": feature_count,
        "features_within_radius": len(nearby),
        "reach_q_counts_within_radius": dict(sorted(quality_counts.items())),
        "good_quality_wse_count": sum(
            1 for item in nearby if item["reach_q"] == 0 and item["wse_m"] is not None
        ),
        "nearest_by_quality": {
            str(q): next((item for item in nearby if item["reach_q"] == q), None)
            for q in (0, 1, 2, 3)
        },
        "nearest_reaches": nearby[:10],
    }


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or abs(number) >= 1e10:
        return None
    return number


def _int_or_none(value: Any) -> int | None:
    number = _finite_or_none(value)
    return int(number) if number is not None else None


def screen_pair(
    *, pair_record_path: Path, output_path: Path, case_id: str | None = None,
    window_days: int = 6, radius_km: float = 50.0,
) -> dict[str, Any]:
    if window_days < 0 or window_days > 30:
        raise ValueError("temporal window must be between 0 and 30 calendar days")
    if not math.isfinite(radius_km) or radius_km <= 0 or radius_km > 500:
        raise ValueError("screen radius must be greater than 0 and no more than 500 km")
    _, pair_case_id, bbox, pair_times = _read_pair(pair_record_path)
    case_id = case_id or pair_case_id or pair_record_path.stem
    if not earthaccess.login(strategy="netrc", persist=False):
        raise RuntimeError("Earthdata Login failed using the local netrc")
    session = earthaccess.get_requests_https_session()
    target_times = [_utc(value) for value in pair_times]
    query_days: set[date] = set()
    for target in target_times:
        for offset in range(-window_days, window_days + 1):
            query_days.add((target + timedelta(days=offset)).date())
    queries = [_query_day(session, day, bbox) for day in sorted(query_days)]
    passes = _select_unique_passes(queries)
    if len(passes) > 64:
        raise ValueError("catalog search returned more than 64 unique passes; narrow the time window")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    retrieved: list[dict[str, Any]] = []
    total_bytes = 0
    with tempfile.TemporaryDirectory(prefix="echo-swot-riversp-") as temp_dir:
        temp_root = Path(temp_dir)
        for entry in passes:
            url = _download_url(entry)
            archive = temp_root / f"{entry.get('id', 'granule')}.zip"
            size, checksum = _download(session, url, archive, MAX_TOTAL_BYTES - total_bytes)
            retrieved_at = datetime.now(timezone.utc).isoformat()
            total_bytes += size
            proximity = _quality_summary(
                archive, bbox=bbox, radius_m=radius_km * 1000.0,
            )
            retrieved.append({
                "cmr_granule_id": entry.get("id"),
                "producer_granule_id": entry.get("producer_granule_id"),
                "acquisition_start_utc": entry.get("time_start"),
                "acquisition_end_utc": entry.get("time_end"),
                "cmr_updated_utc": entry.get("updated"),
                "collection_concept_id": entry.get("collection_concept_id"),
                "download_url": url,
                "download_bytes": size,
                "download_sha256": checksum,
                "retrieved_at_utc": retrieved_at,
                "proximity": proximity,
            })
    good_wse_count = sum(
        item["proximity"]["good_quality_wse_count"] for item in retrieved
    )
    any_good = good_wse_count > 0
    status = (
        "NO_GRANULES_IN_SEARCH_WINDOW" if not passes else
        "RETRIEVED_CANDIDATE_GOOD_QUALITY" if any_good else
        "RETRIEVED_QUALITY_LIMITED"
    )
    record = {
        "record_type": "ECHO_SWOT_RIVERSP_REACH_SCREEN",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "status": status,
        "scope": "Catalog, access, spatial proximity, and provider-quality screen only; not a SAR validation or causal assessment.",
        "source": {
            "provider": "NASA/JPL PO.DAAC",
            "mission": "Surface Water and Ocean Topography (SWOT)",
            "instrument": "Ka-band Radar Interferometer (KaRIn)",
            "product": "SWOT Level 2 River Single-Pass Vector Reach Data Product, Version D",
            "short_name": SHORT_NAME,
            "collection_concept_id": COLLECTION_ID,
            "doi": DOI,
            "dataset_url": DATASET_URL,
            "product_description_document_url": PDD_URL,
            "retrieval_service": "PO.DAAC protected Earthdata HTTPS archive",
            "authentication": "Earthdata Login using local netrc; credentials and tokens are not recorded",
        },
        "case_observations": {
            "source_pair_record": str(pair_record_path),
            "sar_acquisition_times_utc": pair_times,
            "case_window_bbox_wgs84": list(bbox),
            "distance_crs": f"local azimuthal equidistant centered at {((bbox[0] + bbox[2]) / 2):.8f},{((bbox[1] + bbox[3]) / 2):.8f}",
            "distance_reference": "Distance from the reach polyline to the rectangular bounding window of the SAR analysis AOI.",
        },
        "catalog_search": {
            "temporal_window_calendar_days_each_side": window_days,
            "bounding_box_wgs84": list(bbox),
            "unique_pass_count": len(passes),
            "queries": [
                {key: value for key, value in query.items() if key != "entries"}
                for query in queries
            ],
            "duplicate_processing_versions_collapsed": True,
            "duplicate_selection_rule": "For identical producer pass names differing only in PGD0 processing suffix, keep the CMR entry with the latest updated timestamp.",
        },
        "processing": {
            "method": "Retrieve complete pass ZIPs within bounded temporal/AOI catalog search; inspect the reach shapefile using GDAL; transform geometries to a local azimuthal equidistant CRS; calculate distance to the case-window rectangle; summarize native reach_q within the configured radius.",
            "quality_rule": "reach_q 0=good, 1=suspect, 2=degraded, 3=bad per the linked NASA Product Description Document. Only q0 is counted as good; lower quality values are reported without promotion.",
            "software": {
                "earthaccess": earthaccess.__version__,
                "shapely": shapely.__version__,
                "pyproj": pyproj.__version__,
                "gdal_ogr2ogr": subprocess.run([shutil.which("ogr2ogr") or "ogr2ogr", "--version"], capture_output=True, text=True, check=True).stdout.strip(),
            },
            "radius_km": radius_km,
            "total_download_bytes": total_bytes,
        },
        "retrieved_granules": retrieved,
        "result": {
            "good_quality_reaches_q0_with_valid_wse": good_wse_count,
            "nearest_any_reach_m": min(
                (item["proximity"]["nearest_reaches"][0]["distance_to_window_m"]
                 for item in retrieved if item["proximity"]["nearest_reaches"]),
                default=None,
            ),
            "disposition": (
                "At least one provider-quality-good reach was found in the configured radius; "
                "scientific relevance and relationship to the SAR AOI still require review."
                if any_good else
                "No provider-quality-good reach with a valid WSE was found in the configured radius; do not use as directional corroboration or SAR validation."
            ),
        },
        "interpretation_limits": [
            "Reach proximity does not establish hydrologic connectivity or that the reach represents the SAR analysis window.",
            "The screening radius and temporal window are user-configurable search bounds, not scientific acceptance criteria.",
            "Provider quality flags are preserved; q1, q2, and q3 are not treated as good-quality observations.",
            "This screen does not compute water-level changes or alter the SAR pair's provider QA disposition.",
        ],
    }
    output_path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-id")
    parser.add_argument("--window-days", type=int, default=6)
    parser.add_argument("--radius-km", type=float, default=50.0)
    args = parser.parse_args()
    record = screen_pair(
        pair_record_path=args.pair_record,
        output_path=args.output,
        case_id=args.case_id,
        window_days=args.window_days,
        radius_km=args.radius_km,
    )
    print(json.dumps({
        "output": str(args.output),
        "case_id": record["case_id"],
        "status": record["status"],
        "granules": len(record["retrieved_granules"]),
        "bytes": record["processing"]["total_download_bytes"],
        "good_quality_reaches": record["result"]["good_quality_reaches_q0_with_valid_wse"],
        "nearest_reach_m": record["result"]["nearest_any_reach_m"],
    }, indent=2))


if __name__ == "__main__":
    main()
