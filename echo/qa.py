"""Bounded retrieval and provenance-preserving parsing of ASF QA summaries."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from io import StringIO
from typing import Any
from urllib.parse import urlsplit

from echo.analysis import QAEvidence
from echo.nisar_access import (
    NisarAccessError,
    _install_read_budget,
    _validated_product,
)


MAX_QA_SUMMARY_BYTES = 64 * 1024
QA_SUMMARY_RANGE_BYTES = 16 * 1024
_QA_HEADERS = {"Tool", "Check", "Result", "Threshold", "Actual", "Notes"}
_RESULT_NORMALIZATION = {
    "PASS": "PASS",
    "FAIL": "FAIL",
    "SKIP": "SKIPPED",
    "SKIPPED": "SKIPPED",
    "WARNING": "WARNING",
    "NOT_RUN": "NOT_RUN",
}
_REQUIRED_CHECKS = {
    "Able to open input NISAR file?",
    "Coordinate grid metadata cubes are valid?",
    "Calibration information LUTs are valid?",
    "Passes all `identification` group checks?",
    "QA completed with no exceptions?",
}


class QASummaryError(ValueError):
    """Raised when an ASF QA summary cannot be safely retrieved or parsed."""


@dataclass(frozen=True)
class QASummaryRecord:
    scene_id: str
    artifact_uri: str
    artifact_sha256: str
    artifact_size_bytes: int
    retrieved_at_utc: str
    retrieval: dict[str, Any]
    evidence: QAEvidence


def parse_qa_summary(
    content: bytes,
    *,
    scene_id: str,
    artifact_uri: str,
    product_metadata: dict[str, Any],
    retrieved_at: datetime | None = None,
    software_version: str | None = None,
    retrieval: dict[str, Any] | None = None,
) -> QASummaryRecord:
    """Parse one bounded CSV while preserving every provider check row."""
    if not isinstance(content, bytes) or not content:
        raise QASummaryError("QA summary is empty or is not bytes")
    if len(content) > MAX_QA_SUMMARY_BYTES:
        raise QASummaryError("QA summary exceeds the configured size limit")
    if not isinstance(artifact_uri, str) or not artifact_uri.startswith("https://"):
        raise QASummaryError("QA summary source URI must be HTTPS")
    parsed_uri = urlsplit(artifact_uri)
    if (
        parsed_uri.hostname != "nisar.asf.earthdatacloud.nasa.gov"
        or parsed_uri.netloc != "nisar.asf.earthdatacloud.nasa.gov"
        or parsed_uri.username is not None
        or parsed_uri.password is not None
        or parsed_uri.query
        or parsed_uri.fragment
        or not parsed_uri.path.endswith(f"/{scene_id}/{scene_id}_QA_SUMMARY.csv")
    ):
        raise QASummaryError("QA summary URI does not identify this ASF product")
    if not isinstance(product_metadata, dict):
        raise QASummaryError("product identification metadata must be an object")
    try:
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(decoded, newline=""))
        headers = set(reader.fieldnames or [])
        if not _QA_HEADERS.issubset(headers):
            raise QASummaryError("QA summary is missing required CSV columns")
        rows: list[dict[str, str]] = []
        checks: dict[str, str] = {}
        for index, row in enumerate(reader, start=1):
            tool = (row.get("Tool") or "").strip()
            check = (row.get("Check") or "").strip()
            result = (row.get("Result") or "").strip().upper()
            if tool != "QA" or not check:
                raise QASummaryError("QA summary contains an invalid check row")
            disposition = _RESULT_NORMALIZATION.get(result)
            if disposition is None:
                disposition = "UNKNOWN"
            row_record = {
                key.lower(): (row.get(key) or "").strip()
                for key in ("Tool", "Check", "Result", "Threshold", "Actual", "Notes")
            }
            rows.append(row_record)
            checks[f"{index}:{check}"] = disposition
        if not rows:
            raise QASummaryError("QA summary has no check rows")
    except (UnicodeDecodeError, csv.Error) as exc:
        raise QASummaryError("QA summary is not a valid UTF-8 CSV") from exc

    present_checks = {row["check"] for row in rows}
    required_checks_missing = bool(_REQUIRED_CHECKS - present_checks)
    if any(disposition == "FAIL" for disposition in checks.values()):
        status = "FAIL"
    elif not required_checks_missing and all(
        disposition == "PASS" for disposition in checks.values()
    ):
        status = "PASS"
    else:
        status = "INDETERMINATE"

    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise QASummaryError("QA retrieval timestamp must include a timezone")
    retrieved_at_utc = retrieved_at.astimezone(timezone.utc).isoformat()
    digest = hashlib.sha256(content).hexdigest()
    evidence = QAEvidence(
        scene_id=scene_id,
        status=status,
        artifact_uri=artifact_uri,
        artifact_sha256=digest,
        checks=checks,
        software_version=software_version,
        product_metadata=product_metadata,
        check_details=rows,
        retrieved_at_utc=retrieved_at_utc,
        artifact_retrieval=retrieval,
    )
    return QASummaryRecord(
        scene_id=scene_id,
        artifact_uri=artifact_uri,
        artifact_sha256=digest,
        artifact_size_bytes=len(content),
        retrieved_at_utc=retrieved_at_utc,
        retrieval=retrieval or {"method": "provided_bytes", "network_retrieval": False},
        evidence=evidence,
    )


def read_qa_summary(
    feature: dict[str, Any], *, product_metadata: dict[str, Any]
) -> QASummaryRecord:
    """Retrieve the product's canonical ASF QA summary with strict byte limits."""
    scene_id, product_url, _instrument = _validated_product(feature)
    artifact_uri = (
        product_url.rsplit("/", 1)[0] + f"/{scene_id}_QA_SUMMARY.csv"
    )
    try:
        import earthaccess
        from aiohttp import ClientTimeout

        auth = earthaccess.login(strategy="netrc", persist=False)
        if not auth.authenticated:
            raise QASummaryError("Earthdata Login is not authenticated")
        filesystem = earthaccess.get_fsspec_https_session()
        client_kwargs = dict(filesystem.client_kwargs)
        client_kwargs["timeout"] = ClientTimeout(total=25, connect=10, sock_read=20)
        filesystem.client_kwargs = client_kwargs
        with filesystem.open(
            artifact_uri,
            "rb",
            block_size=QA_SUMMARY_RANGE_BYTES,
            cache_type="bytes",
        ) as stream:
            cache = _install_read_budget(stream, limit_bytes=MAX_QA_SUMMARY_BYTES)
            content = stream.read(MAX_QA_SUMMARY_BYTES + 1)
    except QASummaryError:
        raise
    except (ImportError, NisarAccessError) as exc:
        raise QASummaryError(str(exc)) from exc
    except Exception as exc:
        raise QASummaryError(
            f"ASF QA summary retrieval failed ({type(exc).__name__})"
        ) from exc

    return parse_qa_summary(
        content,
        scene_id=scene_id,
        artifact_uri=artifact_uri,
        product_metadata=product_metadata,
        retrieval={
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "HTTPS byte-range streaming",
            "fsspec_range_bytes_requested": int(cache.total_requested_bytes),
            "maximum_range_bytes": MAX_QA_SUMMARY_BYTES,
            "network_retrieval": True,
        },
    )
