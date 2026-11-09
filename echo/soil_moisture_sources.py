"""Revalidation for metadata-only ECOSTRESS and ISMN candidate screens."""

from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ECOSTRESS_TYPE = "ECHO_CATALOG_AVAILABILITY_SCREEN"
ISMN_TYPE = "ECHO_STATION_CATALOG_AVAILABILITY_SCREEN"


def _read_linked_json(relative: str, *, root: Path, expected_hash: str, expected_bytes: int) -> dict[str, Any]:
    path = Path(relative)
    if path.is_absolute():
        raise ValueError("source-response paths must be relative")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("source-response path escapes the project root")
    payload = resolved.read_bytes()
    if len(payload) != expected_bytes or sha256(payload).hexdigest() != expected_hash:
        raise ValueError("source-response checksum or byte count does not match")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("source response is not a JSON object")
    return value


def _haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    radius_km = 6371.0
    p1, p2 = math.radians(lat_a), math.radians(lat_b)
    dp, dl = math.radians(lat_b - lat_a), math.radians(lon_b - lon_a)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(a))


def validate_ecostress_availability_screen(
    record: dict[str, Any], *, pair_record: dict[str, Any], optical_record: dict[str, Any], case_id: str, evidence_root: Path
) -> dict[str, Any]:
    """Verify exact T024 temporal/spatial CMR queries against retained responses."""
    target = record.get("target", {})
    catalog = record.get("catalog", {})
    aoi = optical_record.get("aoi", {}).get("bounds_west_south_east_north")
    acquisitions = [
        f"{pair_record['source_products'][role]['acquisition_start_utc']}/{pair_record['source_products'][role]['acquisition_stop_utc']}"
        for role in ("before", "after")
    ]
    if (
        record.get("record_type") != ECOSTRESS_TYPE
        or record.get("case_id") != case_id
        or record.get("status") != "NO_GRANULES_IN_TARGET_INTERVAL"
        or record.get("candidate", {}).get("short_name") != "ECO_L3G_SM"
        or record.get("candidate", {}).get("version") != "002"
        or target.get("sar_acquisitions") != acquisitions
        or target.get("aoi_bbox_west_south_east_north") != aoi
        or catalog.get("pagination_complete") is not True
        or catalog.get("selection", {}).get("short_name") != "ECO_L3G_SM"
        or catalog.get("selection", {}).get("version") != "002"
        or catalog.get("selection", {}).get("page_size") != 100
    ):
        raise ValueError("ECOSTRESS screen identity, product, or T024 query target is invalid")
    queries = catalog.get("queries", [])
    by_name = {item.get("query_id"): item for item in queries}
    expected = {
        "before_aoi": ("2024-04-20T00:00:00Z", "2024-05-20T23:59:59Z", aoi, True),
        "before_regional": ("2024-04-20T00:00:00Z", "2024-05-20T23:59:59Z", target.get("regional_bbox_west_south_east_north"), True),
        "after_aoi": ("2024-05-15T00:00:00Z", "2024-06-15T23:59:59Z", aoi, True),
        "after_regional": ("2024-05-15T00:00:00Z", "2024-06-15T23:59:59Z", target.get("regional_bbox_west_south_east_north"), True),
        "global_target_interval": ("2024-04-01T00:00:00Z", "2024-07-01T23:59:59Z", None, True),
        "global_positive_control": ("2024-03-01T00:00:00Z", "2024-03-31T23:59:59Z", None, False),
    }
    if set(by_name) != set(expected):
        raise ValueError("ECOSTRESS screen must contain all bounded target and positive-control queries")
    for name, (start, end, bbox, must_be_empty) in expected.items():
        query = by_name[name]
        if (
            query.get("temporal_start") != start
            or query.get("temporal_end") != end
            or query.get("bbox_west_south_east_north") != bbox
            or query.get("page_size") != 100
            or query.get("http_status") != 200
            or query.get("cmr_hits") != query.get("returned_count")
            or query.get("pagination_complete") is not True
            or (must_be_empty and query.get("cmr_hits") != 0)
            or (not must_be_empty and not isinstance(query.get("cmr_hits"), int))
        ):
            raise ValueError(f"ECOSTRESS CMR query {name} does not match its declared screen")
        parsed_url = urlparse(query.get("query_url", ""))
        url_parameters = parse_qs(parsed_url.query)
        expected_bbox = ",".join(str(value) for value in bbox) if bbox is not None else None
        if (
            parsed_url.scheme != "https"
            or parsed_url.netloc != "cmr.earthdata.nasa.gov"
            or parsed_url.path != "/search/granules.json"
            or url_parameters.get("short_name") != ["ECO_L3G_SM"]
            or url_parameters.get("version") != ["002"]
            or url_parameters.get("temporal") != [f"{start},{end}"]
            or url_parameters.get("page_size") != ["100"]
            or url_parameters.get("page_num") != ["1"]
            or url_parameters.get("bounding_box") != ([expected_bbox] if expected_bbox is not None else None)
        ):
            raise ValueError(f"ECOSTRESS CMR URL does not reproduce the declared filters for {name}")
        pages = query.get("response_pages", [])
        if not pages or len(pages) != query.get("page_count"):
            raise ValueError(f"ECOSTRESS CMR query {name} has incomplete response-page provenance")
        entries = []
        for page_number, page in enumerate(pages, start=1):
            if (
                page.get("page_number") != page_number
                or page.get("http_status") != 200
                or page.get("cmr_hits_header") != query.get("cmr_hits")
            ):
                raise ValueError(f"ECOSTRESS response metadata does not match the CMR headers for {name}")
            payload = (evidence_root.resolve() / page["relative_path"]).resolve()
            if not payload.is_relative_to(evidence_root.resolve()):
                raise ValueError("ECOSTRESS CMR response path escapes the project root")
            raw = payload.read_bytes()
            if len(raw) != page.get("response_bytes") or sha256(raw).hexdigest() != page.get("response_sha256"):
                raise ValueError("ECOSTRESS CMR response checksum or size does not match")
            parsed = json.loads(raw)
            page_entries = parsed.get("feed", {}).get("entry", [])
            if len(page_entries) != page.get("returned_entries"):
                raise ValueError(f"ECOSTRESS response page entry count does not reproduce {name}")
            entries.extend(page_entries)
        if len(entries) != query.get("cmr_hits"):
            raise ValueError(f"ECOSTRESS CMR response pages do not reproduce {name} hit count")
    if any(by_name[name]["cmr_hits"] for name in expected if name != "global_positive_control"):
        raise ValueError("ECOSTRESS candidate exists in a target temporal query; empty-coverage status is false")
    positive_hits = by_name["global_positive_control"]["cmr_hits"]
    if positive_hits <= 0:
        raise ValueError("ECOSTRESS positive-control query did not demonstrate collection discoverability")
    return {
        "target_interval_query_count": 5,
        "target_interval_cmr_hits": 0,
        "positive_control_cmr_hits": positive_hits,
        "catalog_pagination_complete": True,
        "pixel_data_retrieved": False,
        "interpretation_role": "metadata-only NASA ECOSTRESS candidate-availability screen; no target-period granules; model-derived L3G soil-moisture product; no H3 test",
    }


def validate_ismn_station_screen(
    record: dict[str, Any], *, pair_record: dict[str, Any], optical_record: dict[str, Any], case_id: str, evidence_root: Path
) -> dict[str, Any]:
    """Recompute station distance and time coverage from the linked public inventory."""
    target = record.get("target", {})
    source = record.get("source", {})
    inventory_meta = record.get("inventory", {})
    aoi = optical_record.get("aoi", {}).get("bounds_west_south_east_north")
    acquisitions = [
        f"{pair_record['source_products'][role]['acquisition_start_utc']}/{pair_record['source_products'][role]['acquisition_stop_utc']}"
        for role in ("before", "after")
    ]
    center_lat = (aoi[1] + aoi[3]) / 2
    center_lon = (aoi[0] + aoi[2]) / 2
    if (
        record.get("record_type") != ISMN_TYPE
        or record.get("case_id") != case_id
        or record.get("status") != "NO_SPATIOTEMPORALLY_SUITABLE_STATION"
        or source.get("url") != "https://ismn.earth/static/dataviewer/network_station_details.json"
        or source.get("retrieval_status") != 200
        or target.get("sar_acquisitions") != acquisitions
        or target.get("aoi_center_latitude") != center_lat
        or target.get("aoi_center_longitude") != center_lon
        or target.get("spatial_screening_radii_km") != [5, 50, 100]
    ):
        raise ValueError("ISMN station screen identity or T024 target is invalid")
    inventory_record = _read_linked_json(
        source.get("inventory_relative_path", ""),
        root=evidence_root.resolve(),
        expected_hash=source.get("sha256", ""),
        expected_bytes=source.get("retrieval_bytes", -1),
    )
    networks = inventory_record.get("Networks", [])
    stations: list[dict[str, Any]] = []
    acquisition_dates = [date.fromisoformat(value[:10]) for value in acquisitions]
    for network in networks:
        for station in network.get("Stations", []):
            lat, lon = station.get("lat"), station.get("lng")
            if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
                continue
            distance = _haversine_km(center_lat, center_lon, float(lat), float(lon))
            soil = "soil moisture" in (station.get("variableText") or "").lower() or "soil moisture" in (network.get("network_variables") or "").lower()
            spans_pair = any(
                (ts.get("depth_from") is not None)
                and date.fromisoformat(ts.get("start_date", "9999-12-31")) <= acquisition_dates[0]
                and date.fromisoformat(ts.get("end_date", "0001-01-01")) >= acquisition_dates[1]
                for ts in station.get("Timeseries", [])
            )
            stations.append({
                "network": network.get("networkID"),
                "station_id": station.get("stationID"),
                "station_name": station.get("station_name"),
                "latitude": float(lat),
                "longitude": float(lon),
                "distance_to_aoi_center_km": distance,
                "has_soil_moisture_variable": soil,
                "listed_time_start": station.get("minimum"),
                "listed_time_end": station.get("maximum"),
                "soil_moisture_timeseries_spans_both_acquisitions": soil and spans_pair,
            })
    if not stations:
        raise ValueError("ISMN inventory has no station coordinates to screen")
    nearest = min(stations, key=lambda item: item["distance_to_aoi_center_km"])
    soil_near = [item for item in stations if item["has_soil_moisture_variable"] and item["distance_to_aoi_center_km"] <= 100]
    spanning_near = [item for item in soil_near if item["soil_moisture_timeseries_spans_both_acquisitions"]]
    expected_nearest = inventory_meta.get("nearest_station", {})
    if (
        inventory_meta.get("network_count") != len(networks)
        or inventory_meta.get("station_count") != len(stations)
        or inventory_meta.get("stations_within_5_km") != sum(item["distance_to_aoi_center_km"] <= 5 for item in stations)
        or inventory_meta.get("stations_within_50_km") != sum(item["distance_to_aoi_center_km"] <= 50 for item in stations)
        or inventory_meta.get("stations_within_100_km") != sum(item["distance_to_aoi_center_km"] <= 100 for item in stations)
        or inventory_meta.get("soil_moisture_stations_within_100_km") != len(soil_near)
        or inventory_meta.get("stations_with_soil_moisture_series_spanning_both_acquisitions_within_100_km") != len(spanning_near)
        or expected_nearest.get("station_id") != nearest["station_id"]
        or expected_nearest.get("network") != nearest["network"]
        or expected_nearest.get("station_name") != nearest["station_name"]
        or expected_nearest.get("latitude") != nearest["latitude"]
        or expected_nearest.get("longitude") != nearest["longitude"]
        or expected_nearest.get("listed_time_start") != nearest["listed_time_start"]
        or expected_nearest.get("listed_time_end") != nearest["listed_time_end"]
        or not math.isclose(expected_nearest.get("distance_to_aoi_center_km", -1), nearest["distance_to_aoi_center_km"], abs_tol=0.01)
        or len(soil_near) != 0
        or len(spanning_near) != 0
    ):
        raise ValueError("ISMN station count, distance, or time-coverage summary does not reproduce from the inventory")
    return {
        "network_count": len(networks),
        "station_count": len(stations),
        "stations_within_100_km": sum(item["distance_to_aoi_center_km"] <= 100 for item in stations),
        "soil_moisture_stations_within_100_km": len(soil_near),
        "nearby_soil_moisture_series_spanning_both_acquisitions": len(spanning_near),
        "nearest_soil_moisture_station": nearest,
        "measurement_data_downloaded": False,
        "interpretation_role": "public inventory coverage only; no nearby ISMN soil-moisture time series spans both SAR dates; no station measurements were downloaded or compared",
    }
