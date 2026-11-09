#!/usr/bin/env python3
"""Attach a reproducible scoped review to a retained OPERA RTC-S1 pair."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from echo.opera_rtc_quality import build_opera_rtc_pair_quality_review


def build_record(pair_path: Path) -> dict:
    record = json.loads(pair_path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("record_type") != "ECHO_OPERA_RTC_S1_PAIR_ANALYSIS":
        raise ValueError("pair record must be an OPERA RTC-S1 pair analysis")
    record["schema_version"] = 2
    record["quality_review"] = build_opera_rtc_pair_quality_review(record)
    return record


def _replace_hashes(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_hashes(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_hashes(item, replacements) for item in value]
    return replacements.get(value, value) if isinstance(value, str) else value


def refresh_linked_hashes(data_root: Path, old_pair_hash: str, new_pair_hash: str) -> int:
    """Propagate changed content hashes through the retained JSON evidence graph."""
    replacements = {old_pair_hash: new_pair_hash}
    changed_paths: set[Path] = set()
    for _ in range(12):
        round_changed = False
        for path in sorted(data_root.rglob("*.json")):
            try:
                raw = path.read_bytes()
                record = json.loads(raw)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                continue
            updated = _replace_hashes(record, replacements)
            if updated == record:
                continue
            updated_bytes = (json.dumps(updated, indent=2, allow_nan=False) + "\n").encode("utf-8")
            old_digest = sha256(raw).hexdigest()
            new_digest = sha256(updated_bytes).hexdigest()
            path.write_bytes(updated_bytes)
            changed_paths.add(path)
            if old_digest != new_digest:
                replacements[old_digest] = new_digest
            round_changed = True
        if not round_changed:
            return len(changed_paths)
    raise ValueError("linked evidence hashes did not settle after 12 propagation passes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-record", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--refresh-linked-hashes-under", type=Path)
    parser.add_argument("--validate-assessment", type=Path)
    args = parser.parse_args()
    old_pair_hash = sha256(args.pair_record.read_bytes()).hexdigest()
    record = build_record(args.pair_record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    new_pair_hash = sha256(args.output.read_bytes()).hexdigest()
    changed_linked_records = 0
    if args.refresh_linked_hashes_under:
        data_root = args.refresh_linked_hashes_under.resolve()
        output_path = args.output.resolve()
        if not output_path.is_relative_to(data_root):
            raise ValueError("pair output must be inside the linked data directory")
        changed_linked_records = refresh_linked_hashes(data_root, old_pair_hash, new_pair_hash)
    if args.validate_assessment:
        if not args.refresh_linked_hashes_under:
            raise ValueError("assessment validation requires --refresh-linked-hashes-under")
        from echo.web import _validate_assessment_record

        assessment_path = args.validate_assessment.resolve()
        if not assessment_path.is_file():
            raise ValueError("linked assessment does not exist")
        assessment = json.loads(assessment_path.read_text(encoding="utf-8"))
        _validate_assessment_record(assessment, Path.cwd().resolve())
    review = record["quality_review"]
    checks = review["echo_bounded_checks"]
    print(
        f"Wrote {review['status']}: {checks['common_finite_positive_count']}/"
        f"{checks['aoi_pixel_count']} measured AOI centers; provider scene verdict remains "
        f"{review['provider_qa']['scene_level_verdict']}; refreshed {changed_linked_records} linked records -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
