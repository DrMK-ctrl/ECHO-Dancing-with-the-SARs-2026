from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from tools.research.screen_nisar_crid_reprocessing_qa import build_screen_record


@dataclass
class _Summary:
    scene_id: str
    artifact_uri: str
    artifact_sha256: str
    artifact_size_bytes: int
    retrieved_at_utc: str
    retrieval: dict
    evidence: dict


def test_alternate_crid_screen_preserves_pairing_and_source_qa_without_pixels():
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads(
        (root / "data/cases/nepal-2026/catalog.json").read_text(encoding="utf-8")
    )
    review = json.loads(
        (root / "data/cases/nepal-2026/case-review.json").read_text(encoding="utf-8")
    )
    summary_calls = []
    report_calls = []

    def read_summary(feature, *, product_metadata):
        scene_id = feature["properties"]["fileID"]
        summary_calls.append(scene_id)
        return _Summary(
            scene_id=scene_id,
            artifact_uri=f"https://qa.test/{scene_id}.csv",
            artifact_sha256="a" * 64,
            artifact_size_bytes=1200,
            retrieved_at_utc="2026-11-07T00:00:00+00:00",
            retrieval={"network_retrieval": True},
            evidence={"status": "FAIL", "checks": {"identification": "FAIL"}},
        )

    def read_report(feature):
        scene_id = feature["properties"]["fileID"]
        report_calls.append(scene_id)
        return {
            "scene_id": scene_id,
            "artifact_sha256": "b" * 64,
            "identification_crosscheck": {"status": "MATCHING_FAILURE_RULES_FOUND"},
        }

    result = build_screen_record(
        features=catalog["features"],
        crid="X05026",
        case_review=review,
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
        qa_summary_reader=read_summary,
        qa_report_reader=read_report,
    )

    assert result["primary_pinned_crid"] == "P05023"
    assert result["catalog_pair_count"] == 1
    assert result["catalog_pairs"][0]["crid"] == "X05026"
    assert len(result["products"]) == 2
    assert sorted(summary_calls) == sorted(report_calls)
    assert all(
        item["provider_qa_summary"]["evidence"]["status"] == "FAIL"
        for item in result["products"].values()
    )
    assert result["pixel_measurements_read"] is False
    assert result["scientific_comparison_performed"] is False


def test_screen_can_limit_qa_retrieval_to_complete_selected_pairs():
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads(
        (root / "data/cases/nepal-2026/catalog.json").read_text(encoding="utf-8")
    )
    review = json.loads(
        (root / "data/cases/nepal-2026/case-review.json").read_text(encoding="utf-8")
    )
    pair_screen = build_screen_record(
        features=catalog["features"],
        crid="X05026",
        case_review=review,
        qa_summary_reader=lambda feature, *, product_metadata: _Summary(
            scene_id=feature["properties"]["fileID"],
            artifact_uri="https://qa.test/summary.csv",
            artifact_sha256="a" * 64,
            artifact_size_bytes=100,
            retrieved_at_utc="2026-11-07T00:00:00+00:00",
            retrieval={},
            evidence={"status": "FAIL", "checks": {}},
        ),
        qa_report_reader=lambda feature: {"scene_id": feature["properties"]["fileID"]},
    )
    pair = pair_screen["catalog_pairs"][0]
    scene_ids = [pair["before_scene"], pair["after_scene"]]
    summary_calls = []

    result = build_screen_record(
        features=catalog["features"],
        crid="X05026",
        case_review=review,
        scene_ids=scene_ids,
        qa_summary_reader=lambda feature, *, product_metadata: (
            summary_calls.append(feature["properties"]["fileID"])
            or _Summary(
                scene_id=feature["properties"]["fileID"],
                artifact_uri="https://qa.test/summary.csv",
                artifact_sha256="a" * 64,
                artifact_size_bytes=100,
                retrieved_at_utc="2026-11-07T00:00:00+00:00",
                retrieval={},
                evidence={"status": "FAIL", "checks": {}},
            )
        ),
        qa_report_reader=lambda feature: {"scene_id": feature["properties"]["fileID"]},
    )
    assert result["selected_scene_ids"] == sorted(scene_ids)
    assert result["catalog_pair_count"] == 1
    assert set(summary_calls) == set(scene_ids)
    assert len(result["products"]) == 2
    with pytest.raises(ValueError, match="complete metadata-compatible pairs"):
        build_screen_record(
            features=catalog["features"],
            crid="X05026",
            case_review=review,
            scene_ids=scene_ids[:1],
            qa_summary_reader=lambda feature, *, product_metadata: None,
            qa_report_reader=lambda feature: None,
        )


def test_retained_path148_frame5_validated_pair_stays_qa_held_without_pixels():
    root = Path(__file__).resolve().parents[1]
    record = json.loads(
        (root / "data/research/validated-gcov-p05036-path148-frame5-qa-2026-11-13.json")
        .read_text(encoding="utf-8")
    )
    catalog = json.loads(
        (root / record["catalog_screen"]["source_record_path"]).read_text(encoding="utf-8")
    )
    scene_ids = set(record["selected_scene_ids"])
    pair = next(
        item for item in catalog["metadata_temporal_pairs"]
        if {item["before_scene"], item["after_scene"]} == scene_ids
    )

    assert record["catalog_pair_count"] == 1
    assert pair["path"] == 148 and pair["frame"] == 5
    assert pair["frame_coverage"] == ["Full", "Full"]
    assert pair["maturity"] == "VALIDATED"
    assert record["pixel_measurements_read"] is False
    assert record["scientific_comparison_performed"] is False
    assert set(record["products"]) == scene_ids

    for scene_id, product in record["products"].items():
        qa = product["provider_qa_summary"]
        report = product["provider_qa_report"]
        checks = qa["evidence"]["checks"]
        assert qa["scene_id"] == scene_id
        assert qa["evidence"]["status"] == "FAIL"
        assert checks["4:Passes all `identification` group checks?"] == "FAIL"
        assert all(
            result == "PASS"
            for check, result in checks.items()
            if check != "4:Passes all `identification` group checks?"
        )
        assert report["scene_id"] == scene_id
        assert report["product_metadata"]["compositeReleaseId"] == "P05036"
        assert report["catalog_crosschecks"]["absolute_orbit_matches_catalog"] is True
        assert report["catalog_crosschecks"]["frame_matches_catalog"] is True
        assert report["catalog_crosschecks"]["track_matches_catalog_path"] is True
        assert report["identification_crosscheck"]["status"] == "MATCHING_FAILURE_RULES_FOUND"
