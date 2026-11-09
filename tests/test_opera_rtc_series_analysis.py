"""Tests for same-grid, multi-acquisition OPERA RTC-S1 diagnostics."""

import json
from pathlib import Path

import numpy as np
import pytest

from echo.opera_rtc_access import OperaRtcS1Window
from echo.opera_rtc_analysis import (
    OperaRtcS1AnalysisError,
    build_opera_rtc_s1_series_analysis,
    validate_opera_rtc_s1_series_record,
)
from echo.opera_rtc_quality import (
    OperaRtcQualityReviewError,
    build_opera_rtc_quality_review,
)


def _window(timestamp, values, mask, *, scene_id=None, crs="EPSG:32722", network=False):
    timestamp_id = timestamp.replace("-", "").replace(":", "")
    timestamp_id = timestamp_id.replace("T", "T").replace("Z", "Z")
    timestamp_id = timestamp_id[:15] + "Z"
    scene_id = scene_id or (
        "OPERA_L2_RTC-S1_T024-050661-IW1_"
        f"{timestamp_id}_20250624T000000Z_S1A_30_v1.0"
    )
    return OperaRtcS1Window(
        scene_id=scene_id,
        polarization="VV",
        values=np.asarray(values, dtype=np.float32),
        mask=np.asarray(mask, dtype=np.uint8),
        selection_mask=np.ones((2, 2), dtype=bool),
        grid={
            "crs": crs,
            "transform": [30.0, 0.0, 500000.0, 0.0, -30.0, 6700000.0],
            "window": {"shape": [2, 2], "bounds_wgs84": [-51.2, -30.1, -51.1, -30.0]},
            "pixel_corners_wgs84": [],
        },
        source={
            "acquisition_start_utc": timestamp,
            "acquisition_stop_utc": timestamp,
            "provider_qa_disposition": "NO_CONSOLIDATED_PASS_FAIL_FIELD_IN_RETRIEVED_HDF5",
            "quality_metadata": {"status": "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"},
        },
        assets={"measurement": {"sha256": "a" * 64}, "mask": {"sha256": "b" * 64}},
        access={
            "network_retrieval": network,
            "authentication": "Earthdata Login via local netrc" if network else "NOT_AUTHENTICATED_TEST_INJECTION",
            "software": {"rasterio": "test"},
        },
    )


def _three_windows():
    masks = [
        np.zeros((2, 2), dtype=np.uint8),
        np.array([[0, 1], [0, 0]], dtype=np.uint8),
        np.array([[0, 0], [0, 255]], dtype=np.uint8),
    ]
    values = [
        [[1, 2], [3, 4]],
        [[2, 4], [6, 8]],
        [[4, 8], [12, 16]],
    ]
    dates = [
        "2024-05-11T08:49:44Z",
        "2024-06-04T08:49:43Z",
        "2025-06-23T08:49:37Z",
    ]
    return [_window(date, value, mask) for date, value, mask in zip(dates, values, masks, strict=True)]


def test_series_uses_one_all_date_support_and_records_adjacent_changes():
    record = build_opera_rtc_s1_series_analysis(_three_windows())

    assert record["status"] == "FIXTURE_DATA_COMPUTATION_NOT_SCIENTIFIC_RESULT"
    assert record["provider_qa"]["scientific_gate"] == "DIAGNOSTIC_ONLY; no provider PASS is asserted"
    assert record["grid"]["resampling"] == "NONE"
    assert record["common_support"]["aoi_pixel_count"] == 4
    assert record["common_support"]["clear_in_every_observation_count"] == 2
    assert record["common_support"]["finite_positive_in_every_observation_count"] == 2
    assert len(record["adjacent_intervals"]) == 2
    assert [item["measured_pixel_count"] for item in record["adjacent_intervals"]] == [2, 2]
    assert record["adjacent_intervals"][0]["summary_db"]["median"] == pytest.approx(10 * np.log10(2))
    baseline = record["reference_baseline"]["comparisons"][0]
    assert baseline["before_scene_id"] == record["observations"][0]["scene_id"]
    assert baseline["after_scene_id"] == record["observations"][2]["scene_id"]
    assert baseline["measured_pixel_count"] == 2
    assert baseline["summary_db"]["median"] == pytest.approx(10 * np.log10(4))
    assert record["processing"]["intervals_share_observations"] is True
    json.dumps(record, allow_nan=False)


@pytest.mark.parametrize(
    "windows, message",
    [
        (_three_windows()[:2], "at least three windows"),
        (list(reversed(_three_windows())), "strictly increasing acquisition order"),
    ],
)
def test_series_rejects_too_few_or_unsorted_inputs(windows, message):
    with pytest.raises(OperaRtcS1AnalysisError, match=message):
        build_opera_rtc_s1_series_analysis(windows)


def test_series_rejects_incompatible_product_or_grid_identity():
    windows = _three_windows()
    windows[2] = _window(
        "2025-06-23T08:49:37Z",
        [[4, 8], [12, 16]],
        np.zeros((2, 2), dtype=np.uint8),
        scene_id=(
            "OPERA_L2_RTC-S1_T024-050660-IW1_20250623T084937Z_"
            "20250624T000000Z_S1A_30_v1.0"
        ),
    )
    with pytest.raises(OperaRtcS1AnalysisError, match="burst values do not match"):
        build_opera_rtc_s1_series_analysis(windows)

    windows = _three_windows()
    windows[2].grid["crs"] = "EPSG:32723"
    with pytest.raises(OperaRtcS1AnalysisError, match="crs metadata do not match"):
        build_opera_rtc_s1_series_analysis(windows)


def test_series_keeps_empty_common_support_inconclusive():
    windows = _three_windows()
    for window in windows:
        window.mask[:] = 255

    record = build_opera_rtc_s1_series_analysis(windows)

    assert record["status"] == "FIXTURE_DATA_COMPUTATION_NOT_SCIENTIFIC_RESULT"
    assert record["common_support"]["finite_positive_in_every_observation_count"] == 0
    assert all(item["measured_pixel_count"] == 0 for item in record["adjacent_intervals"])


def test_retained_real_series_reproduces_and_links_to_original_pair():
    root = Path(__file__).parents[1]
    series = json.loads(
        (root / "data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json").read_text()
    )
    pair = json.loads(
        (root / "data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json").read_text()
    )

    summary = validate_opera_rtc_s1_series_record(series, pair_record=pair)

    assert summary["observation_count"] == 3
    assert summary["common_support_count"] == 1034
    assert summary["aoi_pixel_count"] == 1199
    assert summary["intervals"][0]["summary_db"]["median"] == pytest.approx(-1.4082954275)
    assert summary["intervals"][1]["summary_db"]["median"] == pytest.approx(0.1770550604)

    review = series["quality_review"] if "quality_review" in series else build_opera_rtc_quality_review(series)
    assert review["status"] == "REVIEW_RECORDED_WITH_UNRESOLVED_SCENE_QUALITY_LIMITS"
    assert review["provider_qa"]["scene_level_verdict"] == "NOT_PROVIDED"
    assert review["assessment_boundary"]["provider_qa_overridden"] is False
    assert review["assessment_boundary"]["rfi_residual_effect"] == "UNRESOLVED"
    assert review["echo_bounded_checks"]["common_finite_positive_count"] == 1034
    assert review["echo_bounded_checks"]["aoi_pixel_count"] == 1199
    assert [item["aoi_mask_counts"]["invalid"] for item in review["per_observation"]] == [148, 156, 165]
    assert [item["rfi_metadata"]["information_available"] for item in review["per_observation"]] == [True, True, True]
    assert [item["rfi_metadata"]["mitigation_performed"] for item in review["per_observation"]] == [
        "BasedOnNoiseMeas", "BasedOnNoiseMeas", "BasedOnNoiseMeas"
    ]

    mismatched_qa = json.loads(json.dumps(series))
    mismatched_qa["provider_qa"]["per_observation"][0]["status"] = "PASS"
    with pytest.raises(OperaRtcQualityReviewError, match="not linked to their exact observation"):
        build_opera_rtc_quality_review(mismatched_qa)

    reviewed = json.loads(json.dumps(series))
    reviewed["schema_version"] = 2
    reviewed["quality_review"] = build_opera_rtc_quality_review(reviewed)
    validate_opera_rtc_s1_series_record(reviewed, pair_record=pair)

    tampered_review = json.loads(json.dumps(reviewed))
    tampered_review["quality_review"]["per_observation"][0]["rfi_metadata"]["in_band_out_band_power_ratio"] = 0
    with pytest.raises(OperaRtcS1AnalysisError, match="quality review does not reproduce"):
        validate_opera_rtc_s1_series_record(tampered_review, pair_record=pair)

    altered = json.loads(json.dumps(series))
    altered["adjacent_intervals"][1]["values_db"][1][0] += 0.5
    with pytest.raises(OperaRtcS1AnalysisError, match="interval values do not reproduce"):
        validate_opera_rtc_s1_series_record(altered, pair_record=pair)

    altered = json.loads(json.dumps(series))
    altered["observations"][1], altered["observations"][2] = altered["observations"][2], altered["observations"][1]
    with pytest.raises(OperaRtcS1AnalysisError, match="does not begin with the pair's exact"):
        validate_opera_rtc_s1_series_record(altered, pair_record=pair)

