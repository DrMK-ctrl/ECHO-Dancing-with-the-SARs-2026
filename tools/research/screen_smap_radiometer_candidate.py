"""Screen independent SMAP radiometer soil-moisture metadata against an AOI."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


CMR = "https://cmr.earthdata.nasa.gov/search"
CLIENT_ID = "ECHO-SMAP-RADIOMETER-SCREEN"
SHORT_NAME = "SPL3SMP_E"
VERSION = "006"
COLLECTION_ID = "C2938664763-NSIDC_CPRD"
DOI = "10.5067/M20OXIZHY3RJ"
USER_GUIDE = "https://nsidc.org/sites/default/files/documents/user-guide/spl3smp_e-v006-userguide.pdf"
PRODUCT_PAGE = "https://nsidc.org/data/spl3smp_e/versions/6"
DATE_IN_TITLE = re.compile(r"SMAP_L3_SM_P_E_(\d{8})_")
DATA_REL = "http://esipfed.org/ns/fedsearch/1.1/data#"


class ScreenError(ValueError):
    """Raised when the CMR candidate screen is incomplete or inconsistent."""


def _get_json(url: str) -> tuple[dict, str, int]:
    request = Request(url, headers={"Accept": "application/json", "Client-Id": CLIENT_ID})
    with urlopen(request, timeout=45) as response:
        payload = response.read()
        hits = int(response.headers.get("CMR-Hits", "0"))
    try:
        result = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ScreenError("CMR returned invalid JSON") from exc
    return result, sha256(payload).hexdigest(), hits


def _search_url(endpoint: str, params: dict[str, str]) -> str:
    return f"{CMR}/{endpoint}.json?{urlencode(params)}"


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat, dlon = lat2_r - lat1_r, math.radians(lon2 - lon1)
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(math.sqrt(value))


def build_screen_record(
    *,
    collection_payload: dict,
    collection_sha256: str,
    granule_payload: dict,
    granule_sha256: str,
    cmr_hits: int,
    query_url: str,
    bounds_wgs84: tuple[float, float, float, float],
    start_date: date,
    end_date: date,
    case_id: str,
) -> dict:
    collection_entries = collection_payload.get("feed", {}).get("entry", [])
    if len(collection_entries) != 1:
        raise ScreenError("CMR collection search must resolve exactly one collection")
    collection = collection_entries[0]
    if (
        collection.get("id") != COLLECTION_ID
        or collection.get("short_name") != SHORT_NAME
        or collection.get("version_id") != VERSION
        or "Radiometer" not in collection.get("title", "")
    ):
        raise ScreenError("CMR collection identity differs from the pinned radiometer-only product")
    entries = granule_payload.get("feed", {}).get("entry", [])
    if cmr_hits != len(entries):
        raise ScreenError(f"CMR granule pagination incomplete: {len(entries)} records of {cmr_hits}")
    records = []
    by_date: dict[str, dict] = {}
    for entry in entries:
        title = entry.get("title", "")
        match = DATE_IN_TITLE.search(title)
        if not match:
            raise ScreenError(f"SMAP daily granule title has no acquisition date: {title}")
        day = datetime.strptime(match.group(1), "%Y%m%d").date()
        if day in by_date:
            raise ScreenError(f"CMR returned duplicate daily SMAP granules for {day}")
        data_links = [
            link.get("href")
            for link in entry.get("links", [])
            if link.get("rel") == DATA_REL
            and isinstance(link.get("href"), str)
            and link["href"].startswith("https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/SMAP/SPL3SMP_E/")
            and link["href"].endswith(".h5")
        ]
        if len(data_links) != 1:
            raise ScreenError(f"daily granule must have exactly one data link: {title}")
        record = {
            "granule_id": entry.get("id"),
            "title": title,
            "date_utc": day.isoformat(),
            "temporal_start_utc": entry.get("time_start"),
            "temporal_end_utc": entry.get("time_end"),
            "cmr_updated_utc": entry.get("updated"),
            "data_access_url": data_links[0],
        }
        by_date[day] = record
        records.append(record)
    records.sort(key=lambda item: item["date_utc"])
    expected_days = (end_date - start_date).days + 1
    if expected_days != cmr_hits or [date.fromisoformat(item["date_utc"]) for item in records] != [
        date.fromordinal(start_date.toordinal() + index) for index in range(expected_days)
    ]:
        raise ScreenError("CMR result does not provide one consecutive daily granule per requested day")

    west, south, east, north = bounds_wgs84
    aoi_width_km = _distance_km((south + north) / 2, west, (south + north) / 2, east)
    aoi_height_km = _distance_km(south, (west + east) / 2, north, (west + east) / 2)
    target_days = sorted({"2024-05-08", "2024-06-01"})
    target_granules = [by_date[date.fromisoformat(day)] for day in target_days if date.fromisoformat(day) in by_date]
    if len(target_granules) != 2:
        raise ScreenError("CMR result lacks a daily granule on one of the SAR acquisition dates")

    return {
        "record_type": "ECHO_SMAP_RADIOMETER_CANDIDATE_SCREEN",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "status": "SCREENED_SPATIALLY_TOO_COARSE_FOR_AOI_SCALE_TEST",
        "source": {
            "provider": "NASA National Snow and Ice Data Center DAAC",
            "mission": "Soil Moisture Active Passive (SMAP)",
            "instrument": "L-band radiometer",
            "short_name": SHORT_NAME,
            "version": VERSION,
            "collection_concept_id": COLLECTION_ID,
            "doi": DOI,
            "product_title": collection["title"],
            "product_url": PRODUCT_PAGE,
            "user_guide_url": USER_GUIDE,
            "measurement": "Daily surface soil-moisture retrieval, approximately top 5 cm",
            "source_independence": "Radiometer-only SMAP product; does not use Sentinel-1 radar inputs.",
        },
        "query": {
            "cmr_collection_search_url": _search_url("collections", {"short_name": SHORT_NAME, "version": VERSION, "page_size": "20"}),
            "cmr_granule_search_url": query_url,
            "cmr_retrieval_time_utc": datetime.now(timezone.utc).isoformat(),
            "requested_start_date_utc": start_date.isoformat(),
            "requested_end_date_utc": end_date.isoformat(),
            "bounds_wgs84": list(bounds_wgs84),
            "cmr_hit_count": cmr_hits,
            "cmr_result_count": len(records),
            "collection_response_sha256": collection_sha256,
            "granule_response_sha256": granule_sha256,
        },
        "spatial_suitability": {
            "aoi_width_km_approx": aoi_width_km,
            "aoi_height_km_approx": aoi_height_km,
            "product_grid_posting_km": 9,
            "radiometer_native_footprint_km_approx": 36,
            "backus_gilbert_contributing_domain_km_approx": 33,
            "aoi_width_to_native_footprint_ratio": aoi_width_km / 36,
            "aoi_height_to_native_footprint_ratio": aoi_height_km / 36,
            "disposition": "The daily records cover both SAR dates, and the product is Sentinel-1 independent. However, the AOI is far smaller than both the 9 km posting and approximately 36 km radiometer footprint; its grid values cannot resolve within-AOI surface-state patterns for comparison to the SAR response.",
        },
        "selected_daily_granules": target_granules,
        "screened_daily_granules": records,
        "retrieval": {
            "data_files_downloaded": False,
            "pixel_values_read": False,
            "provider_quality_flags_evaluated": False,
            "disposition": "Metadata-only candidate screen; no soil-moisture measurement entered the investigation.",
        },
        "interpretation_limit": "This product is not rejected for QA. It is not suitable to test an AOI-scale mechanism in this case because its effective spatial support is much coarser than the AOI. It may only serve as regional context if a separate question justifies that scale.",
        "processing": {
            "method": "CMR collection identity check, complete consecutive daily granule screen, date-specific granule selection, and comparison of AOI dimensions to the published product grid posting, native radiometer footprint, and interpolation contributing domain.",
            "no_data_values_retrieved": True,
            "no_resampling": True,
            "no_hypothesis_result": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", default="rio-grande-do-sul-t163-349925-diagnostic-2024")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2024, 5, 7))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2024, 6, 3))
    parser.add_argument("--bbox", nargs=4, type=float, default=(-51.24, -30.04, -51.23, -30.03), help="exact AOI: west south east north")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.end < args.start or (args.end - args.start).days > 60:
        raise SystemExit("screen interval must be ordered and no longer than 61 days")
    collection_url = _search_url("collections", {"short_name": SHORT_NAME, "version": VERSION, "page_size": "20"})
    collection_payload, collection_hash, _ = _get_json(collection_url)
    params = {
        "collection_concept_id": COLLECTION_ID,
        "temporal": f"{args.start.isoformat()}T00:00:00Z,{args.end.isoformat()}T23:59:59Z",
        "bounding_box": ",".join(str(value) for value in args.bbox),
        "page_size": "100",
        "sort_key[]": "start_date",
    }
    query_url = _search_url("granules", params)
    granule_payload, granule_hash, hits = _get_json(query_url)
    result = build_screen_record(
        collection_payload=collection_payload,
        collection_sha256=collection_hash,
        granule_payload=granule_payload,
        granule_sha256=granule_hash,
        cmr_hits=hits,
        query_url=query_url,
        bounds_wgs84=tuple(args.bbox),
        start_date=args.start,
        end_date=args.end,
        case_id=args.case_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "granules": len(result["screened_daily_granules"]), "aoi_width_km": result["spatial_suitability"]["aoi_width_km_approx"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
