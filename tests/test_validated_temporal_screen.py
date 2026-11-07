from datetime import date, datetime, timezone

import pytest

from tools.research.screen_validated_gcov_time_series import (
    MAX_RESULTS_PER_QUERY,
    screen_date_windows,
)


def _feature(scene_id="scene-a", start="2026-10-21T00:00:00Z"):
    return {
        "type": "Feature",
        "geometry": None,
        "properties": {"fileID": scene_id, "startTime": start},
    }


def test_screen_uses_one_day_windows_and_deduplicates_overlapping_scenes():
    calls = []

    def search(start, end):
        calls.append((start, end))
        if start == "2026-10-21":
            return [_feature()]
        if start == "2026-10-22":
            return [_feature(), _feature("scene-b", "2026-10-22T12:00:00Z")]
        return []

    record = screen_date_windows(
        date(2026, 10, 21),
        date(2026, 10, 23),
        search=search,
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert calls == [
        ("2026-10-21", "2026-10-22"),
        ("2026-10-22", "2026-10-23"),
        ("2026-10-23", "2026-10-24"),
    ]
    assert record["unique_scene_count"] == 2
    assert record["metadata_temporal_pair_count"] == 0
    assert record["unique_acquisition_dates_observed"] == [
        "2026-10-21",
        "2026-10-22",
    ]


def test_screen_marks_cap_sized_window_as_potentially_truncated():
    scene = _feature()
    record = screen_date_windows(
        date(2026, 10, 21),
        date(2026, 10, 21),
        search=lambda _start, _end: [scene] * MAX_RESULTS_PER_QUERY,
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["unique_scene_count"] == 1
    assert record["potentially_truncated_window_count"] == 1
    assert record["catalog_query"]["windows"][0]["potentially_truncated"] is True


def test_screen_rejects_oversized_or_reversed_date_ranges():
    with pytest.raises(ValueError, match="ordered calendar dates"):
        screen_date_windows(
            date(2026, 10, 22), date(2026, 10, 21), search=lambda *_args: []
        )
    with pytest.raises(ValueError, match="31 daily queries"):
        screen_date_windows(
            date(2026, 10, 1), date(2026, 11, 1), search=lambda *_args: []
        )
