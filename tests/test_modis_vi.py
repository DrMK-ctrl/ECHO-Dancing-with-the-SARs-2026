from hashlib import sha256

import numpy as np
import pytest
from pathlib import Path

from echo.modis_vi import (
    ModisScreenError,
    build_mod13q1_candidate_screen,
    validate_mod13q1_candidate_screen,
)
from echo.web import _validate_assessment_record
from tools.research.build_cross_sensor_investigation import build_assessment


CASE_ID = "controlled-mod13q1-test"
PAIR = {
    "record_type": "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS",
    "source_products": {
        "before": {"scene_id": "S1-BEFORE", "acquisition_start_utc": "2024-05-08T12:00:00Z"},
        "after": {"scene_id": "S1-AFTER", "acquisition_start_utc": "2024-06-01T12:00:00Z"},
    },
    "grid": {"window": {"bounds_wgs84": [-51.24, -30.04, -51.23, -30.03]}},
}
SOURCE_GRANULES = [
    {
        "provider": "NASA LP DAAC",
        "collection_concept_id": "C1748066515-LPCLOUD",
        "granule_id": f"MOD13Q1.TEST.{index}",
        "period_start_date_utc": start,
        "period_end_date_utc": end,
        "tile_id": f"h13v{index}",
        "source_url": f"https://example.test/{index}.hdf",
        "sha256": f"{index:064x}",
    }
    for index, (start, end) in enumerate(
        [("2024-05-08", "2024-05-23"), ("2024-05-08", "2024-05-23"), ("2024-05-24", "2024-06-08"), ("2024-05-24", "2024-06-08")],
        start=1,
    )
]


def _arrays(*, summary=0, land=1, doy=129):
    detailed = np.full((2, 2), (land << 11), dtype=np.uint16)
    detailed[0, 1] |= 1  # MODLAND quality class is marginal for this pixel.
    return {
        "ndvi": np.full((2, 2), 4500, dtype=np.int16),
        "detailed_qa": detailed,
        "summary_qa": np.full((2, 2), summary, dtype=np.int8),
        "composite_doy": np.full((2, 2), doy, dtype=np.int16),
        "aoi_center_mask": np.ones((2, 2), dtype=bool),
    }


def _record(before=None, after=None):
    pair_bytes = b"controlled pair record"
    return build_mod13q1_candidate_screen(
        pair_record=PAIR,
        case_id=CASE_ID,
        pair_record_sha256=sha256(pair_bytes).hexdigest(),
        source_pair_record_path="controlled-pair.json",
        before_arrays=before or _arrays(doy=129),
        after_arrays=after or _arrays(doy=153),
        grid={"crs": "EPSG: sinusoidal", "transform": [250, 0, 0, 0, -250, 0], "shape": [2, 2]},
        source_granules=SOURCE_GRANULES,
        qa_policy_reference="NASA MOD13Q1 user guide",
        processed_at_utc="2024-06-10T00:00:00Z",
    )


def test_mod13q1_screen_keeps_good_common_land_support_and_actual_composite_dates():
    record = _record()

    assert record["observations"]["common_strictly_accepted_pixel_count"] == 3
    assert record["observations"]["paired_timing_suitable_for_sar_date_comparison"] is True
    assert record["observations"]["before"]["composite_observation_dates"] == ["2024-05-08"]
    assert record["observations"]["after"]["composite_observation_dates"] == ["2024-06-01"]
    assert record["method"]["no_sar_association_computed"] is True
    validate_mod13q1_candidate_screen(
        record,
        pair_record=PAIR,
        pair_record_sha256=sha256(b"controlled pair record").hexdigest(),
        case_id=CASE_ID,
    )


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (_arrays(summary=1), _arrays()),
        (_arrays(land=2), _arrays()),
        (_arrays(), _arrays(land=2)),
    ],
)
def test_mod13q1_marginal_or_nonland_support_is_not_promoted(before, after):
    record = _record(before, after)

    assert record["observations"]["common_strictly_accepted_pixel_count"] == 0
    assert record["observations"]["strict_common_support_suitable_for_test"] is False


def test_mod13q1_validator_rejects_changed_sar_source_and_tampered_counts():
    record = _record()
    with pytest.raises(ModisScreenError, match="identity or linked SAR source"):
        validate_mod13q1_candidate_screen(
            record,
            pair_record=PAIR,
            pair_record_sha256="0" * 64,
            case_id=CASE_ID,
        )

    record["observations"]["after"]["strict_accepted_count"] += 1
    with pytest.raises(ModisScreenError, match="counts do not reproduce"):
        validate_mod13q1_candidate_screen(
            record,
            pair_record=PAIR,
            pair_record_sha256=sha256(b"controlled pair record").hexdigest(),
            case_id=CASE_ID,
        )


def test_mod13q1_screen_rejects_missing_or_misaligned_layers():
    before = _arrays()
    del before["summary_qa"]
    with pytest.raises(ModisScreenError, match="five declared native-grid arrays"):
        _record(before, _arrays())

    after = _arrays()
    after["ndvi"] = np.ones((1, 4), dtype=np.int16)
    with pytest.raises(ModisScreenError, match="share one two-dimensional native grid"):
        _record(_arrays(), after)


def test_real_t163_modis_screen_enters_h4_as_quality_limited_evidence():
    root = Path(__file__).parents[1]
    record_path = Path("data/research/mod13q1-vegetation-candidate-T163-349925-2026-11-08.json")
    pair_path = Path("data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json")
    assessment = build_assessment(
        pair_path,
        Path("data/research/dswx-hls-context-T163-349925-2026-11-07.json"),
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        hls_vegetation_path=Path("data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json"),
        hls_association_path=Path("data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json"),
        hls_s30_vegetation_path=Path("data/research/hls-s30-vegetation-screen-T163-349925-2026-11-08.json"),
        hls_s30_association_path=Path("data/research/hls-s30-rtc-ndvi-association-T163-349925-2026-11-08.json"),
        mod13q1_screen_path=record_path,
    )
    _validate_assessment_record(assessment, root)
    h4 = next(item for item in assessment["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
    f9 = next(item for item in assessment["follow_up_evidence"] if item["follow_up_id"] == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION")

    assert h4["state"] == "UNRESOLVED"
    assert h4["evidence_assessments"][-1]["relationship"] == "LIMITS_INTERPRETATION"
    assert f9["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert f9["evidence_refs"] == ["NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN"]
    artifact = next(item for item in assessment["evidence_artifacts"] if item["evidence_id"] == "NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN")
    assert artifact["lineage"]["derived_from_evidence_ids"] == ["SAR-RTC-S1-PAIR"]
    assert assessment["observations"]["mod13q1_vegetation_candidate_screen"]["common_strictly_accepted_pixel_count"] == 0
