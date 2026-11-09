from datetime import datetime, timezone

import numpy as np
import pytest

from echo.gcov_analysis import build_gcov_pair_analysis
from echo.nisar_access import GcovWindow
from echo.qa import QASummaryRecord
from echo.analysis import QAEvidence
from echo.qa_contract import REQUIRED_PROVIDER_QA_CHECKS


def _feature(scene_id, start_time, orbit, *, collection="NISAR_L2_GCOV_PROVISIONAL_V1"):
    return {
        "properties": {
            "fileID": scene_id,
            "url": f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/{scene_id}/{scene_id}.h5",
            "processingLevel": "GCOV",
            "collectionName": collection,
            "startTime": start_time,
            "stopTime": start_time.replace("Z", "") + ".5Z",
            "crid": "P05023",
            "orbit": orbit,
            "productionConfiguration": "PR",
            "pathNumber": 98,
            "frameNumber": 16,
            "flightDirection": "ASCENDING",
            "mainBandPolarization": ["HH", "HV"],
            "sideBandPolarization": ["HH", "HV"],
            "rangeBandwidth": ["40+5"],
        }
    }


def _qa_record(feature, status):
    scene_id = feature["properties"]["fileID"]
    names = sorted(REQUIRED_PROVIDER_QA_CHECKS)
    evidence = QAEvidence(
        scene_id=scene_id,
        status=status,
        artifact_uri=f"https://qa.example/{scene_id}.csv",
        artifact_sha256="a" * 64,
        checks={f"{index}:{name}": status for index, name in enumerate(names, 1)},
        software_version=None,
        product_metadata={},
        check_details=[
            {
                "tool": "QA",
                "check": name,
                "result": status,
                "threshold": "",
                "actual": "",
                "notes": "",
            }
            for name in names
        ],
        retrieved_at_utc="2026-11-07T00:00:00+00:00",
    )
    return QASummaryRecord(
        scene_id=scene_id,
        artifact_uri=evidence.artifact_uri,
        artifact_sha256=evidence.artifact_sha256,
        artifact_size_bytes=100,
        retrieved_at_utc=evidence.retrieved_at_utc,
        retrieval={"network_retrieval": True},
        evidence=evidence,
    )


def _window(feature, power, orbit, *, exception_value=0, exception_description=None):
    properties = feature["properties"]
    return GcovWindow(
        scene_id=properties["fileID"],
        frequency="A",
        row_start=0,
        row_stop=2,
        column_start=0,
        column_stop=2,
        layers={
            "HHHH": np.asarray(power, dtype=np.float32),
            "mask": np.ones((2, 2), dtype=np.uint8),
            "numberOfLooks": np.full((2, 2), 3.0, dtype=np.float32),
            "inputDataExceptionMask": np.full(
                (2, 2), exception_value,
                dtype=np.uint16 if exception_description else np.uint8,
            ),
        },
        product_url=properties["url"],
        grid_metadata={
            "projection_value": 32645,
            "projection_attributes": {"epsg_code": 32645},
            "x_coordinates": np.array([500000.0, 500030.0]),
            "y_coordinates": np.array([3000000.0, 2999970.0]),
        },
        catalog_metadata={key: properties[key] for key in (
            "fileID", "collectionName", "processingLevel", "startTime", "stopTime",
            "crid", "orbit", "productionConfiguration", "pathNumber", "frameNumber",
            "flightDirection", "mainBandPolarization", "sideBandPolarization", "rangeBandwidth",
        )},
        access={"method": "fixture", "read_at_utc": "2026-11-07T00:00:00+00:00"},
        layer_attributes=(
            {"inputDataExceptionMask": {"description": exception_description}}
            if exception_description
            else {}
        ),
    )


def _metadata(feature):
    properties = feature["properties"]
    return {
        "product": {
            "metadata": {
                "instrumentName": "L-SAR",
                "missionId": "NISAR",
                "absoluteOrbitNumber": properties["orbit"],
                "trackNumber": properties["pathNumber"],
                "frameNumber": properties["frameNumber"],
                "listOfObservationModes": ["DHDH"],
                "productVersion": "1.0.11",
                "productSpecificationVersion": "1.5.0",
                "listOfFrequencies": ["A"],
            }
        }
    }


def test_qa_failure_returns_evidence_without_reading_metadata_or_pixels():
    before = _feature(
        "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001",
        "2026-08-19T23:39:18Z",
        6470,
    )
    after = _feature(
        "NISAR_L2_PR_GCOV_033_098_A_016_4005_DHDH_A_20260831T233918_20260831T233953_P05023_N_F_J_001",
        "2026-08-31T23:39:18Z",
        6471,
    )
    calls = []

    def qa_reader(feature, *, product_metadata):
        calls.append(feature["properties"]["fileID"])
        return _qa_record(feature, "FAIL")

    def must_not_read(*_args, **_kwargs):
        pytest.fail("QA-held pairs must stop before metadata and measurement reads")

    record = build_gcov_pair_analysis(
        before,
        after,
        bounds_wgs84=[85.5, 28.2, 85.6, 28.3],
        frequency="A",
        layer="HHHH",
        qa_reader=qa_reader,
        metadata_reader=must_not_read,
        window_reader=must_not_read,
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["status"] == "QA_HELD"
    assert record["held_roles"] == ["before", "after"]
    assert record["source_products"]["before"]["product_maturity"] == "PROVISIONAL"
    assert record["measurement"] is None
    assert record["manifest"] is None
    assert record["analysis_gates"] == {
        "provider_qa": "HELD_NON_PASS",
        "product_identification": "NOT_EVALUATED",
        "measurement_arrays": "NOT_READ",
        "grid_alignment": "NOT_EVALUATED",
        "aoi_common_valid_coverage": "NOT_EVALUATED",
        "change_calculation": "NOT_PERFORMED",
    }
    assert len(record["next_evidence"]) == 2
    assert record["source_products"]["before"]["mission"] == "NISAR"
    assert record["source_products"]["before"]["acquisition_start_utc"] == "2026-08-19T23:39:18Z"
    assert record["source_products"]["before"]["product_url"].endswith(".h5")
    assert len(calls) == 2
    assert "FAIL" in str(record["provider_qa"])


def test_product_catalog_identity_mismatch_is_held_before_window_reads():
    before = _feature(
        "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001",
        "2026-08-19T23:39:18Z",
        6470,
    )
    after = _feature(
        "NISAR_L2_PR_GCOV_029_098_A_016_4005_DHDH_A_20260831T233918_20260831T233953_P05023_N_F_J_001",
        "2026-08-31T23:39:18Z",
        6471,
    )

    def wrong_before_metadata(feature):
        result = _metadata(feature)
        if feature["properties"]["orbit"] == 6470:
            result["product"]["metadata"]["absoluteOrbitNumber"] = 123
        return result

    def must_not_read(*_args, **_kwargs):
        pytest.fail("identity-held pairs must stop before raster window reads")

    record = build_gcov_pair_analysis(
        before,
        after,
        bounds_wgs84=[85.5, 28.2, 85.6, 28.3],
        frequency="A",
        layer="HHHH",
        qa_reader=lambda feature, **_: _qa_record(feature, "PASS"),
        metadata_reader=wrong_before_metadata,
        window_reader=must_not_read,
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["status"] == "IDENTITY_HELD"
    assert record["held_roles"] == ["before"]
    assert record["analysis_gates"]["provider_qa"] == "PASS"
    assert record["analysis_gates"]["product_identification"] == "HELD_CATALOG_CROSSCHECK"
    assert record["analysis_gates"]["measurement_arrays"] == "NOT_READ"
    assert record["provider_qa"]["before"]["evidence"]["catalog_identity_crosscheck"]["status"] == "MISMATCH"
    assert record["measurement"] is None
    assert record["manifest"] is None


def test_beta_pair_with_qa_pass_is_held_before_metadata_or_pixel_reads():
    before = _feature(
        "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001",
        "2026-08-19T23:39:18Z",
        6470,
        collection="NISAR_L2_GCOV_BETA_V1",
    )
    after = _feature(
        "NISAR_L2_PR_GCOV_033_098_A_016_4005_DHDH_A_20260831T233918_20260831T233953_P05023_N_F_J_001",
        "2026-08-31T23:39:18Z",
        6471,
        collection="NISAR_L2_GCOV_BETA_V1",
    )

    def must_not_read(*_args, **_kwargs):
        pytest.fail("pre-calibration BETA must stop before identification or raster reads")

    record = build_gcov_pair_analysis(
        before,
        after,
        bounds_wgs84=[85.5, 28.2, 85.6, 28.3],
        frequency="A",
        layer="HHHH",
        qa_reader=lambda feature, **_: _qa_record(feature, "PASS"),
        metadata_reader=must_not_read,
        window_reader=must_not_read,
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["status"] == "MATURITY_HELD"
    assert record["held_roles"] == ["before", "after"]
    assert record["source_products"]["before"]["product_maturity"] == "BETA"
    assert record["analysis_gates"]["provider_qa"] == "PASS"
    assert record["analysis_gates"]["product_maturity"] == "HELD_PRECALIBRATION_OR_UNSUPPORTED"
    assert record["analysis_gates"]["measurement_arrays"] == "NOT_READ"
    assert record["measurement"] is None
    assert record["manifest"] is None


def test_passed_pair_runs_gated_measurement_and_returns_geolocated_values():
    before = _feature(
        "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_20260819T233953_P05023_N_F_J_001",
        "2026-08-19T23:39:18Z",
        6470,
    )
    after = _feature(
        "NISAR_L2_PR_GCOV_033_098_A_016_4005_DHDH_A_20260831T233918_20260831T233953_P05023_N_F_J_001",
        "2026-08-31T23:39:18Z",
        6471,
    )

    exception_description=(
        "Bitwise OR of input data exception codes for each image pixel "
        "(0: no anomaly, 2: NISAR LSAR qFSP-H1 sample slip). Also includes OR "
        "of validity mask bits, where each bit is set on for fully-focused data "
        "or off for partially focused or missing data (256:HH, 512:HV, "
        "1024:VH, 2048:VV, 4096:LH, 8192:LV, 16384:RH, 32768:RV)"
    )
    record = build_gcov_pair_analysis(
        before,
        after,
        bounds_wgs84=[85.5, 28.2, 85.6, 28.3],
        frequency="A",
        layer="HHHH",
        qa_reader=lambda feature, **_: _qa_record(feature, "PASS"),
        metadata_reader=_metadata,
        window_reader=lambda feature, **_: _window(
            feature,
            [[4.0, 4.0], [4.0, 4.0]]
            if feature["properties"]["orbit"] == 6470
            else [[4.0, 8.0], [2.0, 4.0]],
            feature["properties"]["orbit"],
            exception_value=768,
            exception_description=exception_description,
        ),
        generated_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record["status"] == "MEASURED_DESCRIPTIVE_ONLY"
    assert record["source_products"]["before"]["product_maturity"] == "PROVISIONAL"
    assert record["source_products"]["after"]["product_maturity"] == "PROVISIONAL"
    assert record["source_products"]["after"]["acquisition_start_utc"] == "2026-08-31T23:39:18Z"
    assert record["measurement"]["values_db"][0] == [0.0, pytest.approx(3.0103, abs=1e-4)]
    assert record["measurement"]["valid_mask"] == [[True, True], [True, True]]
    assert len(record["grid"]["pixel_corners_wgs84"]) == 3
    assert record["manifest"]["analysis"]["classification_performed"] is False
    assert record["manifest"]["grid_alignment"]["status"] == "PASS"
    for role in ("before", "after"):
        mask_record = record["manifest"]["inputs"][role][
            "quality_layer_attribute_records"
        ]["inputDataExceptionMask"]
        assert mask_record["attributes"]["description"] == exception_description
        assert len(mask_record["attributes_sha256"]) == 64
    assert (
        record["provider_qa"]["before"]["evidence"]["product_metadata"][
            "instrumentName"
        ]
        == "L-SAR"
    )
