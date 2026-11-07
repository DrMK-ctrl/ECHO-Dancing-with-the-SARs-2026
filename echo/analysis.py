"""Evidence-gated, provenance-recording analysis of paired GCOV windows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import re
import sys
from typing import Any

import numpy as np

from echo.nisar_access import IDENTIFICATION_FIELDS, GcovWindow
from echo.science import (
    ChangeField,
    gamma0_log_ratio_db,
    strict_common_gcov_mask,
)


class AnalysisGateError(ValueError):
    """Raised when a pair does not meet the declared analysis preconditions."""


@dataclass(frozen=True)
class QAEvidence:
    """Reviewed product QA disposition linked to its source artifact.

    This carries a reviewed record into a run manifest. It does not run the
    provider's QA software or verify the referenced artifact bytes.
    """

    scene_id: str
    status: str
    artifact_uri: str
    artifact_sha256: str
    checks: dict[str, str]
    software_version: str | None
    product_metadata: dict[str, Any]
    check_details: list[dict[str, str]] | None = None
    retrieved_at_utc: str | None = None
    artifact_retrieval: dict[str, Any] | None = None
    identification_crosscheck: dict[str, Any] | None = None


@dataclass(frozen=True)
class GcovPairMeasurement:
    """Descriptive change field, common mask, and its provenance manifest."""

    change: ChangeField
    common_valid_mask: np.ndarray
    manifest: dict[str, Any]


_POWER_LAYERS = {"HHHH", "HVHV", "VVVV", "VHVH", "RHRH", "RVRV"}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMPATIBILITY_FIELDS = (
    "collectionName",
    "processingLevel",
    "crid",
    "productionConfiguration",
    "pathNumber",
    "frameNumber",
    "flightDirection",
    "mainBandPolarization",
    "sideBandPolarization",
    "rangeBandwidth",
)


def _echo_version() -> str:
    try:
        return version("echo-sar-investigation")
    except PackageNotFoundError:
        return "uninstalled"


def _dependency_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "not-installed"


def _canonical_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        items = [_canonical_value(item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, sort_keys=True))
    return value


def _catalog_time(window: GcovWindow, field: str) -> datetime:
    value = window.catalog_metadata.get(field)
    if not isinstance(value, str):
        raise AnalysisGateError(f"catalog {field} is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AnalysisGateError(f"catalog {field} is invalid") from exc
    if parsed.tzinfo is None:
        raise AnalysisGateError(f"catalog {field} has no timezone")
    return parsed.astimezone(timezone.utc)


def _validate_qa(
    window: GcovWindow, evidence: QAEvidence, *, frequency: str
) -> None:
    if evidence.scene_id != window.scene_id:
        raise AnalysisGateError("QA evidence scene does not match its GCOV window")
    if evidence.status != "PASS":
        raise AnalysisGateError(
            f"analysis requires PASS QA evidence; {window.scene_id} is {evidence.status}"
        )
    if not isinstance(evidence.artifact_uri, str) or not evidence.artifact_uri.strip():
        raise AnalysisGateError("QA evidence artifact reference is missing")
    if not isinstance(evidence.artifact_sha256, str) or not _SHA256.fullmatch(
        evidence.artifact_sha256
    ):
        raise AnalysisGateError("QA evidence artifact SHA-256 is missing or malformed")
    if not isinstance(evidence.checks, dict) or not evidence.checks:
        raise AnalysisGateError("QA evidence has no per-check dispositions")
    allowed_checks = {"PASS", "FAIL", "SKIPPED", "NOT_RUN", "WARNING"}
    if any(
        not isinstance(status, str) or status not in allowed_checks
        for status in evidence.checks.values()
    ):
        raise AnalysisGateError("QA evidence contains an unknown check status")
    if evidence.status == "PASS" and any(
        status == "FAIL" for status in evidence.checks.values()
    ):
        raise AnalysisGateError("overall QA PASS conflicts with a failed QA check")
    metadata = evidence.product_metadata
    instrument = metadata.get("instrumentName")
    if not isinstance(instrument, str) or instrument not in {"L-SAR", "S-SAR"}:
        raise AnalysisGateError("product identification has an invalid instrumentName")
    modes = metadata.get("listOfObservationModes")
    if not isinstance(modes, list) or not modes or any(
        not isinstance(mode, str) or _is_placeholder(mode) for mode in modes
    ):
        raise AnalysisGateError("product identification has missing or placeholder observation modes")
    for field in ("productVersion", "productSpecificationVersion"):
        value = metadata.get(field)
        if not isinstance(value, str) or _is_placeholder(value):
            raise AnalysisGateError(f"product identification is missing {field}")
    frequencies = metadata.get("listOfFrequencies")
    if (
        not isinstance(frequencies, list)
        or frequency not in frequencies
        or any(not isinstance(item, str) or _is_placeholder(item) for item in frequencies)
    ):
        raise AnalysisGateError("product identification does not verify the selected frequency")


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().upper()
    return not normalized or normalized in {
        "NONE",
        "NULL",
        "N/A",
        "NOT SPECIFIED",
        "(NOT SPECIFIED)",
        "UNDEFINED",
    }


def _validate_pair_compatibility(before: GcovWindow, after: GcovWindow) -> None:
    for window in (before, after):
        if window.catalog_metadata.get("fileID") != window.scene_id:
            raise AnalysisGateError("catalog product identifier does not match the GCOV window")
        if not isinstance(window.product_url, str) or not window.product_url.strip():
            raise AnalysisGateError("source product URL is missing")
    if before.frequency != after.frequency:
        raise AnalysisGateError("paired windows use different frequencies")
    if (
        before.row_start != after.row_start
        or before.row_stop != after.row_stop
        or before.column_start != after.column_start
        or before.column_stop != after.column_stop
    ):
        raise AnalysisGateError("paired windows use different array index bounds")

    for field in _COMPATIBILITY_FIELDS:
        before_value = before.catalog_metadata.get(field)
        after_value = after.catalog_metadata.get(field)
        if before_value is None or after_value is None:
            raise AnalysisGateError(f"catalog compatibility metadata is missing: {field}")
        if _canonical_value(before_value) != _canonical_value(after_value):
            raise AnalysisGateError(f"paired products differ in {field}")

    before_orbit = before.catalog_metadata.get("orbit")
    after_orbit = after.catalog_metadata.get("orbit")
    if before_orbit is None or after_orbit is None or before_orbit == after_orbit:
        raise AnalysisGateError("paired windows must come from distinct known NISAR orbits")
    before_start = _catalog_time(before, "startTime")
    before_stop = _catalog_time(before, "stopTime")
    after_start = _catalog_time(after, "startTime")
    after_stop = _catalog_time(after, "stopTime")
    if before_stop <= before_start or after_stop <= after_start:
        raise AnalysisGateError("catalog acquisition interval is invalid")
    if before_stop >= after_start:
        raise AnalysisGateError("after acquisition must begin after before acquisition ends")

    before_grid = before.grid_metadata
    after_grid = after.grid_metadata
    before_epsg = before_grid.get("projection_attributes", {}).get("epsg_code")
    after_epsg = after_grid.get("projection_attributes", {}).get("epsg_code")
    if before_epsg is None or after_epsg is None:
        raise AnalysisGateError("paired window CRS metadata is missing")
    if before_epsg != after_epsg:
        raise AnalysisGateError("paired windows use different coordinate reference systems")
    if before_grid.get("projection_value") != after_grid.get("projection_value"):
        raise AnalysisGateError("paired windows have different projection values")
    for axis in ("x_coordinates", "y_coordinates"):
        left = np.asarray(before_grid.get(axis))
        right = np.asarray(after_grid.get(axis))
        if left.size == 0 or right.size == 0 or not np.array_equal(left, right):
            raise AnalysisGateError(f"paired windows do not share identical {axis}")


def _array_digest(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        canonical = np.ascontiguousarray(array)
        digest.update(str(canonical.dtype).encode("ascii"))
        digest.update(json.dumps(canonical.shape).encode("ascii"))
        digest.update(canonical.tobytes(order="C"))
    return digest.hexdigest()


def _window_digest(window: GcovWindow) -> str:
    digest = hashlib.sha256()
    for name in sorted(window.layers):
        digest.update(name.encode("utf-8"))
        digest.update(_array_digest(np.asarray(window.layers[name])).encode("ascii"))
    for axis in ("x_coordinates", "y_coordinates"):
        digest.update(axis.encode("ascii"))
        digest.update(
            _array_digest(np.asarray(window.grid_metadata[axis])).encode("ascii")
        )
    return digest.hexdigest()


def _look_count_summary(window: GcovWindow, common_mask: np.ndarray) -> dict[str, Any]:
    values = np.asarray(window.layers["numberOfLooks"])
    if values.shape != common_mask.shape or np.iscomplexobj(values):
        raise AnalysisGateError("numberOfLooks layer is incompatible with the common mask")
    selected = common_mask & np.isfinite(values) & (values > 0)
    if not np.array_equal(selected, common_mask):
        raise AnalysisGateError("numberOfLooks is missing on common-valid samples")
    selected_values = values[selected].astype(np.float64, copy=False)
    if selected_values.size == 0:
        return {"sample_count": 0, "median": None, "lower_quartile": None, "upper_quartile": None}
    lower, median, upper = np.quantile(selected_values, (0.25, 0.5, 0.75))
    return {
        "sample_count": int(selected_values.size),
        "median": float(median),
        "lower_quartile": float(lower),
        "upper_quartile": float(upper),
    }


def analyze_gcov_pair(
    before: GcovWindow,
    after: GcovWindow,
    *,
    before_qa: QAEvidence,
    after_qa: QAEvidence,
    layer: str = "HHHH",
    generated_at: datetime | None = None,
) -> GcovPairMeasurement:
    """Measure signed gamma0 log ratio after strict QA and exact-grid gates.

    This is a descriptive measurement only. It makes no event classification,
    causal attribution, statistical-significance claim, or confidence estimate.
    """
    if layer not in _POWER_LAYERS:
        raise AnalysisGateError("measurement layer must be a real diagonal GCOV power term")
    _validate_qa(before, before_qa, frequency=before.frequency)
    _validate_qa(after, after_qa, frequency=after.frequency)
    _validate_pair_compatibility(before, after)

    required_layers = {layer, "mask", "numberOfLooks", "inputDataExceptionMask"}
    for scene in (before, after):
        missing = required_layers.difference(scene.layers)
        if missing:
            raise AnalysisGateError(
                f"GCOV window is missing required layers: {', '.join(sorted(missing))}"
            )
        power = np.asarray(scene.layers[layer])
        if not np.issubdtype(power.dtype, np.number) or np.iscomplexobj(power):
            raise AnalysisGateError("selected GCOV power layer must contain real numeric values")
    try:
        masks = strict_common_gcov_mask(
            before.layers["mask"],
            after.layers["mask"],
            before.layers["inputDataExceptionMask"],
            after.layers["inputDataExceptionMask"],
        )
    except ValueError as exc:
        raise AnalysisGateError(f"GCOV quality masks are unusable: {exc}") from exc

    try:
        change = gamma0_log_ratio_db(
            before.layers[layer], after.layers[layer], masks.common_valid_mask
        )
    except ValueError as exc:
        raise AnalysisGateError(f"GCOV power arrays are unusable: {exc}") from exc
    if change.valid_count == 0:
        raise AnalysisGateError("no positive finite power samples remain for the paired window")

    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        raise AnalysisGateError("analysis timestamp must include a timezone")
    generated_at = generated_at.astimezone(timezone.utc)
    valid_mask = change.valid_mask
    measurement_sha256 = _array_digest(change.values_db, valid_mask)
    common_mask_sha256 = _array_digest(masks.common_valid_mask)
    before_look_summary = _look_count_summary(before, masks.common_valid_mask)
    after_look_summary = _look_count_summary(after, masks.common_valid_mask)
    source_metadata_missing = {}
    catalog_metadata_missing = {}
    for role, scene, qa in (
        ("before", before, before_qa),
        ("after", after, after_qa),
    ):
        missing = [field for field in IDENTIFICATION_FIELDS if field not in qa.product_metadata]
        source_metadata_missing[role] = missing
        catalog_metadata_missing[role] = [
            field
            for field in ("stopTime", "frameCoverage", "sideBandPolarization")
            if field not in scene.catalog_metadata
        ]

    manifest = {
        "schema_version": 1,
        "generated_at_utc": generated_at.isoformat(),
        "analysis": {
            "method": "gamma0_temporal_log_ratio",
            "equation": "10 * log10(after_gamma0_power / before_gamma0_power)",
            "layer": layer,
            "frequency": before.frequency,
            "temporal_order": {
                "before_start_utc": before.catalog_metadata["startTime"],
                "before_stop_utc": before.catalog_metadata["stopTime"],
                "after_start_utc": after.catalog_metadata["startTime"],
                "after_stop_utc": after.catalog_metadata["stopTime"],
                "before_orbit": before.catalog_metadata["orbit"],
                "after_orbit": after.catalog_metadata["orbit"],
            },
            "classification_performed": False,
            "causal_interpretation_performed": False,
        },
        "inputs": {
            role: {
                "scene_id": scene.scene_id,
                "product_url": scene.product_url,
                "catalog_metadata": scene.catalog_metadata,
                "product_identification_metadata": qa.product_metadata,
                "retrieval": scene.access,
                "window_sha256": _window_digest(scene),
                "window": {
                    "rows": [scene.row_start, scene.row_stop],
                    "columns": [scene.column_start, scene.column_stop],
                    "epsg_code": scene.grid_metadata["projection_attributes"][
                        "epsg_code"
                    ],
                    "projection_value": scene.grid_metadata["projection_value"],
                    "x_coordinates_sha256": _array_digest(
                        np.asarray(scene.grid_metadata["x_coordinates"])
                    ),
                    "y_coordinates_sha256": _array_digest(
                        np.asarray(scene.grid_metadata["y_coordinates"])
                    ),
                },
                "qa_evidence": {
                    "status": qa.status,
                    "artifact_uri": qa.artifact_uri,
                    "artifact_sha256": qa.artifact_sha256,
                    "checks": qa.checks,
                    "check_details": qa.check_details or [],
                    "qa_software_version": qa.software_version,
                    "artifact_retrieved_at_utc": qa.retrieved_at_utc,
                    "artifact_retrieval": qa.artifact_retrieval or {},
                    "identification_crosscheck": qa.identification_crosscheck
                    or {"status": "NOT_RECORDED"},
                },
            }
            for role, scene, qa in (
                ("before", before, before_qa),
                ("after", after, after_qa),
            )
        },
        "grid_alignment": {
            "status": "PASS",
            "criterion": "identical CRS, array bounds, and pixel-center coordinate vectors",
        },
        "quality_control": {
            "before_nonvalid_samples": masks.before_nonvalid_samples,
            "after_nonvalid_samples": masks.after_nonvalid_samples,
            "before_exception_samples": masks.before_exception_samples,
            "after_exception_samples": masks.after_exception_samples,
            "common_mask_valid_samples": int(np.count_nonzero(masks.common_valid_mask)),
            "numeric_valid_samples": change.valid_count,
            "numeric_excluded_samples": int(
                np.count_nonzero(masks.common_valid_mask) - change.valid_count
            ),
            "number_of_looks": {
                "before": before_look_summary,
                "after": after_look_summary,
                "used_as_weight_or_confidence": False,
            },
            "common_mask_sha256": common_mask_sha256,
        },
        "software": {
            "echo_version": _echo_version(),
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__,
            "asf_search_version": _dependency_version("asf_search"),
            "earthaccess_version": _dependency_version("earthaccess"),
            "fsspec_version": _dependency_version("fsspec"),
            "h5py_version": _dependency_version("h5py"),
        },
        "output": {
            "quantity": "signed_gamma0_log_ratio_db",
            "shape": list(change.values_db.shape),
            "dtype": str(change.values_db.dtype),
            "measurement_sha256": measurement_sha256,
        },
        "source_metadata_missing": source_metadata_missing,
        "catalog_metadata_missing": catalog_metadata_missing,
        "interpretation_limit": (
            "A calibrated backscatter-response difference is descriptive. It does not "
            "identify an event, establish a cause, or estimate confidence."
        ),
    }
    manifest_payload = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    manifest["manifest_sha256"] = hashlib.sha256(manifest_payload).hexdigest()
    return GcovPairMeasurement(
        change=change,
        common_valid_mask=masks.common_valid_mask,
        manifest=manifest,
    )
