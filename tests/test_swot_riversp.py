import copy
import hashlib
import json
from pathlib import Path

import pytest

from echo.swot_riversp import SwotRiverSpError, validate_screen


ROOT = Path(__file__).resolve().parents[1]
PAIR_PATH = ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
SCREEN_PATH = ROOT / "data/research/swot-riversp-screen-T163-349925-2026-11-09.json"
CASE_ID = "rio-grande-do-sul-t163-349925-diagnostic-2024"


@pytest.fixture
def linked_records():
    pair_bytes = PAIR_PATH.read_bytes()
    return (
        json.loads(pair_bytes),
        json.loads(SCREEN_PATH.read_text(encoding="utf-8")),
        hashlib.sha256(pair_bytes).hexdigest(),
    )


def test_retained_swot_screen_matches_pair_provenance_and_quality_summary(linked_records):
    pair, screen, pair_hash = linked_records

    summary = validate_screen(
        screen,
        pair_record=pair,
        case_id=CASE_ID,
        pair_record_sha256=pair_hash,
    )

    assert summary == {
        "granule_count": 9,
        "retrieved_bytes": 95_491_802,
        "good_quality_wse_count": 0,
        "nearest_reach_m": 5004.322,
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda record: record["case_observations"].update(source_pair_record_sha256="0" * 64), "acquisition times"),
        (lambda record: record["case_observations"].update(case_window_bbox_wgs84=[-51, -30, -50, -29]), "spatial window"),
        (lambda record: record["retrieved_granules"][0].update(download_sha256="not-a-checksum"), "source identity"),
        (lambda record: record["result"].update(good_quality_reaches_q0_with_valid_wse=1), "good-quality WSE count"),
    ],
)
def test_swot_screen_rejects_broken_provenance_or_quality_link(linked_records, mutate, message):
    pair, screen, pair_hash = linked_records
    changed = copy.deepcopy(screen)
    mutate(changed)

    with pytest.raises(SwotRiverSpError, match=message):
        validate_screen(
            changed,
            pair_record=pair,
            case_id=CASE_ID,
            pair_record_sha256=pair_hash,
        )
