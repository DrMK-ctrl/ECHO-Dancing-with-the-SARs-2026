"""Reproducible comparison of metadata for a two-scene OPERA RTC-S1 pair.

This module compares only fields explicitly retained from the two source
products. It does not evaluate raster co-registration, infer a cause, or clear
provider QA.
"""

from __future__ import annotations

from typing import Any


RECORD_TYPE = "ECHO_OPERA_RTC_ACQUISITION_CONDITION_REVIEW"
RECORD_STATUS = "DESCRIPTIVE_METADATA_REVIEW_NOT_CAUSAL_OR_QA_CLEARANCE"


class AcquisitionConditionError(ValueError):
    """Raised when source metadata cannot support a reproducible comparison."""


def _comparison(label: str, before: Any, after: Any, *, role: str) -> dict[str, Any]:
    if before is None or after is None:
        state = "NOT_REPORTED"
    elif before == after:
        state = "MATCH"
    else:
        state = "DIFFERS"
    return {
        "field": label,
        "role": role,
        "before": before,
        "after": after,
        "comparison": state,
    }


def build_acquisition_condition_review(
    pair: dict[str, Any],
    *,
    case_id: str,
    source_record_path: str,
    source_record_sha256: str,
) -> dict[str, Any]:
    """Create a bounded, traceable metadata review from an OPERA pair record."""
    if pair.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        raise AcquisitionConditionError("source is not an OPERA RTC-S1 pair-analysis record")
    products = pair.get("source_products")
    if not isinstance(products, dict) or not isinstance(products.get("before"), dict) or not isinstance(products.get("after"), dict):
        raise AcquisitionConditionError("pair record is missing before/after source products")
    before, after = products["before"], products["after"]
    if not before.get("scene_id") or not after.get("scene_id") or before["scene_id"] == after["scene_id"]:
        raise AcquisitionConditionError("pair record must identify two distinct source scenes")
    for role, product in (("before", before), ("after", after)):
        quality = product.get("quality_metadata")
        if (
            not isinstance(quality, dict)
            or quality.get("status") != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
            or not isinstance(quality.get("asset"), dict)
            or not quality["asset"].get("sha256")
        ):
            raise AcquisitionConditionError(f"{role} product lacks hash-linked, diagnostic QA metadata")

    before_quality = before["quality_metadata"]
    after_quality = after["quality_metadata"]
    before_catalog = before.get("catalog_metadata", {})
    after_catalog = after.get("catalog_metadata", {})

    comparisons = [
        _comparison("mission", before.get("mission"), after.get("mission"), role="platform_configuration"),
        _comparison("sensor", before.get("sensor"), after.get("sensor"), role="platform_configuration"),
        _comparison("product", before.get("product"), after.get("product"), role="product_configuration"),
        _comparison("product_version", before.get("product_version"), after.get("product_version"), role="product_configuration"),
        _comparison("burst_id", before.get("burst_id"), after.get("burst_id"), role="acquisition_geometry_identifier"),
        _comparison("flightDirection", before_catalog.get("flightDirection"), after_catalog.get("flightDirection"), role="acquisition_geometry"),
        _comparison("beamModeType", before_catalog.get("beamModeType"), after_catalog.get("beamModeType"), role="acquisition_geometry"),
        _comparison("polarization", before_catalog.get("polarization"), after_catalog.get("polarization"), role="sensor_configuration"),
        _comparison(
            "processing_algorithms",
            before_quality.get("processing_information", {}).get("algorithms"),
            after_quality.get("processing_information", {}).get("algorithms"),
            role="processing_configuration",
        ),
        _comparison(
            "processing_parameters",
            before_quality.get("processing_information", {}).get("parameters"),
            after_quality.get("processing_information", {}).get("parameters"),
            role="processing_configuration",
        ),
        _comparison(
            "dem_source",
            before_quality.get("processing_information", {}).get("inputs", {}).get("demSource"),
            after_quality.get("processing_information", {}).get("inputs", {}).get("demSource"),
            role="processing_input",
        ),
        _comparison(
            "geometric_accuracy_metadata",
            before_quality.get("geometric_accuracy"),
            after_quality.get("geometric_accuracy"),
            role="reported_product_quality_metadata",
        ),
        _comparison(
            "rfi_burst_report",
            before_quality.get("radio_frequency_interference"),
            after_quality.get("radio_frequency_interference"),
            role="per_acquisition_rfi_metadata",
        ),
        _comparison(
            "l1_slc_granules",
            before_quality.get("processing_information", {}).get("inputs", {}).get("l1SlcGranules"),
            after_quality.get("processing_information", {}).get("inputs", {}).get("l1SlcGranules"),
            role="acquisition_specific_processing_input",
        ),
        _comparison(
            "orbit_files",
            before_quality.get("processing_information", {}).get("inputs", {}).get("orbitFiles"),
            after_quality.get("processing_information", {}).get("inputs", {}).get("orbitFiles"),
            role="acquisition_specific_processing_input",
        ),
    ]
    if any(item["comparison"] == "NOT_REPORTED" for item in comparisons[:11]):
        missing = [item["field"] for item in comparisons[:11] if item["comparison"] == "NOT_REPORTED"]
        raise AcquisitionConditionError(f"required paired metadata are missing: {', '.join(missing)}")

    geometric = comparisons[11]
    rfi_before = before_quality["radio_frequency_interference"].get("rfi_in_band_out_band_power_ratio", {}).get("value")
    rfi_after = after_quality["radio_frequency_interference"].get("rfi_in_band_out_band_power_ratio", {}).get("value")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (rfi_before, rfi_after)):
        raise AcquisitionConditionError("per-acquisition RFI burst power ratios are missing or invalid")

    return {
        "record_type": RECORD_TYPE,
        "schema_version": 1,
        "status": RECORD_STATUS,
        "case_id": case_id,
        "source": {
            "provider": "Alaska Satellite Facility DAAC",
            "mission": before.get("mission"),
            "product": before.get("product"),
            "source_pair_record_path": source_record_path,
            "source_pair_record_sha256": source_record_sha256,
            "scene_ids": [before["scene_id"], after["scene_id"]],
            "hdf5_sidecar_sha256": [
                before_quality["asset"]["sha256"],
                after_quality["asset"]["sha256"],
            ],
        },
        "method": {
            "name": "allowlisted exact-field comparison of retained OPERA RTC-S1 product metadata",
            "version": "1",
            "no_numeric_score": True,
            "no_spatial_rfi_association_computed": True,
            "no_incidence_angle_metadata_in_source_record": True,
        },
        "acquisitions": [
            {
                "role": role,
                "scene_id": product["scene_id"],
                "acquisition_start_utc": product.get("acquisition_start_utc"),
                "acquisition_stop_utc": product.get("acquisition_stop_utc"),
                "product_generation_time_utc": product.get("product_generation_time_utc"),
                "sidecar_retrieval_status": product["quality_metadata"]["status"],
            }
            for role, product in (("before", before), ("after", after))
        ],
        "comparisons": comparisons,
        "summary": {
            "platform_configuration_matches": all(item["comparison"] == "MATCH" for item in comparisons[:2]),
            "documented_product_configuration_matches": all(item["comparison"] == "MATCH" for item in comparisons[2:8]),
            "documented_processing_configuration_matches": all(item["comparison"] == "MATCH" for item in comparisons[8:11]),
            "reported_geometric_accuracy_metadata_match": geometric["comparison"] == "MATCH",
            "rfi_burst_metadata_comparison": comparisons[12]["comparison"],
            "rfi_power_ratio_before": rfi_before,
            "rfi_power_ratio_after": rfi_after,
            "incidence_angle_metadata_available": False,
            "spatially_matched_rfi_evidence_available": False,
            "causal_disposition": "UNRESOLVED",
            "hypothesis_relation": "DOES_NOT_DISTINGUISH",
            "testability_state": "NOT_TESTABLE_WITH_RETAINED_EVIDENCE",
        },
        "interpretation": (
            "The retained fields show matching documented platform, burst, mode, polarization, RTC algorithm, processing parameters, DEM source, and reported geometric-accuracy values. The per-acquisition RFI burst reports differ, but the retained summary is not spatially associated with the AOI response; incidence-angle metadata are also absent from this source record. These metadata therefore do not distinguish whether acquisition conditions contributed to the measured SAR response. The products remain diagnostic because neither sidecar supplies a consolidated provider QA disposition."
        ),
        "limitations": [
            "The comparison is limited to fields retained in the checksum-linked sidecars and ASF catalog metadata.",
            "Matching reported geometric-accuracy values do not establish temporal co-registration or raster alignment.",
            "Per-burst RFI power ratios are not spatially matched to the AOI and are not a scene-level clearance verdict.",
            "Incidence-angle metadata were not present in the retained source record.",
            "This review does not establish a physical cause, validate backscatter change, or clear provider QA.",
        ],
    }


def validate_acquisition_condition_review(
    record: dict[str, Any],
    *,
    pair_record: dict[str, Any],
    pair_record_sha256: str,
    case_id: str,
) -> None:
    """Fail closed if a review is linked to other scenes or a different source."""
    source = record.get("source", {})
    if (
        record.get("record_type") != RECORD_TYPE
        or record.get("schema_version") != 1
        or record.get("status") != RECORD_STATUS
        or record.get("case_id") != case_id
        or source.get("source_pair_record_sha256") != pair_record_sha256
    ):
        raise AcquisitionConditionError("acquisition-condition review identity, source, or limits are invalid")
    expected = build_acquisition_condition_review(
        pair_record,
        case_id=case_id,
        source_record_path=source.get("source_pair_record_path"),
        source_record_sha256=pair_record_sha256,
    )
    actual = {key: value for key, value in record.items() if key != "created_at_utc"}
    if actual != expected:
        raise AcquisitionConditionError("acquisition-condition review does not reproduce from its linked pair metadata")
