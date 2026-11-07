"""Bounded, authenticated geographic reads of OPERA RTC-S1 COG assets.

OPERA RTC-S1 polarization files are small per-burst gamma-zero power COGs.
This reader caps each in-memory HTTPS asset, windows the raster to the requested
WGS84 area, retains the product-specific validity mask, and writes no source
asset to disk. The COG is read in full within the explicit asset cap; spatial
windowing bounds the arrays passed into ECHO's analysis and map layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import numpy as np

from echo.opera_rtc import decode_opera_rtc_s1_mask


MAX_RTC_S1_ASSET_BYTES = 16 * 1024 * 1024
MAX_RTC_S1_WINDOW_PIXELS = 65_536
_ASSET_HOST = "datapool.asf.alaska.edu"
_ASSET_PREFIX = "/RTC/OPERA-S1/"
_SCENE_ID = re.compile(
    r"^OPERA_L2_RTC-S1_(?P<burst>T\d{3}-\d{6}-IW[1-3])_"
    r"(?P<acquired>\d{8}T\d{6}Z)_(?P<generated>\d{8}T\d{6}Z)_"
    r"(?P<platform>S1[AB])_(?P<spacing>\d+)_v(?P<version>\d+\.\d+)$"
)


class OperaRtcS1AccessError(ValueError):
    """Raised when an OPERA RTC-S1 feature or bounded read is unsuitable."""


@dataclass(frozen=True)
class OperaRtcS1Window:
    """A geolocated measurement window and its mask/source provenance."""

    scene_id: str
    polarization: str
    values: np.ndarray
    mask: np.ndarray
    selection_mask: np.ndarray
    grid: dict[str, Any]
    source: dict[str, Any]
    assets: dict[str, dict[str, Any]]
    access: dict[str, Any]


def _validate_bounds(value: Any) -> tuple[float, float, float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        raise OperaRtcS1AccessError("bounds_wgs84 must be west, south, east, north")
    if any(
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(item)
        for item in value
    ):
        raise OperaRtcS1AccessError("bounds_wgs84 must contain four finite numbers")
    west, south, east, north = (float(item) for item in value)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise OperaRtcS1AccessError("bounds_wgs84 must be ordered within WGS84")
    return west, south, east, north


def _validated_source(
    feature: dict[str, Any], polarization: str
) -> tuple[str, dict[str, Any], dict[str, str], dict[str, int]]:
    if polarization not in {"VV", "VH", "HH", "HV"}:
        raise OperaRtcS1AccessError("polarization must be VV, VH, HH, or HV")
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        raise OperaRtcS1AccessError("ASF catalog feature has no properties object")
    scene_id = properties.get("fileID")
    match = _SCENE_ID.fullmatch(scene_id) if isinstance(scene_id, str) else None
    if match is None:
        raise OperaRtcS1AccessError("feature is not a supported OPERA RTC-S1 product")
    parsed_id = match.groupdict()
    try:
        acquisition_time = datetime.strptime(
            parsed_id["acquired"], "%Y%m%dT%H%M%SZ"
        ).replace(tzinfo=timezone.utc)
        generation_time = datetime.strptime(
            parsed_id["generated"], "%Y%m%dT%H%M%SZ"
        ).replace(tzinfo=timezone.utc)
        catalog_time = datetime.fromisoformat(
            str(properties.get("startTime", "")).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise OperaRtcS1AccessError("OPERA RTC-S1 acquisition or generation time is invalid") from exc
    if catalog_time.tzinfo is None or catalog_time.astimezone(timezone.utc) != acquisition_time:
        raise OperaRtcS1AccessError(
            "ASF catalog acquisition time does not match the RTC-S1 scene identifier"
        )
    parsed_id["acquisition_time_utc"] = acquisition_time.isoformat()
    parsed_id["generation_time_utc"] = generation_time.isoformat()

    original_url = properties.get("url")
    if not isinstance(original_url, str):
        raise OperaRtcS1AccessError("ASF feature has no RTC-S1 asset URL")
    parsed = urlsplit(original_url)
    expected_path = f"{_ASSET_PREFIX}{scene_id}_"
    if (
        parsed.scheme != "https"
        or parsed.hostname != _ASSET_HOST
        or parsed.netloc != _ASSET_HOST
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.startswith(expected_path)
        or parsed.query
        or parsed.fragment
        or not re.fullmatch(re.escape(scene_id) + r"_(?:VV|VH|HH|HV)\.tif", parsed.path.rsplit("/", 1)[-1])
    ):
        raise OperaRtcS1AccessError("ASF RTC-S1 asset URL is outside the supported host/path")

    base_path = parsed.path.rsplit("_", 1)[0]
    urls = {
        "measurement": urlunsplit(
            (parsed.scheme, parsed.netloc, f"{base_path}_{polarization}.tif", "", "")
        ),
        "mask": urlunsplit(
            (parsed.scheme, parsed.netloc, f"{base_path}_mask.tif", "", "")
        ),
    }
    asset_sizes = properties.get("bytes")
    if not isinstance(asset_sizes, dict):
        raise OperaRtcS1AccessError("ASF feature does not provide bounded asset sizes")
    sizes: dict[str, int] = {}
    for role, asset_url in urls.items():
        filename = asset_url.rsplit("/", 1)[-1]
        detail = asset_sizes.get(filename)
        size = detail.get("bytes") if isinstance(detail, dict) else None
        asset_format = detail.get("format") if isinstance(detail, dict) else None
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise OperaRtcS1AccessError(f"ASF catalog size is missing for {role} asset")
        if asset_format != "GeoTIFF":
            raise OperaRtcS1AccessError(f"ASF catalog format is not GeoTIFF for {role} asset")
        if size > MAX_RTC_S1_ASSET_BYTES:
            raise OperaRtcS1AccessError(
                f"{role} asset exceeds the {MAX_RTC_S1_ASSET_BYTES}-byte read limit"
            )
        sizes[role] = size

    return scene_id, parsed_id, urls, sizes


def _authenticated_session() -> Any:
    try:
        import earthaccess
    except ImportError as exc:
        raise OperaRtcS1AccessError(
            "OPERA RTC-S1 streaming requires the 'nisar' optional dependencies"
        ) from exc
    try:
        auth = earthaccess.login(strategy="netrc", persist=False)
        if not auth.authenticated:
            raise OperaRtcS1AccessError(
                "Earthdata Login failed using the local netrc configuration"
            )
        return earthaccess.get_requests_https_session()
    except OperaRtcS1AccessError:
        raise
    except Exception as exc:
        raise OperaRtcS1AccessError(
            f"Earthdata authenticated session could not be created ({type(exc).__name__})"
        ) from exc


def _authorization_denial_message(response: Any, role: str, status: int) -> str:
    history = getattr(response, "history", ())
    passed_earthdata_oauth = False
    for hop in history:
        location = urlsplit(str(getattr(hop, "url", "")))
        if (
            location.hostname == "urs.earthdata.nasa.gov"
            and location.path == "/oauth/authorize"
        ):
            passed_earthdata_oauth = True
            break
    final = urlsplit(str(getattr(response, "url", "")))
    if (
        passed_earthdata_oauth
        and final.hostname == "cumulus.asf.alaska.edu"
        and final.path == "/login"
    ):
        return (
            f"ASF denied authenticated {role} asset access (HTTP {status}) after "
            "Earthdata OAuth; review any pending ASF data EULA acceptance and "
            "Cumulus application access for this Earthdata account"
        )
    return (
        f"ASF denied authenticated {role} asset access (HTTP {status}); "
        "review any pending ASF data EULA acceptance and Cumulus application "
        "access for this Earthdata account"
    )


def _read_asset(session: Any, url: str, expected_size: int, role: str) -> tuple[bytes, dict[str, Any]]:
    headers = {"Range": f"bytes=0-{expected_size - 1}"}
    try:
        with session.get(
            url,
            headers=headers,
            stream=True,
            timeout=(10, 30),
        ) as response:
            status = response.status_code
            if status in (401, 403):
                raise OperaRtcS1AccessError(
                    _authorization_denial_message(response, role, status)
                )
            if status == 404:
                raise OperaRtcS1AccessError(f"ASF {role} asset was not found (HTTP 404)")
            if status != 206:
                raise OperaRtcS1AccessError(
                    f"ASF did not honor the bounded {role} byte-range request (HTTP {status})"
                )
            content_range = response.headers.get("Content-Range", "")
            match = re.fullmatch(r"bytes 0-(\d+)/(\d+)", content_range.strip())
            if (
                match is None
                or int(match.group(1)) != expected_size - 1
                or int(match.group(2)) != expected_size
            ):
                raise OperaRtcS1AccessError(
                    f"ASF {role} Content-Range does not match the catalog asset size"
                )
            payload_buffer = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if len(payload_buffer) + len(chunk) > expected_size:
                    raise OperaRtcS1AccessError(
                        f"ASF {role} response exceeded the requested byte range"
                    )
                payload_buffer.extend(chunk)
            payload = bytes(payload_buffer)
    except OperaRtcS1AccessError:
        raise
    except Exception as exc:
        status = getattr(exc, "status", None)
        if status in (401, 403):
            raise OperaRtcS1AccessError(
                f"ASF denied authenticated {role} asset access (HTTP {status}); "
                "review any pending ASF data EULA acceptance and Cumulus application "
                "access for this Earthdata account"
            ) from exc
        if status == 404:
            raise OperaRtcS1AccessError(
                f"ASF {role} asset was not found (HTTP 404)"
            ) from exc
        raise OperaRtcS1AccessError(
            f"authenticated {role} asset read failed ({type(exc).__name__})"
        ) from exc
    if len(payload) != expected_size:
        raise OperaRtcS1AccessError(f"remote {role} asset returned an incomplete byte range")
    return payload, {
        "url": url,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "content_range": f"bytes 0-{len(payload) - 1}/{expected_size}",
        "http_status": 206,
    }


def read_opera_rtc_s1_window(
    feature: dict[str, Any],
    *,
    bounds_wgs84: tuple[float, float, float, float] | list[float],
    polarization: str,
    max_pixels: int = MAX_RTC_S1_WINDOW_PIXELS,
    http_session: Any | None = None,
) -> OperaRtcS1Window:
    """Read a bounded AOI from one authenticated OPERA RTC-S1 acquisition.

    Source COGs are held in memory only and must be no larger than the strict
    per-asset cap. The output arrays contain only the enclosing AOI window and
    an exact pixel-center selection mask. The injected ``http_session`` argument
    supports deterministic tests; normal callers use local Earthdata netrc auth.
    """
    try:
        import rasterio
        from rasterio.io import MemoryFile
        from rasterio.windows import Window, from_bounds as window_from_bounds
        import pyproj
        from pyproj import CRS, Transformer
    except ImportError as exc:
        raise OperaRtcS1AccessError(
            "OPERA RTC-S1 geographic reads require rasterio and pyproj"
        ) from exc

    if isinstance(max_pixels, bool) or not isinstance(max_pixels, int) or max_pixels < 1:
        raise OperaRtcS1AccessError("max_pixels must be a positive integer")
    bounds = _validate_bounds(bounds_wgs84)
    scene_id, parsed_id, urls, sizes = _validated_source(feature, polarization)
    properties = feature["properties"]
    injected_http_session = http_session is not None
    http_session = http_session if http_session is not None else _authenticated_session()

    measurement_bytes, measurement_asset = _read_asset(
        http_session, urls["measurement"], sizes["measurement"], "measurement"
    )
    mask_bytes, mask_asset = _read_asset(
        http_session, urls["mask"], sizes["mask"], "mask"
    )
    try:
        with MemoryFile(measurement_bytes) as measurement_file, MemoryFile(mask_bytes) as mask_file:
            with measurement_file.open() as measurement_ds, mask_file.open() as mask_ds:
                if measurement_ds.count != 1 or measurement_ds.dtypes[0] != "float32":
                    raise OperaRtcS1AccessError(
                        "RTC-S1 measurement must be a single-band float32 GeoTIFF"
                    )
                if mask_ds.count != 1 or not np.issubdtype(
                    np.dtype(mask_ds.dtypes[0]), np.integer
                ):
                    raise OperaRtcS1AccessError(
                        "RTC-S1 validity mask must be a single-band integer GeoTIFF"
                    )
                if measurement_ds.crs is None or measurement_ds.crs != mask_ds.crs:
                    raise OperaRtcS1AccessError("measurement and mask CRS do not match")
                if (
                    measurement_ds.width != mask_ds.width
                    or measurement_ds.height != mask_ds.height
                    or measurement_ds.transform != mask_ds.transform
                ):
                    raise OperaRtcS1AccessError(
                        "measurement and mask grids are not exactly aligned"
                    )
                transform = measurement_ds.transform
                if abs(transform.b) > 1e-12 or abs(transform.d) > 1e-12:
                    raise OperaRtcS1AccessError(
                        "rotated RTC-S1 grids are not supported by this reader"
                    )
                crs = CRS.from_user_input(measurement_ds.crs)
                if not crs.is_projected:
                    raise OperaRtcS1AccessError("RTC-S1 grid CRS must be projected")
                expected_spacing = float(parsed_id["spacing"])
                if not (
                    math.isclose(abs(transform.a), expected_spacing, rel_tol=0, abs_tol=1e-6)
                    and math.isclose(abs(transform.e), expected_spacing, rel_tol=0, abs_tol=1e-6)
                ):
                    raise OperaRtcS1AccessError(
                        "RTC-S1 affine pixel spacing differs from the product identifier"
                    )
                forward = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
                inverse = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
                projected = forward.transform_bounds(*bounds, densify_pts=64, errcheck=True)
                if not np.isfinite(projected).all():
                    raise OperaRtcS1AccessError("WGS84 AOI transforms to non-finite RTC-S1 bounds")
                candidate = window_from_bounds(*projected, transform=transform)
                column_start = max(0, math.floor(candidate.col_off))
                row_start = max(0, math.floor(candidate.row_off))
                column_stop = min(
                    measurement_ds.width, math.ceil(candidate.col_off + candidate.width)
                )
                row_stop = min(
                    measurement_ds.height, math.ceil(candidate.row_off + candidate.height)
                )
                if column_start >= column_stop or row_start >= row_stop:
                    raise OperaRtcS1AccessError("WGS84 AOI does not intersect the RTC-S1 raster")
                width = column_stop - column_start
                height = row_stop - row_start
                if width * height > max_pixels:
                    raise OperaRtcS1AccessError(
                        f"RTC-S1 AOI window exceeds the {max_pixels}-pixel limit"
                    )
                window = Window(column_start, row_start, width, height)
                values = measurement_ds.read(1, window=window)
                mask = mask_ds.read(1, window=window)
                try:
                    decode_opera_rtc_s1_mask(mask)
                except ValueError as exc:
                    raise OperaRtcS1AccessError(str(exc)) from exc
                row_centers = np.arange(row_start, row_stop, dtype=np.float64) + 0.5
                column_centers = np.arange(column_start, column_stop, dtype=np.float64) + 0.5
                center_columns, center_rows = np.meshgrid(column_centers, row_centers)
                center_x = (
                    transform.a * center_columns
                    + transform.b * center_rows
                    + transform.c
                )
                center_y = (
                    transform.d * center_columns
                    + transform.e * center_rows
                    + transform.f
                )
                longitude, latitude = inverse.transform(center_x, center_y, errcheck=True)
                if not np.isfinite(longitude).all() or not np.isfinite(latitude).all():
                    raise OperaRtcS1AccessError("RTC-S1 pixel centers cannot be transformed to WGS84")
                west, south, east, north = bounds
                selection = (
                    (longitude >= west)
                    & (longitude <= east)
                    & (latitude >= south)
                    & (latitude <= north)
                )
                if not np.any(selection):
                    raise OperaRtcS1AccessError("WGS84 AOI contains no RTC-S1 pixel centers")
                epsg = measurement_ds.crs.to_epsg()
                grid = {
                    "crs": measurement_ds.crs.to_string(),
                    "epsg": epsg,
                    "transform": [float(value) for value in tuple(transform)[:6]],
                    "raster_shape": [measurement_ds.height, measurement_ds.width],
                    "window": {
                        "row_start": row_start,
                        "row_stop": row_stop,
                        "column_start": column_start,
                        "column_stop": column_stop,
                        "shape": [height, width],
                        "bounds_wgs84": list(bounds),
                        "selected_pixel_center_count": int(np.count_nonzero(selection)),
                    },
                    "pixel_spacing_m": parsed_id["spacing"],
                }
    except OperaRtcS1AccessError:
        raise
    except Exception as exc:
        raise OperaRtcS1AccessError(
            f"RTC-S1 COG metadata or AOI window is invalid ({type(exc).__name__})"
        ) from exc

    acquired = properties.get("startTime")
    if not isinstance(acquired, str):
        raise OperaRtcS1AccessError("ASF catalog acquisition timestamp is missing")
    return OperaRtcS1Window(
        scene_id=scene_id,
        polarization=polarization,
        values=values,
        mask=mask,
        selection_mask=selection,
        grid=grid,
        source={
            "provider": "Alaska Satellite Facility DAAC",
            "mission": "Sentinel-1",
            "product": "NASA OPERA L2 RTC-S1",
            "collection": properties.get("collectionName"),
            "scene_id": scene_id,
            "burst_id": parsed_id["burst"],
            "sensor": parsed_id["platform"],
            "product_generation_time_utc": parsed_id["generation_time_utc"],
            "product_version": parsed_id["version"],
            "acquisition_start_utc": acquired,
            "acquisition_stop_utc": properties.get("stopTime"),
            "catalog_metadata": properties,
            "provider_qa_disposition": "NOT_RETRIEVED",
            "quality_context": "OPERA RTC-S1 per-acquisition mask; classes are preserved",
        },
        assets={"measurement": measurement_asset, "mask": mask_asset},
        access={
            "method": (
                "injected test HTTP session; bounded COG byte range held in memory"
                if injected_http_session
                else "Earthdata-authenticated streamed HTTPS range request; bounded COG held in memory"
            ),
            "authentication": (
                "NOT_AUTHENTICATED_TEST_INJECTION"
                if injected_http_session
                else "Earthdata Login via local netrc"
            ),
            "network_retrieval": not injected_http_session,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "asset_byte_limit": MAX_RTC_S1_ASSET_BYTES,
            "measurement_bytes": len(measurement_bytes),
            "mask_bytes": len(mask_bytes),
            "source_assets_written_to_disk": False,
            "sample_limit": max_pixels,
            "software": {
                "numpy": np.__version__,
                "rasterio": rasterio.__version__,
                "gdal": rasterio.__gdal_version__,
                "pyproj": pyproj.__version__,
                "proj": pyproj.proj_version_str,
            },
        },
    )
