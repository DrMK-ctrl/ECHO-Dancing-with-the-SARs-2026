from datetime import datetime, timezone

import pytest

from echo.opera_rtc_catalog import (
    OperaRtcCatalogError,
    OperaRtcCatalogQuery,
    build_opera_rtc_catalog_record,
)


def _feature(burst, acquired, *, platform="S1A", spacing="30", version="1.0"):
    acquired_token = acquired.replace("-", "").replace(":", "")
    if len(acquired_token) == 15:
        acquired_token += "Z"
    scene_id = (
        f"OPERA_L2_RTC-S1_{burst}_{acquired_token}_20240512T065737Z_"
        f"{platform}_{spacing}_v{version}"
    )
    return {
        "type": "Feature",
        "properties": {"fileID": scene_id, "startTime": acquired},
        "geometry": None,
    }


def _query(**updates):
    values = {
        "bounds_wgs84": [-51.35, -30.12, -51.10, -29.94],
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
    }
    values.update(updates)
    return OperaRtcCatalogQuery(**values)


def test_query_requires_ordered_wgs84_bounds_and_dates():
    with pytest.raises(OperaRtcCatalogError, match="ordered within WGS84"):
        _query(bounds_wgs84=[20, 10, 19, 11]).validate()
    with pytest.raises(OperaRtcCatalogError, match="start_date must not be after"):
        _query(start_date="2024-07-01").validate()


def test_pair_screen_groups_only_compatible_repeated_bursts():
    features = [
        _feature("T163-349924-IW2", "2024-05-08T10:00:00Z"),
        _feature("T163-349924-IW2", "2024-06-01T10:00:00Z"),
        _feature("T163-349924-IW2", "2024-06-25T10:00:00Z", platform="S1B"),
        _feature("T163-349925-IW2", "2024-06-01T10:00:00Z"),
    ]
    record = build_opera_rtc_catalog_record(
        _query(),
        features,
        retrieved_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
    )

    assert record["mission_product"].endswith("not NISAR")
    assert record["returned_feature_count"] == 4
    assert record["candidate_screen_feature_count"] == 4
    assert record["metadata_candidate_count"] == 1
    candidate = record["burst_series"][0]["adjacent_date_candidates"][0]
    assert candidate["interval_days"] == pytest.approx(24)
    assert candidate["metadata_candidate_only"] is True
    assert candidate["grid_and_valid_coverage_verified"] is False
    assert record["potentially_truncated"] is False


def test_catalog_record_marks_cap_as_potentially_truncated():
    query = _query(max_results=1)
    record = build_opera_rtc_catalog_record(
        query, [_feature("T163-349924-IW2", "2024-05-08T10:00:00Z")]
    )
    assert record["potentially_truncated"] is True
