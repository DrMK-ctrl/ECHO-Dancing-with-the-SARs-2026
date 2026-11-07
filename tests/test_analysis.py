from datetime import datetime, timezone
from dataclasses import replace
import hashlib
import json

import numpy as np
import pytest

from echo.analysis import AnalysisGateError, QAEvidence, analyze_gcov_pair
from echo.nisar_access import GcovWindow


def _window(scene_id, acquisition_time, power, *, crid="P05023", x_coordinates=None):
    power = np.asarray(power, dtype=np.float32)
    height, width = power.shape
    if x_coordinates is None:
        x_coordinates = np.arange(width, dtype=np.float64) + 100.0
    return GcovWindow(
        scene_id=scene_id,
        frequency="A",
        row_start=0,
        row_stop=height,
        column_start=0,
        column_stop=width,
        layers={
            "HHHH": power,
            "mask": np.array([[1, 2, 0], [5, 2, 1]], dtype=np.uint8),
            "numberOfLooks": np.array([[2.0, 2.0, 0.0], [3.0, 4.0, 5.0]], dtype=np.float32),
            "inputDataExceptionMask": np.array(
                [[0, 0, 0], [0, 2, 0]], dtype=np.uint8
            ),
        },
        product_url=f"https://example.test/{scene_id}.h5",
        grid_metadata={
            "projection_value": 32645,
            "projection_attributes": {"epsg_code": 32645},
            "x_coordinates": np.asarray(x_coordinates),
            "y_coordinates": np.array([1000.0, 990.0]),
        },
        catalog_metadata={
            "fileID": scene_id,
            "collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1",
            "processingLevel": "GCOV",
            "startTime": acquisition_time,
            "stopTime": acquisition_time.replace("Z", "") + ".5Z",
            "crid": crid,
            "orbit": 6470 if acquisition_time.startswith("2026-08-19") else 6471,
            "productionConfiguration": "PR",
            "pathNumber": 98,
            "frameNumber": 16,
            "flightDirection": "ASCENDING",
            "rangeBandwidth": ["40+5"],
            "mainBandPolarization": ["HH", "HV"],
            "sideBandPolarization": ["HH", "HV"],
        },
        access={"method": "synthetic fixture"},
    )


def _qa(window, *, status="PASS", digest="a" * 64):
    return QAEvidence(
        scene_id=window.scene_id,
        status=status,
        artifact_uri=f"fixture://{window.scene_id}/qa.json",
        artifact_sha256=digest,
        checks={"identification_group": "PASS", "calibration_lut": "PASS"},
        software_version="17.0.0",
        product_metadata={
            "instrumentName": "L-SAR",
            "listOfObservationModes": ["DHDH"],
            "missionId": "NISAR",
            "productVersion": "1.0.11",
            "productSpecificationVersion": "1.5.0",
            "absoluteOrbitNumber": 1000,
            "trackNumber": 98,
            "frameNumber": 16,
            "isUrgentObservation": False,
            "isJointObservation": False,
            "lookDirection": "Right",
            "listOfFrequencies": ["A", "B"],
        },
    )


def _pair():
    before = _window(
        "before-scene",
        "2026-08-19T23:39:18Z",
        [[4.0, 4.0, 4.0], [4.0, 4.0, 4.0]],
    )
    after = _window(
        "after-scene",
        "2026-08-31T23:39:18Z",
        [[4.0, 8.0, 2.0], [4.0, 4.0, 4.0]],
    )
    after.layers["numberOfLooks"] = np.array(
        [[2.0, 4.0, 0.0], [3.0, 4.0, 5.0]], dtype=np.float32
    )
    return before, after


def test_pair_analysis_records_evidence_and_descriptive_measurement():
    before, after = _pair()
    result = analyze_gcov_pair(
        before,
        after,
        before_qa=_qa(before),
        after_qa=_qa(after, digest="b" * 64),
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    np.testing.assert_allclose(
        result.change.values_db[0, :2], [0.0, 3.0103], atol=1e-4
    )
    assert result.common_valid_mask.tolist() == [[True, True, False], [True, False, True]]
    assert result.manifest["grid_alignment"]["status"] == "PASS"
    assert (
        result.manifest["analysis"]["temporal_order"]["before_orbit"]
        != result.manifest["analysis"]["temporal_order"]["after_orbit"]
    )
    assert result.manifest["quality_control"]["common_mask_valid_samples"] == 4
    assert result.manifest["quality_control"]["numeric_valid_samples"] == 4
    assert result.manifest["quality_control"]["number_of_looks"]["before"]["median"] == 2.5
    assert result.manifest["quality_control"]["number_of_looks"]["after"]["median"] == 3.5
    assert result.manifest["inputs"]["before"]["qa_evidence"]["artifact_sha256"] == "a" * 64
    assert (
        result.manifest["inputs"]["before"]["qa_evidence"][
            "identification_crosscheck"
        ]["status"]
        == "NOT_RECORDED"
    )
    assert result.manifest["source_metadata_missing"] == {"before": [], "after": []}
    assert len(result.manifest["inputs"]["before"]["window_sha256"]) == 64
    assert len(result.manifest["output"]["measurement_sha256"]) == 64
    assert len(result.manifest["manifest_sha256"]) == 64
    manifest_payload = {
        key: value for key, value in result.manifest.items() if key != "manifest_sha256"
    }
    serialized = json.dumps(
        manifest_payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    assert result.manifest["manifest_sha256"] == hashlib.sha256(serialized).hexdigest()
    assert result.manifest["analysis"]["classification_performed"] is False


def test_pair_analysis_refuses_qa_hold():
    before, after = _pair()
    with pytest.raises(AnalysisGateError, match="requires PASS QA"):
        analyze_gcov_pair(
            before,
            after,
            before_qa=_qa(before, status="FAIL"),
            after_qa=_qa(after),
        )


def test_pair_analysis_applies_geographic_pixel_center_selection():
    before, after = _pair()
    selected = np.array([[True, False, False], [True, True, False]])
    bounds = [28.0, 40.0, 29.0, 41.0]
    before = replace(
        before,
        selection_mask=selected,
        selection_metadata={
            "bounds_wgs84": bounds,
            "source_crs": "EPSG:4326",
            "grid_crs": "EPSG:32645",
        },
    )
    after = replace(
        after,
        selection_mask=selected.copy(),
        selection_metadata={
            "bounds_wgs84": bounds,
            "source_crs": "EPSG:4326",
            "grid_crs": "EPSG:32645",
        },
    )
    result = analyze_gcov_pair(
        before,
        after,
        before_qa=_qa(before),
        after_qa=_qa(after, digest="b" * 64),
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    np.testing.assert_array_equal(
        result.common_valid_mask,
        np.array([[True, False, False], [True, False, False]]),
    )
    assert result.manifest["schema_version"] == 2
    assert result.manifest["quality_control"]["common_mask_valid_samples"] == 2
    assert result.manifest["inputs"]["before"]["window"]["selection_mask_sha256"]


def test_pair_analysis_refuses_different_geographic_pixel_center_masks():
    before, after = _pair()
    before = replace(
        before,
        selection_mask=np.array([[True, False, False], [True, True, False]]),
        selection_metadata={"bounds_wgs84": [28.0, 40.0, 29.0, 41.0]},
    )
    after = replace(
        after,
        selection_mask=np.array([[True, True, False], [True, False, False]]),
        selection_metadata={"bounds_wgs84": [28.0, 40.0, 29.0, 41.0]},
    )
    with pytest.raises(AnalysisGateError, match="different AOI pixel-center masks"):
        analyze_gcov_pair(
            before, after, before_qa=_qa(before), after_qa=_qa(after)
        )


def test_pair_analysis_refuses_same_orbit_windows():
    before, after = _pair()
    after.catalog_metadata["orbit"] = before.catalog_metadata["orbit"]
    with pytest.raises(AnalysisGateError, match="distinct known NISAR orbits"):
        analyze_gcov_pair(
            before, after, before_qa=_qa(before), after_qa=_qa(after)
        )


def test_pair_analysis_refuses_overlapping_acquisition_intervals():
    before, after = _pair()
    after.catalog_metadata["startTime"] = "2026-08-19T23:39:18.25Z"
    after.catalog_metadata["stopTime"] = "2026-08-19T23:39:19Z"
    with pytest.raises(AnalysisGateError, match="begin after before acquisition ends"):
        analyze_gcov_pair(
            before, after, before_qa=_qa(before), after_qa=_qa(after)
        )


def test_pair_analysis_rejects_placeholder_identification_even_with_qa_pass():
    before, after = _pair()
    before_qa = _qa(before)
    before_qa.product_metadata["instrumentName"] = "LSAR"
    before_qa.product_metadata["listOfObservationModes"] = ["(NOT SPECIFIED)"]
    with pytest.raises(AnalysisGateError, match="invalid instrumentName"):
        analyze_gcov_pair(
            before, after, before_qa=before_qa, after_qa=_qa(after)
        )


def test_pair_analysis_refuses_incompatible_crid_and_grid():
    before, after = _pair()
    after.catalog_metadata["crid"] = "X05026"
    with pytest.raises(AnalysisGateError, match="differ in crid"):
        analyze_gcov_pair(
            before, after, before_qa=_qa(before), after_qa=_qa(after)
        )

    before, after = _pair()
    after.grid_metadata["x_coordinates"] = np.array([100.0, 102.0, 104.0])
    with pytest.raises(AnalysisGateError, match="identical x_coordinates"):
        analyze_gcov_pair(
            before, after, before_qa=_qa(before), after_qa=_qa(after)
        )


def test_pair_analysis_refuses_catalog_identity_mismatch():
    before, after = _pair()
    before.catalog_metadata["fileID"] = "different-product"
    with pytest.raises(AnalysisGateError, match="identifier does not match"):
        analyze_gcov_pair(
            before, after, before_qa=_qa(before), after_qa=_qa(after)
        )


def test_pair_analysis_refuses_unverifiable_qa_artifact_reference():
    before, after = _pair()
    with pytest.raises(AnalysisGateError, match="SHA-256"):
        analyze_gcov_pair(
            before,
            after,
            before_qa=_qa(before, digest="not-a-digest"),
            after_qa=_qa(after),
        )
