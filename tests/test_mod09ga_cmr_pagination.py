import json

import pytest

from tools.research.build_cross_sensor_investigation import AssessmentError, _validate_mod09ga_cmr_query
from tools.research.screen_mod09ga_vegetation import _query_granule


def test_cmr_query_records_and_checks_every_page(monkeypatch):
    class FakeResponse:
        def __init__(self, url, entries, hits):
            self.url = url
            self.headers = {"CMR-Hits": str(hits)}
            self.content = json.dumps({"feed": {"hits": hits, "entry": entries}}).encode()
            self._payload = json.loads(self.content)

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    target_id = "MOD09GA.A2024132.h13v12.061.2024134233435"
    target = {
        "producer_granule_id": target_id,
        "collection_concept_id": "C2202497474-LPCLOUD",
        "id": "G123-LPCLOUD",
        "time_start": "2024-05-11T00:00:00.000Z",
        "time_end": "2024-05-11T23:59:59.000Z",
        "updated": "2024-05-12T00:00:00.000Z",
        "links": [{
            "rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
            "href": f"https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD09GA.061/{target_id}/{target_id}.hdf",
        }],
    }
    responses = [
        FakeResponse(
            "https://cmr.earthdata.nasa.gov/search/granules.json?page_num=1",
            [
                {"producer_granule_id": "MOD09GA.A2024132.h12v12.061.version", "links": []},
                {"producer_granule_id": "MOD09GA.A2024132.h13v11.061.version", "links": []},
            ],
            3,
        ),
        FakeResponse("https://cmr.earthdata.nasa.gov/search/granules.json?page_num=2", [target], 3),
    ]
    requested_pages = []

    def fake_get(url, *, params, timeout):
        requested_pages.append(params["page_num"])
        return responses[params["page_num"] - 1]

    monkeypatch.setattr("tools.research.screen_mod09ga_vegetation.requests.get", fake_get)
    result = _query_granule(
        date="2024-05-11",
        bounds=[-51.24, -30.04, -51.23, -30.03],
        tile_id="h13v12",
    )

    assert requested_pages == [1, 2]
    assert result["cmr_reported_hits"] == result["cmr_returned_count"] == 3
    assert [page["page_num"] for page in result["query_pages"]] == [1, 2]
    assert [page["returned_count"] for page in result["query_pages"]] == [2, 1]
    assert result["query_url"] == "https://cmr.earthdata.nasa.gov/search/granules.json?page_num=1"
    assert result["granule_id"] == target_id
    assert result["data_url"].endswith(".hdf")
    _validate_mod09ga_cmr_query(result)

    corrupted = dict(result)
    corrupted["query_pages"] = [dict(page) for page in result["query_pages"]]
    corrupted["query_pages"][1]["response_sha256"] = "not-a-checksum"
    with pytest.raises(AssessmentError, match="CMR pagination evidence is malformed"):
        _validate_mod09ga_cmr_query(corrupted)
