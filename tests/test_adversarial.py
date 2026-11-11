import json
from hashlib import sha256
from pathlib import Path

import pytest

from echo.adversarial import (
    build_adversarial_challenge,
    build_qa_held_observation_challenge,
)


ROOT = Path(__file__).resolve().parents[1]


def _t163_assessment():
    case = json.loads((ROOT / "data/cases/rio-grande-do-sul-t163-349925-2024/investigation.json").read_text())
    return json.loads((ROOT / case["evidence_records"]["cross_sensor_assessment"]).read_text())


def test_t163_challenge_view_keeps_diagnostic_qa_and_surfaces_existing_alternatives():
    assessment = _t163_assessment()
    report = build_adversarial_challenge(
        assessment,
        hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        assessment_sha256="a" * 64,
        evidence_root=ROOT,
    )

    assert report["status"] == "REVIEWABLE_WITH_RECORDED_LIMITS"
    assert report["observation"]["qa_gate"] == "PROVIDER_QA_UNRESOLVED"
    assert report["observation"]["measurement"]["scene_ids"] == assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"]
    assert report["hypothesis"]["recorded_state"] == "UNRESOLVED"
    assert any(item["hypothesis_id"] == "H3_SOIL_MOISTURE_CHANGE" for item in report["alternatives"])
    assert "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY" in {
        item["evidence_id"] for item in report["sensitivity_review"]["linked_sources"]
    }
    reproduction = report["observation"]["measurement_reproduction"]
    assert reproduction["status"] == "LINKED_MEAN_MEDIAN_AND_MASK_REPRODUCED"
    assert reproduction["valid_sample_count"] == report["observation"]["measurement"]["common_clear_pixel_count"]
    assert reproduction["median_db"] == pytest.approx(report["observation"]["measurement"]["median_db"])
    assert report["next_observations"]
    assert "probability" in report["sensitivity_review"]["interpretation_limit"]


def test_t163_challenge_includes_reproducible_case_wide_comparability_without_promoting_it():
    assessment = _t163_assessment()
    report = build_adversarial_challenge(
        assessment,
        hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
        assessment_sha256="a" * 64,
        evidence_root=ROOT,
    )

    review = report["comparability_review"]
    assert review["state"] == "DESCRIPTIVE_METADATA_REVIEW_NOT_CAUSAL_OR_QA_CLEARANCE"
    assert review["scope"] == "CASE_WIDE_NOT_LINKED_TO_SELECTED_HYPOTHESIS"
    assert review["summary"]["causal_disposition"] == "UNRESOLVED"
    assert review["summary"]["hypothesis_relation"] == "DOES_NOT_DISTINGUISH"
    assert review["summary"]["incidence_angle_metadata_available"] is False
    assert review["summary"]["spatially_matched_rfi_evidence_available"] is False
    assert report["observation"]["qa_gate"] == "PROVIDER_QA_UNRESOLVED"
    assert "rfi_burst_report" in {item["field"] for item in review["comparisons"]}


def test_t163_challenge_rejects_tampered_acquisition_comparability_source_checksum():
    assessment = _t163_assessment()
    artifact = next(
        item for item in assessment["evidence_artifacts"]
        if item["evidence_id"] == "NASA-OPERA-RTC-S1-ACQUISITION-CONDITIONS-REVIEW"
    )
    artifact["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="acquisition-condition review checksum"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="a" * 64,
            evidence_root=ROOT,
        )


def test_challenge_view_reports_referenced_but_unassessed_sources_as_gaps():
    assessment = _t163_assessment()
    hypothesis = next(item for item in assessment["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
    removed = hypothesis["evidence_assessments"].pop()

    report = build_adversarial_challenge(
        assessment,
        hypothesis_id=hypothesis["id"],
        assessment_sha256="b" * 64,
        evidence_root=ROOT,
    )

    assert removed["evidence_id"] in report["evidence_review"]["unassessed_referenced_evidence_ids"]
    assert removed["evidence_id"] not in {
        item["evidence_id"] for item in report["evidence_review"]["recorded_relationships"]
    }


@pytest.mark.parametrize("scene_ids", [[], ["same", "same"], ["only-one"]])
def test_challenge_view_rejects_invalid_sar_comparison_identity(scene_ids):
    assessment = _t163_assessment()
    assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"] = scene_ids

    with pytest.raises(ValueError, match="two distinct acquisition records"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="c" * 64,
            evidence_root=ROOT,
        )


def test_challenge_view_rejects_scene_pair_that_disagrees_with_checksummed_measurement():
    assessment = _t163_assessment()
    scene_ids = assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"]
    assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"] = list(reversed(scene_ids))

    with pytest.raises(ValueError, match="does not match its linked measurement record"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="f" * 64,
            evidence_root=ROOT,
        )


def test_challenge_view_rejects_measurement_summary_that_does_not_reproduce():
    assessment = _t163_assessment()
    assessment["observations"]["sar_diagnostic_measurement"]["median_db"] += 0.25

    with pytest.raises(ValueError, match="median_db does not reproduce"):
        build_adversarial_challenge(
            assessment,
            hypothesis_id="H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE",
            assessment_sha256="9" * 64,
            evidence_root=ROOT,
        )


def test_iraq_challenge_stops_at_provider_qa_hold_without_change_result():
    review_path = ROOT / "data/cases/iraq-2026-nisar-diagnostic/case-review.json"
    review_bytes = review_path.read_bytes()
    review = json.loads(review_bytes)
    preview_bytes = (ROOT / review["diagnostic_single_observation_preview"]["record_path"]).read_bytes()
    report = build_qa_held_observation_challenge(
        review,
        review_sha256=sha256(review_bytes).hexdigest(),
        preview_record=json.loads(preview_bytes),
        preview_sha256=sha256(preview_bytes).hexdigest(),
    )

    assert report["status"] == "QA_HELD_NO_CHANGE_FINDING"
    assert report["finding"] is None
    assert report["challenge_result"]["change_conclusion"] is None
    assert report["challenge_result"]["change_computation_permitted"] is False
    assert [item["provider_qa_state"] for item in report["candidate_pair"]["products"]] == ["FAIL", "FAIL"]
    assert report["observation"]["scientific_disposition"] == "QA_HELD_DIAGNOSTIC_PREVIEW"


def test_iraq_challenge_rejects_preview_that_disagrees_with_provider_qa_record():
    review = json.loads((ROOT / "data/cases/iraq-2026-nisar-diagnostic/case-review.json").read_text())
    preview_path = ROOT / review["diagnostic_single_observation_preview"]["record_path"]
    preview = json.loads(preview_path.read_text())
    preview["source"]["provider_qa_status"] = "PASS"

    with pytest.raises(ValueError, match="provider QA hold"):
        build_qa_held_observation_challenge(
            review,
            review_sha256="d" * 64,
            preview_record=preview,
            preview_sha256="e" * 64,
        )
