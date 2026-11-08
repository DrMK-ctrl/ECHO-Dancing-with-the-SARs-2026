import json
from hashlib import sha256
from pathlib import Path

import pytest

from echo.opera_rtc_conditions import (
    AcquisitionConditionError,
    build_acquisition_condition_review,
    validate_acquisition_condition_review,
)
from echo.web import _validate_assessment_record
from tools.research.build_cross_sensor_investigation import build_assessment


_ROOT = Path(__file__).parents[1]
_PAIR_PATH = _ROOT / "data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json"
_OPTICAL_PATH = _ROOT / "data/research/dswx-hls-context-T163-349925-2026-11-07.json"
_CASE_ID = "rio-grande-do-sul-t163-349925-diagnostic-2024"


def _review(pair_path=_PAIR_PATH):
    payload = pair_path.read_bytes()
    pair = json.loads(payload)
    return build_acquisition_condition_review(
        pair,
        case_id=_CASE_ID,
        source_record_path=str(pair_path.relative_to(_ROOT)),
        source_record_sha256=sha256(payload).hexdigest(),
    )


def test_t163_metadata_review_retains_matches_and_nondiscriminating_rfi_difference():
    record = _review()
    summary = record["summary"]

    assert record["status"] == "DESCRIPTIVE_METADATA_REVIEW_NOT_CAUSAL_OR_QA_CLEARANCE"
    assert summary["platform_configuration_matches"] is True
    assert summary["documented_product_configuration_matches"] is True
    assert summary["documented_processing_configuration_matches"] is True
    assert summary["reported_geometric_accuracy_metadata_match"] is True
    assert summary["rfi_burst_metadata_comparison"] == "DIFFERS"
    assert summary["rfi_power_ratio_before"] == pytest.approx(13.3508)
    assert summary["rfi_power_ratio_after"] == pytest.approx(12.31653)
    assert summary["incidence_angle_metadata_available"] is False
    assert summary["spatially_matched_rfi_evidence_available"] is False
    assert summary["causal_disposition"] == "UNRESOLVED"
    assert summary["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert len(record["source"]["hdf5_sidecar_sha256"]) == 2


def test_metadata_review_refuses_missing_required_fields_and_mismatched_source():
    payload = _PAIR_PATH.read_bytes()
    pair = json.loads(payload)
    del pair["source_products"]["before"]["catalog_metadata"]["beamModeType"]
    with pytest.raises(AcquisitionConditionError, match="required paired metadata are missing"):
        build_acquisition_condition_review(
            pair,
            case_id=_CASE_ID,
            source_record_path="pair.json",
            source_record_sha256=sha256(payload).hexdigest(),
        )

    record = _review()
    pair = json.loads(_PAIR_PATH.read_text())
    with pytest.raises(AcquisitionConditionError, match="identity, source, or limits"):
        validate_acquisition_condition_review(
            record,
            pair_record=pair,
            pair_record_sha256="0" * 64,
            case_id=_CASE_ID,
        )


def test_acquisition_metadata_review_enters_t163_as_limited_h5_evidence(tmp_path):
    review = _review()
    review_path = tmp_path / "acquisition-conditions.json"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    result = build_assessment(
        _PAIR_PATH,
        _OPTICAL_PATH,
        case_id=_CASE_ID,
        acquisition_conditions_path=review_path,
    )
    h5 = next(item for item in result["hypotheses"] if item["id"] == "H5_ACQUISITION_CONDITIONS_EFFECT")
    evidence = {item["evidence_id"]: item for item in result["evidence_artifacts"]}
    followup = next(item for item in result["follow_up_evidence"] if item["follow_up_id"] == "F10_ACQUISITION_CONDITION_REVIEW")

    assert h5["state"] == "UNRESOLVED"
    assert h5["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
    assert h5["evidence_assessments"][0]["relationship"] == "DOES_NOT_DISTINGUISH"
    assert evidence["NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW"]["lineage"]["derived_from_evidence_ids"] == ["SAR-RTC-S1-PAIR"]
    assert followup["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
    assert followup["evidence_refs"] == ["NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW"]


def test_retained_t024_and_t163_assessments_validate_metadata_lineage():
    for name in (
        "data/research/opera-rtc-cross-sensor-investigation-2026-11-07.json",
        "data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-08.json",
    ):
        assessment = json.loads((_ROOT / name).read_text())
        _validate_assessment_record(assessment, _ROOT)
        h5 = next(item for item in assessment["hypotheses"] if item["id"] == "H5_ACQUISITION_CONDITIONS_EFFECT")
        assert h5["state"] == "UNRESOLVED"
        assert h5["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
        assert h5["evidence_refs"] == ["NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW"]


def test_metadata_review_rejects_a_different_pair_record(tmp_path):
    review = _review()
    review_path = tmp_path / "acquisition-conditions.json"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    changed_pair = json.loads(_PAIR_PATH.read_text())
    changed_pair["source_products"]["after"]["scene_id"] = "OTHER-SCENE"
    changed_path = tmp_path / "pair.json"
    changed_path.write_text(json.dumps(changed_pair), encoding="utf-8")

    with pytest.raises(ValueError, match="not linked to this SAR pair"):
        build_assessment(
            changed_path,
            _OPTICAL_PATH,
            case_id=_CASE_ID,
            acquisition_conditions_path=review_path,
        )
