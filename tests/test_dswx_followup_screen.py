import json
from datetime import datetime, timezone

import pytest

from tools.research.screen_dswx_hls_temporal_context import ScreenError, screen


def _item(granule_id, concept_id, acquisition):
    return {
        "meta": {"concept-id": concept_id},
        "umm": {
            "GranuleUR": granule_id,
            "CollectionReference": {"Version": "1.0"},
            "TemporalExtent": {"RangeDateTime": {"BeginningDateTime": acquisition}},
        },
    }


class _Response:
    status_code = 200
    url = "https://cmr.example/search/granules.umm_json"

    def __init__(self, items, hits=None):
        self.content = json.dumps({"items": items}).encode()
        self.headers = {"CMR-Hits": str(len(items) if hits is None else hits)}

    def json(self):
        return json.loads(self.content)


class _Session:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.params = []

    def get(self, url, *, params, timeout):
        self.params.append(params)
        return next(self.responses)


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def test_screen_ranks_metadata_candidates_nearest_to_each_reference():
    before = _Response(
        [
            _item("before-far", "G-FAR", "2024-05-08T12:00:00Z"),
            _item("before-near", "G-NEAR", "2024-05-13T12:00:00Z"),
        ]
    )
    after = _Response([_item("after-near", "G-AFTER", "2024-06-03T12:00:00Z")])
    session = _Session([before, after])

    record = screen(
        (-51.24, -30.04, -51.23, -30.03),
        _time("2024-05-11T08:49:47Z"),
        _time("2024-06-04T08:49:46Z"),
        session=session,
    )

    assert record["status"] == "METADATA_ONLY_NO_PIXEL_QA"
    assert record["source_arrays_retrieved"] is False
    assert record["query_results"][0]["nearest_candidate"]["granule_id"] == "before-near"
    assert record["query_results"][1]["nearest_candidate"]["granule_id"] == "after-near"
    assert record["query_results"][0]["cmr_hit_count"] == 2
    assert session.params[0]["bounding_box"] == "-51.24,-30.04,-51.23,-30.03"


def test_screen_rejects_a_page_that_does_not_cover_all_cmr_hits():
    session = _Session([_Response([_item("one", "G1", "2024-05-11T00:00:00Z")], hits=2)])

    with pytest.raises(ScreenError, match="page is incomplete"):
        screen(
            (-51.24, -30.04, -51.23, -30.03),
            _time("2024-05-11T08:49:47Z"),
            _time("2024-06-04T08:49:46Z"),
            session=session,
        )


def test_screen_rejects_invalid_bounds_and_naive_times():
    with pytest.raises(ScreenError, match="ordered WGS84"):
        screen(
            (1, 1, 0, 0),
            _time("2024-05-11T08:49:47Z"),
            _time("2024-06-04T08:49:46Z"),
            session=_Session([]),
        )
    with pytest.raises(ScreenError, match="timezone"):
        screen(
            (-51.24, -30.04, -51.23, -30.03),
            datetime.fromisoformat("2024-05-11T08:49:47"),
            _time("2024-06-04T08:49:46Z"),
            session=_Session([]),
        )
