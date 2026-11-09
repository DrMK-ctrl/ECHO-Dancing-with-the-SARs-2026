"""Validation for NASA SWOT RiverSP screening records used by investigations."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any
from urllib.parse import unquote, urlparse


RECORD_TYPE = "ECHO_SWOT_RIVERSP_REACH_SCREEN"
RECORD_STATUS = "RETRIEVED_QUALITY_LIMITED"
SHORT_NAME = "SWOT_L2_HR_RiverSP_reach_D"
COLLECTION_ID = "C3233942283-POCLOUD"
_QUALITY_LEVELS = {"0", "1", "2", "3"}


class SwotRiverSpError(ValueError):
    """Raised when a RiverSP screen cannot be linked to a SAR case safely."""


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise SwotRiverSpError(f"{field} is not a timestamp")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SwotRiverSpError(f"{field} is not a valid timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise SwotRiverSpError(f"{field} must include a timezone")
    return result.astimezone(timezone.utc)


def _finite(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def validate_screen(
    record: dict[str, Any], *, pair_record: dict[str, Any], case_id: str,
    pair_record_sha256: str,
) -> dict[str, Any]:
    """Validate this non-directional screen's case, source, query, and QA links."""
    source = record.get("source", {})
    case = record.get("case_observations", {})
    search = record.get("catalog_search", {})
    processing = record.get("processing", {})
    result = record.get("result", {})
    if (
        record.get("record_type") != RECORD_TYPE
        or record.get("status") != RECORD_STATUS
        or record.get("case_id") != case_id
        or source.get("provider") != "NASA/JPL PO.DAAC"
        or source.get("mission") != "Surface Water and Ocean Topography (SWOT)"
        or source.get("short_name") != SHORT_NAME
        or source.get("collection_concept_id") != COLLECTION_ID
        or source.get("doi") != "10.5067/SWOT-RIVERSP-D"
    ):
        raise SwotRiverSpError("SWOT RiverSP screen identity or quality-limited disposition is invalid")

    pair_products = pair_record.get("source_products", {})
    expected_times = [
        pair_products.get(role, {}).get("acquisition_start_utc")
        for role in ("before", "after")
    ]
    if (
        not isinstance(case.get("sar_acquisition_times_utc"), list)
        or case["sar_acquisition_times_utc"] != expected_times
        or case.get("source_pair_record") is None
        or case.get("source_pair_record_sha256") != pair_record_sha256
    ):
        raise SwotRiverSpError("SWOT screen acquisition times do not match the linked SAR pair")
    for timestamp in expected_times:
        _parse_time(timestamp, "SAR acquisition time")
    expected_bbox = pair_record.get("grid", {}).get("window", {}).get("bounds_wgs84")
    bbox = case.get("case_window_bbox_wgs84")
    if (
        not isinstance(expected_bbox, list)
        or len(expected_bbox) != 4
        or bbox != expected_bbox
        or search.get("bounding_box_wgs84") != expected_bbox
    ):
        raise SwotRiverSpError("SWOT screen spatial window does not match the linked SAR pair")

    window_days = search.get("temporal_window_calendar_days_each_side")
    radius_km = processing.get("radius_km")
    if (
        isinstance(window_days, bool)
        or not isinstance(window_days, int)
        or not 0 <= window_days <= 30
        or not _finite(radius_km)
        or not 0 < radius_km <= 500
    ):
        raise SwotRiverSpError("SWOT screen search bounds are invalid")
    target_days = [
        _parse_time(value, "SAR acquisition time").date()
        for value in expected_times
    ]
    queries = search.get("queries")
    if not isinstance(queries, list) or not queries:
        raise SwotRiverSpError("SWOT screen has no retained CMR daily queries")
    query_dates: set[str] = set()
    for query in queries:
        if not isinstance(query, dict):
            raise SwotRiverSpError("SWOT CMR query entry is malformed")
        day = query.get("date_utc")
        try:
            query_day = datetime.strptime(day, "%Y-%m-%d").date()
        except (TypeError, ValueError) as exc:
            raise SwotRiverSpError("SWOT CMR query date is invalid") from exc
        if day in query_dates or min(abs((query_day - target).days) for target in target_days) > window_days:
            raise SwotRiverSpError("SWOT CMR query date is duplicate or outside the declared window")
        query_dates.add(day)
        pages = query.get("pages")
        if not isinstance(pages, list) or not pages:
            raise SwotRiverSpError("SWOT CMR query pagination evidence is missing")
        total = query.get("hit_count")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise SwotRiverSpError("SWOT CMR hit count is invalid")
        page_total = 0
        for expected_page, page in enumerate(pages, start=1):
            if not isinstance(page, dict):
                raise SwotRiverSpError("SWOT CMR page evidence is malformed")
            parsed = urlparse(page.get("url", ""))
            page_hash = page.get("response_sha256")
            entry_count = page.get("entry_count")
            if (
                page.get("page") != expected_page
                or parsed.scheme != "https"
                or parsed.hostname != "cmr.earthdata.nasa.gov"
                or parsed.path != "/search/granules.json"
                or not isinstance(page_hash, str)
                or len(page_hash) != 64
                or any(char not in "0123456789abcdef" for char in page_hash)
                or isinstance(entry_count, bool)
                or not isinstance(entry_count, int)
                or entry_count < 0
            ):
                raise SwotRiverSpError("SWOT CMR page evidence is malformed")
            page_total += entry_count
        if page_total != total:
            raise SwotRiverSpError("SWOT CMR page counts do not match reported hits")

    granules = record.get("retrieved_granules")
    if not isinstance(granules, list) or len(granules) != search.get("unique_pass_count"):
        raise SwotRiverSpError("SWOT retrieved granules do not match the retained catalog count")
    granule_ids: set[str] = set()
    producer_ids: set[str] = set()
    total_bytes = 0
    good_wse_count = 0
    nearest_distances: list[float] = []
    for granule in granules:
        if not isinstance(granule, dict):
            raise SwotRiverSpError("SWOT granule record is malformed")
        granule_id = granule.get("cmr_granule_id")
        producer_id = granule.get("producer_granule_id")
        url = granule.get("download_url")
        parsed_url = urlparse(url) if isinstance(url, str) else None
        file_hash = granule.get("download_sha256")
        size = granule.get("download_bytes")
        if (
            not isinstance(granule_id, str)
            or not granule_id.endswith("-POCLOUD")
            or granule_id in granule_ids
            or not isinstance(producer_id, str)
            or producer_id in producer_ids
            or parsed_url is None
            or parsed_url.scheme != "https"
            or parsed_url.hostname != "archive.swot.podaac.earthdata.nasa.gov"
            or unquote(parsed_url.path.rsplit("/", 1)[-1]) != producer_id
            or not producer_id.endswith(".zip")
            or granule.get("collection_concept_id") != COLLECTION_ID
            or not isinstance(file_hash, str)
            or len(file_hash) != 64
            or any(char not in "0123456789abcdef" for char in file_hash)
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size <= 0
        ):
            raise SwotRiverSpError("SWOT granule source identity, URL, checksum, or size is invalid")
        _parse_time(granule.get("acquisition_start_utc"), "SWOT acquisition start")
        _parse_time(granule.get("acquisition_end_utc"), "SWOT acquisition end")
        _parse_time(granule.get("cmr_updated_utc"), "SWOT CMR update time")
        _parse_time(granule.get("retrieved_at_utc"), "SWOT retrieval time")
        granule_ids.add(granule_id)
        producer_ids.add(producer_id)
        total_bytes += size

        proximity = granule.get("proximity", {})
        counts = proximity.get("reach_q_counts_within_radius", {})
        if (
            not isinstance(counts, dict)
            or any(key not in _QUALITY_LEVELS for key in counts)
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counts.values())
            or isinstance(proximity.get("features_within_radius"), bool)
            or not isinstance(proximity.get("features_within_radius"), int)
            or proximity["features_within_radius"] < 0
            or sum(counts.values()) > proximity["features_within_radius"]
        ):
            raise SwotRiverSpError("SWOT proximity quality counts are invalid")
        good_count = proximity.get("good_quality_wse_count")
        if isinstance(good_count, bool) or not isinstance(good_count, int) or not 0 <= good_count <= counts.get("0", 0):
            raise SwotRiverSpError("SWOT accepted-quality WSE count is invalid")
        good_wse_count += good_count
        nearest = proximity.get("nearest_reaches")
        if not isinstance(nearest, list):
            raise SwotRiverSpError("SWOT nearest-reach summary is invalid")
        if nearest:
            for item in nearest:
                distance = item.get("distance_to_window_m") if isinstance(item, dict) else None
                if not _finite(distance) or distance < 0 or distance > radius_km * 1000:
                    raise SwotRiverSpError("SWOT reach distance is outside the declared search radius")
            nearest_distances.append(nearest[0]["distance_to_window_m"])
        nearest_by_quality = proximity.get("nearest_by_quality", {})
        for quality in _QUALITY_LEVELS:
            selected = nearest_by_quality.get(quality)
            count = counts.get(quality, 0)
            if count == 0 and selected is not None:
                raise SwotRiverSpError("SWOT nearest-by-quality summary exists for an empty quality class")
            if selected is not None:
                if (
                    not isinstance(selected, dict)
                    or selected.get("reach_q") != int(quality)
                    or not _finite(selected.get("distance_to_window_m"))
                    or selected["distance_to_window_m"] > radius_km * 1000
                ):
                    raise SwotRiverSpError("SWOT nearest-by-quality summary is malformed")
                retained_match = next(
                    (item for item in nearest if item.get("reach_q") == int(quality)), None
                )
                if retained_match is not None and selected != retained_match:
                    raise SwotRiverSpError("SWOT nearest-by-quality summary conflicts with nearest reaches")

    if processing.get("total_download_bytes") != total_bytes:
        raise SwotRiverSpError("SWOT total retrieval bytes do not match granule records")
    expected_good = record.get("result", {}).get("good_quality_reaches_q0_with_valid_wse")
    if expected_good != good_wse_count:
        raise SwotRiverSpError("SWOT good-quality WSE count does not match granule summaries")
    expected_nearest = min(nearest_distances, default=None)
    recorded_nearest = result.get("nearest_any_reach_m")
    if recorded_nearest != expected_nearest:
        raise SwotRiverSpError("SWOT nearest-reach result does not match granule summaries")
    expected_status = (
        "NO_GRANULES_IN_SEARCH_WINDOW" if not granules else
        "RETRIEVED_CANDIDATE_GOOD_QUALITY" if good_wse_count else
        RECORD_STATUS
    )
    if record.get("status") != expected_status:
        raise SwotRiverSpError("SWOT record status is inconsistent with retrieved quality-screen results")
    return {
        "granule_count": len(granules),
        "retrieved_bytes": total_bytes,
        "good_quality_wse_count": good_wse_count,
        "nearest_reach_m": expected_nearest,
    }
