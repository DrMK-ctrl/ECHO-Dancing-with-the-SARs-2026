"""QA-first orchestration for bounded, provenance-linked NISAR GCOV pairs."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from typing import Any, Callable

import numpy as np

from echo.analysis import AnalysisGateError, GcovPairMeasurement, QAEvidence, analyze_gcov_pair
from echo.gcov_preview import (
    GcovPreviewError,
    MAX_PREVIEW_SAMPLES,
    _pixel_corners_wgs84,
    _validate_bounds,
)
from echo.nisar_access import (
    GcovWindow,
    NisarAccessError,
    inspect_identification,
    read_gcov_window,
    _validated_product,
)
from echo.qa import (
    QASummaryError,
    QASummaryRecord,
    crosscheck_identification_metadata,
    read_qa_summary,
)


_MEASUREMENT_LAYERS = {"HHHH", "HVHV", "VVVV", "VHVH", "RHRH", "RVRV"}
_WINDOW_QUALITY_LAYERS = ("mask", "numberOfLooks", "inputDataExceptionMask")


class GcovPairAnalysisError(ValueError):
    """Raised when bounded GCOV pair preparation or measurement fails."""


def _matrix_values(array: np.ndarray) -> list[list[float | int | None]]:
    values = np.asarray(array)
    result: list[list[float | int | None]] = []
    for row in values:
        output_row: list[float | int | None] = []
        for value in row:
            if np.issubdtype(values.dtype, np.floating):
                output_row.append(float(value) if np.isfinite(value) else None)
            else:
                output_row.append(int(value))
        result.append(output_row)
    return result


def build_gcov_pair_analysis(
    before_feature: dict[str, Any],
    after_feature: dict[str, Any],
    *,
    bounds_wgs84: tuple[float, float, float, float] | list[float],
    frequency: str,
    layer: str,
    qa_reader: Callable[..., QASummaryRecord] | None = None,
    metadata_reader: Callable[..., dict[str, Any]] | None = None,
    window_reader: Callable[..., GcovWindow] | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Check provider QA before pixel reads, then run the existing gated analyzer.

    QA-held products return their source QA records without opening measurement
    arrays. A passing QA summary is followed by bounded product metadata and
    AOI-window reads; the existing analyzer remains the final compatibility and
    scientific-quality gate.
    """
    qa_reader = qa_reader or read_qa_summary
    metadata_reader = metadata_reader or inspect_identification
    window_reader = window_reader or read_gcov_window
    if frequency not in {"A", "B"}:
        raise GcovPairAnalysisError("frequency must be A or B")
    if layer not in _MEASUREMENT_LAYERS:
        raise GcovPairAnalysisError("layer must be a real-valued diagonal GCOV power term")
    try:
        bounds = _validate_bounds(bounds_wgs84)
    except GcovPreviewError as exc:
        raise GcovPairAnalysisError(str(exc)) from exc

    for feature in (before_feature, after_feature):
        try:
            _validated_product(feature)
        except (NisarAccessError, AttributeError, TypeError) as exc:
            raise GcovPairAnalysisError(str(exc)) from exc

    source_products = {}
    for role, feature in (("before", before_feature), ("after", after_feature)):
        properties = feature["properties"]
        source_products[role] = {
            "provider": "Alaska Satellite Facility DAAC",
            "mission": "NISAR",
            "product": "GCOV",
            "scene_id": properties["fileID"],
            "product_url": properties["url"],
            "collection": properties.get("collectionName"),
            "processing_level": properties.get("processingLevel"),
            "acquisition_start_utc": properties.get("startTime"),
            "acquisition_stop_utc": properties.get("stopTime"),
            "crid": properties.get("crid"),
            "orbit": properties.get("orbit"),
            "path_number": properties.get("pathNumber"),
            "frame_number": properties.get("frameNumber"),
        }

    qa_records: dict[str, QASummaryRecord] = {}
    for role, feature in (
        ("before", before_feature),
        ("after", after_feature),
    ):
        try:
            qa_records[role] = qa_reader(feature, product_metadata={})
        except QASummaryError as exc:
            raise GcovPairAnalysisError(
                f"{role} provider QA could not be retrieved: {exc}"
            ) from exc

    qa_payload = {role: asdict(record) for role, record in qa_records.items()}
    held_roles = [
        role for role, record in qa_records.items() if record.evidence.status != "PASS"
    ]
    if held_roles:
        generated_at = generated_at or datetime.now(timezone.utc)
        if generated_at.tzinfo is None:
            raise GcovPairAnalysisError("analysis timestamp must include a timezone")
        return {
            "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
            "schema_version": 1,
            "created_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
            "status": "QA_HELD",
            "source_products": source_products,
            "provider_qa": qa_payload,
            "held_roles": held_roles,
            "analysis_gates": {
                "provider_qa": "HELD_NON_PASS",
                "product_identification": "NOT_EVALUATED",
                "measurement_arrays": "NOT_READ",
                "grid_alignment": "NOT_EVALUATED",
                "aoi_common_valid_coverage": "NOT_EVALUATED",
                "change_calculation": "NOT_PERFORMED",
            },
            "next_evidence": [
                "Both selected products need canonical ASF provider QA status PASS before product metadata or measurement arrays are evaluated.",
                "After provider QA passes, evaluate product compatibility, grid alignment, AOI coverage, and common valid pixels before calculating a descriptive change measurement.",
            ],
            "measurement": None,
            "manifest": None,
            "interpretation_limits": [
                "Provider QA did not pass for every selected product.",
                "No measurement arrays were read and no change was calculated.",
                "A QA disposition is not reinterpreted by this application.",
            ],
        }

    enriched_evidence: dict[str, QAEvidence] = {}
    for role, record in qa_records.items():
        try:
            inspection = metadata_reader(
                before_feature if role == "before" else after_feature
            )
        except NisarAccessError as exc:
            raise GcovPairAnalysisError(
                f"{role} product identification metadata could not be read: {exc}"
            ) from exc
        product_metadata = inspection.get("product", {}).get("metadata")
        if not isinstance(product_metadata, dict):
            raise GcovPairAnalysisError(
                f"{role} product identification metadata is malformed"
            )
        enriched_evidence[role] = replace(
            record.evidence,
            product_metadata=product_metadata,
            identification_crosscheck=crosscheck_identification_metadata(
                product_metadata,
                software_version=record.evidence.software_version,
            ),
        )
    qa_payload = {
        role: asdict(replace(record, evidence=enriched_evidence[role]))
        for role, record in qa_records.items()
    }

    requested_layers = (layer, *_WINDOW_QUALITY_LAYERS)
    windows = {}
    for role, feature in (("before", before_feature), ("after", after_feature)):
        try:
            windows[role] = window_reader(
                feature,
                frequency=frequency,
                bounds_wgs84=bounds,
                layers=requested_layers,
                max_samples=MAX_PREVIEW_SAMPLES,
            )
        except NisarAccessError as exc:
            raise GcovPairAnalysisError(f"{role} GCOV window read failed: {exc}") from exc

    generated_at = generated_at or datetime.now(timezone.utc)
    try:
        result: GcovPairMeasurement = analyze_gcov_pair(
            windows["before"],
            windows["after"],
            before_qa=enriched_evidence["before"],
            after_qa=enriched_evidence["after"],
            layer=layer,
            generated_at=generated_at,
        )
    except AnalysisGateError as exc:
        raise GcovPairAnalysisError(str(exc)) from exc

    before_window = windows["before"]
    return {
        "record_type": "ECHO_GCOV_PAIR_ANALYSIS",
        "schema_version": 1,
        "created_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "status": "MEASURED_DESCRIPTIVE_ONLY",
        "source_products": source_products,
        "provider_qa": qa_payload,
        "measurement": {
            "quantity": "signed_gamma0_log_ratio_db",
            "equation": "10 * log10(after_gamma0_power / before_gamma0_power)",
            "layer": layer,
            "frequency": frequency,
            "units": "dB",
            "values_db": _matrix_values(result.change.values_db),
            "valid_mask": result.change.valid_mask.tolist(),
            "common_valid_mask": result.common_valid_mask.tolist(),
        },
        "grid": {
            "epsg_code": before_window.grid_metadata["projection_attributes"][
                "epsg_code"
            ],
            "window_shape": list(result.change.values_db.shape),
            "pixel_corners_wgs84": _pixel_corners_wgs84(before_window),
            "coordinate_convention": "GCOV pixel centers; corners derived by midpoint edges",
        },
        "manifest": result.manifest,
        "interpretation_limits": [
            "This is a descriptive backscatter-response difference, not an event classification.",
            "No physical cause or confidence is inferred.",
            "Spatial display stretch, if applied, is not a scientific threshold.",
        ],
    }
