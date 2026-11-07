from datetime import datetime, timezone

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
