#!/usr/bin/env python3
"""Retrieve bounded, daily GPM IMERG context through NASA Harmony.

The output is regional meteorological context, never a SAR measurement or a
causal explanation. Each request is restricted to one UTC day and a small
bounding box so the service does not return the global daily product.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import earthaccess
import h5py
import numpy as np


COLLECTION_ID = "C2723754864-GES_DISC"
PRODUCT = "GPM_3IMERGDF V07 Final Daily"
DOI = "10.5067/GPM/IMERGDF/DAY/07"
HARMONY_URL = (
    "https://harmony.earthdata.nasa.gov/ogc-api-edr/1.1.0/collections/"
    f"{COLLECTION_ID}/cube"
)


def _attr(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def retrieve_context(
    *,
    start: date,
    end: date,
    bbox: tuple[float, float, float, float],
    aoi: tuple[float, float, float, float],
    output_dir: Path,
    case_id: str,
) -> dict[str, Any]:
    if end < start:
        raise ValueError("end date must not precede start date")
    if not earthaccess.login(strategy="netrc", persist=False):
        raise RuntimeError("Earthdata Login authentication failed")
    session = earthaccess.get_requests_https_session()
    output_dir.mkdir(parents=True, exist_ok=True)
    west, south, east, north = bbox
    aoi_west, aoi_south, aoi_east, aoi_north = aoi
    center_lon = (aoi_west + aoi_east) / 2
    center_lat = (aoi_south + aoi_north) / 2
    records: list[dict[str, Any]] = []
    day = start
    while day <= end:
        day_text = day.isoformat()
        params = {
            "bbox": f"{west},{south},{east},{north}",
            "datetime": f"{day_text}T00:00:00Z/{day_text}T23:59:59Z",
            "parameter-name": "precipitation,precipitation_cnt",
            "f": "application/netcdf",
            "maxResults": "1",
        }
        response = session.get(HARMONY_URL, params=params, timeout=(20, 120))
        response.raise_for_status()
        if "netcdf" not in response.headers.get("content-type", "").lower():
            raise RuntimeError(
                f"Harmony did not return a NetCDF subset for {day_text}: "
                f"{response.headers.get('content-type', 'unknown content type')}"
            )
        raw = response.content
        asset_path = output_dir / f"gpm-imerg-v07-{day_text}.nc4"
        asset_path.write_bytes(raw)
        with h5py.File(asset_path, "r") as source:
            lons = np.asarray(source["lon"][()], dtype=np.float64)
            lats = np.asarray(source["lat"][()], dtype=np.float64)
            times = np.asarray(source["time"][()], dtype=np.float64)
            precip = np.asarray(source["precipitation"][()], dtype=np.float64)
            count = np.asarray(source["precipitation_cnt"][()], dtype=np.float64)
            if times.size != 1 or precip.shape != count.shape or precip.shape[0] != 1:
                raise RuntimeError(f"unexpected daily subset dimensions for {day_text}")
            lon_index = int(np.argmin(np.abs(lons - center_lon)))
            lat_index = int(np.argmin(np.abs(lats - center_lat)))
            # The AOI is smaller than one native ~0.1 degree cell. Keep the
            # nearest center as regional context; do not resample onto SAR pixels.
            day_record = {
                "date_utc": day_text,
                "granule_id": (
                    "GPM_3IMERGDF.07:3B-DAY.MS.MRG.3IMERG."
                    f"{day:%Y%m%d}-S000000-E235959.V07B.nc4"
                ),
                "production_time_utc": _attr(source.attrs.get("ProductionTime")),
                "time_coordinate_days_since_1980_01_06": float(times[0]),
                "native_grid": {
                    "crs": "EPSG:4326",
                    "longitude_centers": lons.tolist(),
                    "latitude_centers": lats.tolist(),
                    "longitude_spacing_degrees": float(np.median(np.diff(lons))),
                    "latitude_spacing_degrees": float(np.median(np.diff(lats))),
                },
                "aoi_nearest_cell": {
                    "longitude": float(lons[lon_index]),
                    "latitude": float(lats[lat_index]),
                    "precipitation_mm_per_day": float(precip[0, lon_index, lat_index]),
                    "valid_half_hourly_samples": int(count[0, lon_index, lat_index]),
                    "expected_half_hourly_samples": 48,
                    "full_day_sample_complete": bool(count[0, lon_index, lat_index] == 48),
                },
                "regional_precipitation_mm_per_day": precip[0].tolist(),
                "regional_valid_half_hourly_samples": count[0].astype(int).tolist(),
                "asset": {
                    "relative_path": str(asset_path),
                    "bytes": len(raw),
                    "sha256": sha256(raw).hexdigest(),
                    "content_type": response.headers.get("content-type"),
                },
            }
            records.append(day_record)
        day += timedelta(days=1)

    # Aggregate only complete daily estimates at the nearest native cell.
    complete = [r for r in records if r["aoi_nearest_cell"]["full_day_sample_complete"]]
    nearest_values = [r["aoi_nearest_cell"]["precipitation_mm_per_day"] for r in complete]
    regional_sample_counts = [
        int(value)
        for rec in records
        for row in rec["regional_valid_half_hourly_samples"]
        for value in row
    ]
    return {
        "record_type": "ECHO_GPM_IMERG_DAILY_CONTEXT",
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_id": case_id,
        "status": "NASA_REGIONAL_PRECIPITATION_CONTEXT_NOT_CAUSAL_EVIDENCE",
        "source": {
            "provider": "NASA GES DISC",
            "mission": "Global Precipitation Measurement (GPM)",
            "product": PRODUCT,
            "short_name": "GPM_3IMERGDF",
            "version": "07",
            "doi": DOI,
            "collection_id": COLLECTION_ID,
            "service": "NASA Harmony OGC API EDR cube",
            "service_url": HARMONY_URL,
            "retrieval_authentication": "Earthdata Login via local netrc; credentials not retained",
            "measurement": "Daily mean precipitation rate estimate",
            "units": "mm/day",
            "quality_indicator": "precipitation_cnt counts valid half-hourly retrievals; 48 is a complete nominal UTC day",
        },
        "query": {
            "start_date_utc": start.isoformat(),
            "end_date_utc": end.isoformat(),
            "bbox_west_south_east_north": list(bbox),
            "aoi_west_south_east_north": list(aoi),
            "aoi_nearest_native_cell_center": [
                records[0]["aoi_nearest_cell"]["longitude"],
                records[0]["aoi_nearest_cell"]["latitude"],
            ],
            "variables": ["precipitation", "precipitation_cnt"],
            "request_strategy": "one bounded Harmony subset per UTC day; no global files downloaded",
        },
        "summary": {
            "days_requested": len(records),
            "days_with_48_valid_samples_at_nearest_cell": len(complete),
            "nearest_cell_precipitation_mm_per_day_complete_days": nearest_values,
            "nearest_cell_complete_day_sum_mm": float(sum(nearest_values)),
            "regional_valid_sample_count_min_max": [
                min(regional_sample_counts), max(regional_sample_counts)
            ],
            "interpretation_limit": (
                "The ~0.1 degree grid is much coarser than the SAR AOI. These daily "
                "estimates provide regional meteorological context only; they do not "
                "measure soil moisture, identify the cause of the SAR response, or "
                "validate a flood boundary."
            ),
        },
        "daily_observations": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--bbox", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    parser.add_argument("--aoi", nargs=4, type=float, required=True, metavar=("W", "S", "E", "N"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--assets-dir", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    record = retrieve_context(
        start=args.start,
        end=args.end,
        bbox=tuple(args.bbox),
        aoi=tuple(args.aoi),
        output_dir=args.assets_dir,
        case_id=args.case_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), **record["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
