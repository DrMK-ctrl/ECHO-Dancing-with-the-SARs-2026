"""Screen one AOI's ASF OPERA RTC-S1 catalog series by exact burst identity."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Callable


RESULT_LIMIT = 1000
BURST_PATTERN = re.compile(r"_(T\d{3}-\d{6}-IW\d)_")
BOUNDS_WGS84 = (-51.35, -30.12, -51.10, -29.94)
START_DATE = "2024-01-01"
END_DATE = "2024-06-30"
DEFAULT_OUTPUT = Path(
    "data/research/opera-rtc-s1-brazil-flood-screen-2026-11-07.json"
)


def build_screen_record(
    features: list[dict[str, Any]], *, retrieved_at: datetime | None = None
) -> dict[str, Any]:
    """Group returned RTC-S1 items by burst and retain adjacent date candidates."""
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must be timezone-aware")

    by_burst: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for feature in features:
        properties = feature.get("properties", {})
        scene_id = properties.get("sceneName") or properties.get("fileID")
        if not isinstance(scene_id, str):
            continue
        match = BURST_PATTERN.search(scene_id)
        acquired = properties.get("startTime")
        if match and isinstance(acquired, str):
            by_burst[match.group(1)].append(feature)

    series = []
    for burst_id, burst_features in sorted(by_burst.items()):
        ordered = sorted(
            burst_features,
            key=lambda item: item.get("properties", {}).get("startTime", ""),
        )
        candidates = []
        for before, after in zip(ordered, ordered[1:]):
            before_properties = before.get("properties", {})
            after_properties = after.get("properties", {})
            before_time = before_properties.get("startTime")
            after_time = after_properties.get("startTime")
            if not before_time or not after_time or before_time[:10] == after_time[:10]:
                continue
            before_date = datetime.fromisoformat(before_time.replace("Z", "+00:00"))
            after_date = datetime.fromisoformat(after_time.replace("Z", "+00:00"))
            candidates.append(
                {
                    "before_scene_id": before_properties.get("fileID"),
                    "after_scene_id": after_properties.get("fileID"),
                    "before_acquisition_start_utc": before_time,
                    "after_acquisition_start_utc": after_time,
                    "interval_days": (after_date - before_date).total_seconds() / 86400,
                    "metadata_candidate_only": True,
                    "grid_and_valid_coverage_verified": False,
                }
            )
        series.append(
            {
                "burst_id": burst_id,
                "scene_count": len(ordered),
                "scene_ids": [
                    item.get("properties", {}).get("fileID") for item in ordered
                ],
                "adjacent_date_candidates": candidates,
            }
        )

    return {
        "schema_version": 1,
        "record_type": "ASF_OPERA_RTC_S1_BURST_SERIES_SCREEN",
        "retrieved_at_utc": retrieved_at.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "mission_product": "OPERA RTC-S1 derived from Sentinel-1; not NISAR",
        "catalog_client": "asf_search",
        "catalog_query": {
            "dataset": "OPERA-S1",
            "processing_level": "RTC",
            "bounds_wgs84": list(BOUNDS_WGS84),
            "start_date_inclusive": START_DATE,
            "end_date_inclusive": END_DATE,
            "result_limit": RESULT_LIMIT,
        },
        "returned_feature_count": len(features),
        "potentially_truncated": len(features) >= RESULT_LIMIT,
        "burst_series_count": len(series),
        "metadata_candidate_count": sum(
            len(item["adjacent_date_candidates"]) for item in series
        ),
        "burst_series": series,
        "features": features,
        "interpretation_limit": (
            "Catalog metadata only. Repeated burst identity does not prove equal "
            "pixel grids, valid-pixel overlap, product quality, or a physical "
            "change. OPERA RTC-S1 is a distinct Sentinel-1 product path and does "
            "not clear NISAR QA holds."
        ),
    }


def search_opera_features() -> list[dict[str, Any]]:
    import asf_search as asf

    west, south, east, north = BOUNDS_WGS84
    polygon = (
        f"POLYGON(({west} {south},{east} {south},{east} {north},"
        f"{west} {north},{west} {south}))"
    )
    options = asf.ASFSearchOptions(
        dataset=asf.DATASET.OPERA_S1,
        processingLevel=asf.PRODUCT_TYPE.RTC,
        intersectsWith=polygon,
        start=START_DATE,
        end=END_DATE,
    )
    features = []
    for page in asf.search_generator(opts=options, maxResults=RESULT_LIMIT):
        features.extend(page.geojson().get("features", []))
        if len(features) >= RESULT_LIMIT:
            return features[:RESULT_LIMIT]
    return features


def main() -> int:
    record = build_screen_record(search_opera_features())
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {record['returned_feature_count']} catalog features, "
        f"{record['metadata_candidate_count']} adjacent burst candidates to "
        f"{DEFAULT_OUTPUT}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
