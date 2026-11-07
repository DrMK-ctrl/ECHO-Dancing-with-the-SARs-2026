"""Bounded retrieval and metadata extraction for canonical ASF QA reports."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import re
from typing import Any
from urllib.parse import urlsplit

from echo.nisar_access import (
    NisarAccessError,
    _install_read_budget,
)
from echo.qa import crosscheck_identification_metadata


MAX_QA_REPORT_BYTES = 5 * 1024 * 1024
QA_REPORT_RANGE_BYTES = 1024 * 1024
MAX_QA_REPORT_PAGES = 20
MAX_QA_REPORT_FIRST_PAGE_CHARS = 64 * 1024
ASF_HOST = "nisar.asf.earthdatacloud.nasa.gov"
_ASF_COLLECTIONS = {
    "NISAR_L2_GCOV_BETA_V1": "GCOV",
    "NISAR_L2_GCOV_PROVISIONAL_V1": "GCOV",
    "NISAR_L2_GCOV_V1": "GCOV",
    "NISAR_L2_GUNW_PROVISIONAL_V1": "GUNW",
    "NISAR_L2_GUNW_V1": "GUNW",
}

_REPORT_METADATA_FIELDS = (
    "absoluteOrbitNumber",
    "compositeReleaseId",
    "diagnosticModeFlag",
    "epsg",
    "frameNumber",
    "hasInputDataException",
    "instrumentName",
    "isDithered",
    "isFullFrame",
    "isGeocoded",
    "isJointObservation",
    "isMixedMode",
    "isUrgentObservation",
    "listOfFrequencies",
    "listOfObservationModes",
    "lookDirection",
    "missionId",
    "orbitPassDirection",
    "platformName",
    "processingCenter",
    "processingDateTime",
    "processingType",
    "productDoi",
    "productLevel",
    "productSpecificationVersion",
    "productType",
    "productVersion",
    "radarBand",
    "referenceAbsoluteOrbitNumber",
    "referenceHasInputDataException",
    "referenceIsJointObservation",
    "referenceListOfObservationModes",
    "referenceZeroDopplerEndTime",
    "referenceZeroDopplerStartTime",
    "secondaryAbsoluteOrbitNumber",
    "secondaryHasInputDataException",
    "secondaryIsJointObservation",
    "secondaryListOfObservationModes",
    "secondaryZeroDopplerEndTime",
    "secondaryZeroDopplerStartTime",
    "softwareVersion",
    "trackNumber",
    "zeroDopplerEndTime",
    "zeroDopplerStartTime",
)
_REQUIRED_GCOV_METADATA_FIELDS = {
    "absoluteOrbitNumber",
    "frameNumber",
    "instrumentName",
    "listOfObservationModes",
    "productSpecificationVersion",
    "productVersion",
    "trackNumber",
}
_REQUIRED_GUNW_150_METADATA_FIELDS = {
    "compositeReleaseId",
    "frameNumber",
    "instrumentName",
    "listOfFrequencies",
    "lookDirection",
    "missionId",
    "orbitPassDirection",
    "productSpecificationVersion",
    "productType",
    "productVersion",
    "radarBand",
    "referenceAbsoluteOrbitNumber",
    "referenceListOfObservationModes",
    "referenceZeroDopplerEndTime",
    "referenceZeroDopplerStartTime",
    "secondaryAbsoluteOrbitNumber",
    "secondaryListOfObservationModes",
    "secondaryZeroDopplerEndTime",
    "secondaryZeroDopplerStartTime",
    "trackNumber",
}
_LIST_FIELDS = {
    "listOfFrequencies",
    "listOfObservationModes",
    "referenceListOfObservationModes",
    "secondaryListOfObservationModes",
}
_INTEGER_FIELDS = {
    "absoluteOrbitNumber",
    "diagnosticModeFlag",
    "epsg",
    "frameNumber",
    "hasInputDataException",
    "referenceAbsoluteOrbitNumber",
    "referenceHasInputDataException",
    "secondaryAbsoluteOrbitNumber",
    "secondaryHasInputDataException",
    "trackNumber",
}
_BOOLEAN_FIELDS = {
    "isDithered",
    "isFullFrame",
    "isGeocoded",
    "isJointObservation",
    "isMixedMode",
    "isUrgentObservation",
}


class QAReportError(ValueError):
    """Raised when an ASF QA report cannot be safely retrieved or parsed."""


def _canonical_report_uri(feature: dict[str, Any]) -> tuple[str, str]:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise QAReportError("catalog feature has no properties object")
    scene_id = properties.get("fileID")
    product_url = properties.get("url")
    collection = properties.get("collectionName")
    product_type = _ASF_COLLECTIONS.get(collection)
    if (
        not isinstance(scene_id, str)
        or not isinstance(product_url, str)
        or product_type is None
        or properties.get("processingLevel") != product_type
        or not re.fullmatch(rf"NISAR_L2_PR_{product_type}_[A-Z0-9_]+", scene_id)
    ):
        raise QAReportError("catalog feature is not a supported ASF NISAR GCOV or GUNW product")
    try:
        parsed = urlsplit(product_url)
        path = tuple(part for part in parsed.path.split("/") if part)
    except ValueError as exc:
        raise QAReportError("catalog product URL is malformed") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != ASF_HOST
        or parsed.netloc not in {ASF_HOST, f"{ASF_HOST}:443"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or path != ("NISAR", collection, scene_id, f"{scene_id}.h5")
    ):
        raise QAReportError("catalog product URL is not a canonical ASF NISAR product")
    report_uri = (
        f"https://{ASF_HOST}/NISAR/{collection}/{scene_id}/"
        f"{scene_id}_QA_REPORT.pdf"
    )
    return scene_id, report_uri


def _validate_report_uri(artifact_uri: str, scene_id: str) -> None:
    try:
        parsed = urlsplit(artifact_uri)
    except ValueError as exc:
        raise QAReportError("QA report URI is malformed") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname != ASF_HOST
        or parsed.netloc not in {ASF_HOST, f"{ASF_HOST}:443"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or len(tuple(part for part in parsed.path.split("/") if part)) != 4
    ):
        raise QAReportError("QA report URI does not identify a canonical ASF NISAR product")
    parts = tuple(part for part in parsed.path.split("/") if part)
    collection = parts[1]
    product_type = _ASF_COLLECTIONS.get(collection)
    if (
        product_type is None
        or parts[0] != "NISAR"
        or parts[2] != scene_id
        or parts[3] != f"{scene_id}_QA_REPORT.pdf"
        or not re.fullmatch(rf"NISAR_L2_PR_{product_type}_[A-Z0-9_]+", scene_id)
    ):
        raise QAReportError("QA report URI does not identify this ASF NISAR product")


def _metadata_value(raw_value: str, field: str) -> Any:
    value = raw_value.strip()
    if not value or len(value) > 4096:
        raise QAReportError(f"QA report metadata value is empty or oversized: {field}")
    if field in _LIST_FIELDS:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise QAReportError(f"QA report list metadata is malformed: {field}") from exc
        if (
            not isinstance(parsed, list)
            or len(parsed) > 32
            or any(not isinstance(item, str) for item in parsed)
        ):
            raise QAReportError(f"QA report list metadata has an invalid shape: {field}")
        return parsed
    if field in _INTEGER_FIELDS:
        try:
            return int(value)
        except ValueError as exc:
            raise QAReportError(f"QA report integer metadata is malformed: {field}") from exc
    if field in _BOOLEAN_FIELDS:
        if value not in {"True", "False"}:
            raise QAReportError(f"QA report boolean metadata is malformed: {field}")
        return value == "True"
    return value


def _extract_labeled_value(text: str, label: str) -> str | None:
    match = re.search(
        rf"(?m)^\s*{re.escape(label)}\s*:\s*(?P<value>[^\r\n]+?)\s*$",
        text,
    )
    return match.group("value").strip() if match else None


def _extract_report_metadata(text: str) -> tuple[dict[str, Any], dict[str, str]]:
    metadata: dict[str, Any] = {}
    raw_metadata: dict[str, str] = {}
    for field in _REPORT_METADATA_FIELDS:
        match = re.search(
            rf"(?m)^\s*{re.escape(field)}\s{{2,}}(?P<value>[^\r\n]+?)\s*$",
            text,
        )
        if not match:
            continue
        raw_value = match.group("value").strip()
        raw_metadata[field] = raw_value
        metadata[field] = _metadata_value(raw_value, field)
    return metadata, raw_metadata


def parse_qa_report(
    content: bytes,
    *,
    scene_id: str,
    artifact_uri: str,
    catalog_properties: dict[str, Any],
    retrieved_at: datetime | None = None,
    retrieval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Parse the identity and processing metadata on one canonical ASF QA PDF.

    This report parser does not derive or override the provider's QA disposition.
    The CSV summary remains the source of aggregate check results.
    """
    if not isinstance(content, bytes) or not content:
        raise QAReportError("QA report is empty or is not bytes")
    if len(content) > MAX_QA_REPORT_BYTES:
        raise QAReportError("QA report exceeds the configured size limit")
    _validate_report_uri(artifact_uri, scene_id)
    if not isinstance(catalog_properties, dict):
        raise QAReportError("catalog properties must be an object")

    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content), strict=True)
        if reader.is_encrypted:
            raise QAReportError("encrypted QA reports are not supported")
        page_count = len(reader.pages)
        if not 1 <= page_count <= MAX_QA_REPORT_PAGES:
            raise QAReportError("QA report page count is outside the supported bounds")
        text = reader.pages[0].extract_text(extraction_mode="layout") or ""
    except QAReportError:
        raise
    except ImportError as exc:
        raise QAReportError("QA report parsing requires the 'nisar' optional dependencies") from exc
    except Exception as exc:
        raise QAReportError(f"QA report could not be parsed ({type(exc).__name__})") from exc

    if not text or len(text) > MAX_QA_REPORT_FIRST_PAGE_CHARS:
        raise QAReportError("QA report first page text is empty or exceeds the configured limit")
    compact_text = re.sub(r"\s+", "", text)
    if "NISARQualityAssurance(QA)Report" not in compact_text:
        raise QAReportError("PDF is not a recognizable NISAR QA report")
    if re.sub(r"\s+", "", scene_id) not in compact_text:
        raise QAReportError("QA report granule ID does not match the requested scene")

    software_version = _extract_labeled_value(text, "QA Software Version")
    processing_time = _extract_labeled_value(text, "QA Processing Date")
    if not software_version or not processing_time:
        raise QAReportError("QA report is missing its software version or processing time")
    if processing_time.endswith(" UTC"):
        processing_time = processing_time[:-4] + "Z"
    try:
        parsed_processing_time = datetime.fromisoformat(
            processing_time.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise QAReportError("QA report processing time is malformed") from exc
    if parsed_processing_time.tzinfo is None:
        raise QAReportError("QA report processing time has no timezone")

    metadata, raw_metadata = _extract_report_metadata(text)
    report_path = tuple(part for part in urlsplit(artifact_uri).path.split("/") if part)
    collection = report_path[1]
    product_type = _ASF_COLLECTIONS[collection]
    if product_type == "GCOV":
        required_fields = _REQUIRED_GCOV_METADATA_FIELDS
        contract_status = "SUPPORTED_PRODUCT_CONTRACT"
    elif product_type == "GUNW" and metadata.get("productSpecificationVersion") == "1.5.0":
        required_fields = _REQUIRED_GUNW_150_METADATA_FIELDS
        contract_status = "SUPPORTED_PRODUCT_CONTRACT"
    else:
        required_fields = set()
        contract_status = "UNSUPPORTED_PRODUCT_SPECIFICATION"
    missing_fields = sorted(required_fields - metadata.keys())
    source_crosscheck = crosscheck_identification_metadata(
        metadata, software_version=software_version
    )
    orbit = catalog_properties.get("orbit")
    path = catalog_properties.get("pathNumber")
    frame = catalog_properties.get("frameNumber")
    catalog_crosschecks = {
        "track_matches_catalog_path": (
            metadata.get("trackNumber") == path
            if "trackNumber" in metadata and path is not None
            else None
        ),
        "frame_matches_catalog": (
            metadata.get("frameNumber") == frame
            if "frameNumber" in metadata and frame is not None
            else None
        ),
    }
    if product_type == "GUNW":
        catalog_crosschecks["reference_absolute_orbit_matches_catalog_orbit"] = (
            metadata.get("referenceAbsoluteOrbitNumber") == orbit
            if "referenceAbsoluteOrbitNumber" in metadata and orbit is not None
            else None
        )
    else:
        catalog_crosschecks["absolute_orbit_matches_catalog"] = (
            metadata.get("absoluteOrbitNumber") == orbit
            if "absoluteOrbitNumber" in metadata and orbit is not None
            else None
        )
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise QAReportError("QA report retrieval timestamp must include a timezone")

    return {
        "schema_version": 1,
        "scene_id": scene_id,
        "artifact_uri": artifact_uri,
        "artifact_sha256": hashlib.sha256(content).hexdigest(),
        "artifact_size_bytes": len(content),
        "retrieved_at_utc": retrieved_at.astimezone(timezone.utc).isoformat(),
        "retrieval": retrieval or {"method": "provided_bytes", "network_retrieval": False},
        "report_page_count": page_count,
        "report_processing_time_utc": parsed_processing_time.astimezone(timezone.utc).isoformat(),
        "qa_software_version": software_version,
        "product_metadata": metadata,
        "product_metadata_raw": raw_metadata,
        "product_contract_status": contract_status,
        "required_metadata_fields": sorted(required_fields),
        "missing_required_metadata": missing_fields,
        "report_parse_status": (
            "INCOMPLETE"
            if contract_status != "SUPPORTED_PRODUCT_CONTRACT"
            else "COMPLETE" if not missing_fields else "INCOMPLETE"
        ),
        "catalog_crosschecks": catalog_crosschecks,
        "identification_crosscheck": source_crosscheck,
        "provider_qa_disposition": "NOT_IN_REPORT_PDF",
    }


def read_qa_report(feature: dict[str, Any]) -> dict[str, Any]:
    """Retrieve one canonical ASF QA report PDF with a strict byte budget."""
    try:
        scene_id, artifact_uri = _canonical_report_uri(feature)
        properties = feature["properties"]
        import earthaccess
        from aiohttp import ClientTimeout

        auth = earthaccess.login(strategy="netrc", persist=False)
        if not auth.authenticated:
            raise QAReportError("Earthdata Login is not authenticated")
        filesystem = earthaccess.get_fsspec_https_session()
        client_kwargs = dict(filesystem.client_kwargs)
        client_kwargs["timeout"] = ClientTimeout(total=30, connect=10, sock_read=20)
        filesystem.client_kwargs = client_kwargs
        with filesystem.open(
            artifact_uri,
            "rb",
            block_size=QA_REPORT_RANGE_BYTES,
            cache_type="bytes",
        ) as stream:
            cache = _install_read_budget(stream, limit_bytes=MAX_QA_REPORT_BYTES)
            content = stream.read(MAX_QA_REPORT_BYTES + 1)
    except QAReportError:
        raise
    except (ImportError, NisarAccessError) as exc:
        raise QAReportError(str(exc)) from exc
    except Exception as exc:
        raise QAReportError(
            f"ASF QA report retrieval failed ({type(exc).__name__})"
        ) from exc

    return parse_qa_report(
        content,
        scene_id=scene_id,
        artifact_uri=artifact_uri,
        catalog_properties=properties,
        retrieval={
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "HTTPS byte-range streaming",
            "fsspec_range_bytes_requested": int(cache.total_requested_bytes),
            "maximum_range_bytes": MAX_QA_REPORT_BYTES,
            "network_retrieval": True,
        },
    )
