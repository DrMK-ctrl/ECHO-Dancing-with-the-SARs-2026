"""Validate and summarize aligned AOI windows from a GUNW temporal sequence.

This review compares descriptive coherence summaries only. It never differences
unwrapped phase or turns pair metrics into a surface-change finding.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metadata_record(
    catalog: dict[str, Any], window: dict[str, Any], path: Path
) -> dict[str, Any]:
    scene_id = window.get("scene_id")
    record = next(
        (item for item in catalog.get("records", []) if item.get("scene_id") == scene_id),
        None,
    )
    if record is None:
        raise ValueError(f"window scene is absent from the catalog record: {scene_id}")
    feature = record.get("catalog_feature")
    if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
        raise ValueError(f"catalog feature is malformed for scene: {scene_id}")
    if window.get("catalog_feature_sha256") != record.get("catalog_feature_sha256"):
        raise ValueError(f"catalog feature hash mismatch for scene: {scene_id}")
    qa = record.get("provider_qa_summary", {})
    window_qa = window.get("provider_qa", {})
    if (
        window_qa.get("artifact_sha256") != qa.get("artifact_sha256")
        or window_qa.get("status") != qa.get("observed_provider_status")
    ):
        raise ValueError(f"provider QA reference mismatch for scene: {scene_id}")
    if window_qa.get("status") not in {
        "PASS",
        "FAIL",
        "INDETERMINATE",
        "NO_FAIL_REPORTED",
    }:
        raise ValueError(f"provider QA disposition is missing or unknown: {scene_id}")
    disposition = window.get("scientific_disposition", {})
    if any(
        disposition.get(flag) is not False
        for flag in (
            "phase_correction_applied",
            "phase_to_displacement_conversion_applied",
            "change_measurement_performed",
            "event_extent_or_cause_inferred",
        )
    ):
        raise ValueError(f"window record is not a raw QA characterization: {scene_id}")

    coherence = window.get("layers", {}).get("coherenceMagnitude", {}).get(
        "selected_aoi_centers", {}
    )
    phase = window.get("layers", {}).get("unwrappedPhase", {}).get(
        "selected_aoi_centers", {}
    )
    for name, summary in (("coherenceMagnitude", coherence), ("unwrappedPhase", phase)):
        if not isinstance(summary, dict) or summary.get("sample_count") != window.get(
            "window", {}
        ).get("selected_pixel_center_count"):
            raise ValueError(f"{name} summary count does not match AOI for scene: {scene_id}")
    properties = feature["properties"]
    identification = window.get("identification", {})
    reference_start = identification.get("referenceZeroDopplerStartTime")
    secondary_start = identification.get("secondaryZeroDopplerStartTime")
    reference_orbit = identification.get("referenceAbsoluteOrbitNumber")
    secondary_orbit = identification.get("secondaryAbsoluteOrbitNumber")
    if (
        not isinstance(reference_start, str)
        or not isinstance(secondary_start, str)
        or not isinstance(reference_orbit, int)
        or not isinstance(secondary_orbit, int)
    ):
        raise ValueError(f"GUNW reference/secondary acquisition identity is incomplete: {scene_id}")

    def parse_product_utc(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)

    parsed_start = parse_product_utc(reference_start)
    parsed_stop = parse_product_utc(secondary_start)
    if parsed_stop <= parsed_start:
        raise ValueError(f"catalog pair interval is invalid for scene: {scene_id}")
    catalog_orbit = properties.get("orbit")
    if catalog_orbit is not None and int(catalog_orbit) != reference_orbit:
        raise ValueError(f"catalog orbit does not match the GUNW reference orbit: {scene_id}")

    grid = window.get("grid", {})
    selected = window.get("window", {})
    return {
        "scene_id": scene_id,
        "catalog_feature_sha256": record["catalog_feature_sha256"],
        "provider_qa": {
            "status": window_qa["status"],
            "artifact_uri": window_qa.get("artifact_uri"),
            "artifact_sha256": window_qa["artifact_sha256"],
        },
        "acquisition_pair": {
            "reference_start_utc": reference_start,
            "secondary_start_utc": secondary_start,
            "baseline_days": round((parsed_stop - parsed_start).total_seconds() / 86400, 6),
            "reference_orbit": reference_orbit,
            "secondary_orbit": secondary_orbit,
            "time_source": "GUNW HDF5 identification reference/secondary Zero Doppler start times, UTC",
            "catalog_product_extent_utc": {
                "start": properties.get("startTime"),
                "stop": properties.get("stopTime"),
            },
            "crid": properties.get("crid"),
            "collection": properties.get("collectionName"),
            "path_number": properties.get("pathNumber"),
            "frame_number": properties.get("frameNumber"),
            "flight_direction": properties.get("flightDirection"),
            "polarization": properties.get("mainBandPolarization"),
        },
        "aoi_pixel_count": selected.get("selected_pixel_center_count"),
        "grid_epsg": grid.get("epsg_code"),
        "coordinate_sha256": selected.get("coordinate_sha256"),
        "coherence_summary": coherence,
        "phase_summary_recorded_separately": phase,
        "mask_summary": window.get("decoded_mask_summary"),
        "range_bytes_requested": window.get("range_read", {}).get(
            "range_bytes_requested"
        ),
        "window_record_path": str(path),
        "window_record_sha256": _sha256_file(path),
        "layer_hashes": {
            name: layer.get("sha256")
            for name, layer in window.get("layers", {}).items()
        },
    }


def build_record(catalog_path: Path, window_paths: list[Path]) -> dict[str, Any]:
    catalog = _read_json(catalog_path)
    if catalog.get("record_type") != "ECHO_GUNW_TEMPORAL_CATALOG_QA_REVIEW":
        raise ValueError("catalog input is not an ECHO GUNW temporal catalog/QA record")
    if len(window_paths) < 2:
        raise ValueError("at least two window records are required")
    items = []
    for path in window_paths:
        window = _read_json(path)
        if window.get("record_type") != "ECHO_GUNW_BOUNDED_PIXEL_WINDOW_REVIEW":
            raise ValueError(f"unsupported window record: {path}")
        items.append(_metadata_record(catalog, window, path))
    items.sort(key=lambda item: item["acquisition_pair"]["reference_start_utc"])

    identity_fields = (
        "crid",
        "collection",
        "path_number",
        "frame_number",
        "flight_direction",
        "polarization",
    )
    identity = items[0]["acquisition_pair"]
    if any(
        any(
            item["acquisition_pair"].get(field) != identity.get(field)
            for field in identity_fields
        )
        for item in items[1:]
    ):
        raise ValueError("GUNW products are not compatible in CRID/path/frame/direction/polarization")
    first_window = _read_json(Path(items[0]["window_record_path"]))
    for path in window_paths[1:]:
        current = _read_json(path)
        if (
            current.get("bounds_wgs84") != first_window.get("bounds_wgs84")
            or current.get("polarization") != first_window.get("polarization")
            or current.get("grid", {}).get("epsg_code") != items[0]["grid_epsg"]
            or current.get("window", {}).get("selected_pixel_center_count")
            != items[0]["aoi_pixel_count"]
            or current.get("window", {}).get("coordinate_sha256")
            != items[0]["coordinate_sha256"]
        ):
            raise ValueError("AOI, selected pixel count, or pixel-center coordinate hashes differ")
    for before, after in zip(items, items[1:]):
        if (
            before["acquisition_pair"]["secondary_orbit"]
            != after["acquisition_pair"]["reference_orbit"]
        ):
            raise ValueError("GUNW pairs do not form a continuous absolute-orbit chain")

    means = [item["coherence_summary"].get("mean") for item in items]
    if any(
        not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in means
    ):
        raise ValueError("coherence summaries are missing finite means")
    tool_sha256 = _sha256_file(Path(__file__))
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    return {
        "schema_version": 1,
        "record_type": "ECHO_GUNW_TEMPORAL_AOI_QUALITY_COMPARISON",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_revision": revision,
        "tool_source_sha256": tool_sha256,
        "catalog_record": {
            "path": str(catalog_path),
            "sha256": _sha256_file(catalog_path),
            "retrieved_at_utc": catalog.get("retrieved_at_utc"),
        },
        "comparison_contract": {
            "product": "NISAR L2 GUNW",
            "purpose": "descriptive AOI-level coherence and quality continuity review",
            "required_same_inputs": [
                "CRID, collection, path, frame, flight direction, polarization",
                "WGS84 AOI bounds, projected grid EPSG, selected pixel-center coordinates",
                "selected AOI pixel-center count",
            ],
            "provider_qa_requirement": "Each provider QA disposition is retained unchanged; every non-PASS status remains a hold.",
            "coherence_comparison": "Per-pair AOI summaries are listed; no threshold or significance test is applied.",
            "phase_handling": "Each pair phase summary is recorded separately. Cross-pair phase comparison and differencing are prohibited in this record.",
            "temporal_pair_source": "GUNW HDF5 reference/secondary Zero Doppler times and absolute-orbit identifiers; ASF feature start/stop times are retained only as product extent metadata.",
            "pair_network_rule": "Every adjacent pair must share the previous pair's secondary absolute orbit as the next pair's reference absolute orbit.",
            "measurement_or_event_finding": False,
        },
        "common_aoi": {
            "bounds_wgs84": first_window["bounds_wgs84"],
            "label": first_window.get("aoi_label"),
            "selected_pixel_center_count": items[0]["aoi_pixel_count"],
            "grid_epsg": items[0]["grid_epsg"],
            "coordinate_sha256": items[0]["coordinate_sha256"],
        },
        "orbit_chain": [
            {
                "reference_orbit": item["acquisition_pair"]["reference_orbit"],
                "secondary_orbit": item["acquisition_pair"]["secondary_orbit"],
            }
            for item in items
        ],
        "coherence_mean_descriptive_range": {
            "minimum_across_pairs": min(means),
            "maximum_across_pairs": max(means),
            "spread": max(means) - min(means),
            "interpretation": "descriptive variation among pair-specific AOI means; not a change magnitude, significance, confidence, or damage score",
        },
        "pairs": items,
        "scientific_disposition": {
            "status": (
                "QA_HELD_DESCRIPTIVE_TEMPORAL_CHARACTERIZATION"
                if any(item["provider_qa"]["status"] != "PASS" for item in items)
                else "PASS_QA_DESCRIPTIVE_ONLY"
            ),
            "provider_qa_failures_overridden": False,
            "phase_correction_applied": False,
            "cross_pair_phase_comparison_performed": False,
            "phase_to_displacement_conversion_performed": False,
            "event_extent_or_cause_inferred": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--windows", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = build_record(args.catalog, args.windows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote QA-held descriptive GUNW comparison for {len(record['pairs'])} aligned windows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
