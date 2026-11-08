#!/usr/bin/env python3
"""Retrieve bounded NASA HLS L30 or S30 reflectance and screen vegetation context."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
from typing import Any

import earthaccess
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.windows import from_bounds
from shapely import contains_xy, transform as shapely_transform
from shapely.geometry import box


VERSION = "2.0"
HLS_PRODUCTS = {
    "L30": {
        "short_name": "HLSL30",
        "collection_id": "C2021957657-LPCLOUD",
        "granule_prefix": "HLS.L30.",
        "nir_band": "B05",
        "product_title": "Harmonized Landsat and Sentinel-2 L30 surface reflectance/NBAR",
    },
    "S30": {
        "short_name": "HLSS30",
        "collection_id": "C2021957295-LPCLOUD",
        "granule_prefix": "HLS.S30.",
        "nir_band": "B8A",
        "product_title": "Harmonized Landsat and Sentinel-2 S30 surface reflectance/NBAR",
    },
}
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MAX_WINDOW_CELLS = 65_536
FILL_VALUE = -9999
FMASK_FILL = 255
REFLECTANCE_SCALE = 0.0001


def _bbox(value: str) -> tuple[float, float, float, float]:
    try:
        west, south, east, north = (float(part) for part in value.split(","))
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("bbox must be west,south,east,north") from exc
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise argparse.ArgumentTypeError("bbox bounds are invalid")
    return west, south, east, north


def _item_for_granule(
    day: date,
    bbox: tuple[float, float, float, float],
    granule_id: str,
    product_variant: str,
):
    product = HLS_PRODUCTS[product_variant]
    results = earthaccess.search_data(
        short_name=product["short_name"],
        version=VERSION,
        temporal=(day.isoformat(), day.isoformat()),
        bounding_box=bbox,
        count=100,
    )
    for item in results:
        umm = item.get("umm", {})
        if umm.get("GranuleUR") == granule_id:
            if (
                item.get("meta", {}).get("collection-concept-id") != product["collection_id"]
                or not granule_id.startswith(product["granule_prefix"])
                or not granule_id.endswith(".v2.0")
            ):
                raise ValueError("CMR granule collection identity differs from the requested HLS product")
            if item.get("meta", {}).get("provider-id") != "LPCLOUD":
                raise ValueError("CMR granule is not provided by LP DAAC")
            return item
    raise ValueError(f"requested HLS granule is absent from the bounded CMR query: {granule_id}")


def _read_cog_window(
    session: Any,
    source_url: str,
    bbox_wgs84: tuple[float, float, float, float],
) -> tuple[np.ndarray, dict[str, Any]]:
    # Earthdata redirects to a temporary signed object URL. Keep it in memory;
    # never persist or print it because it contains short-lived access material.
    probe = session.get(
        source_url,
        headers={"Range": "bytes=0-0"},
        timeout=(20, 60),
    )
    probe.raise_for_status()
    content_range = probe.headers.get("content-range", "")
    if probe.status_code != 206 or not content_range.startswith("bytes 0-0/"):
        raise RuntimeError("HLS source asset does not support bounded COG range access")
    try:
        source_size = int(content_range.rsplit("/", 1)[1])
    except (IndexError, ValueError) as exc:
        raise RuntimeError("HLS COG response omitted a valid total asset size") from exc

    with rasterio.open(probe.url) as dataset:
        transformer = Transformer.from_crs("EPSG:4326", dataset.crs, always_xy=True)
        aoi = shapely_transform(
            box(*bbox_wgs84),
            transformer.transform,
            interleaved=False,
        )
        window = from_bounds(*aoi.bounds, transform=dataset.transform).round_offsets().round_lengths()
        width = int(window.width)
        height = int(window.height)
        if width <= 0 or height <= 0 or width * height > MAX_WINDOW_CELLS:
            raise ValueError("requested HLS pixel window is empty or exceeds the 65,536-cell bound")
        values = dataset.read(1, window=window)
        row_indices, column_indices = np.meshgrid(
            np.arange(height) + int(window.row_off),
            np.arange(width) + int(window.col_off),
            indexing="ij",
        )
        pixel_x, pixel_y = rasterio.transform.xy(
            dataset.transform,
            row_indices.ravel(),
            column_indices.ravel(),
            offset="center",
        )
        inside = contains_xy(
            aoi,
            np.asarray(pixel_x).reshape((height, width)),
            np.asarray(pixel_y).reshape((height, width)),
        )
        details = {
            "crs": dataset.crs.to_string(),
            "transform": list(dataset.transform)[:6],
            "window": {
                "column_offset": int(window.col_off),
                "row_offset": int(window.row_off),
                "width": width,
                "height": height,
            },
            "resolution_m": [abs(float(value)) for value in dataset.res],
            "nodata": dataset.nodata,
            "source_asset_size_bytes": source_size,
            "aoi_center_pixel_count": int(inside.sum()),
        }
        return values, {**details, "aoi_center_mask": inside}


def _fmask_counts(values: np.ndarray, inside: np.ndarray) -> dict[str, int]:
    subset = values[inside]
    counts = {int(value): int(count) for value, count in zip(*np.unique(subset, return_counts=True))}
    return {str(key): counts[key] for key in sorted(counts)}


def _summarize_pair(
    before: dict[str, np.ndarray],
    after: dict[str, np.ndarray],
    before_inside: np.ndarray,
    after_inside: np.ndarray,
    nir_band: str,
) -> dict[str, Any]:
    if before_inside.shape != after_inside.shape or not np.array_equal(before_inside, after_inside):
        raise ValueError("paired HLS scenes do not have identical selected AOI pixel centers")
    inside = before_inside

    def derive(scene: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        red = scene["B04"].astype(np.float64) * REFLECTANCE_SCALE
        nir = scene[nir_band].astype(np.float64) * REFLECTANCE_SCALE
        qa = scene["Fmask"].astype(np.uint8)
        cloud = (qa & (1 << 1)) != 0
        adjacent = (qa & (1 << 2)) != 0
        shadow = (qa & (1 << 3)) != 0
        snow = (qa & (1 << 4)) != 0
        water = (qa & (1 << 5)) != 0
        high_aerosol = ((qa >> 6) & 0b11) == 0b11
        nodata = (scene["B04"] == FILL_VALUE) | (scene[nir_band] == FILL_VALUE) | (qa == FMASK_FILL)
        denominator = red + nir
        valid_land = (
            inside & ~nodata & ~cloud & ~adjacent & ~shadow & ~snow & ~water
            & ~high_aerosol & np.isfinite(denominator) & (denominator > 0)
        )
        ndvi = np.full(red.shape, np.nan, dtype=np.float64)
        ndvi[valid_land] = (nir[valid_land] - red[valid_land]) / denominator[valid_land]
        clear_water = inside & ~nodata & water & ~cloud & ~adjacent & ~shadow & ~snow
        return ndvi, valid_land, clear_water

    ndvi_before, valid_before, clear_water_before = derive(before)
    ndvi_after, valid_after, clear_water_after = derive(after)
    common_land = valid_before & valid_after
    delta = ndvi_after[common_land] - ndvi_before[common_land]
    return {
        "aoi_center_pixel_count": int(inside.sum()),
        "before_clear_land_ndvi_pixel_count": int(valid_before.sum()),
        "after_clear_land_ndvi_pixel_count": int(valid_after.sum()),
        "common_clear_land_ndvi_pixel_count": int(common_land.sum()),
        "common_clear_land_aoi_fraction": float(common_land.sum() / inside.sum()) if inside.any() else 0.0,
        "before_clear_water_class_pixel_count": int(clear_water_before.sum()),
        "after_clear_water_class_pixel_count": int(clear_water_after.sum()),
        "ndvi": {
            "definition": "(NIR surface reflectance - red surface reflectance) / (NIR surface reflectance + red surface reflectance)",
            "hls_bands": {"red": "B04", "nir": nir_band},
            "reflectance_scale_factor": REFLECTANCE_SCALE,
            "common_clear_land_median_before": float(np.median(ndvi_before[common_land])) if common_land.any() else None,
            "common_clear_land_median_after": float(np.median(ndvi_after[common_land])) if common_land.any() else None,
            "common_clear_land_median_change_after_minus_before": float(np.median(delta)) if delta.size else None,
            "common_clear_land_change_q10_q90": [float(value) for value in np.percentile(delta, [10, 90])] if delta.size else None,
            "inferential_statistics": "NOT_COMPUTED; the spatial sample is autocorrelated and this index difference does not establish a cause of SAR backscatter change",
        },
        "quality": {
            "fmask_variable": "HLS Fmask byte; bit 0 reserved, bit 1 cloud, bit 2 adjacent to cloud/shadow, bit 3 cloud shadow, bit 4 snow/ice, bit 5 water, bits 6-7 aerosol level",
            "ndvi_eligibility": "AOI pixel center; valid red, NIR, and Fmask; excludes cloud, cloud-adjacent, shadow, snow/ice, water, high aerosol (bits 6-7 == 3), and nonpositive NIR+red denominator",
            "clear_water_count_rule": "Fmask water bit set; valid Fmask and reflectance; excludes cloud, cloud-adjacent, shadow, and snow/ice; retained as a product class, not ground truth",
        },
    }


def retrieve_screen(
    *,
    product_variant: str = "L30",
    case_id: str,
    bbox_wgs84: tuple[float, float, float, float],
    before_date: date,
    after_date: date,
    before_granule_id: str,
    after_granule_id: str,
    output_dir: Path,
    output_record: Path,
) -> dict[str, Any]:
    try:
        product = HLS_PRODUCTS[product_variant]
    except KeyError as exc:
        raise ValueError(f"unsupported HLS product variant: {product_variant}") from exc
    if after_date <= before_date:
        raise ValueError("after_date must follow before_date")
    if not earthaccess.login(strategy="netrc", persist=False):
        raise RuntimeError("Earthdata Login authentication failed")
    session = earthaccess.get_requests_https_session()
    observations = []
    arrays_by_label: dict[str, dict[str, np.ndarray]] = {}
    for label, day, expected_id in (
        ("before", before_date, before_granule_id),
        ("after", after_date, after_granule_id),
    ):
        item = _item_for_granule(day, bbox_wgs84, expected_id, product_variant)
        umm = item.get("umm", {})
        links = item.data_links()
        arrays: dict[str, np.ndarray] = {}
        grids: dict[str, dict[str, Any]] = {}
        source_asset_urls = {}
        nir_band = product["nir_band"]
        for band_name, suffix in (("B04", ".B04.tif"), (nir_band, f".{nir_band}.tif"), ("Fmask", ".Fmask.tif")):
            source_url = next((url for url in links if url.endswith(suffix)), None)
            if not isinstance(source_url, str):
                raise ValueError(f"CMR granule does not advertise required HLS asset {suffix}")
            source_asset_urls[band_name] = source_url
            values, grid = _read_cog_window(session, source_url, bbox_wgs84)
            inside = grid.pop("aoi_center_mask")
            if band_name in arrays and not np.array_equal(arrays[band_name], values):
                raise ValueError("unexpected duplicate HLS asset")
            arrays[band_name] = values
            grids[band_name] = grid
            if "aoi_center_mask" not in grids:
                grids["_aoi_center_mask"] = {"mask": inside}
        reference = grids["B04"]
        if any(
            grids[name]["crs"] != reference["crs"]
            or grids[name]["transform"] != reference["transform"]
            or grids[name]["window"] != reference["window"]
            for name in (nir_band, "Fmask")
        ):
            raise ValueError("HLS spectral and Fmask assets do not share one exact native window")
        inside = grids.pop("_aoi_center_mask")["mask"]
        if any(array.shape != inside.shape for array in arrays.values()):
            raise ValueError("HLS band arrays do not match the exact AOI grid window")
        if any(int(array[inside].size) > MAX_WINDOW_CELLS for array in arrays.values()):
            raise ValueError("HLS source window exceeds the bounded pixel limit")
        if label == "before":
            baseline_grid = reference
            baseline_inside = inside
        elif reference["crs"] != baseline_grid["crs"] or reference["transform"] != baseline_grid["transform"] or reference["window"] != baseline_grid["window"] or not np.array_equal(inside, baseline_inside):
            raise ValueError(f"paired HLS {product_variant} scenes do not share identical native grid support")
        arrays["AOI"] = inside.astype(np.uint8)
        blob = io.BytesIO()
        np.savez_compressed(blob, **arrays)
        payload = blob.getvalue()
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            relative_path = (output_dir / f"hls-{product_variant.lower()}-{case_id}-{label}-{day.isoformat()}-bounded.npz").resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError as exc:
            raise ValueError("bounded HLS subsets must be stored inside the ECHO project") from exc
        asset_path = PROJECT_ROOT / relative_path
        asset_path.write_bytes(payload)
        arrays_by_label[label] = arrays
        extent = umm.get("TemporalExtent", {}).get("RangeDateTime", {})
        platforms = umm.get("Platforms", [])
        observation = {
            "granule_id": expected_id,
            "cmr_concept_id": item.get("meta", {}).get("concept-id"),
            "collection_id": product["collection_id"],
            "temporal_extent_utc": extent,
            "provider_dates": umm.get("ProviderDates", []),
            "platforms": platforms,
            "source_assets": source_asset_urls,
            "grid": reference,
            "fmask_class_counts_in_aoi": _fmask_counts(arrays["Fmask"], inside),
            "retrieval": {
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "access_method": "Earthdata-authenticated redirect to HLS COG, then bounded HTTP range reads through GDAL; signed URL kept in memory and not recorded",
                "per_pixel_window_read": True,
            },
            "asset": {
                "relative_path": relative_path,
                "size_bytes": len(payload),
                "sha256": sha256(payload).hexdigest(),
            },
        }
        observations.append(observation)

    result = _summarize_pair(
        arrays_by_label["before"],
        arrays_by_label["after"],
        baseline_inside,
        baseline_inside,
        nir_band=product["nir_band"],
    )
    record = {
        "record_type": f"ECHO_HLS_{product_variant}_VEGETATION_CONTEXT_SCREEN",
        "schema_version": 1,
        "status": "DESCRIPTIVE_OPTICAL_CONTEXT_NOT_CAUSAL_TEST",
        "case_id": case_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "provider": "NASA LP DAAC",
            "mission_instrument_by_date": [
                {
                    "date": day.isoformat(),
                    "platforms": observation["platforms"],
                }
                for day, observation in zip((before_date, after_date), observations)
            ],
            "product": product["product_title"],
            "product_variant": product_variant,
            "short_name": product["short_name"],
            "version": VERSION,
            "collection_id": product["collection_id"],
            "reference_urls": [
                "https://lpdaac.usgs.gov/products/hlsl30v020/",
                "https://lpdaac.usgs.gov/products/hlss30v020/",
                "https://lpdaac.usgs.gov/documents/1698/HLS_User_Guide_V2.pdf",
            ],
            "measurement_role": f"complementary {product_variant} optical surface-reflectance measurements; NDVI describes spectral vegetation contrast and does not validate SAR causality",
        },
        "query": {
            "bbox_west_south_east_north": list(bbox_wgs84),
            "before_date_utc": before_date.isoformat(),
            "after_date_utc": after_date.isoformat(),
            "product_variant": product_variant,
            "nir_band": product["nir_band"],
            "requested_assets": ["B04", product["nir_band"], "Fmask"],
            "maximum_window_cells": MAX_WINDOW_CELLS,
            "source_pixels_retained_without_resampling": True,
        },
        "observations": observations,
        "comparison": result,
        "processing": {
            "script": "tools/research/screen_hls_l30_vegetation.py",
            "red_band": "B04",
            "nir_band": product["nir_band"],
            "method": "CMR exact-granule identity; bounded COG range reads for red, NIR, and Fmask; AOI pixel-center selection; Fmask-screened common clear-land NDVI; exact native-grid equality check; no resampling.",
            "software": {
                "rasterio": rasterio.__version__,
                "numpy": np.__version__,
            },
        },
        "limitations": [
            "The HLS reflectance and DSWx-HLS products are optical context from separate Landsat and Sentinel-2 acquisitions; product-family processing and the neighboring acquisition times do not make them independent validation of each other.",
            "The paired observations may use different platforms and instruments; the exact values in the CMR records remain part of the interpretation.",
            "The paired common clear-land support is limited to the pixel count and AOI fraction reported above; unobserved cloud, water, snow, or high-aerosol pixels are not treated as unchanged.",
            "NDVI describes spectral vegetation contrast and does not measure soil moisture or establish that vegetation caused a Sentinel-1 backscatter response.",
            "HLS Fmask water classes are retained as product classifications, not ground-truth flood labels.",
            "The Sentinel-1 RTC-S1 pair remains diagnostic because neither acquisition has a consolidated provider QA verdict.",
        ],
    }
    output_record.parent.mkdir(parents=True, exist_ok=True)
    output_record.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--product", choices=sorted(HLS_PRODUCTS), default="L30", help="HLS product family; S30 uses B8A as near-infrared and L30 uses B05")
    parser.add_argument("--bbox", required=True, type=_bbox)
    parser.add_argument("--before-date", required=True, type=date.fromisoformat)
    parser.add_argument("--after-date", required=True, type=date.fromisoformat)
    parser.add_argument("--before-granule", required=True)
    parser.add_argument("--after-granule", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--output-record", required=True, type=Path)
    args = parser.parse_args()
    record = retrieve_screen(
        product_variant=args.product,
        case_id=args.case_id,
        bbox_wgs84=args.bbox,
        before_date=args.before_date,
        after_date=args.after_date,
        before_granule_id=args.before_granule,
        after_granule_id=args.after_granule,
        output_dir=args.output_dir,
        output_record=args.output_record,
    )
    print(f"status={record['status']}")
    print(f"common_clear_land_pixels={record['comparison']['common_clear_land_ndvi_pixel_count']}")
    print(f"ndvi_median_change={record['comparison']['ndvi']['common_clear_land_median_change_after_minus_before']}")
    print(f"output={args.output_record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
