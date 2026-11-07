import hashlib
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from echo.qa_report import (
    MAX_QA_REPORT_BYTES,
    QAReportError,
    _canonical_report_uri,
    parse_qa_report,
    read_qa_report,
)


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "data/research/qa-reports"
BEFORE_SCENE = (
    "NISAR_L2_PR_GCOV_032_098_A_016_4005_DHDH_A_20261006T233918_"
    "20261006T233952_P05023_N_F_J_001"
)
AFTER_SCENE = (
    "NISAR_L2_PR_GCOV_033_098_A_016_4005_DHDH_A_20261018T233918_"
    "20261018T233952_P05023_N_F_J_001"
)
COLLECTION = "NISAR_L2_GCOV_PROVISIONAL_V1"
GUNW_SCENE = (
    "NISAR_L2_PR_GUNW_032_137_D_068_033_2000_SH_20261009T170432_"
    "20261009T170506_20261021T170432_20261021T170507_P05023_N_F_J_001"
)


def _feature(scene_id=AFTER_SCENE):
    return {
        "properties": {
            "fileID": scene_id,
            "url": (
                f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{COLLECTION}/"
                f"{scene_id}/{scene_id}.h5"
            ),
            "collectionName": COLLECTION,
            "processingLevel": "GCOV",
            "orbit": 6425,
            "pathNumber": 98,
            "frameNumber": 16,
        }
    }


def _report_bytes(scene_id):
    return (REPORT_DIR / f"{scene_id}_QA_REPORT.pdf").read_bytes()


@pytest.mark.parametrize(
    ("scene_id", "orbit", "processing_time"),
    [
        (BEFORE_SCENE, 6252, "2026-10-08T21:46:45+00:00"),
        (AFTER_SCENE, 6425, "2026-10-20T19:30:48+00:00"),
    ],
)
def test_real_asf_report_parses_product_identity_and_versioned_metadata(
    scene_id, orbit, processing_time
):
    feature = _feature(scene_id)
    properties = feature["properties"]
    properties.update(orbit=orbit, pathNumber=98, frameNumber=16)
    uri = properties["url"].removesuffix(f"{scene_id}.h5") + f"{scene_id}_QA_REPORT.pdf"

    record = parse_qa_report(
        _report_bytes(scene_id),
        scene_id=scene_id,
        artifact_uri=uri,
        catalog_properties=properties,
    )

    assert record["scene_id"] == scene_id
    assert record["artifact_sha256"] == hashlib.sha256(_report_bytes(scene_id)).hexdigest()
    assert record["qa_software_version"] == "17.0.0"
    assert record["report_processing_time_utc"] == processing_time
    assert record["product_metadata"]["absoluteOrbitNumber"] == orbit
    assert record["product_metadata"]["instrumentName"] == "LSAR"
    assert record["product_metadata"]["listOfObservationModes"] == ["(NOT SPECIFIED)"]
    assert record["catalog_crosschecks"] == {
        "absolute_orbit_matches_catalog": True,
        "track_matches_catalog_path": True,
        "frame_matches_catalog": True,
    }
    assert record["identification_crosscheck"]["status"] == "MATCHING_FAILURE_RULES_FOUND"
    assert record["provider_qa_disposition"] == "NOT_IN_REPORT_PDF"
    assert record["report_parse_status"] == "COMPLETE"


def test_report_rejects_scene_mismatch_and_untrusted_source_url():
    scene_id = AFTER_SCENE
    uri = (
        f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{COLLECTION}/"
        f"{scene_id}/{scene_id}_QA_REPORT.pdf"
    )
    with pytest.raises(QAReportError, match="granule ID does not match"):
        parse_qa_report(
            _report_bytes(scene_id),
            scene_id=BEFORE_SCENE,
            artifact_uri=uri.replace(scene_id, BEFORE_SCENE),
            catalog_properties=_feature(scene_id)["properties"],
        )


def test_canonical_report_uri_supports_gunw_without_widening_product_access():
    collection = "NISAR_L2_GUNW_PROVISIONAL_V1"
    feature = {
        "properties": {
            "fileID": GUNW_SCENE,
            "url": (
                f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/"
                f"{GUNW_SCENE}/{GUNW_SCENE}.h5"
            ),
            "collectionName": collection,
            "processingLevel": "GUNW",
        }
    }

    scene_id, report_uri = _canonical_report_uri(feature)

    assert scene_id == GUNW_SCENE
    assert report_uri == (
        f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/"
        f"{GUNW_SCENE}/{GUNW_SCENE}_QA_REPORT.pdf"
    )
    feature["properties"]["url"] = feature["properties"]["url"].replace(
        "nisar.asf.earthdatacloud.nasa.gov", "attacker.invalid"
    )
    with pytest.raises(QAReportError, match="canonical ASF"):
        _canonical_report_uri(feature)

    bad_report_uri = report_uri.replace("https://", "https://user@example.invalid/")
    with pytest.raises(QAReportError, match="does not identify"):
        parse_qa_report(
            b"not a PDF",
            scene_id=scene_id,
            artifact_uri=bad_report_uri,
            catalog_properties=feature["properties"],
        )


def test_gunw_report_uses_versioned_gunw_identification_contract(monkeypatch):
    collection = "NISAR_L2_GUNW_PROVISIONAL_V1"
    properties = {
        "fileID": GUNW_SCENE,
        "url": (
            f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/"
            f"{GUNW_SCENE}/{GUNW_SCENE}.h5"
        ),
        "collectionName": collection,
        "processingLevel": "GUNW",
        "orbit": 6291,
        "pathNumber": 137,
        "frameNumber": 68,
    }
    metadata = {
        "compositeReleaseId": "P05023",
        "frameNumber": 68,
        "instrumentName": "L-SAR",
        "listOfFrequencies": ["A"],
        "lookDirection": "Left",
        "missionId": "NISAR",
        "orbitPassDirection": "Descending",
        "productSpecificationVersion": "1.5.0",
        "productType": "GUNW",
        "productVersion": "1.0.11",
        "radarBand": "L",
        "referenceAbsoluteOrbitNumber": 6291,
        "referenceListOfObservationModes": ["(NOT SPECIFIED)"],
        "referenceZeroDopplerEndTime": "2026-10-09T17:05:06.000000000",
        "referenceZeroDopplerStartTime": "2026-10-09T17:04:32.000000000",
        "secondaryAbsoluteOrbitNumber": 6464,
        "secondaryListOfObservationModes": ["(NOT SPECIFIED)"],
        "secondaryZeroDopplerEndTime": "2026-10-21T17:05:07.000000000",
        "secondaryZeroDopplerStartTime": "2026-10-21T17:04:32.000000000",
        "trackNumber": 137,
    }
    uri = (
        f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{collection}/"
        f"{GUNW_SCENE}/{GUNW_SCENE}_QA_REPORT.pdf"
    )
    lines = [
        "NISAR Quality Assurance (QA) Report",
        GUNW_SCENE,
        "QA Software Version: 17.0.0",
        "QA Processing Date: 2026-10-23T14:41:28+00:00",
    ]
    lines.extend(
        f"{field}  {value!r}" if isinstance(value, list) else f"{field}  {value}"
        for field, value in metadata.items()
    )
    report_text = "\n".join(lines)

    class Page:
        def extract_text(self, **_kwargs):
            return report_text

    class Reader:
        is_encrypted = False
        pages = [Page()]

        def __init__(self, *_args, **_kwargs):
            pass

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=Reader))
    record = parse_qa_report(
        b"synthetic PDF fixture bytes",
        scene_id=GUNW_SCENE,
        artifact_uri=uri,
        catalog_properties=properties,
    )

    assert record["product_contract_status"] == "SUPPORTED_PRODUCT_CONTRACT"
    assert record["report_parse_status"] == "COMPLETE"
    assert record["missing_required_metadata"] == []
    assert record["catalog_crosschecks"] == {
        "track_matches_catalog_path": True,
        "frame_matches_catalog": True,
        "reference_absolute_orbit_matches_catalog_orbit": True,
    }
    findings = record["identification_crosscheck"]["findings"]
    assert {finding["field"] for finding in findings} == {
        "referenceListOfObservationModes",
        "secondaryListOfObservationModes",
    }


@pytest.mark.parametrize(
    "content, message",
    [
        (b"not a PDF", "could not be parsed"),
        (b"x" * (MAX_QA_REPORT_BYTES + 1), "size limit"),
    ],
)
def test_report_rejects_malformed_or_oversized_bytes(content, message):
    scene_id = AFTER_SCENE
    uri = (
        f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{COLLECTION}/"
        f"{scene_id}/{scene_id}_QA_REPORT.pdf"
    )
    with pytest.raises(QAReportError, match=message):
        parse_qa_report(
            content,
            scene_id=scene_id,
            artifact_uri=uri,
            catalog_properties=_feature(scene_id)["properties"],
        )


def test_read_report_fetches_scene_specific_canonical_pdf(monkeypatch):
    scene_id = AFTER_SCENE
    content = _report_bytes(scene_id)
    opened = {}

    class Stream:
        def __init__(self):
            self.cache = SimpleNamespace(total_requested_bytes=0)
            self.cache.fetcher = self._fetch

        def _fetch(self, start, end):
            self.cache.total_requested_bytes += end - start
            return content[start:end]

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return None

        def read(self, length):
            return self.cache.fetcher(0, min(length, len(content)))

    class FileSystem:
        client_kwargs = {}

        def open(self, url, mode, *, block_size, cache_type):
            opened.update(
                url=url,
                mode=mode,
                block_size=block_size,
                cache_type=cache_type,
            )
            return Stream()

    monkeypatch.setitem(
        sys.modules,
        "earthaccess",
        SimpleNamespace(
            login=lambda **_kwargs: SimpleNamespace(authenticated=True),
            get_fsspec_https_session=lambda: FileSystem(),
        ),
    )
    feature = _feature(scene_id)

    record = read_qa_report(feature)

    assert opened == {
        "url": (
            f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/{COLLECTION}/"
            f"{scene_id}/{scene_id}_QA_REPORT.pdf"
        ),
        "mode": "rb",
        "block_size": 1024 * 1024,
        "cache_type": "bytes",
    }
    assert record["artifact_size_bytes"] == len(content)
    assert record["retrieval"]["fsspec_range_bytes_requested"] == len(content)
    assert record["retrieval"]["network_retrieval"] is True
    assert record["provider_qa_disposition"] == "NOT_IN_REPORT_PDF"
