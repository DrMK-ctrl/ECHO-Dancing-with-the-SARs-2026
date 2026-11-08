#!/usr/bin/env python3
"""Build a non-causal comparison of two retained OPERA RTC-S1 sidecars."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from echo.opera_rtc_conditions import build_acquisition_condition_review


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-record", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = args.pair_record.read_bytes()
    pair = json.loads(payload)
    record = build_acquisition_condition_review(
        pair,
        case_id=args.case_id,
        source_record_path=str(args.pair_record),
        source_record_sha256=sha256(payload).hexdigest(),
    )
    record["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    summary = record["summary"]
    print(f"status={record['status']}")
    print(f"scenes={len(record['acquisitions'])}")
    print(f"processing_configuration_matches={summary['documented_processing_configuration_matches']}")
    print(f"rfi_burst_metadata_comparison={summary['rfi_burst_metadata_comparison']}")
    print(f"causal_disposition={summary['causal_disposition']}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
