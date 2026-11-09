from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from echo.investigation_draft import InvestigationDraftError, _source_role
from echo.opera_rtc_quality import (
    OperaRtcQualityReviewError,
    build_opera_rtc_pair_quality_review,
)
from tools.research.build_opera_rtc_pair_quality_review import build_record, refresh_linked_hashes


PAIR_PATH = (
    Path(__file__).resolve().parents[1]
    / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
)


def _pair() -> dict:
    return json.loads(PAIR_PATH.read_text(encoding="utf-8"))


def test_pair_review_binds_real_t163_inputs_and_keeps_scene_qa_unresolved():
    record = _pair()
    review = build_opera_rtc_pair_quality_review(record)

    assert review["scope"] == "TWO_ACQUISITION_PAIR"
    assert review["provider_qa"]["scene_level_verdict"] == "NOT_PROVIDED"
    assert review["echo_bounded_checks"]["common_clear_support_count"] == 1199
    assert review["echo_bounded_checks"]["common_finite_positive_count"] == 1199
    assert review["assessment_boundary"]["rfi_residual_effect"] == "UNRESOLVED"
    assert review["assessment_boundary"]["physical_cause_supported"] is False
    assert [item["rfi_metadata"]["mitigation_performed"] for item in review["per_observation"]] == [
        "BasedOnNoiseMeas",
        "BasedOnNoiseMeas",
    ]
    assert build_opera_rtc_pair_quality_review(record) == review


def test_pair_review_reproduction_tool_rebuilds_the_retained_record():
    record = build_record(PAIR_PATH)

    assert record["schema_version"] == 2
    assert record["quality_review"] == build_opera_rtc_pair_quality_review(record)


def test_pair_review_basis_changes_when_a_retained_input_changes():
    record = _pair()
    original = build_opera_rtc_pair_quality_review(record)
    changed = deepcopy(record)
    changed["source_products"]["before"]["access"]["read_at_utc"] = "2026-11-09T00:00:00Z"

    assert build_opera_rtc_pair_quality_review(changed)["review_basis_sha256"] != original["review_basis_sha256"]


def test_pair_review_rejects_false_provider_qa_and_inconsistent_support():
    record = _pair()
    false_qa = deepcopy(record)
    false_qa["provider_qa"]["status"] = "PASS"
    with pytest.raises(OperaRtcQualityReviewError, match="source, QA, grid, or measurement"):
        build_opera_rtc_pair_quality_review(false_qa)

    inconsistent = deepcopy(record)
    inconsistent["measurement"]["common_clear_pixel_count"] = 1200
    with pytest.raises(OperaRtcQualityReviewError, match="support counts are invalid"):
        build_opera_rtc_pair_quality_review(inconsistent)

    wrong_timestamp = deepcopy(record)
    wrong_timestamp["source_products"]["after"]["acquisition_start_utc"] = "2024-06-02T22:07:19Z"
    with pytest.raises(OperaRtcQualityReviewError, match="scene identifier and acquisition metadata disagree"):
        build_opera_rtc_pair_quality_review(wrong_timestamp)

    changed_value = deepcopy(record)
    changed_value["measurement"]["values_db"][0][0] += 1
    with pytest.raises(OperaRtcQualityReviewError, match="derived measurement arrays do not match"):
        build_opera_rtc_pair_quality_review(changed_value)


def test_investigation_source_role_reproduces_pair_quality_review():
    record = _pair()
    record["schema_version"] = 2
    record["quality_review"] = build_opera_rtc_pair_quality_review(record)

    assert _source_role(record) == "DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_MEASUREMENT"
    tampered = deepcopy(record)
    tampered["quality_review"]["per_observation"][0]["rfi_metadata"]["in_band_out_band_power_ratio"] = 0
    with pytest.raises(InvestigationDraftError, match="quality review does not match its retained inputs"):
        _source_role(tampered)


def test_pair_hash_refresh_propagates_through_linked_record_digests(tmp_path):
    old_pair_hash = "a" * 64
    new_pair_hash = "b" * 64
    middle = {"source_pair_sha256": old_pair_hash}
    middle_path = tmp_path / "middle.json"
    middle_path.write_text(json.dumps(middle, indent=2) + "\n", encoding="utf-8")
    from hashlib import sha256

    old_middle_hash = sha256(middle_path.read_bytes()).hexdigest()
    assessment_path = tmp_path / "assessment.json"
    assessment_path.write_text(
        json.dumps({"pair_sha256": old_pair_hash, "middle_sha256": old_middle_hash}, indent=2) + "\n",
        encoding="utf-8",
    )

    assert refresh_linked_hashes(tmp_path, old_pair_hash, new_pair_hash) == 2
    refreshed_middle = json.loads(middle_path.read_text(encoding="utf-8"))
    refreshed_assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
    assert refreshed_middle["source_pair_sha256"] == new_pair_hash
    assert refreshed_assessment["pair_sha256"] == new_pair_hash
    assert refreshed_assessment["middle_sha256"] == sha256(middle_path.read_bytes()).hexdigest()
