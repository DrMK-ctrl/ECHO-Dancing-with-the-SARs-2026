import json
from pathlib import Path

import pytest

from tools.research.build_gpm_interacquisition_context import (
    InteracquisitionContextError,
    build_interacquisition_context,
)


_ROOT = Path(__file__).parents[1]


def _source(path):
    payload = path.read_bytes()
    return json.loads(payload), payload


def _build():
    sar, sar_bytes = _source(_ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json")
    interval, interval_bytes = _source(_ROOT / "data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json")
    trailing, trailing_bytes = _source(_ROOT / "data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json")
    return build_interacquisition_context(
        sar_record=sar,
        sar_payload=sar_bytes,
        interval_record=interval,
        interval_payload=interval_bytes,
        after_context_record=trailing,
        after_context_payload=trailing_bytes,
        case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
        project_root=_ROOT,
    )


def test_gpm_daily_context_covers_full_utc_days_between_sar_acquisitions():
    record = _build()

    assert record["status"] == "COMPLETE_REGIONAL_DAILY_CONTEXT_NOT_CAUSAL_EVIDENCE"
    assert record["sar_interval"]["first_full_day_after_before_sar"] == "2024-05-09"
    assert record["sar_interval"]["last_full_day_before_after_sar"] == "2024-05-31"
    assert record["summary"]["days_requested"] == record["summary"]["days_with_complete_nearest_cell_samples"] == 23
    assert record["summary"]["nearest_cell_cumulative_precipitation_mm"] == pytest.approx(214.93)
    assert record["summary"]["maximum_daily_precipitation_date_utc"] == "2024-05-23"
    assert "do not measure AOI soil moisture" in record["summary"]["interpretation_limit"]


def test_gpm_daily_context_rejects_a_missing_day():
    sar, sar_bytes = _source(_ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json")
    interval, interval_bytes = _source(_ROOT / "data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json")
    trailing, trailing_bytes = _source(_ROOT / "data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json")
    interval["daily_observations"].pop(4)

    with pytest.raises(InteracquisitionContextError, match="every full UTC day"):
        build_interacquisition_context(
            sar_record=sar,
            sar_payload=sar_bytes,
            interval_record=interval,
            interval_payload=interval_bytes,
            after_context_record=trailing,
            after_context_payload=trailing_bytes,
            case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
            project_root=_ROOT,
        )


def test_gpm_daily_context_rejects_incomplete_daily_sample_counts():
    sar, sar_bytes = _source(_ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json")
    interval, interval_bytes = _source(_ROOT / "data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json")
    trailing, trailing_bytes = _source(_ROOT / "data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json")
    interval["daily_observations"][0]["aoi_nearest_cell"]["valid_half_hourly_samples"] = 47

    with pytest.raises(InteracquisitionContextError, match="incomplete"):
        build_interacquisition_context(
            sar_record=sar,
            sar_payload=sar_bytes,
            interval_record=interval,
            interval_payload=interval_bytes,
            after_context_record=trailing,
            after_context_payload=trailing_bytes,
            case_id="rio-grande-do-sul-t163-349925-diagnostic-2024",
            project_root=_ROOT,
        )
