#!/usr/bin/env python3
"""Build a checksummed NASA GPM daily chronology between two SAR acquisitions."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np


class InteracquisitionContextError(ValueError):
    """Raised when daily GPM records do not form a complete linked interval."""


def _read(path: Path) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    record = json.loads(payload)
    if (
        not isinstance(record, dict)
        or record.get("record_type") != "ECHO_GPM_IMERG_DAILY_CONTEXT"
        or record.get("status") != "NASA_REGIONAL_PRECIPITATION_CONTEXT_NOT_CAUSAL_EVIDENCE"
    ):
        raise InteracquisitionContextError(f"unexpected GPM daily-context record: {path}")
    return record, payload


def _validate_source_record(record: dict[str, Any], *, case_id: str, root: Path) -> list[dict[str, Any]]:
    source = record.get("source", {})
    observations = record.get("daily_observations")
    if (
        record.get("case_id") != case_id
        or source.get("provider") != "NASA GES DISC"
        or source.get("short_name") != "GPM_3IMERGDF"
        or source.get("version") != "07"
        or source.get("doi") != "10.5067/GPM/IMERGDF/DAY/07"
        or source.get("units") != "mm/day"
        or not isinstance(observations, list)
        or not observations
    ):
        raise InteracquisitionContextError("GPM source identity or daily records are invalid")
    query = record.get("query", {})
    if query.get("aoi_west_south_east_north") != [-51.24, -30.04, -51.23, -30.03]:
        raise InteracquisitionContextError("GPM context does not describe the retained case AOI")
    center = query.get("aoi_nearest_native_cell_center")
    if not isinstance(center, list) or len(center) != 2 or not np.allclose(center, [-51.25, -30.05], rtol=0, atol=1e-6):
        raise InteracquisitionContextError("GPM context uses an unexpected nearest native-cell center")
    for observation in observations:
        sample = observation.get("aoi_nearest_cell", {})
        asset = observation.get("asset", {})
        relative = asset.get("relative_path")
        expected_hash = asset.get("sha256")
        if (
            sample.get("full_day_sample_complete") is not True
            or sample.get("valid_half_hourly_samples") != 48
            or isinstance(sample.get("precipitation_mm_per_day"), bool)
            or not isinstance(sample.get("precipitation_mm_per_day"), (int, float))
            or not np.isfinite(sample["precipitation_mm_per_day"])
            or sample["precipitation_mm_per_day"] < 0
            or not isinstance(relative, str)
            or not isinstance(expected_hash, str)
        ):
            raise InteracquisitionContextError("a GPM day is incomplete or lacks valid subset provenance")
        source_path = Path(relative)
        if source_path.is_absolute():
            raise InteracquisitionContextError("GPM source subset paths must be project-relative")
        resolved = (root / source_path).resolve()
        if not resolved.is_relative_to(root):
            raise InteracquisitionContextError("GPM source subset path escapes the project")
        try:
            source_bytes = resolved.read_bytes()
        except OSError as exc:
            raise InteracquisitionContextError("GPM daily source subset is unavailable") from exc
        if len(source_bytes) != asset.get("bytes") or sha256(source_bytes).hexdigest() != expected_hash:
            raise InteracquisitionContextError("GPM daily source-subset checksum or size validation failed")
    return observations


def build_interacquisition_context(
    *,
    sar_record: dict[str, Any],
    sar_payload: bytes,
    interval_record: dict[str, Any],
    interval_payload: bytes,
    after_context_record: dict[str, Any],
    after_context_payload: bytes,
    case_id: str,
    project_root: Path,
) -> dict[str, Any]:
    if (
        sar_record.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS"
        or sar_record.get("status") != "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON"
        or sar_record.get("provider_qa", {}).get("status")
        != "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION"
    ):
        raise InteracquisitionContextError("SAR pair is not eligible for diagnostic context linkage")
    if sar_record.get("case_id") not in (None, case_id):
        raise InteracquisitionContextError("SAR pair belongs to another investigation case")
    before = sar_record.get("source_products", {}).get("before", {}).get("acquisition_start_utc")
    after = sar_record.get("source_products", {}).get("after", {}).get("acquisition_start_utc")
    try:
        before_dt = datetime.fromisoformat(before.replace("Z", "+00:00"))
        after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise InteracquisitionContextError("SAR pair acquisition timestamps are invalid") from exc
    if before_dt.tzinfo is None or after_dt.tzinfo is None or after_dt <= before_dt:
        raise InteracquisitionContextError("SAR acquisition timestamps must be ordered and timezone-aware")

    root = project_root.resolve()
    interval_days = _validate_source_record(interval_record, case_id=case_id, root=root)
    trailing_days = _validate_source_record(after_context_record, case_id=case_id, root=root)
    all_days = interval_days + trailing_days
    dates = [date.fromisoformat(item.get("date_utc", "")) for item in all_days]
    first_day = before_dt.date() + timedelta(days=1)
    last_day = after_dt.date() - timedelta(days=1)
    expected_days = []
    current = first_day
    while current <= last_day:
        expected_days.append(current)
        current += timedelta(days=1)
    if dates != expected_days:
        raise InteracquisitionContextError("GPM daily observations do not cover every full UTC day between the SAR dates")
    interval_query = interval_record.get("query", {})
    trailing_query = after_context_record.get("query", {})
    if (
        interval_query.get("bbox_west_south_east_north") != trailing_query.get("bbox_west_south_east_north")
        or interval_query.get("aoi_west_south_east_north") != trailing_query.get("aoi_west_south_east_north")
        or interval_query.get("aoi_nearest_native_cell_center") != trailing_query.get("aoi_nearest_native_cell_center")
    ):
        raise InteracquisitionContextError("GPM daily windows do not use the same request area and native cell")
    for day_record in all_days:
        native = day_record.get("native_grid", {})
        if (
            native.get("crs") != "EPSG:4326"
            or not np.isclose(native.get("longitude_spacing_degrees", 0), 0.1, rtol=0, atol=2e-5)
            or not np.isclose(native.get("latitude_spacing_degrees", 0), 0.1, rtol=0, atol=2e-5)
        ):
            raise InteracquisitionContextError("GPM daily windows do not retain the expected native geographic grid")

    values = [float(item["aoi_nearest_cell"]["precipitation_mm_per_day"]) for item in all_days]
    peak_index = int(np.argmax(values))
    total = float(sum(values))
    record = {
        "record_type": "ECHO_GPM_IMERG_INTERACQUISITION_CHRONOLOGY",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "status": "COMPLETE_REGIONAL_DAILY_CONTEXT_NOT_CAUSAL_EVIDENCE",
        "source": interval_record["source"],
        "sar_interval": {
            "before_acquisition_utc": before,
            "after_acquisition_utc": after,
            "before_scene_id": sar_record["source_products"]["before"]["scene_id"],
            "after_scene_id": sar_record["source_products"]["after"]["scene_id"],
            "full_utc_days_only": True,
            "first_full_day_after_before_sar": first_day.isoformat(),
            "last_full_day_before_after_sar": last_day.isoformat(),
            "days_between_acquisitions": len(all_days),
        },
        "sources": {
            "sar_pair_record_sha256": sha256(sar_payload).hexdigest(),
            "intervening_gpm_context_record_sha256": sha256(interval_payload).hexdigest(),
            "trailing_gpm_context_record_sha256": sha256(after_context_payload).hexdigest(),
            "daily_granule_ids": [item["granule_id"] for item in all_days],
            "daily_asset_sha256": [item["asset"]["sha256"] for item in all_days],
        },
        "query": {
            "bbox_west_south_east_north": interval_query["bbox_west_south_east_north"],
            "aoi_west_south_east_north": interval_query["aoi_west_south_east_north"],
            "aoi_nearest_native_cell_center": interval_query["aoi_nearest_native_cell_center"],
        },
        "daily_observations": [
            {
                "date_utc": item["date_utc"],
                "granule_id": item["granule_id"],
                "precipitation_mm_per_day": float(item["aoi_nearest_cell"]["precipitation_mm_per_day"]),
                "valid_half_hourly_samples": int(item["aoi_nearest_cell"]["valid_half_hourly_samples"]),
                "expected_half_hourly_samples": int(item["aoi_nearest_cell"]["expected_half_hourly_samples"]),
                "full_day_sample_complete": bool(item["aoi_nearest_cell"]["full_day_sample_complete"]),
                "production_time_utc": item["production_time_utc"],
                "asset": item["asset"],
            }
            for item in all_days
        ],
        "summary": {
            "days_requested": len(all_days),
            "days_with_complete_nearest_cell_samples": len(all_days),
            "nearest_cell_cumulative_precipitation_mm": total,
            "nearest_cell_mean_daily_precipitation_mm_per_day": total / len(all_days),
            "maximum_daily_precipitation_mm_per_day": values[peak_index],
            "maximum_daily_precipitation_date_utc": all_days[peak_index]["date_utc"],
            "native_grid_spacing_degrees": interval_record["daily_observations"][0]["native_grid"]["longitude_spacing_degrees"],
            "daily_series_mm_per_day": values,
            "interpretation_limit": "The ~0.1 degree GPM grid is much coarser than the SAR AOI. These complete daily estimates describe regional precipitation timing; they do not measure AOI soil moisture, establish flood extent, or determine the cause of the SAR response.",
        },
        "processing": {
            "script": "tools/research/build_gpm_interacquisition_context.py",
            "method": "Join full UTC days after the earlier SAR acquisition through the last full UTC day before the later acquisition; verify consecutive dates, native-cell identity, complete 48/48 samples, and every retained bounded source-subset hash; compute descriptive daily and interval aggregates only.",
            "software": {"numpy": np.__version__},
            "no_causal_or_inferential_claim": True,
        },
    }
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sar-record", type=Path, required=True)
    parser.add_argument("--intervening-gpm-record", type=Path, required=True)
    parser.add_argument("--trailing-gpm-record", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sar_payload = args.sar_record.read_bytes()
    interval_payload = args.intervening_gpm_record.read_bytes()
    trailing_payload = args.trailing_gpm_record.read_bytes()
    result = build_interacquisition_context(
        sar_record=json.loads(sar_payload),
        sar_payload=sar_payload,
        interval_record=json.loads(interval_payload),
        interval_payload=interval_payload,
        after_context_record=json.loads(trailing_payload),
        after_context_payload=trailing_payload,
        case_id=args.case_id,
        project_root=Path(__file__).resolve().parents[2],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), **result["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
