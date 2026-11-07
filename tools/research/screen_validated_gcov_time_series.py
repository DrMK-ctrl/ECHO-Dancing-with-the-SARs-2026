"""Screen recent global NISAR VALIDATED GCOV acquisitions for time-series pairs."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

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


def screen_date_windows(
    start: date,
    end: date,
    *,
    search: Callable[[str, str], list[dict[str, Any]]],
    retrieved_at: datetime | None = None,
) -> dict[str, Any]:
    """Search one-day ASF windows, deduplicate scenes, and run existing pair rules.

    ASF date windows are queried as ``[day, next_day]``. Adjacent windows can
    return a scene whose acquisition interval overlaps the boundary; scene IDs
    are deduplicated before temporal matching. A result count equal to the cap
    is recorded as potentially truncated.
    """
    if not isinstance(start, date) or not isinstance(end, date) or start > end:
        raise ValueError("start and end must be ordered calendar dates")
    day_count = (end - start).days + 1
    if day_count > MAX_QUERY_DAYS:
        raise ValueError(f"date span exceeds {MAX_QUERY_DAYS} daily queries")

    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")
    windows = []
    features_by_id: dict[str, dict[str, Any]] = {}
    cursor = start
    while cursor <= end:
        next_day = cursor + timedelta(days=1)
        features = search(cursor.isoformat(), next_day.isoformat())
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
    all_dates = sorted(
        {
            feature.get("properties", {}).get("startTime", "")[:10]
            for feature in features
            if isinstance(feature.get("properties", {}).get("startTime"), str)
        }
    )
    return {
        "schema_version": 1,
        "record_type": "ASF_NISAR_VALIDATED_GCOV_GLOBAL_TEMPORAL_SCREEN",
        "retrieved_at_utc": retrieved_at.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "catalog_client": "asf_search",
        "catalog_query": {
            "dataset": "NISAR",
            "processing_level": "GCOV",
            "data_maturity": "VALIDATED",
            "spatial_filter": None,
            "start_date_inclusive": start.isoformat(),
            "end_date_inclusive": end.isoformat(),
            "daily_query_result_cap": MAX_RESULTS_PER_QUERY,
            "pagination": "asf_search.search_generator; features deduplicated by scene ID",
            "windows": windows,
        },
        "unique_scene_count": len(features),
        "unique_acquisition_dates_observed": all_dates,
        "potentially_truncated_window_count": sum(
            window["potentially_truncated"] for window in windows
        ),
        "metadata_temporal_pair_count": len(pairs),
        "metadata_temporal_pairs": pairs,
        "features": [_compact_catalog_feature(feature) for feature in features],
        "interpretation_limit": (
            "ASF catalog metadata only. This screen is global within the queried "
            "date windows, and one or more capped windows may be incomplete. It "
            "does not establish archive completeness, QA suitability, spatial "
            "coverage of a particular AOI, pixel alignment, or a physical change."
        ),
    }


def _asf_search(start: str, end: str) -> list[dict[str, Any]]:
    import asf_search as asf

    options = asf.ASFSearchOptions(
        start=start,
        end=end,
        processingLevel=["GCOV"],
        dataset=["NISAR"],
        dataMaturity="VALIDATED",
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    record = screen_date_windows(args.start, args.end, search=_asf_search)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {record['unique_scene_count']} unique scenes; "
        f"{record['metadata_temporal_pair_count']} temporal pairs; "
        f"{record['potentially_truncated_window_count']} potentially capped day(s) "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
