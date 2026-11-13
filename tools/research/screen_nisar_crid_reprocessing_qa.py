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


def validate_selection_manifest(
    manifest: Any,
    *,
    catalog_path: str,
    catalog_sha256: str,
    scene_ids: list[str] | None,
) -> None:
    """Require a persisted selection record to match the catalog and exact scene set."""
    if (
        not isinstance(manifest, dict)
        or manifest.get("record_type") not in {
            "NISAR_VALIDATED_GCOV_UNSCREENED_FULL_PAIR_SELECTION",
            "NISAR_VALIDATED_GCOV_PARTIAL_PAIR_SELECTION",
            "NISAR_VALIDATED_GCOV_CROSS_WINDOW_PAIR_SELECTION",
        }
        or not isinstance(manifest.get("selected_scene_ids"), list)
        or sorted(manifest["selected_scene_ids"]) != sorted(scene_ids or [])
        or manifest.get("catalog_source", {}).get("path") != catalog_path
        or manifest.get("catalog_source", {}).get("sha256") != catalog_sha256
    ):
        raise ValueError("selection manifest does not match the requested catalog and scene IDs")


def build_screen_record(
    *,
    features: list[dict[str, Any]],
    crid: str,
    case_review: dict[str, Any],
    scene_ids: list[str] | None = None,
    include_reports: bool = True,
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
        if include_reports:
            try:
                report = qa_report_reader(feature)
                report_error = None
                report_status = "RETRIEVED"
            except QAReportError as exc:
                report = None
                report_error = str(exc)
                report_status = "RETRIEVAL_FAILED"
        else:
            report = None
            report_error = None
            report_status = "NOT_REQUESTED"
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
            "provider_qa_report_status": report_status,
        }

    primary = case_review.get("candidate_pair", {})
    primary_pinned_crid = primary.get("processing_release")
    is_alternate_crid = isinstance(primary_pinned_crid, str) and primary_pinned_crid != crid
    return {
        "schema_version": 1,
        "record_type": (
            "NISAR_GCOV_ALTERNATE_CRID_QA_SCREEN"
            if is_alternate_crid
            else "NISAR_GCOV_CRID_QA_SCREEN"
        ),
        "created_at_utc": retrieved_at.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "case_id": case_review.get("case_id"),
        "primary_pinned_crid": primary_pinned_crid,
        "screened_crid": crid,
        "alternate_crid": crid if is_alternate_crid else None,
        "selected_scene_ids": sorted(requested_scene_ids) if scene_ids is not None else None,
        "catalog_pair_count": len(pairs),
        "catalog_pairs": pairs,
        "products": products,
        "report_screening_mode": "FULL_REPORTS" if include_reports else "SUMMARY_ONLY",
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
    parser.add_argument(
        "--scene-id-file",
        type=Path,
        help="UTF-8 text file containing one exact scene identifier per line; mutually exclusive with --scene-id",
    )
    parser.add_argument(
        "--selection-manifest",
        type=Path,
        help="optional checksummed selection JSON whose selected_scene_ids must match the requested pair selection",
    )
    parser.add_argument(
        "--summaries-only",
        action="store_true",
        help="retrieve provider QA CSVs without downloading QA report PDFs; use for bounded candidate screening",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    catalog_bytes = args.catalog.read_bytes()
    catalog_sha256 = hashlib.sha256(catalog_bytes).hexdigest()
    if args.case_review is not None:
        case_review = json.loads(args.case_review.read_text(encoding="utf-8"))
        if args.case_id is not None:
            parser.error("--case-id cannot be combined with --case-review")
    elif args.case_id:
        case_review = {"case_id": args.case_id, "candidate_pair": {}}
    else:
        parser.error("provide --case-review or --case-id")
    if args.scene_id is not None and args.scene_id_file is not None:
        parser.error("--scene-id and --scene-id-file cannot be combined")
    try:
        scene_ids = args.scene_id
        if args.scene_id_file is not None:
            scene_ids = [
                line.strip()
                for line in args.scene_id_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
    except OSError as exc:
        parser.error(f"cannot read scene ID list: {exc}")
    selection_manifest_bytes = None
    if args.selection_manifest is not None:
        try:
            selection_manifest_bytes = args.selection_manifest.read_bytes()
            selection_manifest = json.loads(selection_manifest_bytes)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            parser.error(f"cannot read selection manifest: {exc}")
        try:
            validate_selection_manifest(
                selection_manifest,
                catalog_path=str(args.catalog),
                catalog_sha256=catalog_sha256,
                scene_ids=scene_ids,
            )
        except ValueError as exc:
            parser.error(str(exc))
    record = build_screen_record(
        features=catalog["features"],
        crid=args.crid,
        case_review=case_review,
        scene_ids=scene_ids,
        include_reports=not args.summaries_only,
    )
    record["catalog_screen"] = {
        "source_record_path": str(args.catalog),
        "source_record_sha256": catalog_sha256,
        "source_record_type": catalog.get("record_type"),
        "source_start_date_inclusive": catalog.get("catalog_query", {}).get("start_date_inclusive"),
        "source_end_date_inclusive": catalog.get("catalog_query", {}).get("end_date_inclusive"),
        "global_metadata_temporal_pair_count": catalog.get("metadata_temporal_pair_count"),
        "selected_scene_count": len(record.get("selected_scene_ids") or []),
        "scene_id_file_sha256": (
            hashlib.sha256(args.scene_id_file.read_bytes()).hexdigest()
            if args.scene_id_file is not None
            else None
        ),
        "selection_manifest_path": str(args.selection_manifest) if args.selection_manifest else None,
        "selection_manifest_sha256": (
            hashlib.sha256(selection_manifest_bytes).hexdigest()
            if selection_manifest_bytes is not None
            else None
        ),
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
