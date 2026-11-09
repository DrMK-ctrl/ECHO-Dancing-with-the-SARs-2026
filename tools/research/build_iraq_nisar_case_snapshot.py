#!/usr/bin/env python3
"""Build a replayable Iraq case snapshot from retained ASF/NISAR records.

This is a local, deterministic assembly step. It performs no catalog or product
requests and does not change the source records' QA dispositions.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CASE_ID = "iraq-2026-nisar-gcov-diagnostic"
SCENE_PAIR = (
    "NISAR_L2_PR_GCOV_032_122_D_070_2005_DHDH_A_20261008T160723_20261008T160758_P05023_N_F_J_001",
    "NISAR_L2_PR_GCOV_033_122_D_070_2005_DHDH_A_20261020T160723_20261020T160758_P05023_N_F_J_001",
)
CATALOG_PATH = Path("data/research/provisional-gcov-path122-frame70-iraq-aoi-2026-10-08-20.json")
QA_PATH = Path("data/research/provisional-gcov-iraq-aoi-p05023-qa-sample-2026-11-08.json")
PREVIEW_PATH = Path("data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json")
OUTPUT_DIR = Path("data/cases/iraq-2026-nisar-diagnostic")


def _read(relative_path: Path) -> tuple[dict[str, Any], str]:
    payload = (ROOT / relative_path).read_bytes()
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError(f"{relative_path} must contain a JSON object")
    return value, sha256(payload).hexdigest()


def build_case() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    catalog_screen, catalog_hash = _read(CATALOG_PATH)
    qa_screen, qa_hash = _read(QA_PATH)
    preview, preview_hash = _read(PREVIEW_PATH)
    if (
        catalog_screen.get("record_type") != "ASF_NISAR_PROVISIONAL_GCOV_SPATIAL_TEMPORAL_SCREEN"
        or catalog_screen.get("catalog_query", {}).get("query_coverage_status") != "COMPLETE"
        or catalog_screen.get("potentially_truncated_window_count") != 0
        or qa_screen.get("record_type") != "NISAR_GCOV_ALTERNATE_CRID_QA_SCREEN"
        or qa_screen.get("primary_pinned_crid") != "P05023"
        or preview.get("record_type") != "ECHO_GCOV_SINGLE_OBSERVATION_PREVIEW"
        or preview.get("scientific_disposition") != "QA_HELD_DIAGNOSTIC_PREVIEW"
    ):
        raise ValueError("retained source records do not match the expected NISAR diagnostic inputs")

    source_features = {
        feature.get("properties", {}).get("fileID"): feature
        for feature in catalog_screen.get("features", [])
        if isinstance(feature, dict) and isinstance(feature.get("properties"), dict)
    }
    features = [source_features.get(scene_id) for scene_id in SCENE_PAIR]
    if any(feature is None for feature in features):
        raise ValueError("the selected path 122/frame 70 scenes are missing from the retained catalog screen")
    source_pairs = [
        pair for pair in catalog_screen.get("metadata_temporal_pairs", [])
        if pair.get("before_scene") == SCENE_PAIR[0] and pair.get("after_scene") == SCENE_PAIR[1]
    ]
    if len(source_pairs) != 1:
        raise ValueError("the retained catalog screen does not contain exactly one selected metadata pair")
    pair = source_pairs[0]
    if (
        pair.get("status") != "METADATA_MATCH_ONLY"
        or pair.get("interval_days") != 12.0
        or pair.get("path") != 122
        or pair.get("frame") != 70
        or pair.get("crid") != "P05023"
    ):
        raise ValueError("the retained candidate does not match the declared same-path/frame P05023 pair")

    qa_products = qa_screen.get("products", {})
    products: list[dict[str, Any]] = []
    qa_report_records: dict[str, Any] = {}
    for scene_id in SCENE_PAIR:
        product = qa_products.get(scene_id)
        if not isinstance(product, dict):
            raise ValueError(f"provider QA screen has no record for {scene_id}")
        summary = product.get("provider_qa_summary", {}).get("evidence", {})
        report = product.get("provider_qa_report", {})
        if summary.get("status") != "FAIL" or report.get("scene_id") != scene_id:
            raise ValueError(f"provider QA evidence does not retain the expected FAIL for {scene_id}")
        qa_report_records[scene_id] = report
        metadata = product["catalog_metadata"]
        products.append({
            "scene_id": scene_id,
            "acquisition_time_utc": metadata["startTime"],
            "orbit": metadata["orbit"],
            "qa_summary": {
                "identification_group": summary["status"],
                "artifact_uri": summary["artifact_uri"],
                "artifact_sha256": summary["artifact_sha256"],
                "retrieved_at_utc": product["provider_qa_summary"]["retrieved_at_utc"],
            },
            "qa_report": {
                "artifact_uri": report["artifact_uri"],
                "artifact_sha256": report["artifact_sha256"],
                "qa_software_version": report.get("qa_software_version"),
                "identification_crosscheck": report.get("identification_crosscheck"),
                "scope_limit": "ECHO cross-check against nisarqa source rules; not a provider per-field QA result.",
            },
        })

    preview_scene = preview.get("source", {}).get("scene_id")
    if preview_scene != SCENE_PAIR[1]:
        raise ValueError("the retained bounded measurement preview is not the selected after-scene")
    bounds = preview.get("grid", {}).get("window", {}).get("bounds_wgs84")
    if not isinstance(bounds, list) or len(bounds) != 4:
        raise ValueError("the bounded preview has no valid WGS84 area")

    catalog = {
        "schema_version": 1,
        "queried_at_utc": catalog_screen["retrieved_at_utc"],
        "feature_count": len(features),
        "features": features,
        "metadata_candidate_pairs": [pair],
        "query": {
            "data_maturity": "PROVISIONAL",
            "dataset": "NISAR",
            "end_date": "2026-10-20",
            "latitude": (bounds[1] + bounds[3]) / 2,
            "longitude": (bounds[0] + bounds[2]) / 2,
            "processing_level": "GCOV",
            "start_date": "2026-10-08",
            "bounds_wgs84": bounds,
        },
        "source": {
            "api_client": "asf_search",
            "catalog_only": True,
            "pixels_downloaded": False,
            "provider": "Alaska Satellite Facility DAAC",
            "case_snapshot_source": str(CATALOG_PATH),
            "case_snapshot_source_sha256": catalog_hash,
            "provider_qa_screen_source": str(QA_PATH),
            "provider_qa_screen_source_sha256": qa_hash,
            "interpretation_limit": "Two catalog-compatible footprints are metadata evidence only; valid-pixel overlap, co-registration, and a usable temporal comparison have not been established.",
        },
        "interpretation_limit": "This case uses a bounded NISAR GCOV sample. Both pair products retain provider QA FAIL; the after-scene raster is diagnostic only.",
    }

    case_review = {
        "schema_version": 1,
        "case_id": CASE_ID,
        "reviewed_on_utc_date": qa_screen["created_at_utc"][:10],
        "status": "QA_HOLD_DIAGNOSTIC_PREVIEW",
        "status_label": "NISAR P05023 · PROVIDER QA FAIL · DIAGNOSTIC PREVIEW ONLY",
        "scientific_analysis_performed": False,
        "nisar_raster_pixels_read": True,
        "event": {"name": "Iraq AOI · NISAR GCOV sample"},
        "location_label": f"Iraq AOI · {catalog['query']['longitude']:.4f}°E · {catalog['query']['latitude']:.4f}°N",
        "candidate_question": "What does the bounded NISAR observation measure here, and why is the metadata-matched pair held from change analysis?",
        "summary": "ECHO has a real bounded HHHH backscatter preview from the October 20 acquisition. Both products in the 12-day same-path/frame candidate retain provider QA FAIL, so pair analysis is held and no change result is computed.",
        "catalog_query": {
            "provider": "Alaska Satellite Facility DAAC",
            "queried_on_utc_date": catalog_screen["retrieved_at_utc"][:10],
            "longitude": catalog["query"]["longitude"],
            "latitude": catalog["query"]["latitude"],
            "start_date": catalog["query"]["start_date"],
            "end_date": catalog["query"]["end_date"],
            "data_maturity": "PROVISIONAL",
            "feature_count": len(features),
            "local_snapshot": str(OUTPUT_DIR / "catalog.json"),
            "source_search_bounds_wgs84": catalog_screen["catalog_query"]["spatial_filter"]["bounds"],
            "source_catalog_screen": str(CATALOG_PATH),
            "source_catalog_screen_sha256": catalog_hash,
        },
        "candidate_pair": {
            "status": "METADATA_MATCH_ONLY",
            "qa_status": "QA_HOLD",
            "collection": "NISAR_L2_GCOV_PROVISIONAL_V1",
            "processing_release": "P05023",
            "path": 122,
            "frame": 70,
            "orbit_direction": "DESCENDING",
            "polarizations": ["HH", "HV"],
            "interval_days": 12.0,
            "metadata_footprints_intersect": True,
            "before": {"scene_id": SCENE_PAIR[0], "acquisition_time_utc": products[0]["acquisition_time_utc"]},
            "after": {"scene_id": SCENE_PAIR[1], "acquisition_time_utc": products[1]["acquisition_time_utc"]},
            "products": products,
            "interpretation_limit": "Provider QA FAIL is retained for both products. Metadata footprint overlap does not establish valid-pixel overlap, co-registration, or analytical suitability.",
        },
        "products": products,
        "diagnostic_single_observation_preview": {
            "record_type": preview["record_type"],
            "record_path": str(PREVIEW_PATH),
            "record_sha256": preview_hash,
            "scene_id": preview_scene,
            "scientific_disposition": preview["scientific_disposition"],
            "measurement": preview["measurement"]["dataset"],
            "units": preview["measurement"]["units"],
            "acquired_at_utc": products[1]["acquisition_time_utc"],
            "bounds_wgs84": bounds,
            "selected_pixel_center_count": preview["access"]["geographic_selection"]["selected_pixel_center_count"],
        },
        "source_records": {
            "catalog_screen": {"path": str(CATALOG_PATH), "sha256": catalog_hash},
            "provider_qa_screen": {"path": str(QA_PATH), "sha256": qa_hash},
            "diagnostic_preview": {"path": str(PREVIEW_PATH), "sha256": preview_hash},
            "qa_report_before": {"path": str(OUTPUT_DIR / "qa-report-before.json"), "scene_id": SCENE_PAIR[0]},
            "qa_report_after": {"path": str(OUTPUT_DIR / "qa-report-after.json"), "scene_id": SCENE_PAIR[1]},
        },
        "interpretation_limits": [
            "The retained October 20 HHHH measurement is one QA-held diagnostic observation, not a temporal change result.",
            "The October 8 and October 20 scenes are a metadata candidate only; both provider QA summaries report FAIL.",
            "A provider identification-group failure blocks pair analysis even though other QA summary checks passed.",
            "The ECHO identification-rule cross-check is diagnostic and does not replace or overturn provider QA.",
            "No event, flood boundary, cause, damage, or ground condition is inferred from this preview.",
        ],
    }
    return catalog, case_review, {
        "record_type": "ECHO_CASE_SNAPSHOT_BUILD_RECORD",
        "schema_version": 1,
        "case_id": CASE_ID,
        "input_records": {
            str(CATALOG_PATH): catalog_hash,
            str(QA_PATH): qa_hash,
            str(PREVIEW_PATH): preview_hash,
        },
        "scene_ids": list(SCENE_PAIR),
        "provider_qa_disposition": "FAIL_FOR_BOTH_PRODUCTS",
        "temporal_analysis_performed": False,
    }, qa_report_records


def main() -> int:
    catalog, case_review, build_record, qa_reports = build_case()
    destination = ROOT / OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    (destination / "case-review.json").write_text(json.dumps(case_review, indent=2) + "\n", encoding="utf-8")
    (destination / "qa-report-before.json").write_text(json.dumps(qa_reports[SCENE_PAIR[0]], indent=2) + "\n", encoding="utf-8")
    (destination / "qa-report-after.json").write_text(json.dumps(qa_reports[SCENE_PAIR[1]], indent=2) + "\n", encoding="utf-8")
    print(json.dumps(build_record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
