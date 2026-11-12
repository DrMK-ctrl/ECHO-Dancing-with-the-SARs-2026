"""Capture a same-path/frame GUNW catalog sequence and provider QA summaries."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
import subprocess

import asf_search as asf
import earthaccess
from aiohttp import ClientTimeout
from echo.catalog import asf_inclusive_end

from screen_gunw_qa import _canonical_qa_uri, _fetch_summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--longitude", type=float, required=True)
    parser.add_argument("--latitude", type=float, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--path", type=int, required=True)
    parser.add_argument("--frame", type=int, required=True)
    parser.add_argument(
        "--direction", choices=("ASCENDING", "DESCENDING"), required=True
    )
    parser.add_argument("--maturity", choices=("BETA", "PROVISIONAL", "VALIDATED"), default="PROVISIONAL")
    parser.add_argument("--max-results", type=int, default=250)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not (-180 <= args.longitude <= 180 and -90 <= args.latitude <= 90):
        parser.error("longitude/latitude are outside WGS84 bounds")
    if not 1 <= args.max_results <= 250:
        parser.error("--max-results must be between 1 and 250")
    try:
        start = datetime.fromisoformat(args.start_date)
        end = datetime.fromisoformat(args.end_date)
    except ValueError:
        parser.error("dates must use ISO format YYYY-MM-DD")
    if start.date().isoformat() != args.start_date or end.date().isoformat() != args.end_date or start > end:
        parser.error("date range must be ordered ISO dates (YYYY-MM-DD)")
    return args


def build_record(args: argparse.Namespace) -> dict[str, object]:
    application_revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    tool_source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    intersects = f"POINT({args.longitude} {args.latitude})"
    query: dict[str, object] = {
        "processingLevel": ["GUNW"],
        "dataset": ["NISAR"],
        "dataMaturity": args.maturity,
        "start": args.start_date,
        "end": asf_inclusive_end(args.end_date),
        "maxResults": args.max_results,
        "intersectsWith": intersects,
    }
    features = asf.search(opts=asf.ASFSearchOptions(**query)).geojson().get("features", [])
    matching = [
        feature
        for feature in features
        if feature.get("properties", {}).get("pathNumber") == args.path
        and feature.get("properties", {}).get("frameNumber") == args.frame
        and feature.get("properties", {}).get("flightDirection") == args.direction
    ]
    matching.sort(key=lambda feature: feature.get("properties", {}).get("startTime", ""))

    auth = earthaccess.login(strategy="netrc", persist=False)
    if not auth.authenticated:
        raise RuntimeError("Earthdata Login is not authenticated via local netrc")
    filesystem = earthaccess.get_fsspec_https_session()
    filesystem.client_kwargs = {
        **filesystem.client_kwargs,
        "timeout": ClientTimeout(total=25, connect=10, sock_read=20),
    }

    records: list[dict[str, object]] = []
    for feature in matching:
        properties = feature.get("properties", {})
        scene_id, qa_uri = _canonical_qa_uri(feature)
        serialized = json.dumps(
            feature, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        records.append(
            {
                "scene_id": scene_id,
                "catalog_feature_sha256": hashlib.sha256(serialized).hexdigest(),
                "catalog_feature": feature,
                "provider_qa_summary": _fetch_summary(filesystem, qa_uri),
            }
        )

    parse_time = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    pair_baselines: list[dict[str, object]] = []
    extended_baselines: list[dict[str, object]] = []
    for record in records:
        properties = record["catalog_feature"]["properties"]  # type: ignore[index]
        start_time, stop_time = properties.get("startTime"), properties.get("stopTime")
        if not isinstance(start_time, str) or not isinstance(stop_time, str):
            continue
        elapsed_days = (parse_time(stop_time) - parse_time(start_time)).total_seconds() / 86400
        baseline = {
            "scene_id": record["scene_id"],
            "start_utc": start_time,
            "stop_utc": stop_time,
            "elapsed_days": round(elapsed_days, 6),
        }
        pair_baselines.append(baseline)
        if elapsed_days > 12.5:
            extended_baselines.append(
                {
                    **baseline,
                    "status": "EXTENDED_PAIR_BASELINE",
                    "note": (
                        "This GUNW product spans longer than the nominal nearest-neighbor "
                        "interval. It does not establish whether additional acquisitions "
                        "exist without a matching product in this query."
                    ),
                }
            )

    return {
        "schema_version": 1,
        "record_type": "ECHO_GUNW_TEMPORAL_CATALOG_QA_REVIEW",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_revision": application_revision,
        "inspection_tool_source_sha256": tool_source_sha256,
        "source": {
            "catalog_provider": "Alaska Satellite Facility DAAC",
            "catalog_client": "asf_search",
            "catalog_client_version": version("asf-search"),
            "authenticated_qa_provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
        },
        "catalog_query": query,
        "catalog_result_count": len(features),
        "catalog_result_count_is_capped": len(features) == args.max_results,
        "series_filter": {
            "path_number": args.path,
            "frame_number": args.frame,
            "flight_direction": args.direction,
            "selection_rule": "all matching query results sorted by acquisition start time",
        },
        "aoi_note": (
            "ASF spatial-intersection query only; this does not validate pixel support "
            "inside a user-selected AOI."
        ),
        "product_scope": {
            "mission": "NISAR",
            "processing_level": "L2 GUNW",
            "data_maturity": args.maturity,
            "polarization": "catalog metadata; product layers must be checked individually",
            "frequency": "catalog metadata; product layers must be checked individually",
        },
        "pair_baselines": pair_baselines,
        "extended_pair_baselines": extended_baselines,
        "catalog_feature_count": len(records),
        "records": records,
        "scientific_disposition": {
            "status": "CATALOG_AND_PROVIDER_QA_ONLY",
            "pixels_read": False,
            "pixel_coverage_validated": False,
            "cross_pair_phase_comparison_performed": False,
            "displacement_estimated": False,
            "event_interpreted": False,
            "provider_qa_failures_overridden": False,
        },
    }


def main() -> int:
    args = _parse_args()
    record = build_record(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Wrote {args.output}: {record['catalog_feature_count']} matching GUNW products, "
        f"{len(record['extended_pair_baselines'])} extended pair baselines; provider QA retained."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
