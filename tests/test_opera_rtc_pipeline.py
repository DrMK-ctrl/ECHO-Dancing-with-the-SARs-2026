import pytest

from echo.opera_rtc_pipeline import (
    OperaRtcS1PipelineError,
    build_opera_rtc_s1_pair_record,
)


def _feature(scene_id):
    return {
        "properties": {
            "fileID": scene_id,
            "url": f"https://datapool.asf.alaska.edu/RTC/OPERA-S1/{scene_id}_VV.tif",
            "startTime": "2024-05-08T10:00:00Z",
            "bytes": {"asset.tif": {"bytes": 10, "format": "GeoTIFF"}},
        }
    }


def test_pair_orchestration_reads_both_sources_with_same_aoi(monkeypatch):
    before = _feature(
        "OPERA_L2_RTC-S1_T163-349924-IW2_20240508T100000Z_"
        "20240509T100000Z_S1A_30_v1.0"
    )
    after = _feature(
        "OPERA_L2_RTC-S1_T163-349924-IW2_20240601T100000Z_"
        "20240602T100000Z_S1A_30_v1.0"
    )
    bounds = [-51.25, -30.08, -51.24, -30.07]
    calls = []
    windows = {before["properties"]["fileID"]: object(), after["properties"]["fileID"]: object()}

    def reader(feature, *, bounds_wgs84, polarization):
        calls.append((feature, bounds_wgs84, polarization))
        return windows[feature["properties"]["fileID"]]

    expected = {"status": "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"}
    monkeypatch.setattr(
        "echo.opera_rtc_pipeline.build_opera_rtc_s1_pair_analysis",
        lambda *_args: expected,
    )
    record = build_opera_rtc_s1_pair_record(
        before,
        after,
        bounds_wgs84=bounds,
        polarization="VV",
        window_reader=reader,
    )

    assert record == expected
    assert len(calls) == 2
    assert all(call[1] == bounds and call[2] == "VV" for call in calls)


def test_pair_orchestration_rejects_duplicate_scene_before_any_read():
    scene = "OPERA_L2_RTC-S1_T163-349924-IW2_20240508T100000Z_20240509T100000Z_S1A_30_v1.0"
    feature = _feature(scene)
    called = False

    def reader(*_args, **_kwargs):
        nonlocal called
        called = True

    with pytest.raises(OperaRtcS1PipelineError, match="must be different"):
        build_opera_rtc_s1_pair_record(
            feature,
            feature,
            bounds_wgs84=[-51.25, -30.08, -51.24, -30.07],
            polarization="VV",
            window_reader=reader,
        )
    assert called is False
