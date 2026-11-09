"""Bounded quality context for retained NASA OPERA RTC-S1 measurements."""

from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any
from datetime import datetime, timezone

import numpy as np


JPL_RTC_PRODUCT_URL = "https://www.jpl.nasa.gov/go/opera/products/rtc-product/"
RTC_PRODUCT_SPEC_URL = "https://d2pn8kiwq2w21t.cloudfront.net/documents/ProductSpec_RTC-S1.pdf"
ASF_RTC_GUIDE_URL = "https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/"
_PAIR_SCENE_ID = re.compile(
    r"^OPERA_L2_RTC-S1_(?P<burst>T\d{3}-\d{6}-IW[1-3])_"
    r"(?P<acquired>\d{8}T\d{6}Z)_(?P<generated>\d{8}T\d{6}Z)_"
    r"(?P<platform>S1[AB])_(?P<spacing>\d+)_v(?P<version>\d+\.\d+)$"
)


class OperaRtcQualityReviewError(ValueError):
    """Raised when an OPERA quality review cannot be derived from its record."""


def _metadata_value(metadata: dict[str, Any], key: str) -> Any:
    value = metadata.get(key)
    return value.get("value") if isinstance(value, dict) else None


def _asset_sha256(assets: dict[str, Any], key: str) -> str:
    asset = assets.get(key)
    digest = asset.get("sha256") if isinstance(asset, dict) else None
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise OperaRtcQualityReviewError(f"{key} source asset checksum is invalid")
    return digest


def _matrix_sha256(values: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(values)
    digest = sha256()
    digest.update(contiguous.dtype.str.encode("ascii"))
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(contiguous.view(np.uint8))
    return digest.hexdigest()


def _basis_hash(record: dict[str, Any]) -> str:
    basis = {
        "source": record.get("source"),
        "provider_qa": record.get("provider_qa"),
        "grid": {
            key: record.get("grid", {}).get(key)
            for key in ("crs", "transform", "window", "registration_gate", "resampling")
        },
        "common_support": {
            key: record.get("common_support", {}).get(key)
            for key in (
                "aoi_pixel_count",
                "clear_in_every_observation_count",
                "finite_positive_in_every_observation_count",
                "mask_rule",
                "mask_sha256",
            )
        },
        "observations": [
            {
                "scene_id": observation.get("scene_id"),
                "mask_counts_within_aoi": observation.get("mask_counts_within_aoi"),
                "mask_sha256": observation.get("mask_sha256"),
                "values_sha256": observation.get("values_sha256"),
                "source_product": {
                    key: observation.get("source_product", {}).get(key)
                    for key in ("assets", "quality_metadata")
                },
            }
            for observation in record.get("observations", [])
        ],
    }
    canonical = json.dumps(basis, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return sha256(canonical.encode("utf-8")).hexdigest()


def build_opera_rtc_quality_review(record: dict[str, Any]) -> dict[str, Any]:
    """Summarize provider, per-scene, and bounded ECHO checks independently.

    The result is an inspectable quality record, not a provider PASS, a
    scene-level certification, or a decision about a physical explanation.
    """
    if (
        not isinstance(record, dict)
        or record.get("record_type") != "ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS"
        or record.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES"
    ):
        raise OperaRtcQualityReviewError("quality review requires a diagnostic OPERA RTC-S1 series")
    observations = record.get("observations")
    qa = record.get("provider_qa")
    common = record.get("common_support")
    grid = record.get("grid")
    if (
        not isinstance(observations, list)
        or not observations
        or not isinstance(qa, dict)
        or qa.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
        or not isinstance(common, dict)
        or not isinstance(grid, dict)
    ):
        raise OperaRtcQualityReviewError("series source, QA, or support records are incomplete")
    qa_observations = qa.get("per_observation")
    if not isinstance(qa_observations, list) or len(qa_observations) != len(observations):
        raise OperaRtcQualityReviewError("provider QA entries do not match the observation count")

    per_observation = []
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            raise OperaRtcQualityReviewError("an observation record is malformed")
        scene_id = observation.get("scene_id")
        product = observation.get("source_product")
        metadata = product.get("quality_metadata") if isinstance(product, dict) else None
        mask_counts = observation.get("mask_counts_within_aoi")
        assets = product.get("assets") if isinstance(product, dict) else None
        if (
            not isinstance(scene_id, str)
            or not isinstance(metadata, dict)
            or not isinstance(mask_counts, dict)
            or not isinstance(assets, dict)
        ):
            raise OperaRtcQualityReviewError("an acquisition lacks sidecar, mask, or asset provenance")
        qa_entry = qa_observations[index]
        if (
            not isinstance(qa_entry, dict)
            or qa_entry.get("scene_id") != scene_id
            or qa_entry.get("status") != "NO_CONSOLIDATED_PASS_FAIL_FIELD_IN_RETRIEVED_HDF5"
            or qa_entry.get("quality_metadata") != metadata
            or metadata.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
        ):
            raise OperaRtcQualityReviewError("provider QA metadata are not linked to their exact observation")
        asset_hashes = {
            key: _asset_sha256(assets, key)
            for key in ("metadata", "mask", "measurement")
        }
        geometric = metadata.get("geometric_accuracy")
        rfi = metadata.get("radio_frequency_interference")
        geometric = geometric if isinstance(geometric, dict) else {}
        rfi = rfi if isinstance(rfi, dict) else {}
        per_observation.append(
            {
                "scene_id": scene_id,
                "provider_scene_disposition": "NOT_PROVIDED_IN_RETRIEVED_SIDECAR",
                "sidecar_sha256": asset_hashes["metadata"],
                "mask_sha256": asset_hashes["mask"],
                "measurement_sha256": asset_hashes["measurement"],
                "aoi_mask_counts": {
                    "clear_code_0": mask_counts.get("clear"),
                    "layover_affected": mask_counts.get("layover_affected"),
                    "shadow_affected": mask_counts.get("shadow_affected"),
                    "invalid": mask_counts.get("invalid"),
                },
                "geometric_accuracy_metadata": {
                    key: _metadata_value(geometric, key)
                    for key in (
                        "geometric_accuracy_bias_x",
                        "geometric_accuracy_bias_y",
                        "geometric_accuracy_stddev_x",
                        "geometric_accuracy_stddev_y",
                    )
                },
                "rfi_metadata": {
                    "information_available": _metadata_value(rfi, "rfi_info_available"),
                    "burst_azimuth_time_utc": _metadata_value(rfi, "rfi_burst_azimuth_time"),
                    "swath": _metadata_value(rfi, "rfi_burst_swath"),
                    "in_band_out_band_power_ratio": _metadata_value(rfi, "rfi_in_band_out_band_power_ratio"),
                    "mitigation_performed": _metadata_value(rfi, "rfi_mitigation_performed"),
                    "mitigation_domain": _metadata_value(rfi, "rfi_mitigation_domain"),
                    "residual_impact_status": "NOT_SPATIALLY_QUANTIFIED_BY_RETAINED_METADATA",
                },
                "metadata_missing_fields": metadata.get("missing_fields", []),
            }
        )

    aoi_count = common.get("aoi_pixel_count")
    support_count = common.get("finite_positive_in_every_observation_count")
    if not isinstance(aoi_count, int) or not isinstance(support_count, int) or aoi_count <= 0:
        raise OperaRtcQualityReviewError("common-support counts are invalid")

    return {
        "record_type": "ECHO_OPERA_RTC_S1_SCOPED_QUALITY_REVIEW",
        "schema_version": 1,
        "status": "REVIEW_RECORDED_WITH_UNRESOLVED_SCENE_QUALITY_LIMITS",
        "review_basis_sha256": _basis_hash(record),
        "provider_product_validation": {
            "provider": "NASA Jet Propulsion Laboratory OPERA project",
            "source_url": JPL_RTC_PRODUCT_URL,
            "validation_scope": "Published accuracy results describe the validation data considered; they are not a per-acquisition or per-AOI certificate.",
            "published_results": [
                {
                    "measure": "absolute geolocation accuracy",
                    "requirement": "less than 6 m for 80% of validation data considered",
                    "reported_validation_data_result": "100% met the requirement",
                },
                {
                    "measure": "relative geolocation accuracy",
                    "requirement": "less than 6 m for 80% of validation data considered",
                    "reported_validation_data_result": "100% met the requirement",
                },
                {
                    "measure": "terrain flattening performance",
                    "requirement": "less than 1 dB difference between foreslope and backslope for 80% of validation data considered",
                    "reported_validation_data_result": "100% met the requirement",
                },
            ],
            "product_specification_url": RTC_PRODUCT_SPEC_URL,
            "product_qa_is_per_scene_pass_fail": False,
        },
        "provider_qa": {
            "status": qa["status"],
            "scene_level_verdict": "NOT_PROVIDED",
            "interpretation": "No provider PASS or FAIL is inferred from the JPL validation summary or local checks.",
        },
        "echo_bounded_checks": {
            "compatible_burst_platform_version_polarization": "CHECKED_BY_SERIES_VALIDATOR",
            "exact_crs_transform_window_and_aoi_centers": "CHECKED_BY_SERIES_VALIDATOR",
            "resampling": grid.get("resampling"),
            "per_acquisition_mask_source": "ASF OPERA RTC-S1 product validity mask",
            "mask_semantics_source_url": ASF_RTC_GUIDE_URL,
            "common_support_rule": common.get("mask_rule"),
            "aoi_pixel_count": aoi_count,
            "common_finite_positive_count": support_count,
            "common_support_fraction": support_count / aoi_count,
            "check_scope": "Input identity, grid, mask, numerical support, and provenance checks; not an independent product calibration or scene-level QA verdict.",
        },
        "per_observation": per_observation,
        "assessment_boundary": {
            "disposition": "DESCRIPTIVE_MEASUREMENT_REMAINS_DIAGNOSTIC",
            "rfi_residual_effect": "UNRESOLVED",
            "physical_cause_supported": False,
            "event_boundary_or_damage_established": False,
            "provider_qa_overridden": False,
        },
    }


def build_opera_rtc_pair_quality_review(record: dict[str, Any]) -> dict[str, Any]:
    """Build a source-bound, diagnostic quality review for an OPERA pair."""
    if (
        not isinstance(record, dict)
        or record.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS"
        or record.get("status") not in {
            "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON",
            "INCONCLUSIVE_NO_COMMON_CLEAR_VALID_PIXELS",
        }
    ):
        raise OperaRtcQualityReviewError("quality review requires a diagnostic OPERA RTC-S1 pair")
    products = record.get("source_products")
    provider_qa = record.get("provider_qa")
    grid = record.get("grid")
    measurement = record.get("measurement")
    checksums = record.get("checksums")
    if (
        not isinstance(products, dict)
        or not isinstance(provider_qa, dict)
        or provider_qa.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
        or not isinstance(grid, dict)
        or not isinstance(measurement, dict)
        or not isinstance(checksums, dict)
    ):
        raise OperaRtcQualityReviewError("pair source, QA, grid, or measurement records are incomplete")

    mask_counts = measurement.get("mask_counts")
    if not isinstance(mask_counts, dict):
        raise OperaRtcQualityReviewError("pair mask counts are missing")
    aoi_count = measurement.get("aoi_pixel_count")
    clear_count = measurement.get("common_clear_pixel_count")
    measured_count = measurement.get("measured_pixel_count")
    if (
        not isinstance(aoi_count, int) or isinstance(aoi_count, bool) or aoi_count <= 0
        or not isinstance(clear_count, int) or isinstance(clear_count, bool) or not 0 <= clear_count <= aoi_count
        or not isinstance(measured_count, int) or isinstance(measured_count, bool) or not 0 <= measured_count <= clear_count
        or not isinstance(mask_counts.get("aoi_pixel_count"), int)
        or isinstance(mask_counts.get("aoi_pixel_count"), bool)
        or mask_counts.get("aoi_pixel_count") != aoi_count
    ):
        raise OperaRtcQualityReviewError("pair AOI, common-clear, or measured support counts are invalid")

    per_observation = []
    basis_products = {}
    for role in ("before", "after"):
        product = products.get(role)
        if not isinstance(product, dict):
            raise OperaRtcQualityReviewError(f"{role} pair source product is missing")
        scene_id = product.get("scene_id")
        metadata = product.get("quality_metadata")
        assets = product.get("assets")
        if (
            not isinstance(scene_id, str) or not scene_id
            or not isinstance(metadata, dict)
            or metadata.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
            or product.get("provider_qa_disposition") != "NO_CONSOLIDATED_PASS_FAIL_FIELD_IN_RETRIEVED_HDF5"
            or provider_qa.get(role) != metadata.get("status")
            or not isinstance(assets, dict)
        ):
            raise OperaRtcQualityReviewError(f"{role} provider QA is not linked to its source product")
        asset_hashes = {key: _asset_sha256(assets, key) for key in ("metadata", "mask", "measurement")}
        geometric = metadata.get("geometric_accuracy")
        rfi = metadata.get("radio_frequency_interference")
        geometric = geometric if isinstance(geometric, dict) else {}
        rfi = rfi if isinstance(rfi, dict) else {}
        role_mask_counts = {
            "clear_code_0": mask_counts.get(f"{role}_clear"),
            "layover_affected": mask_counts.get(f"{role}_layover_affected"),
            "shadow_affected": mask_counts.get(f"{role}_shadow_affected"),
            "invalid": mask_counts.get(f"{role}_invalid"),
        }
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in role_mask_counts.values()):
            raise OperaRtcQualityReviewError(f"{role} AOI mask counts are incomplete")
        if any(value > aoi_count for value in role_mask_counts.values()):
            raise OperaRtcQualityReviewError(f"{role} AOI mask count exceeds the selected AOI")
        per_observation.append({
            "role": role,
            "scene_id": scene_id,
            "provider_scene_disposition": "NOT_PROVIDED_IN_RETRIEVED_SIDECAR",
            "sidecar_sha256": asset_hashes["metadata"],
            "mask_asset_sha256": asset_hashes["mask"],
            "measurement_asset_sha256": asset_hashes["measurement"],
            "aoi_mask_counts": role_mask_counts,
            "geometric_accuracy_metadata": {
                key: _metadata_value(geometric, key)
                for key in (
                    "geometric_accuracy_bias_x", "geometric_accuracy_bias_y",
                    "geometric_accuracy_stddev_x", "geometric_accuracy_stddev_y",
                )
            },
            "rfi_metadata": {
                "information_available": _metadata_value(rfi, "rfi_info_available"),
                "burst_azimuth_time_utc": _metadata_value(rfi, "rfi_burst_azimuth_time"),
                "swath": _metadata_value(rfi, "rfi_burst_swath"),
                "in_band_out_band_power_ratio": _metadata_value(rfi, "rfi_in_band_out_band_power_ratio"),
                "mitigation_performed": _metadata_value(rfi, "rfi_mitigation_performed"),
                "mitigation_domain": _metadata_value(rfi, "rfi_mitigation_domain"),
                "residual_impact_status": "NOT_SPATIALLY_QUANTIFIED_BY_RETAINED_METADATA",
            },
            "metadata_missing_fields": metadata.get("missing_fields", []),
        })
        basis_products[role] = {
            "scene_id": scene_id,
            "identity": {key: product.get(key) for key in (
                "provider", "mission", "product", "burst_id", "sensor", "product_version",
                "acquisition_start_utc", "acquisition_stop_utc", "product_generation_time_utc",
            )},
            "quality_metadata": metadata,
            "asset_sha256": asset_hashes,
            "asset_references": {
                key: {field: assets[key].get(field) for field in ("url", "sha256", "bytes")}
                for key in ("metadata", "mask", "measurement")
            },
            "access": {
                key: product.get("access", {}).get(key)
                for key in ("provider", "method", "authentication", "read_at_utc", "network_retrieval")
            },
        }

    before_identity = basis_products["before"]["identity"]
    after_identity = basis_products["after"]["identity"]
    if any(
        before_identity.get(key) != after_identity.get(key)
        for key in ("provider", "mission", "product", "burst_id", "sensor", "product_version")
    ):
        raise OperaRtcQualityReviewError("pair source acquisitions do not share their declared product identity")
    acquisition_times = []
    for role in ("before", "after"):
        identity = basis_products[role]["identity"]
        match = _PAIR_SCENE_ID.fullmatch(basis_products[role]["scene_id"])
        if match is None:
            raise OperaRtcQualityReviewError(f"{role} source scene identifier is not a supported RTC-S1 scene")
        try:
            acquired = datetime.fromisoformat(str(identity.get("acquisition_start_utc", "")).replace("Z", "+00:00"))
            encoded = datetime.strptime(match.group("acquired"), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        except ValueError as exc:
            raise OperaRtcQualityReviewError(f"{role} acquisition timestamp is invalid") from exc
        if (
            acquired.tzinfo is None
            or acquired.astimezone(timezone.utc) != encoded
            or match.group("burst") != identity.get("burst_id")
            or match.group("platform") != identity.get("sensor")
            or match.group("version") != identity.get("product_version")
        ):
            raise OperaRtcQualityReviewError(f"{role} scene identifier and acquisition metadata disagree")
        acquisition_times.append(acquired.astimezone(timezone.utc))
    if acquisition_times[0] >= acquisition_times[1]:
        raise OperaRtcQualityReviewError("pair acquisitions are not in before/after chronological order")
    if (
        not isinstance(measurement.get("polarization"), str)
        or not measurement["polarization"]
        or grid.get("registration_gate") != "EXACT_CRS_TRANSFORM_SHAPE_AND_AOI_CENTER_SELECTION_MATCH"
        or grid.get("resampling") != "NONE"
        or not isinstance(mask_counts.get("before_clear"), int)
        or isinstance(mask_counts.get("before_clear"), bool)
        or mask_counts["before_clear"] > aoi_count
        or not isinstance(mask_counts.get("after_clear"), int)
        or isinstance(mask_counts.get("after_clear"), bool)
        or mask_counts["after_clear"] > aoi_count
        or clear_count > min(mask_counts["before_clear"], mask_counts["after_clear"])
        or measurement.get("quantity") != "signed_gamma0_log_ratio_db"
        or measurement.get("units") != "dB"
        or before_identity.get("provider") != "Alaska Satellite Facility DAAC"
        or before_identity.get("mission") != "Sentinel-1"
        or before_identity.get("product") != "NASA OPERA L2 RTC-S1"
        or not isinstance(record.get("processing"), dict)
        or not isinstance(record.get("processing", {}).get("method"), str)
        or not isinstance(record.get("processing", {}).get("software"), dict)
    ):
        raise OperaRtcQualityReviewError("pair grid registration, polarization, or common support is inconsistent")

    checksum_names = (
        "before_values_sha256", "after_values_sha256", "before_mask_sha256", "after_mask_sha256",
        "before_selection_mask_sha256", "after_selection_mask_sha256", "change_values_sha256",
        "change_valid_mask_sha256",
    )
    derived_hashes = {key: checksums.get(key) for key in checksum_names}
    if any(
        not isinstance(value, str) or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
        for value in derived_hashes.values()
    ):
        raise OperaRtcQualityReviewError("pair measurement checksums are incomplete or invalid")
    raw_values = measurement.get("values_db")
    raw_valid = measurement.get("valid_mask")
    shape = grid.get("window", {}).get("shape") if isinstance(grid.get("window"), dict) else None
    if (
        not isinstance(shape, list) or len(shape) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in shape)
        or not isinstance(raw_values, list) or len(raw_values) != shape[0]
        or not isinstance(raw_valid, list) or len(raw_valid) != shape[0]
        or any(not isinstance(row, list) or len(row) != shape[1] for row in raw_values)
        or any(not isinstance(row, list) or len(row) != shape[1] for row in raw_valid)
        or any(not isinstance(value, bool) for row in raw_valid for value in row)
        or any(value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)) for row in raw_values for value in row)
    ):
        raise OperaRtcQualityReviewError("pair derived arrays do not match the declared grid")
    try:
        values_array = np.asarray(
            [[np.nan if value is None else value for value in row] for row in raw_values],
            dtype=np.float32,
        )
        valid_array = np.asarray(raw_valid, dtype=bool)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OperaRtcQualityReviewError("pair derived arrays contain invalid numeric values") from exc
    if (
        int(valid_array.sum()) != measured_count
        or not np.isfinite(values_array[valid_array]).all()
        or np.isfinite(values_array[~valid_array]).any()
        or _matrix_sha256(values_array) != derived_hashes["change_values_sha256"]
        or _matrix_sha256(valid_array) != derived_hashes["change_valid_mask_sha256"]
    ):
        raise OperaRtcQualityReviewError("pair derived measurement arrays do not match their retained checksums")
    basis = {
        "source_products": basis_products,
        "provider_qa": provider_qa,
        "grid": {key: grid.get(key) for key in ("crs", "transform", "window", "registration_gate", "resampling")},
        "measurement": {
            "quantity": measurement.get("quantity"), "equation": measurement.get("equation"),
            "polarization": measurement.get("polarization"), "units": measurement.get("units"),
            "aoi_pixel_count": aoi_count, "common_clear_pixel_count": clear_count,
            "measured_pixel_count": measured_count, "mask_counts": mask_counts,
            "derived_sha256": derived_hashes,
        },
        "processing": record.get("processing"),
    }
    basis_hash = sha256(json.dumps(basis, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
    return {
        "record_type": "ECHO_OPERA_RTC_S1_SCOPED_QUALITY_REVIEW",
        "schema_version": 1,
        "scope": "TWO_ACQUISITION_PAIR",
        "status": "REVIEW_RECORDED_WITH_UNRESOLVED_SCENE_QUALITY_LIMITS",
        "review_basis_sha256": basis_hash,
        "provider_product_validation": {
            "provider": "NASA Jet Propulsion Laboratory OPERA project",
            "source_url": JPL_RTC_PRODUCT_URL,
            "validation_scope": "Published accuracy results describe the validation data considered; they are not a per-acquisition or per-AOI certificate.",
            "published_results": [
                {"measure": "absolute geolocation accuracy", "requirement": "less than 6 m for 80% of validation data considered", "reported_validation_data_result": "100% met the requirement"},
                {"measure": "relative geolocation accuracy", "requirement": "less than 6 m for 80% of validation data considered", "reported_validation_data_result": "100% met the requirement"},
                {"measure": "terrain flattening performance", "requirement": "less than 1 dB difference between foreslope and backslope for 80% of validation data considered", "reported_validation_data_result": "100% met the requirement"},
            ],
            "product_specification_url": RTC_PRODUCT_SPEC_URL,
            "product_qa_is_per_scene_pass_fail": False,
        },
        "provider_qa": {
            "status": provider_qa["status"],
            "scene_level_verdict": "NOT_PROVIDED",
            "interpretation": "No provider PASS or FAIL is inferred from the JPL validation summary or local checks.",
        },
        "echo_bounded_checks": {
            "compatible_burst_platform_version_polarization": "CHECKED_BY_PAIR_BUILDER",
            "exact_crs_transform_window_and_aoi_centers": "CHECKED_BY_PAIR_BUILDER",
            "registration_gate": grid.get("registration_gate"),
            "resampling": grid.get("resampling"),
            "per_acquisition_mask_source": "ASF OPERA RTC-S1 product validity mask",
            "mask_semantics_source_url": ASF_RTC_GUIDE_URL,
            "common_clear_support_count": clear_count,
            "common_finite_positive_count": measured_count,
            "aoi_pixel_count": aoi_count,
            "common_clear_support_fraction": clear_count / aoi_count,
            "common_finite_positive_fraction": measured_count / aoi_count,
            "derived_change_values_sha256": derived_hashes["change_values_sha256"],
            "derived_change_mask_sha256": derived_hashes["change_valid_mask_sha256"],
            "check_scope": "Input identity, grid, mask, numerical support, and provenance checks; not an independent product calibration or scene-level QA verdict.",
        },
        "per_observation": per_observation,
        "assessment_boundary": {
            "disposition": (
                "DESCRIPTIVE_MEASUREMENT_REMAINS_DIAGNOSTIC"
                if record.get("status") == "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
                else "NO_COMPARISON_MEASUREMENT_AVAILABLE"
            ),
            "rfi_residual_effect": "UNRESOLVED",
            "physical_cause_supported": False,
            "event_boundary_or_damage_established": False,
            "provider_qa_overridden": False,
        },
    }
