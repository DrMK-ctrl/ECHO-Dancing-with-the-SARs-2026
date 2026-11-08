from datetime import date, timedelta

import pytest

from tools.research.screen_smap_radiometer_candidate import ScreenError, build_screen_record


def _payloads():
    collection = {
        "feed": {
            "entry": [{
                "id": "C2938664763-NSIDC_CPRD",
                "short_name": "SPL3SMP_E",
                "version_id": "006",
                "title": "SMAP Enhanced L3 Radiometer Global Daily 9 km Soil Moisture V006",
            }]
        }
    }
    granules = []
    for offset in range(28):
        day = date(2024, 5, 7) + timedelta(days=offset)
        day_text = day.strftime("%Y%m%d")
        granules.append({
            "id": f"G-{day_text}",
            "title": f"SMAP_L3_SM_P_E_{day_text}_R19240_001.h5",
            "time_start": f"{day.isoformat()}T00:00:00.000Z",
            "time_end": f"{day.isoformat()}T23:59:59.999Z",
            "updated": "2026-11-08T00:00:00Z",
            "links": [{
                "rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
                "href": f"https://data.nsidc.earthdatacloud.nasa.gov/nsidc-cumulus-prod-protected/SMAP/SPL3SMP_E/006/2024/05/{day.day:02d}/SMAP_L3_SM_P_E_{day_text}_R19240_001.h5",
            }],
        })
    return collection, {"feed": {"entry": granules}}


def test_radiometer_screen_records_complete_catalog_timing_and_spatial_rejection():
    collection, granules = _payloads()
    record = build_screen_record(
        collection_payload=collection,
        collection_sha256="a" * 64,
        granule_payload=granules,
        granule_sha256="b" * 64,
        cmr_hits=28,
        query_url="https://cmr.earthdata.nasa.gov/search/granules.json",
        bounds_wgs84=(-51.24, -30.04, -51.23, -30.03),
        start_date=date(2024, 5, 7),
        end_date=date(2024, 6, 3),
        case_id="case",
    )

    suitability = record["spatial_suitability"]
    assert record["status"] == "SCREENED_SPATIALLY_TOO_COARSE_FOR_AOI_SCALE_TEST"
    assert record["source"]["instrument"] == "L-band radiometer"
    assert record["query"]["cmr_result_count"] == 28
    assert [item["date_utc"] for item in record["selected_daily_granules"]] == ["2024-05-08", "2024-06-01"]
    assert suitability["aoi_width_km_approx"] == pytest.approx(0.963, abs=0.002)
    assert suitability["radiometer_native_footprint_km_approx"] == 36
    assert record["retrieval"]["data_files_downloaded"] is False


def test_radiometer_screen_rejects_incomplete_cmr_pages_and_wrong_collection():
    collection, granules = _payloads()
    args = {
        "collection_payload": collection,
        "collection_sha256": "a" * 64,
        "granule_payload": granules,
        "granule_sha256": "b" * 64,
        "cmr_hits": 29,
        "query_url": "https://cmr.earthdata.nasa.gov/search/granules.json",
        "bounds_wgs84": (-51.24, -30.04, -51.23, -30.03),
        "start_date": date(2024, 5, 7),
        "end_date": date(2024, 6, 3),
        "case_id": "case",
    }
    with pytest.raises(ScreenError, match="pagination incomplete"):
        build_screen_record(**args)

    collection["feed"]["entry"][0]["short_name"] = "SPL2SMAP_S"
    args["cmr_hits"] = 28
    with pytest.raises(ScreenError, match="collection identity"):
        build_screen_record(**args)
