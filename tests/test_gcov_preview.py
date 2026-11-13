from datetime import datetime, timezone

import json
import numpy as np

from echo.analysis import QAEvidence
from echo.nisar_access import (
    FALLBACK_REMOTE_BLOCK_BYTES,
    GcovWindow,
    MAX_WINDOW_RANGE_BYTES,
    NisarAccessError,
    REMOTE_BLOCK_BYTES,
)
from echo.qa import QASummaryRecord
from echo.gcov_preview import build_gcov_preview


SCENE_ID = (
    "NISAR_L2_PR_GCOV_028_098_A_016_4005_DHDH_A_20260819T233918_"
    "20260819T233953_P05023_N_F_J_001"
)
FEATURE = {
    "properties": {
        "fileID": SCENE_ID,
        "url": (
            "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
            f"NISAR_L2_GCOV_PROVISIONAL_V1/{SCENE_ID}/{SCENE_ID}.h5"
        ),
        "processingLevel": "GCOV",
        "collectionName": "NISAR_L2_GCOV_PROVISIONAL_V1",
        "startTime": "2026-08-19T23:39:18Z",
        "mainBandPolarization": ["HH", "HV"],
    }
}


def test_uint16_exception_flags_show_diagnostic_pixels_without_clearing_qa_fail(monkeypatch):
    evidence = QAEvidence(
        scene_id=SCENE_ID,
        status="FAIL",
        artifact_uri=f"https://example.test/{SCENE_ID}_QA_SUMMARY.csv",
        artifact_sha256="a" * 64,
        checks={"1:identification": "FAIL"},
        software_version="17.2.0",
        product_metadata={},
        check_details=[{"check": "identification", "result": "FAIL"}],
        retrieved_at_utc="2026-11-07T00:00:00+00:00",
        artifact_retrieval={"network_retrieval": True},
    )
    qa = QASummaryRecord(
        scene_id=SCENE_ID,
        artifact_uri=evidence.artifact_uri,
        artifact_sha256=evidence.artifact_sha256,
        artifact_size_bytes=512,
        retrieved_at_utc=evidence.retrieved_at_utc,
        retrieval={"provider": "ASF", "method": "bounded range"},
        evidence=evidence,
    )
    values = np.array([[0.25, 1.0], [2.0, np.nan]], dtype=np.float32)
    mask = np.array([[1, 2], [0, 255]], dtype=np.uint32)
    looks = np.array([[4, 4], [4, 0]], dtype=np.float32)
    exceptions = np.array([[0, 768], [0, 0]], dtype=np.uint16)
    selection = np.ones((2, 2), dtype=bool)
    window = GcovWindow(
        scene_id=SCENE_ID,
        frequency="A",
        row_start=10,
        row_stop=12,
        column_start=20,
        column_stop=22,
        layers={
            "HHHH": values,
            "mask": mask,
            "numberOfLooks": looks,
            "inputDataExceptionMask": exceptions,
        },
        product_url=FEATURE["properties"]["url"],
        grid_metadata={
            "projection_attributes": {"epsg_code": 4326},
            "coordinate_convention": "pixel centers",
            "x_coordinates": np.array([10.0, 10.001]),
            "y_coordinates": np.array([20.0, 20.001]),
        },
        catalog_metadata={"fileID": SCENE_ID, "processingLevel": "GCOV"},
        access={
            "read_at_utc": "2026-11-07T00:00:01+00:00",
            "method": "HTTPS byte-range streaming",
            "fsspec_range_bytes_requested": 1024,
            "max_fsspec_range_bytes_requested": 64 * 1024 * 1024,
            "geographic_selection": {
                "transform_expected_accuracy_m": None,
                "transform_expected_accuracy_status": "UNKNOWN",
            },
        },
        selection_mask=selection,
        layer_attributes={
            "inputDataExceptionMask": {
                "description": (
                    "Bitwise OR of input data exception codes for each image pixel "
                    "(0: no anomaly, 2: NISAR LSAR qFSP-H1 sample slip). Also includes OR "
                    "of validity mask bits, where each bit is set on for fully-focused data "
                    "or off for partially focused or missing data (256:HH, 512:HV, "
                    "1024:VH, 2048:VV, 4096:LH, 8192:LV, 16384:RH, 32768:RV)"
                )
            }
        },
    )
    calls = []

    def read_qa(*_args, **_kwargs):
        calls.append("qa")
        return qa

    def read_window(*_args, **kwargs):
        calls.append("pixels")
        assert kwargs["layers"] == (
            "HHHH",
            "mask",
            "numberOfLooks",
            "inputDataExceptionMask",
        )
        assert kwargs["max_samples"] == 65_536
        return window

    monkeypatch.setattr("echo.gcov_preview.read_qa_summary", read_qa)
    monkeypatch.setattr("echo.gcov_preview.read_gcov_window", read_window)
    record = build_gcov_preview(
        FEATURE,
        bounds_wgs84=(10.0, 20.0, 10.001, 20.001),
        frequency="A",
        layer="HHHH",
    )

    assert calls == ["qa", "pixels"]
    assert record["scientific_disposition"] == "QA_HELD_DIAGNOSTIC_PREVIEW"
    assert record["source"]["provider_qa_status"] == "FAIL"
    assert record["measurement"]["quality"]["display_eligible_pixel_count"] == 1
    assert record["measurement"]["quality"]["input_data_exception_code_counts"] == {
        "0": 3,
        "768": 1,
    }
    assert record["measurement"]["quality"]["unknown_quality_code_count"] == 0
    assert record["measurement"]["quality"]["input_data_exception_mask_encoding"] == (
        "UINT16_POLARIZATION_VALIDITY_AND_EXCEPTION_BITS"
    )
    assert record["measurement"]["quality"]["input_data_exception_mask_polarization_flag"] == 256
    assert record["measurement"]["values"][0][1] == 1.0
    assert record["display_transform"]["units"] == "dB"
    assert record["checksums"]["HHHH"]["sha256"]
    assert len(record["grid"]["pixel_corners_wgs84"]) == 3
    assert record["access"]["geographic_selection"]["transform_expected_accuracy_m"] is None
    assert record["access"]["geographic_selection"]["transform_expected_accuracy_status"] == "UNKNOWN"
    json.dumps(record, allow_nan=False)

    calls.clear()
    fail_first_attempt = True
    pixel_attempts = []
    window.access.clear()
    window.access.update({
        "read_at_utc": "2026-11-08T00:00:01+00:00",
        "method": "HTTPS byte-range streaming",
        "fsspec_range_bytes_requested": 2048,
        "max_fsspec_range_bytes_requested": MAX_WINDOW_RANGE_BYTES,
        "fsspec_read_ahead_block_bytes": FALLBACK_REMOTE_BLOCK_BYTES,
    })

    def read_window_with_one_reset(*_args, **kwargs):
        calls.append("pixels")
        pixel_attempts.append(kwargs)
        assert kwargs["layers"] == (
            "HHHH",
            "mask",
            "numberOfLooks",
            "inputDataExceptionMask",
        )
        if fail_first_attempt and len(pixel_attempts) == 1:
            error = NisarAccessError("remote NISAR product read failed (ConnectionResetError)")
            error.remote_range_bytes_requested = 4096
            error.remote_range_request_count = 3
            error.remote_range_fetch_elapsed_seconds = 2.5
            raise error from ConnectionResetError("connection reset")
        assert kwargs["_remote_block_bytes"] == FALLBACK_REMOTE_BLOCK_BYTES
        assert kwargs["_max_range_bytes"] == MAX_WINDOW_RANGE_BYTES - 4096
        window.access["fsspec_range_request_count"] = 2
        window.access["fsspec_range_fetch_elapsed_seconds"] = 4.25
        return window

    monkeypatch.setattr("echo.gcov_preview.read_gcov_window", read_window_with_one_reset)
    retry_record = build_gcov_preview(
        FEATURE,
        bounds_wgs84=(10.0, 20.0, 10.001, 20.001),
        frequency="A",
        layer="HHHH",
    )
    retry = retry_record["access"]["range_read_retry"]
    assert [call.get("_remote_block_bytes", REMOTE_BLOCK_BYTES) for call in pixel_attempts] == [
        REMOTE_BLOCK_BYTES,
        FALLBACK_REMOTE_BLOCK_BYTES,
    ]
    assert retry["combined_range_bytes_requested"] == 6144
    assert retry["combined_range_byte_limit"] == MAX_WINDOW_RANGE_BYTES
    assert retry["attempts"][0]["range_request_count"] == 3
    assert retry["attempts"][0]["range_fetch_elapsed_seconds"] == 2.5
    assert retry["attempts"][1]["range_request_count"] == 2
    assert retry["attempts"][1]["range_fetch_elapsed_seconds"] == 4.25
    assert retry_record["access"]["fsspec_range_request_count"] == 5
    assert retry_record["access"]["fsspec_range_fetch_elapsed_seconds"] == 6.75
    assert retry_record["source"]["provider_qa_status"] == "FAIL"
    assert retry_record["scientific_disposition"] == "QA_HELD_DIAGNOSTIC_PREVIEW"
    json.dumps(retry_record, allow_nan=False)
