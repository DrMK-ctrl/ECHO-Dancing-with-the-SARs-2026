from datetime import datetime, timezone

import pytest

from tools.research.screen_opera_rtc_series import build_screen_record


def _feature(scene_id, start_time):
    return {
        "type": "Feature",
        "properties": {"fileID": scene_id, "sceneName": scene_id, "startTime": start_time},
        "geometry": None,
    }


def test_opera_series_pairs_adjacent_dates_only_within_exact_burst():
    first = _feature(
        "OPERA_L2_RTC-S1_T163-349924-IW2_20240508T220717Z_S1A_30_v1.0",
        "2024-05-08T22:07:17Z",
    )
    later = _feature(
        "OPERA_L2_RTC-S1_T163-349924-IW2_20240601T220716Z_S1A_30_v1.0",
        "2024-06-01T22:07:16Z",
    )
    other_burst = _feature(
        "OPERA_L2_RTC-S1_T163-349925-IW2_20240601T220719Z_S1A_30_v1.0",
        "2024-06-01T22:07:19Z",
    )

    record = build_screen_record(
        [later, other_burst, first],
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["returned_feature_count"] == 3
    assert record["metadata_candidate_count"] == 1
    candidate = record["burst_series"][0]["adjacent_date_candidates"][0]
    assert candidate["before_scene_id"] == first["properties"]["fileID"]
    assert candidate["after_scene_id"] == later["properties"]["fileID"]
    assert candidate["interval_days"] == 23.999988425925926
    assert candidate["grid_and_valid_coverage_verified"] is False


def test_opera_series_does_not_pair_same_day_records():
    record = build_screen_record(
        [
            _feature("OPERA_L2_RTC-S1_T163-349924-IW2_A", "2024-05-08T01:00:00Z"),
            _feature("OPERA_L2_RTC-S1_T163-349924-IW2_B", "2024-05-08T02:00:00Z"),
        ]
    )
    assert record["metadata_candidate_count"] == 0


def test_opera_series_record_preserves_requested_temporal_and_geographic_scope():
    bounds = (-51.24, -30.04, -51.23, -30.03)
    record = build_screen_record(
        [],
        bounds_wgs84=bounds,
        start_date="2024-04-01",
        end_date="2024-05-10",
        result_limit=20,
    )

    assert record["catalog_query"] == {
        "dataset": "OPERA-S1",
        "processing_level": "RTC",
        "bounds_wgs84": list(bounds),
        "start_date_inclusive": "2024-04-01",
        "end_date_inclusive": "2024-05-10",
        "result_limit": 20,
    }
    assert record["potentially_truncated"] is False


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"start_date": "2024-05-11", "end_date": "2024-04-01"}, "must not precede"),
        ({"bounds_wgs84": (-52, -30, -51, 91)}, "ordered WGS84 rectangle"),
        ({"result_limit": 1001}, "between 1 and 1000"),
    ],
)
def test_opera_series_rejects_invalid_search_scope(kwargs, message):
    with pytest.raises(ValueError, match=message):
        build_screen_record([], **kwargs)
