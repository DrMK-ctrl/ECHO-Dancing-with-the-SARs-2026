"""Retain T024 ECOSTRESS catalog and ISMN station-coverage screens."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import sys

import requests


ROOT = Path(__file__).resolve().parents[2]
PAIR = ROOT / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json"
OPTICAL = ROOT / "data/research/dswx-hls-rtc-aoi-context-2026-11-07.json"
OUT_DIR = ROOT / "data/research/source-artifacts/soil-moisture-T024-050661-2026-11-09"
ECOSTRESS_OUT = ROOT / "data/research/ecostress-soil-moisture-catalog-screen-T024-050661-2026-11-09.json"
ISMN_OUT = ROOT / "data/research/ismn-station-coverage-screen-T024-050661-2026-11-09.json"
CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
ISMN_URL = "https://ismn.earth/static/dataviewer/network_station_details.json"


def _save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    p1, p2 = math.radians(lat_a), math.radians(lat_b)
    dp, dl = math.radians(lat_b - lat_a), math.radians(lon_b - lon_a)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def _cmr_screen(pair: dict, optical: dict, case_id: str) -> dict:
    bounds = optical["aoi"]["bounds_west_south_east_north"]
    acquisitions = [
        f"{pair['source_products'][role]['acquisition_start_utc']}/{pair['source_products'][role]['acquisition_stop_utc']}"
        for role in ("before", "after")
    ]
    regional = [-52.0, -31.0, -50.0, -29.0]
    specs = [
        ("before_aoi", "2024-04-20T00:00:00Z", "2024-05-20T23:59:59Z", bounds, True),
        ("before_regional", "2024-04-20T00:00:00Z", "2024-05-20T23:59:59Z", regional, True),
        ("after_aoi", "2024-05-15T00:00:00Z", "2024-06-15T23:59:59Z", bounds, True),
        ("after_regional", "2024-05-15T00:00:00Z", "2024-06-15T23:59:59Z", regional, True),
        ("global_target_interval", "2024-04-01T00:00:00Z", "2024-07-01T23:59:59Z", None, True),
        ("global_positive_control", "2024-03-01T00:00:00Z", "2024-03-31T23:59:59Z", None, False),
    ]
    query_records = []
    for query_id, start, end, bbox, must_be_empty in specs:
        queried_at = datetime.now(timezone.utc).isoformat()
        params = {"short_name": "ECO_L3G_SM", "version": "002", "temporal": f"{start},{end}", "page_size": 100, "page_num": 1}
        if bbox is not None:
            params["bounding_box"] = ",".join(str(x) for x in bbox)
        first = requests.get(CMR, params=params, timeout=45)
        first.raise_for_status()
        hit_count = int(first.headers.get("CMR-Hits", "-1"))
        if hit_count < 0:
            raise RuntimeError(f"CMR omitted CMR-Hits for {query_id}")
        total_pages = max(1, math.ceil(hit_count / 100))
        pages = []
        all_entries = []
        for page_num in range(1, total_pages + 1):
            response = first if page_num == 1 else requests.get(CMR, params={**params, "page_num": page_num}, timeout=45)
            response.raise_for_status()
            body = response.content
            document = response.json()
            entries = document.get("feed", {}).get("entry", [])
            all_entries.extend(entries)
            relative = Path("data/research/source-artifacts/soil-moisture-T024-050661-2026-11-09") / f"ecostress-{query_id}-page-{page_num}.json"
            (ROOT / relative).write_bytes(body)
            pages.append({
                "page_number": page_num,
                "relative_path": relative.as_posix(),
                "http_status": response.status_code,
                "cmr_hits_header": int(response.headers.get("CMR-Hits", "-1")),
                "returned_entries": len(entries),
                "response_bytes": len(body),
                "response_sha256": sha256(body).hexdigest(),
            })
        if len(all_entries) != hit_count:
            raise RuntimeError(f"CMR pagination incomplete for {query_id}: {len(all_entries)} of {hit_count}")
        if must_be_empty and hit_count != 0:
            raise RuntimeError(f"Target ECOSTRESS candidates exist in {query_id}; do not record an empty-coverage screen")
        query_records.append({
            "query_id": query_id,
            "queried_at_utc": queried_at,
            "scope": "AOI" if bbox == bounds else "regional" if bbox is not None else "global",
            "temporal_start": start,
            "temporal_end": end,
            "bbox_west_south_east_north": bbox,
            "query_url": first.url,
            "page_size": 100,
            "http_status": 200,
            "cmr_hits": hit_count,
            "returned_count": len(all_entries),
            "page_count": total_pages,
            "pagination_complete": True,
            "response_pages": pages,
        })
    positive = next(q["cmr_hits"] for q in query_records if q["query_id"] == "global_positive_control")
    if positive <= 0:
        raise RuntimeError("ECOSTRESS positive control did not demonstrate discoverability")
    return {
        "record_type": "ECHO_CATALOG_AVAILABILITY_SCREEN",
        "record_id": "NASA-ECOSTRESS-L3G-SM-CATALOG-SCREEN-T024-050661-2026-11-09",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "status": "NO_GRANULES_IN_TARGET_INTERVAL",
        "purpose": "Check catalog coverage for an independent soil-moisture candidate near both diagnostic SAR acquisitions.",
        "candidate": {
            "provider": "NASA LP DAAC", "mission": "ECOSTRESS", "short_name": "ECO_L3G_SM", "version": "002",
            "product_title": "Gridded Downscaled Soil Moisture Instantaneous L3 Global 70 m",
            "product_url": "https://data.nasa.gov/dataset/ecostress-gridded-downscaled-soil-moisture-instantaneous-l3-global-70-m-v002-96acf",
            "measurement_semantics": "The 70 m soil-moisture layer is a model-derived estimate based on GEOS-5 FP soil moisture and ECOSTRESS surface temperature, NDVI, and albedo; it is not a direct 70 m soil-moisture measurement.",
            "method_references": ["https://data.nasa.gov/dataset/ecostress-gridded-downscaled-soil-moisture-instantaneous-l3-global-70-m-v002-96acf", "https://ecostress.jpl.nasa.gov/data/atbds-summary-table"],
        },
        "target": {"sar_acquisitions": acquisitions, "aoi_bbox_west_south_east_north": bounds, "regional_bbox_west_south_east_north": regional},
        "catalog": {
            "provider": "NASA Common Metadata Repository", "endpoint": CMR,
            "selection": {"short_name": "ECO_L3G_SM", "version": "002", "page_size": 100},
            "pagination_complete": True, "queries": query_records,
        },
        "disposition": "NO_CATALOG_COVERAGE_FOR_TARGET_INTERVAL", "scientific_status": "NOT_TESTED",
        "interpretation": f"Five target AOI, regional, and global CMR queries returned zero granules; the March global positive control returned {positive} granules. No ECOSTRESS pixels were retrieved or evaluated.",
        "limitations": [
            "This is a catalog availability result, not a measurement or scientific assessment.",
            "The screen covers the declared queries only; it does not establish absence from every ECOSTRESS product, processing version, or possible time window.",
            "The product soil-moisture layer is model-derived and downscaled, not a direct 70 m measurement.",
            "No hypothesis disposition or SAR QA status changes as a result.",
        ],
    }


def _ismn_screen(pair: dict, optical: dict, case_id: str) -> dict:
    response = requests.get(ISMN_URL, timeout=60)
    response.raise_for_status()
    raw = response.content
    document = response.json()
    relative = Path("data/research/source-artifacts/soil-moisture-T024-050661-2026-11-09/ismn-network-station-details.json")
    (ROOT / relative).write_bytes(raw)
    bounds = optical["aoi"]["bounds_west_south_east_north"]
    lat, lon = (bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2
    acquisitions = [
        f"{pair['source_products'][role]['acquisition_start_utc']}/{pair['source_products'][role]['acquisition_stop_utc']}"
        for role in ("before", "after")
    ]
    dates = [datetime.fromisoformat(x.split("/", 1)[0].replace("Z", "+00:00")).date() for x in acquisitions]
    stations = []
    networks = document.get("Networks", [])
    for network in networks:
        for station in network.get("Stations", []):
            if not isinstance(station.get("lat"), (int, float)) or not isinstance(station.get("lng"), (int, float)):
                continue
            distance = _haversine_km(lat, lon, float(station["lat"]), float(station["lng"]))
            variables = f"{network.get('network_variables', '')} {station.get('variableText', '')}".lower()
            soil = "soil moisture" in variables
            spans = any(
                ts.get("start_date") and ts.get("end_date")
                and datetime.fromisoformat(ts["start_date"]).date() <= dates[0]
                and datetime.fromisoformat(ts["end_date"]).date() >= dates[1]
                for ts in station.get("Timeseries", [])
            )
            stations.append({
                "network": network.get("networkID"), "station_id": station.get("stationID"), "station_name": station.get("station_name"),
                "latitude": float(station["lat"]), "longitude": float(station["lng"]), "distance_to_aoi_center_km": distance,
                "soil_moisture_variable": soil, "series_spans_both_acquisitions": soil and spans,
                "listed_time_start": station.get("minimum"), "listed_time_end": station.get("maximum"),
            })
    nearest = min(stations, key=lambda item: item["distance_to_aoi_center_km"])
    nearby_soil = [s for s in stations if s["soil_moisture_variable"] and s["distance_to_aoi_center_km"] <= 100]
    nearby_spanning = [s for s in nearby_soil if s["series_spans_both_acquisitions"]]
    if nearby_soil or nearby_spanning:
        raise RuntimeError("A potentially suitable nearby ISMN station exists; evaluate it rather than recording a coverage failure")
    return {
        "record_type": "ECHO_STATION_CATALOG_AVAILABILITY_SCREEN",
        "record_id": "ISMN-SOIL-MOISTURE-STATION-COVERAGE-T024-050661-2026-11-09",
        "case_id": case_id, "status": "NO_SPATIOTEMPORALLY_SUITABLE_STATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "question": "Does the public ISMN inventory expose a soil-moisture station within 100 km with listed series spanning both SAR acquisitions?",
        "source": {
            "provider": "International Soil Moisture Network (ISMN), hosted by ICWRGC and BfG", "url": ISMN_URL,
            "retrieval_status": response.status_code, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "retrieval_bytes": len(raw), "last_modified": response.headers.get("Last-Modified"), "etag": response.headers.get("ETag"),
            "sha256": sha256(raw).hexdigest(), "inventory_relative_path": relative.as_posix(),
            "metadata_role": "Public station/time-series inventory; measurement archive was not downloaded.",
        },
        "target": {"aoi_center_latitude": lat, "aoi_center_longitude": lon, "sar_acquisitions": acquisitions, "spatial_screening_radii_km": [5, 50, 100]},
        "inventory": {
            "network_count": len(networks), "station_count": len(stations),
            "stations_within_5_km": sum(s["distance_to_aoi_center_km"] <= 5 for s in stations),
            "stations_within_50_km": sum(s["distance_to_aoi_center_km"] <= 50 for s in stations),
            "stations_within_100_km": sum(s["distance_to_aoi_center_km"] <= 100 for s in stations),
            "soil_moisture_stations_within_100_km": len(nearby_soil),
            "stations_with_soil_moisture_series_spanning_both_acquisitions_within_100_km": len(nearby_spanning),
            "distance_method": "Great-circle Haversine distance from AOI center, Earth radius 6371 km.",
            "nearest_station": {k: nearest[k] for k in ("network", "station_id", "station_name", "latitude", "longitude", "distance_to_aoi_center_km", "listed_time_start", "listed_time_end")},
        },
        "disposition": "NO_SPATIOTEMPORALLY_SUITABLE_STATION_IN_SCREENED_INVENTORY", "scientific_status": "NOT_TESTED",
        "interpretation": f"The nearest inventoried station is {nearest['distance_to_aoi_center_km']:.1f} km from the AOI; no soil-moisture station within 100 km is listed. No station measurements were retrieved or compared.",
        "limitations": [
            "This screens the public ISMN inventory snapshot only and does not establish that no independent station source exists.",
            "A station point is not an AOI-wide measurement; representativeness depends on separation and local conditions.",
            "Inventory availability is not measurement access; ISMN registration is required for its observation archive.",
            "No hypothesis disposition or SAR QA status changes as a result.",
        ],
    }


def main() -> int:
    pair = json.loads(PAIR.read_text())
    optical = json.loads(OPTICAL.read_text())
    case_id = "rio-grande-do-sul-cross-sensor-diagnostic-2024"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ecostress = _cmr_screen(pair, optical, case_id)
    ismn = _ismn_screen(pair, optical, case_id)
    _save_json(ECOSTRESS_OUT, ecostress)
    _save_json(ISMN_OUT, ismn)
    print(f"ECOSTRESS queries: {len(ecostress['catalog']['queries'])}; target hits: {sum(q['cmr_hits'] for q in ecostress['catalog']['queries'] if q['query_id'] != 'global_positive_control')}; positive control: {ecostress['catalog']['queries'][-1]['cmr_hits']}")
    print(f"ISMN inventory: {ismn['inventory']['network_count']} networks, {ismn['inventory']['station_count']} stations; nearest {ismn['inventory']['nearest_station']['distance_to_aoi_center_km']:.1f} km; nearby soil-moisture stations: {ismn['inventory']['soil_moisture_stations_within_100_km']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
