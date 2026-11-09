"""Bounded quality context for retained NASA OPERA RTC-S1 measurements."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


JPL_RTC_PRODUCT_URL = "https://www.jpl.nasa.gov/go/opera/products/rtc-product/"
RTC_PRODUCT_SPEC_URL = "https://d2pn8kiwq2w21t.cloudfront.net/documents/ProductSpec_RTC-S1.pdf"
ASF_RTC_GUIDE_URL = "https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/"


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
