import json
from pathlib import Path

import pytest

from tools.research.evaluate_rtc_hls_ndvi_association import (
    AssociationError,
    evaluate_association,
)


_ROOT = Path(__file__).parents[1]
_SAR_PATH = _ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
_HLS_PATH = _ROOT / "data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json"


def _records():
    sar_payload = _SAR_PATH.read_bytes()
    hls_payload = _HLS_PATH.read_bytes()
    return json.loads(sar_payload), json.loads(hls_payload), sar_payload, hls_payload


def test_retained_hls_and_sar_inputs_reproduce_descriptive_association():
    sar, hls, sar_payload, hls_payload = _records()

    result = evaluate_association(sar, hls, sar_payload, hls_payload)

    assert result["status"] == "DIAGNOSTIC_SPATIAL_ASSOCIATION"
    assert [item["sar_cells"] for item in result["coverage_sensitivity"]] == [312, 265, 218]
    assert result["coverage_sensitivity"][2]["descriptive_pearson_r_ndvi_change_vs_sar_log_ratio_db"] == pytest.approx(-0.2904524)
    assert result["sources"]["optical_minus_sar_offsets_hours"] == pytest.approx([-8.821965, -8.8205617])
    assert "NOT_COMPUTED" in result["coverage_sensitivity"][2]["inferential_statistics"]


def test_association_rejects_changed_bounded_hls_asset_hash():
    sar, hls, sar_payload, hls_payload = _records()
    hls["observations"][0]["asset"]["sha256"] = "0" * 64

    with pytest.raises(AssociationError, match="checksum or size"):
        evaluate_association(sar, hls, sar_payload, hls_payload)


def test_association_rejects_sar_provider_qa_relabeling():
    sar, hls, sar_payload, hls_payload = _records()
    sar["provider_qa"]["status"] = "PASS"

    with pytest.raises(AssociationError, match="provider QA state"):
        evaluate_association(sar, hls, sar_payload, hls_payload)
