#!/usr/bin/env python3
"""Screen a local, bounded MOD13Q1 pair against a linked RTC-S1 case."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any

import numpy as np
import rasterio
import requests
from pyproj import Transformer
from shapely import contains_xy, transform as transform_geometry
from shapely.geometry import box
from rasterio.transform import xy

from echo.modis_vi import build_mod13q1_candidate_screen


COLLECTION_ID = "C1748066515-LPCLOUD"
SHORT_NAME = "MOD13Q1"
VERSION = "061"
GRID_NAME = "MODIS_Grid_16DAY_250m_500m_VI"
LAYERS = {
    "ndvi": "250m 16 days NDVI",
    "detailed_qa": "250m 16 days VI Quality",
    "composite_doy": "250m 16 days composite day of the year",
    "summary_qa": "250m 16 days pixel reliability",
}
QA_REFERENCE = "NASA LP DAAC MOD13 User Guide V6.1, Tables 1, 4, 5; DOI 10.5067/MODIS/MOD13Q1.061"


class ScreenError(ValueError):
    """Raised when CMR or local MODIS sources do not meet the screen contract."""


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(args, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "")
        raise ScreenError(f"GDAL extraction failed: {str(detail).strip()[:500]}") from exc
    return result.stdout


def _cmr_granules(bounds: list[float], start: str, end: str) -> list[dict[str, Any]]:
    response = requests.get(
        "https://cmr.earthdata.nasa.gov/search/granules.json",
        params={
            "collection_concept_id": COLLECTION_ID,
            "bounding_box": ",".join(str(value) for value in bounds),
            "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
            "page_size": 200,
        },
        timeout=45,
    )
    response.raise_for_status()
    entries = response.json().get("feed", {}).get("entry", [])
    if not isinstance(entries, list):
        raise ScreenError("CMR returned an invalid granule listing")
    return entries


def _granule_info(path: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not re.fullmatch(r"MOD13Q1\.A\d{7}\.h\d{2}v\d{2}\.061\.\d{13}\.hdf", path.name):
        raise ScreenError(f"unexpected MOD13Q1 filename: {path.name}")
    granule_id = path.name.removesuffix(".hdf")
    entry = next((item for item in entries if item.get("producer_granule_id") == granule_id), None)
    if entry is None:
        raise ScreenError(f"CMR did not return the supplied source granule: {granule_id}")
    url = next(
        (
            link["href"] for link in entry.get("links", [])
            if link.get("rel", "").endswith("data#") and link.get("href", "").endswith(".hdf")
        ),
        None,
    )
    if not isinstance(url, str):
        raise ScreenError(f"CMR granule has no HDF data link: {granule_id}")
    return {
        "provider": "NASA LP DAAC",
        "collection_concept_id": COLLECTION_ID,
        "cmr_granule_concept_id": entry["id"],
        "granule_id": granule_id,
        "period_start_date_utc": entry["time_start"][:10],
        "period_end_date_utc": entry["time_end"][:10],
        "tile_id": re.search(r"\.(h\d{2}v\d{2})\.", path.name).group(1),
        "source_url": url,
        "retrieved_local_filename": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "cmr_updated_at_utc": entry.get("updated"),
    }


def _local_arrays(
    pair_record: dict[str, Any],
    source_paths: list[Path],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, Any], list[dict[str, Any]]]:
    bounds = pair_record["grid"]["window"]["bounds_wgs84"]
    dates = [
        pair_record["source_products"][role]["acquisition_start_utc"][:10]
        for role in ("before", "after")
    ]
    if len(source_paths) < 2:
        raise ScreenError("provide the HDF tiles for both composite periods")
    entries = _cmr_granules(bounds, dates[0], dates[1])
    sources = [_granule_info(path, entries) for path in source_paths]
    period_for_date: dict[str, str] = {}
    for date in dates:
        covering = [
            item for item in sources
            if item["period_start_date_utc"] <= date <= item["period_end_date_utc"]
        ]
        periods = sorted({item["period_start_date_utc"] for item in covering})
        if len(periods) != 1:
            raise ScreenError(f"SAR date {date} maps to {len(periods)} supplied MODIS periods")
        period_for_date[date] = periods[0]
    selected_periods = set(period_for_date.values())
    selected = [item for item in sources if item["period_start_date_utc"] in selected_periods]
    tiles_by_period = {
        period: {item["tile_id"] for item in selected if item["period_start_date_utc"] == period}
        for period in selected_periods
    }
    if len(selected_periods) != 2 or len(set(map(tuple, (sorted(tiles) for tiles in tiles_by_period.values())))) != 1:
        raise ScreenError("the two SAR dates require two distinct periods with the same MODIS tile coverage")

    result: dict[str, dict[str, np.ndarray]] = {}
    grid: dict[str, Any] | None = None
    with tempfile.TemporaryDirectory(prefix="echo-mod13q1-") as temporary:
        temp = Path(temporary)
        for role, target_date in zip(("before", "after"), dates):
            period = period_for_date[target_date]
            period_sources = [
                source_paths[sources.index(source)]
                for source in selected if source["period_start_date_utc"] == period
            ]
            role_arrays: dict[str, np.ndarray] = {}
            for key, layer in LAYERS.items():
                subdatasets = [
                    f'HDF4_EOS:EOS_GRID:"{path}":{GRID_NAME}:"{layer}"'
                    for path in period_sources
                ]
                vrt = temp / f"{role}-{key}.vrt"
                tif = temp / f"{role}-{key}.tif"
                _run(["gdalbuildvrt", "-overwrite", str(vrt), *subdatasets])
                _run([
                    "gdal_translate", "-q", "-projwin_srs", "EPSG:4326",
                    "-projwin", str(bounds[0]), str(bounds[3]), str(bounds[2]), str(bounds[1]),
                    str(vrt), str(tif),
                ])
                with rasterio.open(tif) as dataset:
                    signature = {
                        "crs": dataset.crs.to_string(),
                        "transform": list(dataset.transform)[:6],
                        "shape": [dataset.height, dataset.width],
                    }
                    if grid is None:
                        grid = signature
                    elif signature != grid:
                        raise ScreenError("bounded MODIS layer windows do not share one native grid")
                    role_arrays[key] = dataset.read(1)
            result[role] = role_arrays
        assert grid is not None
        transform = rasterio.Affine(*grid["transform"])
        aoi = transform_geometry(
            box(*bounds),
            Transformer.from_crs("EPSG:4326", grid["crs"], always_xy=True).transform,
            interleaved=False,
        )
        row_index, column_index = np.meshgrid(
            np.arange(grid["shape"][0]), np.arange(grid["shape"][1]), indexing="ij"
        )
        center_x, center_y = xy(
            transform, row_index.ravel(), column_index.ravel(), offset="center"
        )
        aoi_mask = contains_xy(
            aoi,
            np.asarray(center_x).reshape(row_index.shape),
            np.asarray(center_y).reshape(row_index.shape),
        )
        result["before"]["aoi_center_mask"] = aoi_mask
        result["after"]["aoi_center_mask"] = aoi_mask.copy()
    return result["before"], result["after"], grid, sources


def screen(
    pair_path: Path,
    case_id: str,
    source_paths: list[Path],
    output_path: Path,
) -> dict[str, Any]:
    pair_bytes = pair_path.read_bytes()
    pair = json.loads(pair_bytes)
    before, after, grid, sources = _local_arrays(pair, source_paths)
    record = build_mod13q1_candidate_screen(
        pair_record=pair,
        case_id=case_id,
        pair_record_sha256=sha256(pair_bytes).hexdigest(),
        source_pair_record_path=str(pair_path),
        before_arrays=before,
        after_arrays=after,
        grid=grid,
        source_granules=sources,
        qa_policy_reference=QA_REFERENCE,
        processed_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair-record", required=True, type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--source-hdf", required=True, type=Path, action="append", help="repeat for every intersecting tile in both periods")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    record = screen(args.pair_record, args.case_id, args.source_hdf, args.output)
    observation = record["observations"]
    print(f"status={record['status']}")
    print(f"aoi_pixel_centers={observation['before']['aoi_pixel_center_count']}")
    print(f"strict_common_accepted={observation['common_strictly_accepted_pixel_count']}")
    print(f"paired_timing_suitable={observation['paired_timing_suitable_for_sar_date_comparison']}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
