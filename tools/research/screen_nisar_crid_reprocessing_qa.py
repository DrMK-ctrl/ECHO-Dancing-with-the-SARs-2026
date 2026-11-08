"""Compare QA evidence for metadata-compatible NISAR GCOV CRID alternatives."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from echo.catalog import pair_gcov_scenes
from echo.qa import QASummaryError, QASummaryRecord, read_qa_summary
from echo.qa_report import QAReportError, read_qa_report


def build_screen_record(
    *,
    features: list[dict[str, Any]],
    crid: str,
    case_review: dict[str, Any],
    scene_ids: list[str] | None = None,
    retrieved_at: datetime | None = None,
    qa_summary_reader: Callable[..., QASummaryRecord] | None = None,
    qa_report_reader: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Retrieve QA evidence only for metadata-paired products of one CRID."""
    if not isinstance(crid, str) or not crid.strip():
        raise ValueError("CRID must be a non-empty string")
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieval timestamp must include a timezone")
    qa_summary_reader = qa_summary_reader or read_qa_summary
    qa_report_reader = qa_report_reader or read_qa_report

    requested_scene_ids = set(scene_ids or [])
    if scene_ids is not None and (
        not scene_ids
        or any(not isinstance(scene_id, str) or not scene_id.strip() for scene_id in scene_ids)
        or len(requested_scene_ids) != len(scene_ids)
    ):
        raise ValueError("scene_ids must be a nonempty list of unique scene identifiers")
    selected = [
        feature
        for feature in features
        if feature.get("properties", {}).get("crid") == crid
        and feature.get("properties", {}).get("collectionName")
        in {"NISAR_L2_GCOV_BETA_V1", "NISAR_L2_GCOV_PROVISIONAL_V1", "NISAR_L2_GCOV_V1"}
        and (scene_ids is None or feature.get("properties", {}).get("fileID") in requested_scene_ids)
    ]
    if scene_ids is not None:
        selected_scene_ids = {feature.get("properties", {}).get("fileID") for feature in selected}
        missing = requested_scene_ids - selected_scene_ids
        if missing:
            raise ValueError(f"requested scene identifiers are absent from the selected catalog and CRID: {sorted(missing)}")
    pairs = pair_gcov_scenes(selected)
    paired_ids = {
        scene_id
        for pair in pairs
        for scene_id in (pair["before_scene"], pair["after_scene"])
    }
    if scene_ids is not None and paired_ids != requested_scene_ids:
        unpaired = requested_scene_ids - paired_ids
        raise ValueError(f"requested scenes do not form complete metadata-compatible pairs: {sorted(unpaired)}")
    selected_by_id = {
        feature["properties"]["fileID"]: feature
        for feature in selected
        if feature.get("properties", {}).get("fileID") in paired_ids
    }

    products = {}
    for scene_id in sorted(paired_ids):
        feature = selected_by_id[scene_id]
        try:
            summary = qa_summary_reader(feature, product_metadata={})
            summary_record = asdict(summary)
            summary_error = None
        except QASummaryError as exc:
            summary_record = None
            summary_error = str(exc)
        try:
            report = qa_report_reader(feature)
            report_error = None
        except QAReportError as exc:
            report = None
            report_error = str(exc)
        products[scene_id] = {
            "catalog_metadata": {
                key: feature["properties"].get(key)
                for key in (
                    "fileID",
                    "url",
                    "collectionName",
                    "processingLevel",
                    "startTime",
                    "stopTime",
                    "crid",
                    "orbit",
                    "pathNumber",
                    "frameNumber",
                    "flightDirection",
                    "mainBandPolarization",
                    "rangeBandwidth",
                )
            },
            "provider_qa_summary": summary_record,
            "provider_qa_summary_retrieval_error": summary_error,
            "provider_qa_report": report,
            "provider_qa_report_retrieval_error": report_error,
        }

    primary = case_review.get("candidate_pair", {})
    return {
        "schema_version": 1,
        "record_type": "NISAR_GCOV_ALTERNATE_CRID_QA_SCREEN",
        "created_at_utc": retrieved_at.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "case_id": case_review.get("case_id"),
        "primary_pinned_crid": primary.get("processing_release"),
        "alternate_crid": crid,
        "selected_scene_ids": sorted(requested_scene_ids) if scene_ids is not None else None,
        "catalog_pair_count": len(pairs),
        "catalog_pairs": pairs,
        "products": products,
        "pixel_measurements_read": False,
        "scientific_comparison_performed": False,
        "interpretation_limits": [
            "ASF QA dispositions are preserved and were not changed by this screen.",
            "A matching source-rule cross-check is diagnostic and does not replace provider QA.",
            "Catalog compatibility and QA reports do not establish valid-pixel overlap or change.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--case-review", type=Path)
    parser.add_argument("--case-id", help="case or bounded QA-screen identifier when no case-review JSON is supplied")
    parser.add_argument("--crid", required=True)
    parser.add_argument("--scene-id", action="append", help="exact scene to include; repeat to select complete pairs without screening every scene in the CRID")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    if args.case_review is not None:
        case_review = json.loads(args.case_review.read_text(encoding="utf-8"))
        if args.case_id is not None:
            parser.error("--case-id cannot be combined with --case-review")
    elif args.case_id:
        case_review = {"case_id": args.case_id, "candidate_pair": {"processing_release": args.crid}}
    else:
        parser.error("provide --case-review or --case-id")
    record = build_screen_record(
        features=catalog["features"], crid=args.crid, case_review=case_review, scene_ids=args.scene_id
    )
    catalog_bytes = args.catalog.read_bytes()
    record["catalog_screen"] = {
        "source_record_path": str(args.catalog),
        "source_record_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
        "source_record_type": catalog.get("record_type"),
        "source_start_date_inclusive": catalog.get("catalog_query", {}).get("start_date_inclusive"),
        "source_end_date_inclusive": catalog.get("catalog_query", {}).get("end_date_inclusive"),
        "global_metadata_temporal_pair_count": catalog.get("metadata_temporal_pair_count"),
        "selected_scene_count": len(record.get("selected_scene_ids") or []),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"Screened CRID {args.crid}: {record['catalog_pair_count']} metadata pair(s), "
        f"{len(record['products'])} paired product QA records -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
