"""Add an ECHO scoped quality review to a retained diagnostic RTC-S1 series."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from echo.opera_rtc_analysis import validate_opera_rtc_s1_series_record
from echo.opera_rtc_quality import build_opera_rtc_quality_review


def build_record(series_path: Path, pair_path: Path) -> dict:
    series = json.loads(series_path.read_text(encoding="utf-8"))
    pair = json.loads(pair_path.read_text(encoding="utf-8"))
    if not isinstance(series, dict) or not isinstance(pair, dict):
        raise ValueError("series and pair records must be JSON objects")
    series["schema_version"] = 2
    series["quality_review"] = build_opera_rtc_quality_review(series)
    validate_opera_rtc_s1_series_record(series, pair_record=pair)
    return series


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--series-record", required=True, type=Path)
    parser.add_argument("--pair-record", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    record = build_record(args.series_record, args.pair_record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    review = record["quality_review"]
    checks = review["echo_bounded_checks"]
    print(
        f"Wrote {review['status']}: {checks['common_finite_positive_count']}/"
        f"{checks['aoi_pixel_count']} common centers; provider scene verdict remains "
        f"{review['provider_qa']['scene_level_verdict']} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
