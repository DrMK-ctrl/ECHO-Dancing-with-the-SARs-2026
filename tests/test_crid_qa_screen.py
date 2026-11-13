from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from tools.research.screen_nisar_crid_reprocessing_qa import (
    build_screen_record,
    validate_selection_manifest,
)


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

    assert result["record_type"] == "NISAR_GCOV_ALTERNATE_CRID_QA_SCREEN"
    assert result["primary_pinned_crid"] == "P05023"
    assert result["screened_crid"] == "X05026"
    assert result["alternate_crid"] == "X05026"
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


def test_summary_only_screen_does_not_fetch_qa_pdfs():
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads(
        (root / "data/cases/nepal-2026/catalog.json").read_text(encoding="utf-8")
    )
    review = json.loads(
        (root / "data/cases/nepal-2026/case-review.json").read_text(encoding="utf-8")
    )
    pair = build_screen_record(
        features=catalog["features"],
        crid="X05026",
        case_review=review,
        scene_ids=[
            "NISAR_L2_PR_GCOV_029_098_A_016_4005_DHDH_A_20260831T233918_20260831T233952_X05026_N_F_J_001",
            "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_X05026_N_F_J_001",
        ],
        include_reports=False,
        qa_summary_reader=lambda feature, *, product_metadata: _Summary(
            scene_id=feature["properties"]["fileID"],
            artifact_uri="https://qa.test/summary.csv",
            artifact_sha256="a" * 64,
            artifact_size_bytes=100,
            retrieved_at_utc="2026-11-07T00:00:00+00:00",
            retrieval={},
            evidence={"status": "FAIL", "checks": {}},
        ),
        qa_report_reader=lambda feature: pytest.fail("summary-only screen must not fetch QA PDFs"),
    )
    assert pair["report_screening_mode"] == "SUMMARY_ONLY"
    assert len(pair["products"]) == 2
    assert all(item["provider_qa_report_status"] == "NOT_REQUESTED" for item in pair["products"].values())


def test_selection_manifest_must_match_catalog_digest_and_exact_scene_set():
    manifest = {
        "record_type": "NISAR_VALIDATED_GCOV_UNSCREENED_FULL_PAIR_SELECTION",
        "catalog_source": {"path": "catalog.json", "sha256": "a" * 64},
        "selected_scene_ids": ["scene-before", "scene-after"],
    }
    validate_selection_manifest(
        manifest,
        catalog_path="catalog.json",
        catalog_sha256="a" * 64,
        scene_ids=["scene-before", "scene-after"],
    )
    partial_selection = {**manifest, "record_type": "NISAR_VALIDATED_GCOV_PARTIAL_PAIR_SELECTION"}
    validate_selection_manifest(
        partial_selection,
        catalog_path="catalog.json",
        catalog_sha256="a" * 64,
        scene_ids=["scene-before", "scene-after"],
    )
    cross_window_selection = {
        **manifest,
        "record_type": "NISAR_VALIDATED_GCOV_CROSS_WINDOW_PAIR_SELECTION",
    }
    validate_selection_manifest(
        cross_window_selection,
        catalog_path="catalog.json",
        catalog_sha256="a" * 64,
        scene_ids=["scene-before", "scene-after"],
    )
    for altered in (
        {**manifest, "selected_scene_ids": ["scene-before"]},
        {**manifest, "catalog_source": {"path": "catalog.json", "sha256": "b" * 64}},
    ):
        with pytest.raises(ValueError, match="does not match"):
            validate_selection_manifest(
                altered,
                catalog_path="catalog.json",
                catalog_sha256="a" * 64,
                scene_ids=["scene-before", "scene-after"],
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


def test_global_unscreened_full_full_validated_pairs_retain_all_qa_holds():
    root = Path(__file__).resolve().parents[1]
    record_path = root / "data/research/validated-gcov-p05036-unscreened-full-pairs-qa-2026-11-13.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    selection_path = root / "data/research/validated-gcov-p05036-unscreened-full-pair-selection-2026-11-13.json"
    selection_bytes = selection_path.read_bytes()
    selection = json.loads(selection_bytes)
    catalog_path = root / "data/research/validated-gcov-global-time-series-2026-10-09-11-08.json"
    catalog_bytes = catalog_path.read_bytes()
    catalog = json.loads(catalog_bytes)

    assert record["report_screening_mode"] == "SUMMARY_ONLY"
    assert record["record_type"] == "NISAR_GCOV_CRID_QA_SCREEN"
    assert record["primary_pinned_crid"] is None
    assert record["screened_crid"] == "P05036"
    assert record["alternate_crid"] is None
    assert record["catalog_pair_count"] == 31
    assert len(record["products"]) == 62
    assert record["selected_scene_ids"] == selection["selected_scene_ids"]
    assert record["catalog_screen"]["selection_manifest_path"] == str(selection_path.relative_to(root))
    assert record["catalog_screen"]["selection_manifest_sha256"] == sha256(selection_bytes).hexdigest()
    assert record["catalog_screen"]["source_record_sha256"] == sha256(catalog_bytes).hexdigest()
    assert record["catalog_screen"]["source_record_type"] == catalog["record_type"]
    assert record["pixel_measurements_read"] is False
    assert record["scientific_comparison_performed"] is False
    for scene_id, product in record["products"].items():
        summary = product["provider_qa_summary"]
        assert product["provider_qa_summary_retrieval_error"] is None
        assert product["provider_qa_report_status"] == "NOT_REQUESTED"
        assert product["provider_qa_report"] is None
        assert summary["scene_id"] == scene_id
        assert summary["evidence"]["status"] == "FAIL"
        checks = summary["evidence"]["check_details"]
        assert [item["result"] for item in checks].count("FAIL") == 1
        assert next(item for item in checks if item["result"] == "FAIL")["check"] == (
            "Passes all `identification` group checks?"
        )
        assert all(
            item["result"] == "PASS"
            for item in checks
            if item["check"] != "Passes all `identification` group checks?"
        )


def test_partial_coverage_validated_pairs_remain_qa_held_without_array_reads():
    root = Path(__file__).resolve().parents[1]
    record_path = root / "data/research/validated-gcov-p05036-partial-pairs-qa-2026-11-13.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    selection_path = root / "data/research/validated-gcov-p05036-partial-pair-selection-2026-11-13.json"
    selection_bytes = selection_path.read_bytes()
    catalog_path = root / "data/research/validated-gcov-global-time-series-2026-10-09-11-08.json"
    catalog_bytes = catalog_path.read_bytes()

    assert record["report_screening_mode"] == "SUMMARY_ONLY"
    assert record["record_type"] == "NISAR_GCOV_CRID_QA_SCREEN"
    assert record["primary_pinned_crid"] is None
    assert record["screened_crid"] == "P05036"
    assert record["alternate_crid"] is None
    assert record["catalog_pair_count"] == 15
    assert len(record["products"]) == 30
    assert record["selected_scene_ids"] == json.loads(selection_bytes)["selected_scene_ids"]
    assert record["catalog_screen"]["selection_manifest_path"] == str(selection_path.relative_to(root))
    assert record["catalog_screen"]["selection_manifest_sha256"] == sha256(selection_bytes).hexdigest()
    assert record["catalog_screen"]["source_record_sha256"] == sha256(catalog_bytes).hexdigest()
    assert record["pixel_measurements_read"] is False
    assert record["scientific_comparison_performed"] is False
    for scene_id, product in record["products"].items():
        summary = product["provider_qa_summary"]
        assert product["provider_qa_summary_retrieval_error"] is None
        assert product["provider_qa_report_status"] == "NOT_REQUESTED"
        assert summary["scene_id"] == scene_id
        assert summary["evidence"]["status"] == "FAIL"
        checks = summary["evidence"]["check_details"]
        assert sum(item["result"] == "FAIL" for item in checks) == 1
        assert next(item for item in checks if item["result"] == "FAIL")["check"] == (
            "Passes all `identification` group checks?"
        )
        assert all(
            item["result"] == "PASS"
            for item in checks
            if item["check"] != "Passes all `identification` group checks?"
        )


def test_new_november_validated_cross_window_pairs_remain_qa_held():
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads(
        (root / "data/research/validated-gcov-global-time-series-2026-11-10-13.json")
        .read_text(encoding="utf-8")
    )
    records = (
        (
            "validated-gcov-p05036-path77-frame78-cross-window-input-2026-11-13.json",
            "validated-gcov-p05036-path77-frame78-cross-window-selection-2026-11-13.json",
            "validated-gcov-p05036-path77-frame78-cross-window-scene-ids-2026-11-13.txt",
            "validated-gcov-p05036-path77-frame78-cross-window-qa-2026-11-13.json",
            1,
        ),
        (
            "validated-gcov-p05036-path77-other-cross-window-pairs-2026-11-13-input.json",
            "validated-gcov-p05036-path77-other-cross-window-pairs-2026-11-13-selection.json",
            "validated-gcov-p05036-path77-other-cross-window-pairs-2026-11-13-scene-ids.txt",
            "validated-gcov-p05036-path77-other-cross-window-pairs-qa-2026-11-13.json",
            11,
        ),
    )

    assert catalog["unique_scene_count"] == 19
    assert catalog["unique_acquisition_dates_observed"] == ["2026-11-10"]
    assert catalog["catalog_query"]["query_coverage_status"] == "COMPLETE"
    assert catalog["metadata_temporal_pair_count"] == 0

    combined_scene_ids = set()
    for input_name, selection_name, scene_name, qa_name, expected_pairs in records:
        input_path = root / "data/research" / input_name
        selection_path = root / "data/research" / selection_name
        scene_path = root / "data/research" / scene_name
        qa_path = root / "data/research" / qa_name
        input_bytes = input_path.read_bytes()
        selection_bytes = selection_path.read_bytes()
        scene_bytes = scene_path.read_bytes()
        input_record = json.loads(input_bytes)
        selection = json.loads(selection_bytes)
        record = json.loads(qa_path.read_text(encoding="utf-8"))
        scene_ids = [
            line.strip()
            for line in scene_bytes.decode("utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

        assert selection["record_type"] == "NISAR_VALIDATED_GCOV_CROSS_WINDOW_PAIR_SELECTION"
        assert selection["catalog_source"]["sha256"] == sha256(input_bytes).hexdigest()
        assert selection["selected_scene_ids"] == scene_ids
        assert record["record_type"] == "NISAR_GCOV_CRID_QA_SCREEN"
        assert record["screened_crid"] == "P05036"
        assert record["catalog_pair_count"] == expected_pairs
        assert record["catalog_screen"]["source_record_sha256"] == sha256(input_bytes).hexdigest()
        assert record["catalog_screen"]["selection_manifest_sha256"] == sha256(selection_bytes).hexdigest()
        assert record["catalog_screen"]["scene_id_file_sha256"] == sha256(scene_bytes).hexdigest()
        assert record["pixel_measurements_read"] is False
        assert record["scientific_comparison_performed"] is False
        assert set(record["products"]) == set(scene_ids)
        assert input_record["catalog_query"]["query_coverage_status"] == "TWO_RETAINED_WINDOWS_WITH_GAP"
        assert selection["source_catalogs"] == input_record["source_catalogs"]
        for source in input_record["source_catalogs"]:
            source_path = root / source["path"]
            assert sha256(source_path.read_bytes()).hexdigest() == source["sha256"]

        for scene_id, product in record["products"].items():
            summary = product["provider_qa_summary"]
            assert product["provider_qa_summary_retrieval_error"] is None
            assert product["provider_qa_report_status"] == "NOT_REQUESTED"
            assert summary["scene_id"] == scene_id
            assert summary["evidence"]["status"] == "FAIL"
            checks = summary["evidence"]["check_details"]
            assert [item["result"] for item in checks].count("FAIL") == 1
            assert next(item for item in checks if item["result"] == "FAIL")["check"] == (
                "Passes all `identification` group checks?"
            )
            assert all(
                item["result"] == "PASS"
                for item in checks
                if item["check"] != "Passes all `identification` group checks?"
            )
        combined_scene_ids.update(record["products"])

    assert len(combined_scene_ids) == 24
