"""Provenance-linked descriptive analysis of compatible OPERA RTC-S1 windows."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import re
from typing import Any

import numpy as np

from echo.opera_rtc import analyze_opera_rtc_s1_pair
from echo.opera_rtc_access import OperaRtcS1Window


_SCENE_ID = re.compile(
    r"^OPERA_L2_RTC-S1_(?P<burst>T\d{3}-\d{6}-IW[1-3])_"
    r"(?P<acquired>\d{8}T\d{6}Z)_(?P<generated>\d{8}T\d{6}Z)_"
    r"(?P<platform>S1[AB])_(?P<spacing>\d+)_v(?P<version>\d+\.\d+)$"
)


class OperaRtcS1AnalysisError(ValueError):
    """Raised when two RTC-S1 observations cannot be compared responsibly."""


def _array_sha256(array: np.ndarray) -> str:
    values = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(values.dtype.str.encode("ascii"))
    digest.update(str(values.shape).encode("ascii"))
    digest.update(values.view(np.uint8))
    return digest.hexdigest()


def _json_matrix(array: np.ndarray, *, floating: bool) -> list[list[Any]]:
    values = np.asarray(array)
    if values.ndim != 2:
        raise OperaRtcS1AnalysisError("analysis arrays must be two-dimensional")
    if floating:
        return [
            [float(value) if np.isfinite(value) else None for value in row]
            for row in values
        ]
    return [[bool(value) for value in row] for row in values]


def _parse_time(value: Any, role: str) -> datetime:
    if not isinstance(value, str):
        raise OperaRtcS1AnalysisError(f"{role} acquisition timestamp is missing")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperaRtcS1AnalysisError(f"{role} acquisition timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise OperaRtcS1AnalysisError(f"{role} acquisition timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def build_opera_rtc_s1_pair_analysis(
    before: OperaRtcS1Window,
    after: OperaRtcS1Window,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Check source and grid compatibility, calculate, and record the pair.

    No reprojection, resampling, mask reinterpretation, flood classification,
    or physical-cause inference is performed. Per-product QA metadata and the
    per-acquisition OPERA masks are retained without inventing a PASS/FAIL verdict.
    """
    if before.scene_id == after.scene_id:
        raise OperaRtcS1AnalysisError("before and after scenes must be different")
    before_identity = _SCENE_ID.fullmatch(before.scene_id)
    after_identity = _SCENE_ID.fullmatch(after.scene_id)
    if before_identity is None or after_identity is None:
        raise OperaRtcS1AnalysisError("an input is not a supported OPERA RTC-S1 scene")
    for field in ("burst", "platform", "spacing", "version"):
        if before_identity[field] != after_identity[field]:
            raise OperaRtcS1AnalysisError(f"OPERA RTC-S1 pair {field} values do not match")
    if before.polarization != after.polarization:
        raise OperaRtcS1AnalysisError("OPERA RTC-S1 pair polarizations do not match")

    before_time = _parse_time(
        before.source.get("acquisition_start_utc"), "before"
    )
    after_time = _parse_time(after.source.get("acquisition_start_utc"), "after")
    for role, observed_time, identity in (
        ("before", before_time, before_identity),
        ("after", after_time, after_identity),
    ):
        encoded_time = datetime.strptime(
            identity["acquired"], "%Y%m%dT%H%M%SZ"
        ).replace(tzinfo=timezone.utc)
        if observed_time != encoded_time:
            raise OperaRtcS1AnalysisError(
                f"{role} catalog acquisition time does not match its scene identifier"
            )
    if before_time >= after_time:
        raise OperaRtcS1AnalysisError("acquisitions must be distinct and chronologically ordered")
    interval_days = (after_time - before_time).total_seconds() / 86400.0
    for field in ("crs", "transform", "window"):
        if before.grid.get(field) != after.grid.get(field):
            raise OperaRtcS1AnalysisError(f"OPERA RTC-S1 pair {field} metadata do not match")
    if not np.array_equal(before.selection_mask, after.selection_mask):
        raise OperaRtcS1AnalysisError("OPERA RTC-S1 AOI pixel-center selections do not match")
    if before.values.shape != after.values.shape:
        raise OperaRtcS1AnalysisError("OPERA RTC-S1 pair windows do not have identical shapes")
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        raise OperaRtcS1AnalysisError("analysis timestamp must include a timezone")
    if not isinstance(before.access, dict) or not isinstance(after.access, dict):
        raise OperaRtcS1AnalysisError("source access provenance is missing")
    network_inputs = all(
        window.access.get("network_retrieval") is True
        and window.access.get("authentication") == "Earthdata Login via local netrc"
        for window in (before, after)
    )

    try:
        result = analyze_opera_rtc_s1_pair(
            before.values,
            after.values,
            before.mask,
            after.mask,
            before_crs=before.grid["crs"],
            after_crs=after.grid["crs"],
            before_transform=before.grid["transform"],
            after_transform=after.grid["transform"],
            selection_mask=before.selection_mask,
        )
    except (KeyError, ValueError) as exc:
        raise OperaRtcS1AnalysisError(str(exc)) from exc

    valid_count = result.change.valid_count
    clear_count = int(np.count_nonzero(result.mask.common_clear))
    numerical_invalid_count = int(
        np.count_nonzero(
            result.mask.common_clear
            & (
                ~np.isfinite(before.values)
                | ~np.isfinite(after.values)
                | (before.values <= 0)
                | (after.values <= 0)
            )
        )
    )
    try:
        echo_version = version("echo-sar-investigation")
    except PackageNotFoundError:
        echo_version = "source-checkout"
    return {
        "record_type": "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS",
        "schema_version": 1,
        "created_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "status": (
            "FIXTURE_DATA_COMPUTATION_NOT_SCIENTIFIC_RESULT"
            if not network_inputs
            else "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
            if valid_count
            else "INCONCLUSIVE_NO_COMMON_CLEAR_VALID_PIXELS"
        ),
        "source_products": {
            "before": {**before.source, "assets": before.assets, "access": before.access},
            "after": {**after.source, "assets": after.assets, "access": after.access},
        },
        "acquisition_interval_days": interval_days,
        "provider_qa": {
            "status": "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION",
            "basis": "Per-product HDF5 QA metadata are retained for both acquisitions. The sidecars do not provide a consolidated PASS/FAIL disposition.",
            "before": before.source.get("quality_metadata", {}).get("status", "NOT_RETRIEVED"),
            "after": after.source.get("quality_metadata", {}).get("status", "NOT_RETRIEVED"),
            "scientific_gate": "DIAGNOSTIC_ONLY; QA metadata do not establish temporal registration or validate change interpretation",
        },
        "grid": {
            "crs": before.grid["crs"],
            "transform": before.grid["transform"],
            "window": before.grid["window"],
            "pixel_corners_wgs84": before.grid["pixel_corners_wgs84"],
            "registration_gate": "EXACT_CRS_TRANSFORM_SHAPE_AND_AOI_CENTER_SELECTION_MATCH",
            "resampling": "NONE",
        },
        "measurement": {
            "quantity": "signed_gamma0_log_ratio_db",
            "equation": "10 * log10(after_gamma0_power / before_gamma0_power)",
            "polarization": before.polarization,
            "units": "dB",
            "values_db": _json_matrix(result.change.values_db, floating=True),
            "valid_mask": _json_matrix(result.change.valid_mask, floating=False),
            "common_clear_mask": _json_matrix(
                result.mask.common_clear, floating=False
            ),
            "window_pixel_count": int(result.change.candidate_count),
            "aoi_pixel_count": result.mask.aoi_pixel_count,
            "common_clear_pixel_count": clear_count,
            "excluded_nonfinite_or_nonpositive_count": numerical_invalid_count,
            "measured_pixel_count": valid_count,
            "mask_counts": {
                "aoi_pixel_count": result.mask.aoi_pixel_count,
                "before_clear": result.mask.before_clear_count,
                "after_clear": result.mask.after_clear_count,
                "before_shadow_affected": result.mask.before_shadow_affected_count,
                "after_shadow_affected": result.mask.after_shadow_affected_count,
                "before_layover_affected": result.mask.before_layover_affected_count,
                "after_layover_affected": result.mask.after_layover_affected_count,
                "before_invalid": result.mask.before_invalid_count,
                "after_invalid": result.mask.after_invalid_count,
            },
        },
        "checksums": {
            "before_values_sha256": _array_sha256(before.values),
            "after_values_sha256": _array_sha256(after.values),
            "before_mask_sha256": _array_sha256(before.mask),
            "after_mask_sha256": _array_sha256(after.mask),
            "before_selection_mask_sha256": _array_sha256(before.selection_mask),
            "after_selection_mask_sha256": _array_sha256(after.selection_mask),
            "change_values_sha256": _array_sha256(result.change.values_db),
            "change_valid_mask_sha256": _array_sha256(result.change.valid_mask),
        },
        "processing": {
            "software": {
                "echo": echo_version,
                "numpy": np.__version__,
                "before_readers": before.access.get("software"),
                "after_readers": after.access.get("software"),
            },
            "method": "strict common-clear mask followed by linear-gamma-zero log ratio",
            "mask_rule": "code 0 in both products; codes 1, 2, 3, and 255 excluded from the primary comparison",
        },
        "interpretation_limits": [
            "The output is descriptive change in OPERA RTC-S1 gamma-zero backscatter, not a surface-change classification.",
            "Provider QA summary was not retrieved; this record does not claim provider QA PASS.",
            "No event, cause, flood extent, damage, or ground condition is inferred.",
            "Independent evidence review and sensitivity analysis remain necessary before an investigation finding.",
        ],
    }
