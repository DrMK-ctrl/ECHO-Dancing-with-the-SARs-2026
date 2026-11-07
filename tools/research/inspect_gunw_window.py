"""Persist descriptive evidence for one bounded GUNW pixel-window read."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

from echo.gunw_access import decode_gunw_mask, read_gunw_window


SCREEN_PATH = Path("data/research/gunw-provisional-qa-screen-2026-11-07.json")
OUTPUT_PATH = Path(
    "data/research/gunw-istanbul-ayazaga-pixel-window-2026-11-07.json"
)
GUNW_SCHEMA_URL = (
    "https://github.com/isce-framework/nisarqa/blob/v17.0.0/"
    "src/nisarqa/product_specs/1.5.0/nisar_L2_GUNW.xml"
)
GUNW_SCHEMA_SHA256 = (
    "c75acedfbfe8a5c0893df89336641b690cb296dddce1245f5ae9dafd8891fbd3"
)
DEFAULT_SCENE = (
    "NISAR_L2_PR_GUNW_032_137_D_068_033_2000_SH_20261009T170432_"
    "20261009T170506_20261021T170432_20261021T170507_P05023_N_F_J_001"
)
DEFAULT_BOUNDS = (28.98, 41.095, 29.0, 41.115)


def _numeric_summary(values: np.ndarray) -> dict[str, Any]:
    selected = np.asarray(values)
    if np.issubdtype(selected.dtype, np.inexact):
        finite = selected[np.isfinite(selected)]
    else:
        finite = selected.reshape(-1)
    return {
        "dtype": str(selected.dtype),
        "shape": list(selected.shape),
        "sample_count": int(selected.size),
        "finite_or_integer_count": int(finite.size),
        "minimum": float(finite.min()) if finite.size else None,
        "maximum": float(finite.max()) if finite.size else None,
        "mean": float(finite.mean()) if finite.size else None,
        "zero_count": int(np.count_nonzero(finite == 0)) if finite.size else 0,
    }


def _mask_summary(fields: dict[str, np.ndarray], selection: np.ndarray) -> dict[str, Any]:
    selected = {name: values[selection] for name, values in fields.items()}
    ref_subswath = selected["reference_subswath"]
    sec_subswath = selected["secondary_subswath"]
    combined = (
        ~selected["fill"]
        & (ref_subswath > 0)
        & (sec_subswath > 0)
    )
    any_anomaly = (
        (selected["reference_anomaly_flags"] != 0)
        | (selected["secondary_anomaly_flags"] != 0)
    )
    return {
        "aoi_pixel_center_count": int(selection.sum()),
        "fill_count": int(np.count_nonzero(selected["fill"])),
        "reference_subswath_zero_count": int(np.count_nonzero(ref_subswath == 0)),
        "secondary_subswath_zero_count": int(np.count_nonzero(sec_subswath == 0)),
        "nonzero_reference_and_secondary_subswath_count": int(
            np.count_nonzero(combined)
        ),
        "any_reference_or_secondary_anomaly_flag_count": int(
            np.count_nonzero(any_anomaly)
        ),
        "ionosphere_interpolated_count": int(
            np.count_nonzero(selected["ionosphere_interpolated"])
        ),
        "reserved_bit_count": int(np.count_nonzero(selected["reserved_bits"])),
        "water_flag_value_counts": {
            str(int(value)): int(np.count_nonzero(selected["water_flag"] == value))
            for value in np.unique(selected["water_flag"])
        },
        "note": (
            "Field counts reflect the product's encoded mask. They are not a final "
            "scientific validity decision or event classification."
        ),
    }


def _find_entry(screen: dict[str, Any], scene_id: str) -> dict[str, Any]:
    for entry in screen.get("entries", []):
        if entry.get("scene_id") == scene_id and isinstance(
            entry.get("catalog_feature"), dict
        ):
            return entry
    raise ValueError(f"scene is not in the retained GUNW screen: {scene_id}")


def build_record(
    entry: dict[str, Any],
    *,
    bounds: tuple[float, float, float, float],
    polarization: str,
    aoi_label: str,
    include_ionosphere: bool = False,
) -> dict[str, Any]:
    feature = entry["catalog_feature"]
    layers = (
        "unwrappedPhase",
        "coherenceMagnitude",
        "connectedComponents",
        "mask",
    )
    if include_ionosphere:
        layers += ("ionospherePhaseScreen", "ionospherePhaseScreenUncertainty")
    window = read_gunw_window(
        feature,
        polarization=polarization,
        bounds_wgs84=bounds,
        layers=layers,
        provider_qa_summary=entry["provider_qa_summary"],
    )
    selection = window.selection_mask
    if selection is None:
        raise RuntimeError("geographic GUNW read returned no pixel-center selection mask")
    decoded_mask = decode_gunw_mask(window.arrays["mask"])
    array_summaries = {}
    for name, values in window.arrays.items():
        selected = values[selection]
        array_summaries[name] = {
            "enclosing_window": _numeric_summary(values),
            "selected_aoi_centers": _numeric_summary(selected),
            "sha256": window.access["window_provenance"]["layers"][name]["sha256"],
        }
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    module_sha256 = hashlib.sha256(
        Path("echo/gunw_access.py").read_bytes()
    ).hexdigest()
    tool_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return {
        "schema_version": 1,
        "record_type": "ECHO_GUNW_BOUNDED_PIXEL_WINDOW_REVIEW",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "application_revision": head,
        "reader_source_sha256": module_sha256,
        "inspection_tool_sha256": tool_sha256,
        "product_specification": {
            "version": "1.5.0",
            "source_url": GUNW_SCHEMA_URL,
            "source_sha256": GUNW_SCHEMA_SHA256,
        },
        "area_label": entry["area_label"],
        "aoi_label": aoi_label,
        "aoi_role": "bounded pixel-access and mask characterization; not an event boundary",
        "bounds_wgs84": list(bounds),
        "scene_id": window.scene_id,
        "polarization": window.polarization,
        "identification": window.identification,
        "catalog_feature_sha256": entry["catalog_feature_sha256"],
        "provider_qa": window.provider_qa,
        "grid": window.grid_metadata,
        "window": {
            "rows": [window.row_start, window.row_stop],
            "columns": [window.column_start, window.column_stop],
            "enclosing_shape": list(window.arrays["unwrappedPhase"].shape),
            "selected_pixel_center_count": int(selection.sum()),
            "selection": window.access["geographic_selection"],
            "coordinate_sha256": window.access["window_provenance"]["coordinates"],
        },
        "range_read": {
            "provider": window.access["provider"],
            "method": window.access["method"],
            "range_bytes_requested": window.access["fsspec_range_bytes_requested"],
            "range_byte_limit": window.access["maximum_range_bytes"],
            "complete_product_download_requested": False,
        },
        "layers": array_summaries,
        "decoded_mask_summary": _mask_summary(decoded_mask, selection),
        "scientific_disposition": {
            "status": "PIXEL_ACCESS_AND_MASK_CHARACTERIZATION_ONLY",
            "provider_qa_status_preserved": window.provider_qa["status"],
            "ionosphere_layers_included": include_ionosphere,
            "ionosphere_correction_applied": False,
            "phase_correction_applied": False,
            "phase_to_displacement_conversion_applied": False,
            "change_measurement_performed": False,
            "event_extent_or_cause_inferred": False,
            "interpretation": (
                "The selected AOI window was read and summarized. Phase values must not be "
                "interpreted independently of the GUNW mask and other quality evidence; "
                "this record makes no event or displacement finding."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-id", default=DEFAULT_SCENE)
    parser.add_argument("--screen", type=Path, default=SCREEN_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--polarization", choices=("HH", "VV"), default="HH")
    parser.add_argument(
        "--aoi-label",
        default="approximate Ayazaga catalog-search point",
        help="descriptive AOI label; it does not imply an event boundary",
    )
    parser.add_argument(
        "--include-ionosphere",
        action="store_true",
        help="also read the GUNW ionosphere phase screen and uncertainty layers",
    )
    parser.add_argument(
        "--bounds",
        nargs=4,
        type=float,
        metavar=("WEST", "SOUTH", "EAST", "NORTH"),
        default=DEFAULT_BOUNDS,
    )
    args = parser.parse_args()
    screen = json.loads(args.screen.read_text(encoding="utf-8"))
    entry = _find_entry(screen, args.scene_id)
    record = build_record(
        entry,
        bounds=tuple(args.bounds),
        polarization=args.polarization,
        aoi_label=args.aoi_label,
        include_ionosphere=args.include_ionosphere,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    phase = record["layers"]["unwrappedPhase"]["selected_aoi_centers"]
    mask = record["decoded_mask_summary"]
    print(f"Wrote GUNW window review to {args.output}")
    print(
        f"scene={record['scene_id']} provider_qa={record['provider_qa']['status']} "
        f"selected_centers={record['window']['selected_pixel_center_count']} "
        f"phase_finite={phase['finite_or_integer_count']} "
        f"mask_subswath_support={mask['nonzero_reference_and_secondary_subswath_count']} "
        f"interpretation={record['scientific_disposition']['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
