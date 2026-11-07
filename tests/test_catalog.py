from datetime import datetime, timedelta, timezone

import pytest

from echo.catalog import CatalogQuery, CatalogQueryError, build_catalog_record, pair_gcov_scenes


def _feature(name: str, date: str, *, collection="NISAR_L2_GCOV_BETA_V1", crid="X05010"):
    start_time = datetime.fromisoformat(date.replace("Z", "+00:00"))
    orbit = start_time.date().toordinal()
    stop_time = (start_time + timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[33, -25], [34, -25], [34, -24], [33, -24], [33, -25]]],
        },
        "properties": {
            "fileID": name,
            "startTime": date,
            "stopTime": stop_time,
            "collectionName": collection,
            "processingLevel": "GCOV",
            "pathNumber": 114,
            "frameNumber": 165,
            "flightDirection": "ASCENDING",
            "rangeBandwidth": ["40+5"],
            "mainBandPolarization": ["HH", "HV"],
            "productionConfiguration": "PR",
            "crid": crid,
            "orbit": orbit,
            "sideBandPolarization": ["HH", "HV"],
            "frameCoverage": "Partial",
        },
    }


def test_pairs_adjacent_scenes_when_product_metadata_matches():
    features = [
        _feature("after", "2026-01-17T03:42:32Z"),
        _feature("before", "2026-01-05T03:42:32Z"),
    ]

    pairs = pair_gcov_scenes(features)

    assert len(pairs) == 1
    assert pairs[0]["before_scene"] == "before"
    assert pairs[0]["after_scene"] == "after"
    assert pairs[0]["interval_days"] == 12.0
    assert pairs[0]["maturity"] == "BETA"
    assert pairs[0]["before_orbit"] != pairs[0]["after_orbit"]
    assert pairs[0]["status"] == "METADATA_MATCH_ONLY"
    assert "verify spatial grid alignment and valid-pixel overlap" in pairs[0]["required_before_analysis"]


@pytest.mark.parametrize(
    "changed",
    [
        {"collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1"},
        {"crid": "X05011"},
        {"pathNumber": 115},
        {"productionConfiguration": "UR"},
    ],
)
def test_does_not_pair_scenes_across_product_or_acquisition_changes(changed):
    before = _feature("before", "2026-01-05T03:42:32Z")
    after = _feature("after", "2026-01-17T03:42:32Z")
    after["properties"].update(changed)

    assert pair_gcov_scenes([before, after]) == []


def test_does_not_pair_non_overlapping_footprints():
    before = _feature("before", "2026-01-05T03:42:32Z")
    after = _feature("after", "2026-01-17T03:42:32Z")
    after["geometry"]["coordinates"] = [[[40, -25], [41, -25], [41, -24], [40, -24], [40, -25]]]

    assert pair_gcov_scenes([before, after]) == []


def test_does_not_pair_neighboring_granules_from_the_same_orbit():
    before = _feature("before", "2026-10-21T03:42:32Z")
    after = _feature("after", "2026-10-21T03:43:10Z")
    after["properties"]["orbit"] = before["properties"]["orbit"]

    assert pair_gcov_scenes([before, after]) == []


def test_does_not_pair_overlapping_acquisition_intervals():
    before = _feature("before", "2026-10-21T03:42:32Z")
    after = _feature("after", "2026-10-21T03:42:38Z")
    after["properties"]["orbit"] += 1

    assert pair_gcov_scenes([before, after]) == []


def test_pairing_requires_orbit_and_stop_time_metadata():
    before = _feature("before", "2026-10-09T03:42:32Z")
    after = _feature("after", "2026-10-21T03:42:32Z")
    del after["properties"]["orbit"]
    assert pair_gcov_scenes([before, after]) == []

    after = _feature("after", "2026-10-21T03:42:32Z")
    del after["properties"]["stopTime"]
    assert pair_gcov_scenes([before, after]) == []


def test_validated_collection_is_identified_and_pairable():
    features = [
        _feature(
            "before",
            "2026-10-09T03:42:32Z",
            collection="NISAR_L2_GCOV_V1",
            crid="P05036",
        ),
        _feature(
            "after",
            "2026-10-21T03:42:32Z",
            collection="NISAR_L2_GCOV_V1",
            crid="P05036",
        ),
    ]

    pairs = pair_gcov_scenes(features)

    assert len(pairs) == 1
    assert pairs[0]["maturity"] == "VALIDATED"


def test_query_rejects_invalid_coordinate_or_time_order():
    with pytest.raises(CatalogQueryError):
        CatalogQuery(181, -24.5, "2026-01-01", "2026-01-31").validate()
    with pytest.raises(CatalogQueryError):
        CatalogQuery(33.5, -24.5, "2026-02-01", "2026-01-01").validate()


def test_catalog_query_accepts_validated_maturity():
    CatalogQuery(
        33.5, -24.5, "2026-10-01", "2026-10-31", maturity="VALIDATED"
    ).validate()


def test_catalog_record_labels_search_as_metadata_only():
    query = CatalogQuery(33.5, -24.5, "2026-01-01", "2026-01-31", maturity="BETA")

    record = build_catalog_record(
        query,
        [_feature("sample", "2026-01-05T03:42:32Z")],
        queried_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["source"]["pixels_downloaded"] is False
    assert record["query"]["data_maturity"] == "BETA"
    assert "does not establish" in record["interpretation_limit"]
