"""Record a bounded, metadata-only ASF GUNW availability and QA screen."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from importlib.metadata import version
from io import StringIO
from urllib.parse import urlsplit

import asf_search as asf
import earthaccess
from aiohttp import ClientTimeout

from echo.nisar_access import _install_read_budget


MAX_QA_SUMMARY_BYTES = 64 * 1024
RANGE_BLOCK_BYTES = 16 * 1024
SCENES = (
    ("Istanbul", "POINT(28.99 41.105)"),
    ("Rasuwa Nepal", "POINT(85.55 28.30)"),
    ("Southern Mozambique", "POINT(33.5 -24.5)"),
    ("Beirut", "POINT(35.5 33.9)"),
    ("Tehran", "POINT(51.4 35.7)"),
)
START_DATE = "2026-06-17"
END_DATE = "2026-11-07"
COLLECTION = "NISAR_L2_GUNW_PROVISIONAL_V1"
ASF_HOST = "nisar.asf.earthdatacloud.nasa.gov"


def _catalog_query(intersects: str) -> dict[str, object]:
    return {
        "processingLevel": ["GUNW"],
        "dataset": ["NISAR"],
        "dataMaturity": "PROVISIONAL",
        "start": START_DATE,
        "end": END_DATE,
        "maxResults": 100,
        "intersectsWith": intersects,
    }


def _canonical_qa_uri(feature: dict[str, object]) -> tuple[str, str]:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("catalog feature has no properties object")
    scene_id = properties.get("fileID")
    product_url = properties.get("url")
    if not isinstance(scene_id, str) or not isinstance(product_url, str):
        raise ValueError("catalog feature is missing product identity or URL")
    parsed = urlsplit(product_url)
    parts = tuple(part for part in parsed.path.split("/") if part)
    if (
        parsed.scheme != "https"
        or parsed.hostname != ASF_HOST
        or parsed.netloc != ASF_HOST
        or parsed.query
        or parsed.fragment
        or parts != ("NISAR", COLLECTION, scene_id, f"{scene_id}.h5")
    ):
        raise ValueError("catalog URL is not a canonical PROVISIONAL GUNW product")
    return scene_id, product_url.rsplit("/", 1)[0] + f"/{scene_id}_QA_SUMMARY.csv"


def _fetch_summary(filesystem, uri: str) -> dict[str, object]:
    with filesystem.open(
        uri,
        "rb",
        block_size=RANGE_BLOCK_BYTES,
        cache_type="bytes",
    ) as stream:
        cache = _install_read_budget(stream, limit_bytes=MAX_QA_SUMMARY_BYTES)
        content = stream.read(MAX_QA_SUMMARY_BYTES + 1)
    if len(content) > MAX_QA_SUMMARY_BYTES:
        raise ValueError("QA summary exceeded the configured byte limit")
    text = content.decode("utf-8-sig")
    rows = list(csv.DictReader(StringIO(text)))
    headers = {header.strip() for header in (rows[0].keys() if rows else ())}
    if not {"Tool", "Check", "Result", "Threshold", "Actual", "Notes"} <= headers:
        raise ValueError("QA summary is missing expected CSV columns")
    if not rows or any((row.get("Tool") or "").strip() != "QA" for row in rows):
        raise ValueError("QA summary has no valid provider check rows")
    statuses = {(row.get("Result") or "").strip().upper() for row in rows}
    reported_status = "FAIL" if "FAIL" in statuses else "NO_FAIL_REPORTED"
    return {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_uri": uri,
        "artifact_size_bytes": len(content),
        "artifact_sha256": hashlib.sha256(content).hexdigest(),
        "retrieval": {
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "bounded HTTPS byte-range read",
            "range_block_bytes": RANGE_BLOCK_BYTES,
            "range_bytes_requested": int(cache.total_requested_bytes),
            "maximum_bytes": MAX_QA_SUMMARY_BYTES,
            "network_retrieval": True,
        },
        "observed_provider_status": reported_status,
        "check_rows": [
            {key: (value or "").strip() for key, value in row.items()}
            for row in rows
        ],
    }


def build_screen() -> dict[str, object]:
    auth = earthaccess.login(strategy="netrc", persist=False)
    if not auth.authenticated:
        raise RuntimeError("Earthdata Login is not authenticated via local netrc")
    filesystem = earthaccess.get_fsspec_https_session()
    filesystem.client_kwargs = {
        **filesystem.client_kwargs,
        "timeout": ClientTimeout(total=25, connect=10, sock_read=20),
    }

    validated_query = {
        "processingLevel": ["GUNW"],
        "dataset": ["NISAR"],
        "dataMaturity": "VALIDATED",
        "start": "2026-10-21",
        "end": END_DATE,
        "maxResults": 250,
    }
    validated_features = asf.search(
        opts=asf.ASFSearchOptions(**validated_query)
    ).geojson().get("features", [])
    validated_availability = {
        "query": validated_query,
        "result_count": len(validated_features),
        "sample_scene_ids": [
            feature.get("properties", {}).get("fileID")
            for feature in validated_features[:10]
        ],
        "collection_counts": dict(
            Counter(
                feature.get("properties", {}).get("collectionName", "UNKNOWN")
                for feature in validated_features
            )
        ),
        "count_is_capped_at_max_results": len(validated_features)
        == validated_query["maxResults"],
    }

    seen_scene_ids: set[str] = set()
    entries: list[dict[str, object]] = []
    for label, geometry in SCENES:
        query = _catalog_query(geometry)
        features = asf.search(opts=asf.ASFSearchOptions(**query)).geojson().get(
            "features", []
        )
        catalog_retrieved_at = datetime.now(timezone.utc).isoformat()
        selected = next(
            (
                feature
                for feature in features
                if feature.get("properties", {}).get("fileID") not in seen_scene_ids
            ),
            None,
        )
        entry: dict[str, object] = {
            "area_label": label,
            "query": query,
            "catalog_retrieved_at_utc": catalog_retrieved_at,
            "catalog_result_count": len(features),
            "selection_rule": "first ASF response-order feature not already sampled",
        }
        if selected is None:
            entry["sample_status"] = "NO_UNIQUE_CANDIDATE"
            entries.append(entry)
            continue

        scene_id, qa_uri = _canonical_qa_uri(selected)
        seen_scene_ids.add(scene_id)
        entry.update(
            {
                "sample_status": "QA_RETRIEVED",
                "scene_id": scene_id,
                "catalog_feature_sha256": hashlib.sha256(
                    json.dumps(
                        selected,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest(),
                "catalog_feature": selected,
                "provider_qa_summary": _fetch_summary(filesystem, qa_uri),
            }
        )
        entries.append(entry)

    return {
        "record_type": "ECHO_PRODUCT_QA_SCREEN",
        "schema_version": 1,
        "screened_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "bounded GUNW product-path feasibility screen; no interferogram arrays read",
        "source": {
            "catalog_provider": "Alaska Satellite Facility DAAC",
            "catalog_client": "asf_search",
            "catalog_client_version": version("asf-search"),
            "qa_artifact_provider": "Alaska Satellite Facility DAAC",
        },
        "product_scope": {
            "mission": "NISAR",
            "product": "L2 GUNW",
            "collection": COLLECTION,
            "data_maturity": "PROVISIONAL",
            "catalog_start_date": START_DATE,
            "catalog_end_date": END_DATE,
            "maximum_results_per_point": 100,
            "catalog_searches_are_metadata_only": True,
            "radar_product_pixels_read": False,
        },
        "sampling_limit": "one response-order product per point; targeted feasibility sample, not an archive census",
        "validated_gunw_availability_probe": validated_availability,
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/research/gunw-provisional-qa-screen-2026-11-07.json"),
    )
    args = parser.parse_args()
    screen = build_screen()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(screen, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    counts = [entry["catalog_result_count"] for entry in screen["entries"]]
    outcomes = [
        entry.get("provider_qa_summary", {}).get("observed_provider_status")
        for entry in screen["entries"]
    ]
    print(f"Wrote GUNW QA screen to {args.output}")
    print(f"Point-search result counts: {counts}")
    print(f"Sampled provider QA outcomes: {outcomes}")
    print(
        "Validated GUNW result count:",
        screen["validated_gunw_availability_probe"]["result_count"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
