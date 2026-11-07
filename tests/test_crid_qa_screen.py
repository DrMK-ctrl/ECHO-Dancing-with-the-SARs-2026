from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

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
