#!/usr/bin/env python3
"""Compare diagnostic VV/VH spatial associations on common RTC-S1 support.

This is a sensitivity analysis of one acquisition pair, not independent
validation, product QA clearance, or a surface-change classification.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np


class PolarizationSensitivityError(ValueError):
    """Raised when records cannot support a paired polarization comparison."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PolarizationSensitivityError(message)


def compare_spatial_support(
    vv: dict[str, Any], vh: dict[str, Any], *, minimum_coverage: float = 0.75
) -> dict[str, Any]:
    """Compare per-cell VV/VH change against the same optical context cells."""
    _require(0 < minimum_coverage <= 1, "minimum coverage must be in (0, 1]")
    for label, record, polarization in (("VV", vv, "VV"), ("VH", vh, "VH")):
        _require(record.get("record_type") == "ECHO_RTC_DSWX_SPATIAL_SUPPORT_DIAGNOSTIC", f"{label} record type is invalid")
        _require(record.get("status") == "DIAGNOSTIC_SPATIAL_ASSOCIATION", f"{label} record is not diagnostic")
        _require(record.get("sources", {}).get("sar_polarization") == polarization, f"record is not {label}")
        _require(record.get("sources", {}).get("sar_pair_status") == "DIAGNOSTIC_PRODUCT_MASKED_COMPARISON", f"{label} pair disposition is unexpected")
        _require(record.get("sources", {}).get("sar_provider_qa", {}).get("status") == "PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION", f"{label} provider QA state is missing")
    for field in ("sar_scene_ids", "optical_granule_ids", "optical_context_record_sha256"):
        _require(vv["sources"].get(field) == vh["sources"].get(field), f"VV and VH {field} differ")
    _require(vv["sources"].get("sar_grid_crs") == vh["sources"].get("sar_grid_crs"), "VV and VH grids use different CRSs")
    _require(vv["sources"].get("optical_wtr_source_sha256") == vh["sources"].get("optical_wtr_source_sha256"), "VV and VH do not share optical source rasters")

    def cells(record: dict[str, Any], polarization: str) -> dict[tuple[int, int], dict[str, Any]]:
        result: dict[tuple[int, int], dict[str, Any]] = {}
        for item in record.get("per_sar_cell", []):
            key = (item.get("sar_row"), item.get("sar_column"))
            _require(all(isinstance(value, int) and not isinstance(value, bool) for value in key), f"{polarization} cell index is invalid")
            _require(key not in result, f"{polarization} contains duplicate cell indices")
            result[key] = item
        _require(bool(result), f"{polarization} has no cell records")
        return result

    vv_cells, vh_cells = cells(vv, "VV"), cells(vh, "VH")
    _require(vv_cells.keys() == vh_cells.keys(), "VV and VH cell grids do not match")
    selected = []
    for key, v in vv_cells.items():
        h = vh_cells[key]
        _require(v.get("common_valid_wtr_area_fraction") == h.get("common_valid_wtr_area_fraction"), "VV and VH optical support differs")
        _require(v.get("water_fraction_change_after_minus_before") == h.get("water_fraction_change_after_minus_before"), "VV and VH optical water changes differ")
        coverage = v.get("common_valid_wtr_area_fraction")
        if (
            isinstance(coverage, (int, float))
            and not isinstance(coverage, bool)
            and coverage >= minimum_coverage
            and v.get("sar_measurement_valid") is True
            and h.get("sar_measurement_valid") is True
        ):
            vv_value, vh_value = v.get("sar_log_ratio_db"), h.get("sar_log_ratio_db")
            water_change = v.get("water_fraction_change_after_minus_before")
            if all(isinstance(x, (int, float)) and not isinstance(x, bool) and np.isfinite(x) for x in (vv_value, vh_value, water_change)):
                selected.append((float(water_change), float(vv_value), float(vh_value)))
    _require(len(selected) >= 3, "fewer than three cells meet common support and validity requirements")
    values = np.asarray(selected, dtype=np.float64)
    water, vv_change, vh_change = values.T
    vv_r = float(np.corrcoef(water, vv_change)[0, 1])
    vh_r = float(np.corrcoef(water, vh_change)[0, 1])
    pol_r = float(np.corrcoef(vv_change, vh_change)[0, 1])
    _require(all(np.isfinite(x) for x in (vv_r, vh_r, pol_r)), "selected samples have undefined correlation")
    difference = vh_change - vv_change
    return {
        "record_type": "ECHO_RTC_POLARIZATION_SENSITIVITY_DIAGNOSTIC",
        "status": "DIAGNOSTIC_SENSITIVITY_ONLY",
        "scope": "Same OPERA RTC-S1 acquisition pair and DSWx-HLS context; VV and VH are related measurements, not independent validation.",
        "method": {
            "support": "Use only cells meeting the minimum common-valid optical area fraction and valid SAR measurements in both polarizations.",
            "association": "Descriptive Pearson correlations only; no inferential statistic is computed because neighboring cells are spatially dependent and provider QA has no consolidated disposition.",
            "minimum_common_valid_wtr_area_fraction": minimum_coverage,
        },
        "sources": {
            "sar_scene_ids": vv["sources"]["sar_scene_ids"],
            "optical_granule_ids": vv["sources"]["optical_granule_ids"],
            "optical_context_record_sha256": vv["sources"]["optical_context_record_sha256"],
            "vv_pair_record": vv["sources"]["sar_pair_record"],
            "vv_pair_record_sha256": vv["sources"]["sar_pair_record_sha256"],
            "vh_pair_record": vh["sources"]["sar_pair_record"],
            "vh_pair_record_sha256": vh["sources"]["sar_pair_record_sha256"],
            "vv_spatial_record_sha256": None,
            "vh_spatial_record_sha256": None,
        },
        "summary": {
            "common_cells": int(len(selected)),
            "water_fraction_change_median": float(np.median(water)),
            "vv_mean_log_ratio_db": float(np.mean(vv_change)),
            "vv_median_log_ratio_db": float(np.median(vv_change)),
            "vv_pearson_r_water_change_vs_log_ratio": vv_r,
            "vh_mean_log_ratio_db": float(np.mean(vh_change)),
            "vh_median_log_ratio_db": float(np.median(vh_change)),
            "vh_pearson_r_water_change_vs_log_ratio": vh_r,
            "vv_vh_pearson_r_log_ratio": pol_r,
            "vh_minus_vv_mean_db": float(np.mean(difference)),
            "vh_minus_vv_median_db": float(np.median(difference)),
            "vh_minus_vv_median_absolute_deviation_db": float(np.median(np.abs(difference - np.median(difference)))),
        },
        "interpretation_limits": [
            "Both polarizations come from the same Sentinel-1 acquisitions and NASA OPERA RTC-S1 processing; agreement is not independent corroboration.",
            "DSWx-HLS is optical algorithm context, not field truth or SAR validation.",
            "The weak descriptive associations do not establish or exclude a water-related cause.",
            "Both SAR results remain diagnostic because the retained product metadata provide no consolidated provider PASS/FAIL disposition.",
            "No inferential statistic is reported; spatial dependence is not handled by this descriptive comparison.",
        ],
    }


def evaluate_files(vv_path: Path, vh_path: Path, output_path: Path) -> dict[str, Any]:
    vv = json.loads(vv_path.read_text(encoding="utf-8"))
    vh = json.loads(vh_path.read_text(encoding="utf-8"))
    record = compare_spatial_support(vv, vh)
    record["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    record["sources"]["vv_spatial_record_sha256"] = sha256(vv_path.read_bytes()).hexdigest()
    record["sources"]["vh_spatial_record_sha256"] = sha256(vh_path.read_bytes()).hexdigest()
    record["processing"] = {
        "script": "tools/research/evaluate_rtc_polarization_sensitivity.py",
        "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "created_at_utc": record["created_at_utc"],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return record


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vv", type=Path, default=root / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-2026-11-08.json")
    parser.add_argument("--vh", type=Path, default=root / "data/research/opera-rtc-dswx-spatial-support-T163-349925-VH-2026-11-08.json")
    parser.add_argument("--output", type=Path, default=root / "data/research/opera-rtc-polarization-sensitivity-T163-349925-2026-11-08.json")
    args = parser.parse_args()
    record = evaluate_files(args.vv, args.vh, args.output)
    print(json.dumps({"status": record["status"], "summary": record["summary"], "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
