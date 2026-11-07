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
_NISARQA_IDENTIFICATION_SOURCES = {
    "17.0.0": {
        "repository": "https://github.com/isce-framework/nisarqa",
        "version": "17.0.0",
        "commit": "1caca75a4b76ef8ab9c967a1770b32428e1a4733",
        "path": "src/nisarqa/validate/sanity_checks.py",
        "url": "https://github.com/isce-framework/nisarqa/blob/v17.0.0/src/nisarqa/validate/sanity_checks.py",
    },
    "17.2.0": {
        "repository": "https://github.com/isce-framework/nisarqa",
        "version": "17.2.0",
        "commit": "4d40bbcf9864d006c5e2656b0b9901caa51c95bf",
        "path": "src/nisarqa/validate/sanity_checks.py",
        "url": "https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py",
    },
}


class QASummaryError(ValueError):
    """Raised when an ASF QA summary cannot be safely retrieved or parsed."""


def crosscheck_identification_metadata(
    product_metadata: dict[str, Any], *, software_version: str | None
) -> dict[str, Any]:
    """Find values matching selected rules in a supported nisarqa source version.

    This deliberately checks only two field rules. It does not reproduce the
    provider's full identification checks or identify the exact rows that caused
    a product's aggregate QA result.
    """
    validator = _NISARQA_IDENTIFICATION_SOURCES.get(software_version or "")
    if validator is None:
        status = "VERSION_UNKNOWN" if not software_version else "UNSUPPORTED_VERSION"
        return {
            "status": status,
            "scope": "partial source cross-check; no provider failure attribution",
            "validator": {"software_version": software_version},
            "findings": [],
        }

    findings: list[dict[str, Any]] = []
    instrument = product_metadata.get("instrumentName")
    if instrument is not None and (
        not isinstance(instrument, str) or instrument not in {"L-SAR", "S-SAR"}
    ):
        findings.append(
            {
                "field": "instrumentName",
                "observed_value": instrument,
                "rule": f"nisarqa v{software_version} accepts L-SAR or S-SAR",
                "result": "SOURCE_RULE_MISMATCH",
            }
        )

    modes = product_metadata.get("listOfObservationModes")
    if isinstance(modes, list):
        for index, mode in enumerate(modes):
            if isinstance(mode, str) and mode.strip().upper() == "(NOT SPECIFIED)":
                findings.append(
                    {
                        "field": "listOfObservationModes",
                        "index": index,
                        "observed_value": mode,
                        "rule": (
                            f"nisarqa v{software_version} requires a formatted "
                            "NISAR observation-mode string"
                        ),
                        "result": "SOURCE_RULE_MISMATCH",
                    }
                )

    return {
        "status": (
            "MATCHING_FAILURE_RULES_FOUND"
            if findings
            else "NO_MATCH_IN_CHECKED_RULES"
        ),
        "scope": "partial source cross-check; not a provider per-field QA result",
        "validator": dict(validator),
        "checked_rules": ["instrumentName allowlist", "observation-mode placeholder"],
        "findings": findings,
    }


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
        identification_crosscheck=crosscheck_identification_metadata(
            product_metadata, software_version=software_version
        ),
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
    feature: dict[str, Any],
    *,
    product_metadata: dict[str, Any],
    software_version: str | None = None,
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
        software_version=software_version,
        retrieval={
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "HTTPS byte-range streaming",
            "fsspec_range_bytes_requested": int(cache.total_requested_bytes),
            "maximum_range_bytes": MAX_QA_SUMMARY_BYTES,
            "network_retrieval": True,
        },
    )
