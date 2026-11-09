"""Validation for supplemental HLS candidate screens that lack paired support."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import numpy as np


EXPECTED_CANDIDATES = {
    "before": ("HLS.L30.T22JDM.2024129T131759.v2.0", "G2991124953-LPCLOUD"),
    "after_selected": ("HLS.L30.T22JDM.2024161T131748.v2.0", "G3119894050-LPCLOUD"),
    "after_existing": ("HLS.L30.T22JDM.2024153T131804.v2.0", "G3058321942-LPCLOUD"),
}


def validate_hls_candidate_screen(
    record: dict[str, Any],
    *,
    pair_record: dict[str, Any],
    case_id: str,
    aoi_bounds: list[float],
    evidence_root: Path,
) -> dict[str, Any]:
    """Recheck the bounded search result and prove the selected pair has no NDVI support."""
    source = record.get("source", {})
    query = record.get("query", {})
    observations = record.get("observations")
    comparison = record.get("comparison", {})
    discovery = record.get("candidate_discovery", {})
    expected_pair_dates = [
        pair_record.get("source_products", {}).get(role, {}).get("acquisition_start_utc", "")[:10]
        for role in ("before", "after")
    ]
    if (
        record.get("record_type") != "ECHO_HLS_L30_VEGETATION_CONTEXT_SCREEN"
        or record.get("case_id") != case_id
        or source.get("provider") != "NASA LP DAAC"
        or source.get("short_name") != "HLSL30"
        or source.get("product_variant") != "L30"
        or source.get("collection_id") != "C2021957657-LPCLOUD"
        or query.get("bbox_west_south_east_north") != aoi_bounds
        or query.get("before_date_utc") != "2024-05-08"
        or query.get("after_date_utc") != "2024-06-09"
        or expected_pair_dates != ["2024-05-11", "2024-06-04"]
        or observations is None
        or len(observations) != 2
        or comparison.get("aoi_center_pixel_count") != 1152
        or comparison.get("common_clear_land_ndvi_pixel_count") != 0
        or comparison.get("common_clear_land_aoi_fraction") != 0.0
        or any(value is not None for key, value in comparison.get("ndvi", {}).items() if key.startswith("common_clear_land_"))
    ):
        raise ValueError("supplemental HLS candidate screen identity, bounds, dates, or no-support result is invalid")
    if (
        discovery.get("provider") != "NASA CMR"
        or discovery.get("collection_concept_id") != "C2021957657-LPCLOUD"
        or discovery.get("pagination_complete") is not True
        or len(discovery.get("windows", [])) != 2
    ):
        raise ValueError("supplemental HLS candidate discovery metadata is incomplete")
    windows = {item.get("label"): item for item in discovery["windows"]}
    root = evidence_root.resolve()
    expected_windows = {
        "before": ("2024-05-03T00:00:00Z,2024-05-19T23:59:59Z", 1),
        "after": ("2024-05-27T00:00:00Z,2024-06-12T23:59:59Z", 2),
    }
    for label, (temporal, hits) in expected_windows.items():
        window = windows.get(label, {})
        candidates = window.get("candidates", [])
        if (
            window.get("temporal") != temporal
            or window.get("bbox_west_south_east_north") != aoi_bounds
            or window.get("http_status") != 200
            or window.get("cmr_hits") != hits
            or window.get("returned_count") != hits
            or len(candidates) != hits
            or len(window.get("response_sha256", "")) != 64
        ):
            raise ValueError(f"supplemental HLS CMR {label} candidate window is inconsistent")
        response_relative = Path(window.get("response_relative_path", ""))
        if response_relative.is_absolute():
            raise ValueError("supplemental HLS CMR response path must be relative")
        response_path = (root / response_relative).resolve()
        if not response_path.is_relative_to(root):
            raise ValueError("supplemental HLS CMR response path escapes the evidence root")
        response_bytes = response_path.read_bytes()
        if (
            len(response_bytes) > 2 * 1024 * 1024
            or len(response_bytes) != window.get("response_bytes")
            or sha256(response_bytes).hexdigest() != window.get("response_sha256")
        ):
            raise ValueError("supplemental HLS CMR response checksum or size is invalid")
        try:
            raw_items = json.loads(response_bytes).get("items", [])
            raw_candidates = [
                {
                    "granule_id": item.get("umm", {}).get("GranuleUR"),
                    "cmr_concept_id": item.get("meta", {}).get("concept-id"),
                    "acquisition_utc": item.get("umm", {}).get("TemporalExtent", {}).get("RangeDateTime", {}).get("BeginningDateTime"),
                }
                for item in raw_items
            ]
        except (json.JSONDecodeError, TypeError, AttributeError) as exc:
            raise ValueError("supplemental HLS CMR response is not valid UMM JSON") from exc
        if raw_candidates != candidates:
            raise ValueError("supplemental HLS CMR candidate list does not match its retained response")
    actual = [
        (item.get("granule_id"), item.get("cmr_concept_id"))
        for item in observations
    ]
    if actual != [EXPECTED_CANDIDATES["before"], EXPECTED_CANDIDATES["after_selected"]]:
        raise ValueError("supplemental HLS observations do not match the selected CMR candidate pair")
    all_candidates = {
        (item.get("granule_id"), item.get("cmr_concept_id"))
        for window in windows.values()
        for item in window.get("candidates", [])
    }
    if not set(EXPECTED_CANDIDATES.values()).issubset(all_candidates):
        raise ValueError("supplemental HLS CMR record omits a candidate used for selection")
    observed_fmask_counts: list[dict[str, int]] = []
    for observation in observations:
        asset = observation.get("asset", {})
        relative = Path(asset.get("relative_path", ""))
        if relative.is_absolute():
            raise ValueError("supplemental HLS asset path must be relative")
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            raise ValueError("supplemental HLS asset path escapes the evidence root")
        payload = path.read_bytes()
        if (
            len(payload) > 64 * 1024 * 1024
            or len(payload) != asset.get("size_bytes")
            or sha256(payload).hexdigest() != asset.get("sha256")
        ):
            raise ValueError("supplemental HLS bounded asset checksum or size is invalid")
        with np.load(path, allow_pickle=False) as archive:
            if set(archive.files) != {"B04", "B05", "Fmask", "AOI"}:
                raise ValueError("supplemental HLS bounded asset has unexpected arrays")
            aoi = archive["AOI"].astype(bool)
            fmask = archive["Fmask"][aoi]
        counts = {str(int(value)): int(count) for value, count in zip(*np.unique(fmask, return_counts=True), strict=True)}
        if int(aoi.sum()) != comparison.get("aoi_center_pixel_count") or counts != observation.get("fmask_class_counts_in_aoi"):
            raise ValueError("supplemental HLS AOI or Fmask counts do not reproduce from the bounded asset")
        observed_fmask_counts.append(counts)
    after = np.array([int(key) for key in observed_fmask_counts[1] for _ in range(observed_fmask_counts[1][key])], dtype=np.uint8)
    if (
        len(after) != 1152
        or not np.all((after & 2) != 0)
        or not np.all(((after >> 6) & 3) == 3)
        or observed_fmask_counts[1] != {"194": 1152}
    ):
        raise ValueError("supplemental HLS selected observation does not reproduce the all-cloud/high-aerosol Fmask hold")
    return {
        "candidate_count_before": expected_windows["before"][1],
        "candidate_count_after": expected_windows["after"][1],
        "selected_before_granule": actual[0][0],
        "selected_after_granule": actual[1][0],
        "aoi_center_pixel_count": 1152,
        "after_fmask_class_counts": observed_fmask_counts[1],
        "common_clear_land_ndvi_pixel_count": 0,
        "common_clear_land_aoi_fraction": 0.0,
        "ndvi_difference_computed": False,
        "interpretation_role": "candidate coverage screen only; insufficient clear-land support; does not test vegetation causality or validate SAR",
    }
