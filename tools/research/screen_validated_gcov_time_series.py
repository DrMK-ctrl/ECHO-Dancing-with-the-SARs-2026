"""Screen recent global NISAR GCOV acquisitions for time-series pairs."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Callable

from asf_search.exceptions import ASFSearchError

from echo.catalog import pair_gcov_scenes


DEFAULT_START = date(2026, 10, 21)
DEFAULT_END = date(2026, 11, 7)
DEFAULT_OUTPUT = Path(
    "data/research/validated-gcov-global-time-series-2026-11-07.json"
)
MAX_RESULTS_PER_QUERY = 2000
MAX_QUERY_DAYS = 31
_CATALOG_EVIDENCE_FIELDS = (
    "fileID",
    "url",
    "processingLevel",
    "collectionName",
    "startTime",
    "stopTime",
    "crid",
    "orbit",
    "pathNumber",
    "frameNumber",
    "frameCoverage",
    "flightDirection",
    "mainBandPolarization",
    "sideBandPolarization",
    "rangeBandwidth",
    "productionConfiguration",
    "platform",
    "sensor",
)


class SearchBatch(list[dict[str, Any]]):
    """ASF result features plus the number of API pages actually consumed."""

    def __init__(self, features: list[dict[str, Any]], *, pages_retrieved: int) -> None:
        super().__init__(features)
        self.pages_retrieved = pages_retrieved


def _compact_catalog_feature(feature: dict[str, Any]) -> dict[str, Any]:
    """Keep matcher inputs and source links while hashing the complete ASF feature."""
    properties = feature.get("properties", {})
    raw = json.dumps(feature, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "type": feature.get("type", "Feature"),
        "id": feature.get("id"),
        "geometry": feature.get("geometry"),
        "properties": {
            key: properties[key]
            for key in _CATALOG_EVIDENCE_FIELDS
            if key in properties
        },
        "provenance": {
            "complete_asf_feature_sha256": hashlib.sha256(raw.encode("ascii")).hexdigest(),
            "catalog_product_url": properties.get("url"),
        },
    }


def _validated_wgs84_bounds(value: list[float] | tuple[float, ...] | None) -> list[float] | None:
    if value is None:
        return None
    if len(value) != 4 or any(not math.isfinite(item) for item in value):
        raise ValueError("bounds must be four finite WGS84 values: west south east north")
    west, south, east, north = value
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("bounds must be ordered within WGS84 longitude/latitude limits")
    return [float(west), float(south), float(east), float(north)]


def _wgs84_bounds_wkt(bounds: list[float] | None) -> str | None:
    if bounds is None:
        return None
    west, south, east, north = bounds
    return (
        f"POLYGON(({west} {south},{east} {south},{east} {north},"
        f"{west} {north},{west} {south}))"
    )


def screen_date_windows(
    start: date,
    end: date,
    *,
    search: Callable[[str, str], list[dict[str, Any]]],
    maturity: str = "VALIDATED",
    cmr_timeout_seconds: int = 30,
    query_window_days: int = 1,
    bounds_wgs84: list[float] | tuple[float, ...] | None = None,
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    """Search bounded ASF date windows, deduplicate scenes, and run pair rules.

    Each query is an inclusive-start/exclusive-boundary interval such as
    ``[day, next_day]``. Multi-day queries reduce CMR request volume but remain
    capped at ``MAX_RESULTS_PER_QUERY``; a cap-sized response is explicitly
    marked incomplete. Scene IDs are deduplicated across adjacent windows.
    """
    if not isinstance(start, date) or not isinstance(end, date) or start > end:
        raise ValueError("start and end must be ordered calendar dates")
    if maturity not in {"BETA", "PROVISIONAL", "VALIDATED"}:
        raise ValueError("maturity must be BETA, PROVISIONAL, or VALIDATED")
    if isinstance(cmr_timeout_seconds, bool) or not isinstance(cmr_timeout_seconds, int) or cmr_timeout_seconds <= 0:
        raise ValueError("cmr_timeout_seconds must be a positive integer")
    if isinstance(query_window_days, bool) or not isinstance(query_window_days, int) or not 1 <= query_window_days <= MAX_QUERY_DAYS:
        raise ValueError(f"query_window_days must be between 1 and {MAX_QUERY_DAYS}")
    bounds_wgs84 = _validated_wgs84_bounds(bounds_wgs84)
    day_count = (end - start).days + 1
    if day_count > MAX_QUERY_DAYS:
        raise ValueError(f"date span exceeds {MAX_QUERY_DAYS} daily queries")

    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    windows = []
    features_by_id: dict[str, dict[str, Any]] = {}
    failed_window_count = 0
    cursor = start
    while cursor <= end:
        next_day = min(cursor + timedelta(days=query_window_days), end + timedelta(days=1))
        try:
            features = search(cursor.isoformat(), next_day.isoformat())
        except ASFSearchError as exc:
            failed_window_count += 1
            windows.append(
                {
                    "start_inclusive": cursor.isoformat(),
                    "end_query_boundary": next_day.isoformat(),
                    "query_status": "FAILED",
                    "query_error": {
                        "type": type(exc).__name__,
                        "message": str(exc).splitlines()[0][:500],
                    },
                    "returned_feature_count": None,
                    "returned_scene_id_count": None,
                    "potentially_truncated": None,
                    "pages_retrieved": None,
                    "acquisition_dates_observed": [],
                }
            )
            cursor = next_day
            continue
        scene_ids = []
        acquisition_dates = set()
        for feature in features:
            properties = feature.get("properties", {})
            scene_id = properties.get("fileID")
            if isinstance(scene_id, str) and scene_id:
                features_by_id[scene_id] = feature
                scene_ids.append(scene_id)
            start_time = properties.get("startTime")
            if isinstance(start_time, str) and len(start_time) >= 10:
                acquisition_dates.add(start_time[:10])
        windows.append(
            {
                "start_inclusive": cursor.isoformat(),
                "end_query_boundary": next_day.isoformat(),
                "query_status": "COMPLETE",
                "query_error": None,
                "returned_feature_count": len(features),
                "returned_scene_id_count": len(set(scene_ids)),
                "potentially_truncated": len(features) >= MAX_RESULTS_PER_QUERY,
                "pages_retrieved": getattr(features, "pages_retrieved", None),
                "acquisition_dates_observed": sorted(acquisition_dates),
            }
        )
        cursor = next_day

    features = [features_by_id[key] for key in sorted(features_by_id)]
    pairs = pair_gcov_scenes(features)
    completed_window_count = len(windows) - failed_window_count
    truncated_window_count = sum(window["potentially_truncated"] is True for window in windows)
    query_execution_status = (
        "FAILED"
        if completed_window_count == 0
        else "PARTIAL"
        if failed_window_count
        else "COMPLETE"
    )
    query_coverage_status = (
        "NOT_ESTABLISHED"
        if completed_window_count == 0
        else "PARTIAL"
        if failed_window_count or truncated_window_count
        else "COMPLETE"
    )
    all_dates = sorted(
        {
            feature.get("properties", {}).get("startTime", "")[:10]
            for feature in features
            if isinstance(feature.get("properties", {}).get("startTime"), str)
        }
    )
    return {
        "schema_version": 1,
        "record_type": (
            f"ASF_NISAR_{maturity}_GCOV_SPATIAL_TEMPORAL_SCREEN"
            if bounds_wgs84 is not None
            else f"ASF_NISAR_{maturity}_GCOV_GLOBAL_TEMPORAL_SCREEN"
        ),
        "retrieved_at_utc": retrieved_at.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "catalog_client": "asf_search",
        "catalog_query": {
            "dataset": "NISAR",
            "processing_level": "GCOV",
            "data_maturity": maturity,
            "cmr_timeout_seconds": cmr_timeout_seconds,
            "spatial_filter": (
                {"type": "WGS84_BBOX", "bounds": bounds_wgs84}
                if bounds_wgs84 is not None
                else None
            ),
            "start_date_inclusive": start.isoformat(),
            "end_date_inclusive": end.isoformat(),
            "query_window_days": query_window_days,
            "query_execution_status": query_execution_status,
            "query_coverage_status": query_coverage_status,
            "completed_query_window_count": completed_window_count,
            "failed_query_window_count": failed_window_count,
            "potentially_truncated_window_count": truncated_window_count,
            "daily_query_result_cap": MAX_RESULTS_PER_QUERY,
            "pagination": "asf_search.search_generator; features deduplicated by scene ID",
            "windows": windows,
        },
        "unique_scene_count": len(features),
        "unique_acquisition_dates_observed": all_dates,
        "potentially_truncated_window_count": sum(
            window["potentially_truncated"] is True for window in windows
        ),
        "metadata_temporal_pair_count": len(pairs),
        "metadata_temporal_pairs": pairs,
        "features": [_compact_catalog_feature(feature) for feature in features],
        "interpretation_limit": (
            "All daily ASF catalog queries failed. A zero returned-scene "
            "count represents an unavailable search, not zero catalog coverage."
            if query_execution_status == "FAILED"
            else "One or more ASF catalog queries failed and/or reached the per-query "
            "result cap. Returned scenes and metadata pairs may omit candidates; "
            "coverage across the requested interval is incomplete."
            if query_coverage_status == "PARTIAL"
            else (
                "ASF catalog metadata only for the requested WGS84 bounding box and "
                "date interval. Footprint intersection is a discovery filter, not "
                "proof of full AOI coverage, valid pixels, product QA suitability, "
                "grid alignment, or physical change."
                if bounds_wgs84 is not None
                else "ASF catalog metadata only across the queried date windows. "
                "This does not establish archive completeness, product QA "
                "suitability, spatial coverage of a particular AOI, pixel "
                "alignment, or physical change."
            )
        ),
    }


def _asf_search(
    start: str,
    end: str,
    *,
    maturity: str = "VALIDATED",
    cmr_timeout_seconds: int = 30,
    intersects_with: str | None = None,
) -> list[dict[str, Any]]:
    import asf_search as asf
    from echo.catalog import asf_inclusive_end
    from asf_search.constants import INTERNAL

    if isinstance(cmr_timeout_seconds, bool) or not isinstance(cmr_timeout_seconds, int) or cmr_timeout_seconds <= 0:
        raise ValueError("cmr_timeout_seconds must be a positive integer")
    INTERNAL.CMR_TIMEOUT = cmr_timeout_seconds

    options = asf.ASFSearchOptions(
        start=start,
        end=asf_inclusive_end(end),
        processingLevel=["GCOV"],
        dataset=["NISAR"],
        dataMaturity=maturity,
        intersectsWith=intersects_with,
    )
    features = []
    pages_retrieved = 0
    for page in asf.search_generator(opts=options, maxResults=MAX_RESULTS_PER_QUERY):
        pages_retrieved += 1
        features.extend(page.geojson().get("features", []))
        if len(features) >= MAX_RESULTS_PER_QUERY:
            break
    return SearchBatch(features, pages_retrieved=pages_retrieved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=DEFAULT_START)
    parser.add_argument("--end", type=date.fromisoformat, default=DEFAULT_END)
    parser.add_argument(
        "--maturity",
        choices=("BETA", "PROVISIONAL", "VALIDATED"),
        default="VALIDATED",
        help="ASF catalog maturity to query; BETA products remain subject to the analysis maturity hold",
    )
    parser.add_argument(
        "--cmr-timeout-seconds",
        type=int,
        default=30,
        help="CMR response timeout for each ASF catalog request",
    )
    parser.add_argument(
        "--query-window-days",
        type=int,
        default=1,
        help=f"calendar days per ASF query window (1-{MAX_QUERY_DAYS}); cap-sized results remain flagged as potentially incomplete",
    )
    parser.add_argument(
        "--bounds",
        type=float,
        nargs=4,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        help="optional WGS84 bounding box to limit catalog queries",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        bounds_wgs84 = _validated_wgs84_bounds(args.bounds)
    except ValueError as exc:
        parser.error(str(exc))

    def search_window(start: str, end: str) -> list[dict[str, Any]]:
        print(f"Searching ASF {args.maturity} GCOV: {start} to {end} boundary", flush=True)
        features = _asf_search(
            start,
            end,
            maturity=args.maturity,
            cmr_timeout_seconds=args.cmr_timeout_seconds,
            intersects_with=_wgs84_bounds_wkt(bounds_wgs84),
        )
        print(
            f"ASF returned {len(features)} features across {features.pages_retrieved} page(s)",
            flush=True,
        )
        return features

    record = screen_date_windows(
        args.start,
        args.end,
        search=search_window,
        maturity=args.maturity,
        cmr_timeout_seconds=args.cmr_timeout_seconds,
        query_window_days=args.query_window_days,
        bounds_wgs84=bounds_wgs84,
    )
    output = args.output or (
        DEFAULT_OUTPUT
        if args.maturity == "VALIDATED"
        and args.start == DEFAULT_START
        and args.end == DEFAULT_END
        else Path(
            f"data/research/{args.maturity.lower()}-gcov-global-time-series-"
            f"{args.start.isoformat()}-{args.end.isoformat()}.json"
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {record['unique_scene_count']} unique scenes; "
        f"{record['metadata_temporal_pair_count']} temporal pairs; "
        f"{record['potentially_truncated_window_count']} potentially capped day(s) "
        f"to {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
