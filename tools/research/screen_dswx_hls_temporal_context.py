#!/usr/bin/env python3
"""Screen NASA CMR for DSWx-HLS granules near two reference acquisitions.

This is metadata discovery only. CMR bounding-box matches are intersections,
not proof that a product has valid pixels across the requested AOI.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import requests


CMR_GRANULE_URL = "https://cmr.earthdata.nasa.gov/search/granules.umm_json"
CMR_API_DOCS = "https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html"
COLLECTION_CONCEPT_ID = "C2617126679-POCLOUD"
MAX_PAGE_SIZE = 200


class ScreenError(ValueError):
    """Raised when the CMR response cannot be recorded completely."""


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ScreenError(f"invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ScreenError("reference timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _granule_item(item: dict[str, Any], reference_time: datetime) -> dict[str, Any]:
    umm = item.get("umm", {})
    meta = item.get("meta", {})
    granule_id = umm.get("GranuleUR")
    concept_id = meta.get("concept-id")
    temporal = umm.get("TemporalExtent", {}).get("RangeDateTime", {})
    acquisition = temporal.get("BeginningDateTime") or temporal.get("EndingDateTime")
    if not isinstance(granule_id, str) or not isinstance(concept_id, str) or not acquisition:
        raise ScreenError("CMR granule is missing identity or acquisition time")
    acquired_at = _parse_time(acquisition)
    delta_days = (acquired_at - reference_time).total_seconds() / 86400
    return {
        "granule_id": granule_id,
        "cmr_concept_id": concept_id,
        "collection_version": umm.get("CollectionReference", {}).get("Version"),
        "acquisition_time_utc": acquired_at.isoformat().replace("+00:00", "Z"),
        "offset_from_reference_days": round(delta_days, 6),
        "cmr_granule_url": f"https://cmr.earthdata.nasa.gov/search/concepts/{concept_id}.umm_json",
    }


def search_reference(
    session: requests.Session,
    *,
    label: str,
    reference_time: datetime,
    bounds_wgs84: tuple[float, float, float, float],
    window_days: int,
) -> dict[str, Any]:
    start = reference_time - timedelta(days=window_days)
    end = reference_time + timedelta(days=window_days)
    params = {
        "collection_concept_id": COLLECTION_CONCEPT_ID,
        "bounding_box": ",".join(str(value) for value in bounds_wgs84),
        "temporal": f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')},{end.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "page_size": MAX_PAGE_SIZE,
        "sort_key": "-start_date",
    }
    response = session.get(CMR_GRANULE_URL, params=params, timeout=(10, 45))
    if response.status_code != 200:
        raise ScreenError(f"NASA CMR returned HTTP {response.status_code}")
    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        raise ScreenError("NASA CMR returned invalid JSON") from exc
    raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise ScreenError("NASA CMR UMM-G response has no granule list")
    try:
        hit_count = int(response.headers.get("CMR-Hits", len(raw_items)))
    except ValueError as exc:
        raise ScreenError("NASA CMR returned an invalid hit count") from exc
    if hit_count > len(raw_items):
        raise ScreenError(
            f"NASA CMR page is incomplete ({len(raw_items)} of {hit_count}); narrow the time window"
        )
    candidates = [_granule_item(item, reference_time) for item in raw_items]
    candidates.sort(key=lambda item: (abs(item["offset_from_reference_days"]), item["granule_id"]))
    return {
        "reference_label": label,
        "reference_acquisition_utc": reference_time.isoformat().replace("+00:00", "Z"),
        "temporal_window_utc": [
            start.isoformat().replace("+00:00", "Z"),
            end.isoformat().replace("+00:00", "Z"),
        ],
        "request_url": response.url,
        "http_status": response.status_code,
        "cmr_hit_count": hit_count,
        "returned_item_count": len(raw_items),
        "response_sha256": sha256(response.content).hexdigest(),
        "nearest_candidate": candidates[0] if candidates else None,
        "candidates_by_absolute_time_offset": candidates,
    }


def screen(
    bounds_wgs84: tuple[float, float, float, float],
    reference_before: datetime,
    reference_after: datetime,
    *,
    window_days: int = 7,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    west, south, east, north = bounds_wgs84
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ScreenError("bounds must be an ordered WGS84 rectangle")
    if any(value.tzinfo is None or value.utcoffset() is None for value in (reference_before, reference_after)):
        raise ScreenError("reference timestamps must include a timezone")
    if not 1 <= window_days <= 60:
        raise ScreenError("window_days must be between 1 and 60")
    client = session or requests.Session()
    results = [
        search_reference(
            client,
            label=label,
            reference_time=reference,
            bounds_wgs84=bounds_wgs84,
            window_days=window_days,
        )
        for label, reference in (("before", reference_before), ("after", reference_after))
    ]
    candidates: dict[str, dict[str, Any]] = {}
    for result in results:
        for item in result["candidates_by_absolute_time_offset"]:
            candidates[item["granule_id"]] = item
    return {
        "record_type": "ECHO_DSWX_HLS_TEMPORAL_CONTEXT_CATALOG_SCREEN",
        "schema_version": 1,
        "status": "METADATA_ONLY_NO_PIXEL_QA",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "NASA CMR / PO.DAAC",
        "collection_concept_id": COLLECTION_CONCEPT_ID,
        "collection": "OPERA_L3_DSWX-HLS_V1",
        "api_documentation_url": CMR_API_DOCS,
        "bounds_wgs84": list(bounds_wgs84),
        "window_days_each_side": window_days,
        "query_results": results,
        "unique_candidate_count": len(candidates),
        "spatial_limit": "CMR bounding-box matching indicates footprint intersection only; valid AOI coverage requires bounded pixel extraction and product quality review.",
        "analysis_limit": "Catalog metadata do not establish suitability, valid optical coverage, water extent, SAR corroboration, or causation.",
        "source_arrays_retrieved": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bounds", required=True, nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--reference-before", required=True, help="ISO-8601 timestamp of first reference acquisition")
    parser.add_argument("--reference-after", required=True, help="ISO-8601 timestamp of second reference acquisition")
    parser.add_argument("--window-days", type=int, default=7, help="catalog search window on each side of each reference")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        record = screen(
            tuple(args.bounds),
            _parse_time(args.reference_before),
            _parse_time(args.reference_after),
            window_days=args.window_days,
        )
    except (ScreenError, requests.RequestException) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"status={record['status']}")
    print(f"unique_candidate_count={record['unique_candidate_count']}")
    for query in record["query_results"]:
        nearest = query["nearest_candidate"]
        print(f"nearest_{query['reference_label']}={nearest['granule_id'] if nearest else 'NONE'}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
