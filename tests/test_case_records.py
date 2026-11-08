import json
from hashlib import sha256
from pathlib import Path

from echo.web import _validate_assessment_record

_ISTANBUL = Path(__file__).parents[1] / "data/cases/istanbul-2026"
_PROJECT = Path(__file__).parents[1]


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


def test_rio_grande_cross_sensor_cases_link_their_own_evidence_and_candidate_pair():
    for case_name in ("rio-grande-do-sul-t024-2024", "rio-grande-do-sul-t163-349925-2024"):
        case_dir = _PROJECT / "data/cases" / case_name
        catalog = json.loads((case_dir / "catalog.json").read_text(encoding="utf-8"))
        review = json.loads((case_dir / "case-review.json").read_text(encoding="utf-8"))
        manifest = json.loads((case_dir / "investigation.json").read_text(encoding="utf-8"))
        assert catalog["feature_count"] == 0
        assert catalog["query"]["dataset"] == "OPERA RTC-S1"
        assert catalog["query"]["bounds_wgs84"] == [-51.24, -30.04, -51.23, -30.03]
        assert review["status"] == "DIAGNOSTIC_CASE"
        assert review["primary_opera_pair"]["before_scene_id"] != review["primary_opera_pair"]["after_scene_id"]
        assert manifest["schema_version"] == 1

        context_path = _PROJECT / manifest["evidence_records"]["dswx_context"]
        assessment_path = _PROJECT / manifest["evidence_records"]["cross_sensor_assessment"]
        context = json.loads(context_path.read_text(encoding="utf-8"))
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        assert context["aoi"]["bounds_west_south_east_north"] == catalog["query"]["bounds_wgs84"]
        assert assessment["status"] == "CAUSAL_INTERPRETATION_UNRESOLVED"
        assert assessment["case_id"] == review["case_id"]
        evidence_ids = _validate_assessment_record(assessment, _PROJECT)
        assert len(evidence_ids) == len(assessment["evidence_artifacts"])
        assert len(assessment["hypotheses"]) == 6
        sar_scenes = assessment["observations"]["sar_diagnostic_measurement"]["scene_ids"]
        assert sar_scenes == [review["primary_opera_pair"]["before_scene_id"], review["primary_opera_pair"]["after_scene_id"]]
        assert assessment["evidence_artifacts"][1]["sha256"] == sha256(context_path.read_bytes()).hexdigest()
        if case_name.endswith("t163-349925-2024"):
            screen_path = _PROJECT / "data/research/dswx-hls-screen-T163-349925-2026-11-07.json"
            catalog_evidence = next(item for item in assessment["evidence_artifacts"] if item["evidence_id"] == "NASA-CMR-DSWX-TEMPORAL-SCREEN")
            assert catalog_evidence["sha256"] == sha256(screen_path.read_bytes()).hexdigest()
            assert assessment["follow_up_evidence"][1]["availability_state"] == "CATALOG_SCREENED_CONTEXT_RETRIEVED"
            evidence_ids = {item["evidence_id"] for item in assessment["evidence_artifacts"]}
            assert {
                "ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY",
                "NASA-OPERA-RTC-S1-VH-PAIR",
                "NASA-OPERA-RTC-VH-DSWX-SPATIAL-SUPPORT",
                "NASA-OPERA-RTC-POLARIZATION-SENSITIVITY",
                "NASA-SPL2SMAP-S-CANDIDATE-SCREEN",
                "NASA-HLS-L30-VEGETATION-SCREEN",
                "NASA-HLS-L30-NDVI-SAR-ASSOCIATION",
                "NASA-HLS-S30-VEGETATION-SCREEN",
                "NASA-HLS-S30-NDVI-SAR-ASSOCIATION",
            } <= evidence_ids
            assert assessment["observations"]["smap_sentinel_soil_moisture_screen"]["paired_quality_eligible_cells"] == 0
            soil_moisture_hypothesis = next(item for item in assessment["hypotheses"] if item["id"] == "H3_SOIL_MOISTURE_CHANGE")
            vegetation_hypothesis = next(item for item in assessment["hypotheses"] if item["id"] == "H4_VEGETATION_STATE_CHANGE")
            assert soil_moisture_hypothesis["state"] == "UNRESOLVED"
            assert soil_moisture_hypothesis["testability_state"] == "NOT_TESTABLE_WITH_RETAINED_EVIDENCE"
            assert "NASA-SPL2SMAP-S-CANDIDATE-SCREEN" in [item["evidence_id"] for item in soil_moisture_hypothesis["evidence_assessments"]]
            assert all(not item["evidence_id"].startswith("NASA-HLS-") for item in soil_moisture_hypothesis["evidence_assessments"])
            assert vegetation_hypothesis["state"] == "UNRESOLVED"
            assert vegetation_hypothesis["testability_state"] == "DESCRIPTIVE_ASSOCIATION_ONLY"
            assert {item["evidence_id"] for item in vegetation_hypothesis["evidence_assessments"]} == {
                "NASA-HLS-L30-NDVI-SAR-ASSOCIATION",
                "NASA-HLS-S30-NDVI-SAR-ASSOCIATION",
                "NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN",
            }
            modis_assessment = next(item for item in vegetation_hypothesis["evidence_assessments"] if item["evidence_id"] == "NASA-MOD13Q1-VEGETATION-CANDIDATE-SCREEN")
            assert modis_assessment["relationship"] == "LIMITS_INTERPRETATION"
            assert all(
                item["relationship"] == "DOES_NOT_DISTINGUISH"
                for item in vegetation_hypothesis["evidence_assessments"]
                if item["evidence_id"].startswith("NASA-HLS-")
            )
            assert assessment["observations"]["hls_l30_vegetation_context"]["common_clear_land_aoi_fraction"] < 0.25
            assert assessment["follow_up_evidence"][-3]["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
            assert assessment["follow_up_evidence"][-2]["availability_state"] == "RETRIEVED_QUALITY_LIMITED"
            assert assessment["follow_up_evidence"][-2]["follow_up_id"] == "F9_BETTER_SUPPORTED_VEGETATION_OBSERVATION"
            assert assessment["follow_up_evidence"][-1]["follow_up_id"] == "F10_ACQUISITION_CONDITION_REVIEW"
            water_hypothesis = next(item for item in assessment["hypotheses"] if item["id"] == "H2_WATER_CHANGE_EXPLAINS_SAR_RESPONSE")
            assert water_hypothesis["state"] == "UNRESOLVED"
            water_evidence = {item["evidence_id"]: item for item in water_hypothesis["evidence_assessments"]}
            assert water_evidence["NASA-OPERA-RTC-POLARIZATION-SENSITIVITY"]["relationship"] == "DOES_NOT_DISTINGUISH"
            assert water_evidence["ANA-GUAIBA-FLOOD-STAGE-CHRONOLOGY"]["relationship"] == "DOES_NOT_DISTINGUISH"
            assert _validate_assessment_record(assessment, _PROJECT)
