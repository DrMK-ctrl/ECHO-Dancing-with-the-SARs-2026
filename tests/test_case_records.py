import json
from pathlib import Path


_ISTANBUL = Path(__file__).parents[1] / "data/cases/istanbul-2026"


def test_istanbul_candidate_provenance_is_consistent_and_fail_closed():
    catalog = json.loads((_ISTANBUL / "catalog.json").read_text(encoding="utf-8"))
    review = json.loads((_ISTANBUL / "case-review.json").read_text(encoding="utf-8"))
    catalog_ids = {
        feature["properties"]["fileID"] for feature in catalog["features"]
    }
    candidate = review["candidate_pair"]

    assert review["status"] == "CANDIDATE_QA_HOLD"
    assert review["scientific_analysis_performed"] is False
    assert review["nisar_raster_pixels_read"] is False
    assert candidate["status"] == "METADATA_MATCH_ONLY"
    assert candidate["qa_status"] == "QA_HOLD"
    assert candidate["before"]["scene_id"] in catalog_ids
    assert candidate["after"]["scene_id"] in catalog_ids

    for product in candidate["products"]:
        scene_id = product["scene_id"]
        role = product["role"]
        identification = json.loads(
            (_ISTANBUL / f"identification-{role}.json").read_text(encoding="utf-8")
        )
        qa = json.loads(
            (_ISTANBUL / f"qa-summary-{role}.json").read_text(encoding="utf-8")
        )
        assert identification["product"]["scene_id"] == scene_id
        assert qa["scene_id"] == scene_id
        assert qa["evidence"]["status"] == "FAIL"
        assert qa["artifact_sha256"] == product["provider_qa"]["summary_sha256"]
        assert product["qa_summary"]["identification_group"] == "FAIL"
