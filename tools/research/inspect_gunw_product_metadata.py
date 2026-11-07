"""Review one retained PROVISIONAL GUNW QA report and bounded HDF5 metadata."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import earthaccess
import h5py
from aiohttp import ClientTimeout

from echo.nisar_access import NisarAccessError, _install_read_budget
from echo.qa_report import _canonical_report_uri, read_qa_report


SCREEN_PATH = Path("data/research/gunw-provisional-qa-screen-2026-11-07.json")
OUTPUT_PATH = Path("data/research/gunw-p05023-product-metadata-review.json")
MAX_METADATA_BYTES = 64 * 1024 * 1024
REMOTE_BLOCK_BYTES = 1024 * 1024
ASF_HOST = "nisar.asf.earthdatacloud.nasa.gov"
IDENTIFICATION_FIELDS = (
    "instrumentName",
    "listOfObservationModes",
    "missionId",
    "productVersion",
    "productSpecificationVersion",
    "productType",
    "radarBand",
    "listOfFrequencies",
    "absoluteOrbitNumber",
    "trackNumber",
    "frameNumber",
    "zeroDopplerStartTime",
    "zeroDopplerEndTime",
    "lookDirection",
)


def _json_scalar(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "tolist"):
        return _json_scalar(value.tolist())
    if isinstance(value, list):
        return [_json_scalar(item) for item in value]
    if isinstance(value, tuple):
        return [_json_scalar(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _find_entry(screen: dict[str, Any], scene_id: str) -> dict[str, Any]:
    for entry in screen.get("entries", []):
        if entry.get("scene_id") == scene_id and isinstance(
            entry.get("catalog_feature"), dict
        ):
            return entry
    raise ValueError(f"scene is not in the retained GUNW QA screen: {scene_id}")


def _inspect_hdf5_metadata(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature["properties"]
    scene_id = properties["fileID"]
    product_url = properties["url"]
    auth = earthaccess.login(strategy="netrc", persist=False)
    if not auth.authenticated:
        raise RuntimeError("Earthdata Login is not authenticated via local netrc")
    filesystem = earthaccess.get_fsspec_https_session()
    filesystem.client_kwargs = {
        **filesystem.client_kwargs,
        "timeout": ClientTimeout(total=90, connect=10, sock_read=60),
    }
    result: dict[str, Any] = {
        "method": "h5py over authenticated HTTPS range reads",
        "product_url": product_url,
        "maximum_range_bytes": MAX_METADATA_BYTES,
        "pixel_arrays_read": False,
    }
    cache = None
    try:
        with filesystem.open(
            product_url,
            "rb",
            block_size=REMOTE_BLOCK_BYTES,
            cache_type="bytes",
        ) as remote:
            cache = _install_read_budget(remote, limit_bytes=MAX_METADATA_BYTES)
            with h5py.File(remote, "r") as product:
                root = "science/LSAR/identification"
                if root not in product:
                    raise ValueError("GUNW product lacks its expected identification group")
                group = product[root]
                identification = {
                    name: _json_scalar(group[name][()])
                    for name in IDENTIFICATION_FIELDS
                    if name in group
                }
                gunw_root = "science/LSAR/GUNW"
                groups = list(product[gunw_root].keys()) if gunw_root in product else []
        result.update(
            {
                "status": "METADATA_READ_COMPLETE",
                "range_bytes_requested": int(cache.total_requested_bytes),
                "identification": identification,
                "gunw_root_groups": groups,
            }
        )
    except NisarAccessError:
        result.update(
            {
                "status": "BLOCKED_BY_RANGE_READ_BUDGET",
                "range_bytes_requested_before_block": (
                    int(cache.total_requested_bytes) if cache is not None else None
                ),
                "note": (
                    "ECHO's range guard declined an HDF5 metadata request that would exceed "
                    "the configured budget. No pixel arrays were read."
                ),
            }
        )
    return result


def inspect_entry(entry: dict[str, Any]) -> dict[str, Any]:
    feature = entry["catalog_feature"]
    properties = feature["properties"]
    scene_id = entry["scene_id"]
    if (
        properties.get("fileID") != scene_id
        or properties.get("processingLevel") != "GUNW"
        or properties.get("crid") != "P05023"
    ):
        raise ValueError("selected item is not the retained P05023 GUNW product")
    _canonical_report_uri(feature)
    summary = entry["provider_qa_summary"]
    checks = summary["check_rows"]
    nonpassing = [row for row in checks if row.get("Result", "").upper() != "PASS"]
    report = read_qa_report(feature)
    hdf5 = _inspect_hdf5_metadata(feature)
    return {
        "schema_version": 1,
        "record_type": "ECHO_GUNW_PRODUCT_METADATA_REVIEW",
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "mission": "NISAR",
        "instrument": "LSAR",
        "scene_id": scene_id,
        "area_label": entry["area_label"],
        "collection": properties["collectionName"],
        "crid": properties["crid"],
        "catalog_feature_sha256": entry["catalog_feature_sha256"],
        "provider_qa_summary": {
            "artifact_uri": summary["artifact_uri"],
            "artifact_sha256": summary["artifact_sha256"],
            "artifact_size_bytes": summary["artifact_size_bytes"],
            "retrieved_at_utc": summary["retrieved_at_utc"],
            "observed_provider_status": summary["observed_provider_status"],
            "check_row_count": len(checks),
            "nonpassing_rows": nonpassing,
        },
        "nasa_subject_matter_expert_guidance": {
            "source_url": "https://forum.earthdata.nasa.gov/viewtopic.php?t=8325",
            "author_role": "NISAR subject matter expert on NASA Earthdata Forum",
            "posted_at": "2026-10-22",
            "scope": "PROVISIONAL GUNW products with identification QA summary failures",
            "guidance": {
                "qa_summary": "The QA check summary may be ignored by users at this stage.",
                "crid": (
                    "Using a consistent CRID for time-series analysis is acceptable; mixing "
                    "P05023 with earlier CRIDs, including BETA, should be done with caution."
                ),
                "nominal_pair_network": (
                    "The mission currently produces nearest-neighbor interferograms, nominally "
                    "12 days apart."
                ),
                "phase_corrections": (
                    "Correction layers are expected to be removed by subtraction from "
                    "unwrapped phase."
                ),
                "product_accuracy": (
                    "N/F reflects the worse orbit/attitude accuracy designation; in normal "
                    "production F is usually due to attitude, while urgent-response products "
                    "may require special care."
                ),
            },
            "echo_disposition": (
                "retained_provider_FAIL; expert guidance permits user consideration of the "
                "product, but does not establish scene-specific scientific suitability"
            ),
        },
        "qa_report_review": report,
        "hdf5_metadata_probe": hdf5,
        "product_access": {
            "catalog": entry["catalog_retrieved_at_utc"],
            "qa_summary_retrieval": summary["retrieval"],
            "qa_report_retrieval": report["retrieval"],
            "pixel_arrays_read": False,
        },
        "interpretation_limit": (
            "No interferogram phase, coherence, connected-component, offset, or correction "
            "pixels were read or interpreted. This record does not authorize a change finding."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--screen", type=Path, default=SCREEN_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    screen = json.loads(args.screen.read_text(encoding="utf-8"))
    record = inspect_entry(_find_entry(screen, args.scene_id))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote GUNW metadata review to {args.output}")
    print(
        f"scene={record['scene_id']} qa={record['provider_qa_summary']['observed_provider_status']} "
        f"hdf5={record['hdf5_metadata_probe']['status']} "
        f"pixel_arrays_read={record['product_access']['pixel_arrays_read']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
