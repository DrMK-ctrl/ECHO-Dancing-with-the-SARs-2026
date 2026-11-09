"""Provenance-linked descriptive analysis of compatible OPERA RTC-S1 windows."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import re
from typing import Any

import numpy as np

from echo.opera_rtc import analyze_opera_rtc_s1_pair, decode_opera_rtc_s1_mask
from echo.opera_rtc_access import OperaRtcS1Window
from echo.opera_rtc_quality import (
    OperaRtcQualityReviewError,
    build_opera_rtc_pair_quality_review,
    build_opera_rtc_quality_review,
)


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


def validate_opera_rtc_s1_series_record(
    record: dict[str, Any],
    *,
    pair_record: dict[str, Any],
) -> dict[str, Any]:
    """Validate a retained temporal-series record against its linked SAR pair.

    This checks product/grid compatibility, the all-date support, adjacent
    per-pixel differences, summary statistics, and the diagnostic QA state.
    It does not decide whether the measured pattern has a physical cause.
    """
    try:
        if (
            record.get("record_type") != "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS"
            or record.get("schema_version") not in {1, 2}
            or record.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
            or record.get("processing", {}).get("intervals_share_observations") is not True
            or record.get("provider_qa", {}).get("status")
            != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
        ):
            raise OperaRtcS1AnalysisError("series record identity or diagnostic disposition is unsupported")
        observations = record["observations"]
        intervals = record["adjacent_intervals"]
        source = record["source"]
        grid = record["grid"]
        if not isinstance(observations, list) or not 3 <= len(observations) <= 12:
            raise OperaRtcS1AnalysisError("series must contain three to twelve observations")
        if not isinstance(intervals, list) or len(intervals) != len(observations) - 1:
            raise OperaRtcS1AnalysisError("series must contain one interval for each adjacent observation pair")

        pair_sources = pair_record["source_products"]
        pair_ids = [pair_sources[role]["scene_id"] for role in ("before", "after")]
        scene_ids = [item["scene_id"] for item in observations]
        if scene_ids[:2] != pair_ids or len(scene_ids) != len(set(scene_ids)):
            raise OperaRtcS1AnalysisError("series does not begin with the pair's exact unique source acquisitions")
        for index, observation in enumerate(observations):
            identity = _SCENE_ID.fullmatch(observation["scene_id"])
            if identity is None:
                raise OperaRtcS1AnalysisError("series includes an unsupported OPERA RTC-S1 scene identifier")
            if any(identity[name] != source[field] for name, field in (
                ("burst", "burst_id"), ("platform", "platform"), ("version", "product_version")
            )):
                raise OperaRtcS1AnalysisError("series scenes do not share their declared burst, platform, and version")
            if observation.get("burst_id") != source["burst_id"] or observation.get("platform") != source["platform"] or observation.get("product_version") != source["product_version"] or observation.get("polarization") != source["polarization"]:
                raise OperaRtcS1AnalysisError("observation metadata do not match the series source identity")
            acquired = _parse_time(observation.get("acquisition_start_utc"), "series")
            encoded = datetime.strptime(identity["acquired"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            if acquired != encoded or (index and acquired <= _parse_time(observations[index - 1]["acquisition_start_utc"], "series")):
                raise OperaRtcS1AnalysisError("series acquisition timestamps do not match ordered scene identifiers")

        for field in ("crs", "transform", "window"):
            if grid.get(field) != pair_record.get("grid", {}).get(field):
                raise OperaRtcS1AnalysisError(f"series and pair {field} metadata differ")
        shape = grid["window"]["shape"]
        if not isinstance(shape, list) or len(shape) != 2 or any(not isinstance(value, int) or value <= 0 for value in shape) or shape[0] * shape[1] > 65536:
            raise OperaRtcS1AnalysisError("series grid shape is invalid or exceeds the supported bound")
        support_record = record["common_support"]
        support = np.asarray(support_record["mask"], dtype=bool)
        aoi_pixel_count = support_record["aoi_pixel_count"]
        if (
            not isinstance(aoi_pixel_count, int)
            or not 0 < int(support.sum()) <= aoi_pixel_count <= shape[0] * shape[1]
            or support.shape != tuple(shape)
            or int(support.sum()) != support_record["clear_in_every_observation_count"]
            or int(support.sum()) != support_record["finite_positive_in_every_observation_count"]
        ):
            raise OperaRtcS1AnalysisError("series common-support mask and counts disagree")
        observation_values = []
        for observation in observations:
            raw = observation["backscatter_db_on_common_support"]
            values = np.asarray([[np.nan if value is None else float(value) for value in row] for row in raw], dtype=np.float64)
            if values.shape != tuple(shape) or not np.isfinite(values[support]).all() or np.isfinite(values[~support]).any():
                raise OperaRtcS1AnalysisError("observation backscatter does not match the common support")
            observation_values.append(values)

        for index, interval in enumerate(intervals):
            if interval["before_scene_id"] != scene_ids[index] or interval["after_scene_id"] != scene_ids[index + 1]:
                raise OperaRtcS1AnalysisError("interval does not link consecutive observations")
            expected_days = (
                _parse_time(observations[index + 1]["acquisition_start_utc"], "series")
                - _parse_time(observations[index]["acquisition_start_utc"], "series")
            ).total_seconds() / 86400
            if not np.isclose(interval.get("interval_days", np.nan), expected_days, rtol=0, atol=1e-9):
                raise OperaRtcS1AnalysisError("interval duration does not reproduce from acquisition timestamps")
            values = np.asarray([[np.nan if value is None else float(value) for value in row] for row in interval["values_db"]], dtype=np.float64)
            valid = np.asarray(interval["valid_mask"], dtype=bool)
            expected = observation_values[index + 1] - observation_values[index]
            if values.shape != tuple(shape) or valid.shape != tuple(shape) or not np.array_equal(valid, support) or not np.allclose(values[support], expected[support], rtol=0, atol=1e-9) or np.isfinite(values[~support]).any():
                raise OperaRtcS1AnalysisError("interval values do not reproduce from adjacent observations on common support")
            sample = values[support]
            summary = interval["summary_db"]
            calculated = {
                "mean": float(np.mean(sample)),
                "median": float(np.median(sample)),
                "p05": float(np.quantile(sample, 0.05)),
                "p25": float(np.quantile(sample, 0.25)),
                "p75": float(np.quantile(sample, 0.75)),
                "p95": float(np.quantile(sample, 0.95)),
                "positive_pixel_count": int(np.count_nonzero(sample > 0)),
                "negative_pixel_count": int(np.count_nonzero(sample < 0)),
            }
            if interval.get("measured_pixel_count") != int(support.sum()) or any(
                not np.isclose(summary.get(key, np.nan), expected_value, rtol=1e-9, atol=1e-9)
                for key, expected_value in calculated.items()
            ):
                raise OperaRtcS1AnalysisError("interval summary does not reproduce from retained measurement pixels")
        if record.get("schema_version") == 2:
            try:
                expected_quality_review = build_opera_rtc_quality_review(record)
            except OperaRtcQualityReviewError as exc:
                raise OperaRtcS1AnalysisError(f"series quality review cannot be reproduced: {exc}") from exc
            if record.get("quality_review") != expected_quality_review:
                raise OperaRtcS1AnalysisError("series quality review does not reproduce from retained QA and measurement metadata")
        elif "quality_review" in record:
            raise OperaRtcS1AnalysisError("schema version 1 cannot carry a scoped quality review")
        return {
            "observation_count": len(observations),
            "common_support_count": int(support.sum()),
            "aoi_pixel_count": int(support_record["aoi_pixel_count"]),
            "scene_ids": scene_ids,
            "intervals": [
                {
                    "before_acquisition_start_utc": observations[index]["acquisition_start_utc"],
                    "after_acquisition_start_utc": observations[index + 1]["acquisition_start_utc"],
                    "interval_days": interval["interval_days"],
                    "measured_pixel_count": interval["measured_pixel_count"],
                    "summary_db": interval["summary_db"],
                }
                for index, interval in enumerate(intervals)
            ],
        }
    except OperaRtcS1AnalysisError:
        raise
    except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
        raise OperaRtcS1AnalysisError(f"series record is malformed: {exc}") from exc


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
    record = {
        "record_type": "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS",
        "schema_version": 2 if network_inputs else 1,
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
    if network_inputs:
        try:
            record["quality_review"] = build_opera_rtc_pair_quality_review(record)
        except OperaRtcQualityReviewError as exc:
            raise OperaRtcS1AnalysisError(f"pair quality review cannot be derived: {exc}") from exc
    return record


def build_opera_rtc_s1_series_analysis(
    windows: list[OperaRtcS1Window],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Measure adjacent change across a same-grid RTC-S1 observation series.

    Every interval uses one common AOI support that is clear and numerically
    usable in every supplied acquisition. The series is diagnostic: OPERA
    per-product masks are preserved, but this function does not invent a
    provider QA verdict, classify a surface event, or infer causation.
    """
    if not isinstance(windows, list) or len(windows) < 3:
        raise OperaRtcS1AnalysisError("an RTC-S1 temporal series requires at least three windows")
    identities = [_SCENE_ID.fullmatch(window.scene_id) for window in windows]
    if any(identity is None for identity in identities):
        raise OperaRtcS1AnalysisError("every temporal-series input must be a supported RTC-S1 scene")
    first_identity = identities[0]
    assert first_identity is not None
    for identity in identities[1:]:
        assert identity is not None
        for field in ("burst", "platform", "spacing", "version"):
            if identity[field] != first_identity[field]:
                raise OperaRtcS1AnalysisError(
                    f"RTC-S1 temporal-series {field} values do not match"
                )
    if len({window.scene_id for window in windows}) != len(windows):
        raise OperaRtcS1AnalysisError("temporal-series scenes must be unique")
    if len({window.polarization for window in windows}) != 1:
        raise OperaRtcS1AnalysisError("RTC-S1 temporal-series polarizations do not match")

    times: list[datetime] = []
    for window, identity in zip(windows, identities, strict=True):
        assert identity is not None
        observed = _parse_time(window.source.get("acquisition_start_utc"), "series")
        encoded = datetime.strptime(
            identity["acquired"], "%Y%m%dT%H%M%SZ"
        ).replace(tzinfo=timezone.utc)
        if observed != encoded:
            raise OperaRtcS1AnalysisError(
                "temporal-series catalog acquisition time does not match its scene identifier"
            )
        times.append(observed)
    if any(before >= after for before, after in zip(times, times[1:])):
        raise OperaRtcS1AnalysisError(
            "temporal-series windows must be in strictly increasing acquisition order"
        )

    reference = windows[0]
    for window in windows[1:]:
        for field in ("crs", "transform", "window"):
            if window.grid.get(field) != reference.grid.get(field):
                raise OperaRtcS1AnalysisError(
                    f"RTC-S1 temporal-series {field} metadata do not match"
                )
        if not np.array_equal(window.selection_mask, reference.selection_mask):
            raise OperaRtcS1AnalysisError(
                "RTC-S1 temporal-series AOI pixel-center selections do not match"
            )
        if window.values.shape != reference.values.shape or window.mask.shape != reference.mask.shape:
            raise OperaRtcS1AnalysisError("RTC-S1 temporal-series array shapes do not match")
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        raise OperaRtcS1AnalysisError("analysis timestamp must include a timezone")
    if any(not isinstance(window.access, dict) for window in windows):
        raise OperaRtcS1AnalysisError("temporal-series source access provenance is missing")

    selected = np.asarray(reference.selection_mask, dtype=bool)
    common_clear = selected.copy()
    common_positive = selected.copy()
    decoded_masks = []
    for window in windows:
        try:
            decoded = decode_opera_rtc_s1_mask(window.mask)
        except ValueError as exc:
            raise OperaRtcS1AnalysisError(str(exc)) from exc
        if window.mask.shape != window.values.shape or window.values.ndim != 2:
            raise OperaRtcS1AnalysisError(
                "RTC-S1 temporal-series measurements and masks must be shape-matched two-dimensional arrays"
            )
        decoded_masks.append(decoded)
        common_clear &= decoded.clear
        common_positive &= np.isfinite(window.values) & (window.values > 0)
    common_valid = common_clear & common_positive

    observation_records = []
    for index, (window, observed, identity, decoded) in enumerate(
        zip(windows, times, identities, decoded_masks, strict=True)
    ):
        assert identity is not None
        backscatter_db = np.full(window.values.shape, np.nan, dtype=np.float64)
        backscatter_db[common_valid] = 10.0 * np.log10(
            window.values[common_valid].astype(np.float64)
        )
        observation_records.append({
            "scene_id": window.scene_id,
            "acquisition_start_utc": observed.isoformat(),
            "acquisition_stop_utc": window.source.get("acquisition_stop_utc"),
            "platform": identity["platform"],
            "burst_id": identity["burst"],
            "product_version": identity["version"],
            "polarization": window.polarization,
            "source_product": {**window.source, "assets": window.assets, "access": window.access},
            "backscatter_db_on_common_support": _json_matrix(backscatter_db, floating=True),
            "mask_counts_within_aoi": {
                "clear": int(np.count_nonzero(selected & decoded.clear)),
                "shadow_affected": int(np.count_nonzero(selected & decoded.shadow_affected)),
                "layover_affected": int(np.count_nonzero(selected & decoded.layover_affected)),
                "invalid": int(np.count_nonzero(selected & decoded.invalid)),
            },
            "values_sha256": _array_sha256(window.values),
            "mask_sha256": _array_sha256(window.mask),
        })

    def compare_indices(before_index: int, after_index: int) -> dict[str, Any]:
        before = windows[before_index]
        after = windows[after_index]
        change_db = np.full(before.values.shape, np.nan, dtype=np.float64)
        change_db[common_valid] = 10.0 * np.log10(
            after.values[common_valid].astype(np.float64)
            / before.values[common_valid].astype(np.float64)
        )
        valid_values = change_db[common_valid]
        percentiles = (
            np.percentile(valid_values, (5, 25, 50, 75, 95)).tolist()
            if valid_values.size
            else [None, None, None, None, None]
        )
        return {
            "before_scene_id": before.scene_id,
            "after_scene_id": after.scene_id,
            "before_acquisition_start_utc": times[before_index].isoformat(),
            "after_acquisition_start_utc": times[after_index].isoformat(),
            "interval_days": (times[after_index] - times[before_index]).total_seconds() / 86400.0,
            "values_db": _json_matrix(change_db, floating=True),
            "valid_mask": _json_matrix(common_valid, floating=False),
            "measured_pixel_count": int(valid_values.size),
            "summary_db": {
                "p05": percentiles[0],
                "p25": percentiles[1],
                "median": percentiles[2],
                "p75": percentiles[3],
                "p95": percentiles[4],
                "mean": float(np.mean(valid_values)) if valid_values.size else None,
                "positive_pixel_count": int(np.count_nonzero(valid_values > 0)),
                "negative_pixel_count": int(np.count_nonzero(valid_values < 0)),
            },
            "values_sha256": _array_sha256(change_db),
        }

    intervals = [compare_indices(index, index + 1) for index in range(len(windows) - 1)]
    baseline_comparisons = [
        compare_indices(0, index) for index in range(2, len(windows))
    ]

    network_inputs = all(
        window.access.get("network_retrieval") is True
        and window.access.get("authentication") == "Earthdata Login via local netrc"
        for window in windows
    )
    try:
        echo_version = version("echo-sar-investigation")
    except PackageNotFoundError:
        echo_version = "source-checkout"
    record = {
        "record_type": "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS",
        "schema_version": 2 if network_inputs else 1,
        "created_at_utc": generated_at.astimezone(timezone.utc).isoformat(),
        "status": (
            "FIXTURE_DATA_COMPUTATION_NOT_SCIENTIFIC_RESULT"
            if not network_inputs
            else "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
            if np.any(common_valid)
            else "INCONCLUSIVE_NO_COMMON_CLEAR_VALID_PIXELS"
        ),
        "source": {
            "provider": "Alaska Satellite Facility DAAC",
            "mission_product": "NASA OPERA RTC-S1 derived from Sentinel-1; not NISAR",
            "burst_id": first_identity["burst"],
            "platform": first_identity["platform"],
            "product_version": first_identity["version"],
            "polarization": reference.polarization,
        },
        "provider_qa": {
            "status": "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION",
            "per_observation": [
                {
                    "scene_id": window.scene_id,
                    "status": window.source.get("provider_qa_disposition", "NOT_RETRIEVED"),
                    "quality_metadata": window.source.get("quality_metadata", {}),
                }
                for window in windows
            ],
            "scientific_gate": "DIAGNOSTIC_ONLY; no provider PASS is asserted",
        },
        "grid": {
            "crs": reference.grid["crs"],
            "transform": reference.grid["transform"],
            "window": reference.grid["window"],
            "pixel_corners_wgs84": reference.grid["pixel_corners_wgs84"],
            "registration_gate": "EXACT_CRS_TRANSFORM_SHAPE_AND_AOI_CENTER_SELECTION_MATCH_FOR_ALL_OBSERVATIONS",
            "resampling": "NONE",
        },
        "common_support": {
            "aoi_pixel_count": int(np.count_nonzero(selected)),
            "clear_in_every_observation_count": int(np.count_nonzero(common_clear)),
            "finite_positive_in_every_observation_count": int(np.count_nonzero(common_valid)),
            "mask_rule": "code 0 in every product mask; all gamma-zero samples finite and positive; exact shared AOI pixel centers only",
            "mask": _json_matrix(common_valid, floating=False),
            "mask_sha256": _array_sha256(common_valid),
        },
        "observations": observation_records,
        "adjacent_intervals": intervals,
        "reference_baseline": {
            "scene_id": windows[0].scene_id,
            "acquisition_start_utc": times[0].isoformat(),
            "comparisons": baseline_comparisons,
            "selection_rule": "first chronological observation in the submitted series",
        },
        "processing": {
            "software": {
                "echo": echo_version,
                "numpy": np.__version__,
                "readers": [window.access.get("software") for window in windows],
            },
            "method": "per-observation 10*log10(gamma0 power); adjacent signed dB differences and first-observation baseline comparisons on one all-date common support",
            "intervals_share_observations": True,
        },
        "interpretation_limits": [
            "These are descriptive OPERA RTC-S1 gamma-zero backscatter measurements, not a surface-change classification.",
            "The provider sidecars do not establish a consolidated PASS/FAIL verdict; the series remains diagnostic.",
            "Every interval shares the all-date support and adjacent intervals share observations; interval summaries are not independent corroboration.",
            "No event, cause, flood extent, damage, or ground condition is inferred.",
            "The catalog selection, same-burst identity, and exact grid check do not replace independent evidence or scientific validation.",
        ],
    }
    if network_inputs:
        try:
            record["quality_review"] = build_opera_rtc_quality_review(record)
        except OperaRtcQualityReviewError as exc:
            raise OperaRtcS1AnalysisError(f"could not derive bounded quality review: {exc}") from exc
    return record
