from datetime import datetime, timezone
import hashlib
import sys
from types import SimpleNamespace

import pytest

from echo.qa import (
    MAX_QA_SUMMARY_BYTES,
    QASummaryError,
    crosscheck_identification_metadata,
    parse_qa_summary,
    read_qa_summary,
)


SCENE_ID = "NISAR_L2_PR_GCOV_fixture"
SUMMARY_URL = (
    "https://nisar.asf.earthdatacloud.nasa.gov/NISAR/"
    f"NISAR_L2_GCOV_V1/{SCENE_ID}/{SCENE_ID}_QA_SUMMARY.csv"
)


def _csv(*results):
    lines = ["Tool,Check,Result,Threshold,Actual,Notes"]
    for check, result, notes in results:
        lines.append(f'QA,"{check}",{result},,,"{notes}"')
    return ("\r\n".join(lines) + "\r\n").encode("utf-8")


def test_parsed_fail_is_preserved_with_source_hash_and_check_details():
    content = _csv(
        ("Able to open input NISAR file?", "PASS", ""),
        ("Passes all identification group checks?", "FAIL", "field check failed"),
    )
    record = parse_qa_summary(
        content,
        scene_id=SCENE_ID,
        artifact_uri=SUMMARY_URL,
        product_metadata={"instrumentName": "L-SAR"},
        retrieved_at=datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert record.evidence.status == "FAIL"
    assert record.artifact_sha256 == hashlib.sha256(content).hexdigest()
    assert record.retrieval["network_retrieval"] is False
    assert record.artifact_size_bytes == len(content)
    assert record.evidence.checks["2:Passes all identification group checks?"] == "FAIL"
    assert record.evidence.check_details[1]["notes"] == "field check failed"
    assert record.evidence.retrieved_at_utc == "2026-11-07T00:00:00+00:00"


def test_parsed_pass_requires_every_row_to_pass():
    required_checks = (
        "Able to open input NISAR file?",
        "Coordinate grid metadata cubes are valid?",
        "Calibration information LUTs are valid?",
        "Passes all `identification` group checks?",
        "QA completed with no exceptions?",
    )
    content = _csv(*((check, "PASS", "") for check in required_checks))
    record = parse_qa_summary(
        content,
        scene_id=SCENE_ID,
        artifact_uri=SUMMARY_URL,
        product_metadata={},
    )

    assert record.evidence.status == "PASS"


def test_missing_required_check_cannot_produce_qa_pass():
    content = _csv(("Able to open input NISAR file?", "PASS", ""))
    record = parse_qa_summary(
        content,
        scene_id=SCENE_ID,
        artifact_uri=SUMMARY_URL,
        product_metadata={},
    )

    assert record.evidence.status == "INDETERMINATE"


def test_unknown_check_result_is_indeterminate():
    content = _csv(("Input opens", "MAYBE", "provider result is unfamiliar"))
    record = parse_qa_summary(
        content,
        scene_id=SCENE_ID,
        artifact_uri=SUMMARY_URL,
        product_metadata={},
    )

    assert record.evidence.status == "INDETERMINATE"
    assert next(iter(record.evidence.checks.values())) == "UNKNOWN"


def test_identification_crosscheck_reports_only_versioned_candidate_rules():
    metadata = {
        "instrumentName": "LSAR",
        "listOfObservationModes": ["(NOT SPECIFIED)"],
    }

    unknown = crosscheck_identification_metadata(metadata, software_version=None)
    unsupported = crosscheck_identification_metadata(
        metadata, software_version="17.0.0"
    )
    result = crosscheck_identification_metadata(metadata, software_version="17.2.0")

    assert unknown["status"] == "VERSION_UNKNOWN"
    assert unknown["findings"] == []
    assert unsupported["status"] == "UNSUPPORTED_VERSION"
    assert unsupported["findings"] == []
    assert result["status"] == "MATCHING_FAILURE_RULES_FOUND"
    assert [item["field"] for item in result["findings"]] == [
        "instrumentName",
        "listOfObservationModes",
    ]
    assert "not a provider per-field QA result" in result["scope"]


def test_qa_record_keeps_provider_fail_separate_from_source_crosscheck():
    content = _csv(("Passes all `identification` group checks?", "FAIL", ""))
    record = parse_qa_summary(
        content,
        scene_id=SCENE_ID,
        artifact_uri=SUMMARY_URL,
        product_metadata={
            "instrumentName": "LSAR",
            "listOfObservationModes": ["(NOT SPECIFIED)"],
        },
        software_version="17.2.0",
    )

    assert record.evidence.status == "FAIL"
    assert (
        record.evidence.identification_crosscheck["status"]
        == "MATCHING_FAILURE_RULES_FOUND"
    )
    assert all(
        item["result"] == "SOURCE_RULE_MISMATCH"
        for item in record.evidence.identification_crosscheck["findings"]
    )


@pytest.mark.parametrize(
    "content",
    [b"", b"Tool,Result\nQA,PASS\n", b"Tool,Check,Result,Threshold,Actual,Notes\n"],
)
def test_invalid_or_empty_qa_csv_is_rejected(content):
    with pytest.raises(QASummaryError):
        parse_qa_summary(
            content,
            scene_id=SCENE_ID,
            artifact_uri=SUMMARY_URL,
            product_metadata={},
        )


def test_oversized_qa_csv_is_rejected():
    with pytest.raises(QASummaryError, match="size limit"):
        parse_qa_summary(
            b"x" * (MAX_QA_SUMMARY_BYTES + 1),
            scene_id=SCENE_ID,
            artifact_uri=SUMMARY_URL,
            product_metadata={},
        )


def test_read_qa_summary_fetches_the_canonical_product_artifact(monkeypatch):
    content = _csv(("Input opens", "PASS", ""), ("Identification", "FAIL", ""))
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
            opened.update(url=url, mode=mode, block_size=block_size, cache_type=cache_type)
            return Stream()

    monkeypatch.setattr(
        "echo.qa._validated_product",
        lambda _feature: (
            SCENE_ID,
            f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/{SCENE_ID}/{SCENE_ID}.h5",
            "LSAR",
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "earthaccess",
        SimpleNamespace(
            login=lambda **_kwargs: SimpleNamespace(authenticated=True),
            get_fsspec_https_session=lambda: FileSystem(),
        ),
    )

    record = read_qa_summary(
        {},
        product_metadata={
            "instrumentName": "LSAR",
            "listOfObservationModes": ["(NOT SPECIFIED)"],
        },
        software_version="17.2.0",
    )

    assert opened == {
        "url": SUMMARY_URL,
        "mode": "rb",
        "block_size": 16 * 1024,
        "cache_type": "bytes",
    }
    assert record.evidence.status == "FAIL"
    assert record.artifact_sha256 == hashlib.sha256(content).hexdigest()
    assert record.evidence.artifact_retrieval["network_retrieval"] is True
    assert (
        record.evidence.identification_crosscheck["status"]
        == "MATCHING_FAILURE_RULES_FOUND"
    )
