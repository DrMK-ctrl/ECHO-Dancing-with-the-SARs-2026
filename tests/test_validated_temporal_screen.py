from datetime import date, datetime, timezone

import pytest

from tools.research.screen_validated_gcov_time_series import (
    MAX_RESULTS_PER_QUERY,
    SearchBatch,
    _asf_search,
    _compact_catalog_feature,
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


def test_asf_search_collects_all_pages_and_records_page_count(monkeypatch):
    import asf_search as asf
    from asf_search.constants import INTERNAL

    monkeypatch.setattr(INTERNAL, "CMR_TIMEOUT", 30)

    class Page:
        def __init__(self, features):
            self.features = features

        def geojson(self):
            return {"features": self.features}

    options = []
    search_limits = []

    def make_options(**kwargs):
        options.append(kwargs)
        return kwargs

    def search_generator(*, opts, maxResults):
        search_limits.append(maxResults)
        return iter([Page([_feature("scene-a")]), Page([_feature("scene-b")])])

    monkeypatch.setattr(asf, "ASFSearchOptions", make_options)
    monkeypatch.setattr(asf, "search_generator", search_generator)

    result = _asf_search(
        "2026-10-22",
        "2026-10-23",
        maturity="PROVISIONAL",
        cmr_timeout_seconds=45,
    )

    assert "maxResults" not in options[0]
    assert options[0]["dataMaturity"] == "PROVISIONAL"
    assert INTERNAL.CMR_TIMEOUT == 45
    assert search_limits == [MAX_RESULTS_PER_QUERY]
    assert [feature["properties"]["fileID"] for feature in result] == [
        "scene-a",
        "scene-b",
    ]
    assert isinstance(result, SearchBatch)
    assert result.pages_retrieved == 2


def test_screen_records_pages_retrieved_for_paged_search_results():
    batch = SearchBatch([_feature()], pages_retrieved=3)
    record = screen_date_windows(
        date(2026, 10, 21),
        date(2026, 10, 21),
        search=lambda _start, _end: batch,
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["catalog_query"]["pagination"].startswith("asf_search.search_generator")
    assert record["catalog_query"]["windows"][0]["pages_retrieved"] == 3


def test_compact_catalog_record_retains_match_fields_and_hashes_full_feature():
    import hashlib
    import json

    source = _feature()
    source["geometry"] = {"type": "Point", "coordinates": [10.0, 20.0]}
    source["properties"].update(
        {
            "url": "https://example.invalid/product.h5",
            "collectionName": "NISAR_L2_GCOV_V1",
            "orbit": 123,
            "pathNumber": 1,
            "frameNumber": 2,
            "flightDirection": "ASCENDING",
            "rangeBandwidth": ["40+5"],
            "mainBandPolarization": ["HH"],
            "productionConfiguration": "PR",
            "crid": "P05036",
            "sideBandPolarization": ["HH"],
            "additionalUrls": ["https://example.invalid/irrelevant.png"],
        }
    )

    compact = _compact_catalog_feature(source)

    assert compact["geometry"] == source["geometry"]
    assert compact["properties"]["fileID"] == "scene-a"
    assert compact["properties"]["url"] == "https://example.invalid/product.h5"
    assert "additionalUrls" not in compact["properties"]
    expected_hash = hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()
    assert compact["provenance"]["complete_asf_feature_sha256"] == expected_hash


def test_screen_rejects_oversized_or_reversed_date_ranges():
    with pytest.raises(ValueError, match="ordered calendar dates"):
        screen_date_windows(
            date(2026, 10, 22), date(2026, 10, 21), search=lambda *_args: []
        )
    with pytest.raises(ValueError, match="31 daily queries"):
        screen_date_windows(
            date(2026, 10, 1), date(2026, 11, 1), search=lambda *_args: []
        )


def test_screen_records_requested_maturity_and_rejects_unknown_values():
    record = screen_date_windows(
        date(2026, 10, 21),
        date(2026, 10, 21),
        search=lambda _start, _end: [],
        maturity="PROVISIONAL",
    )
    assert record["catalog_query"]["data_maturity"] == "PROVISIONAL"
    assert record["catalog_query"]["cmr_timeout_seconds"] == 30
    assert record["record_type"] == "ASF_NISAR_PROVISIONAL_GCOV_GLOBAL_TEMPORAL_SCREEN"
    with pytest.raises(ValueError, match="maturity must be"):
        screen_date_windows(
            date(2026, 10, 21),
            date(2026, 10, 21),
            search=lambda _start, _end: [],
            maturity="UNKNOWN",
        )
    with pytest.raises(ValueError, match="positive integer"):
        screen_date_windows(
            date(2026, 10, 21),
            date(2026, 10, 21),
            search=lambda _start, _end: [],
            cmr_timeout_seconds=0,
        )
