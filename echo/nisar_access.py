"""Bounded, authenticated inspection of NISAR GCOV identification metadata."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import urlsplit


REMOTE_BLOCK_BYTES = 1024 * 1024
MAX_METADATA_RANGE_BYTES = 64 * 1024 * 1024
IDENTIFICATION_FIELDS = (
    "instrumentName",
    "listOfObservationModes",
    "missionId",
    "productVersion",
    "productSpecificationVersion",
    "absoluteOrbitNumber",
    "trackNumber",
    "frameNumber",
    "isUrgentObservation",
    "isJointObservation",
    "lookDirection",
    "listOfFrequencies",
)
_SCENE_ID = re.compile(r"^NISAR_([LS])2_PR_GCOV_[A-Z0-9_]+$")
_ASF_HOST = "nisar.asf.earthdatacloud.nasa.gov"
_ASF_COLLECTIONS = {"NISAR_L2_GCOV_BETA_V1", "NISAR_L2_GCOV_PROVISIONAL_V1"}


class NisarAccessError(ValueError):
    """Raised for invalid catalog entries or failed remote metadata access."""


def _install_read_budget(remote_file: Any) -> Any:
    cache = getattr(remote_file, "cache", None)
    original_fetcher = getattr(cache, "fetcher", None)
    if cache is None or not callable(original_fetcher):
        raise NisarAccessError("remote byte-range cache does not support read budgeting")

    def fetch_with_budget(start: int, end: int) -> bytes:
        if cache.total_requested_bytes > MAX_METADATA_RANGE_BYTES:
            raise NisarAccessError(
                f"metadata range-read budget exceeded ({MAX_METADATA_RANGE_BYTES} bytes)"
            )
        return original_fetcher(start, end)

    cache.fetcher = fetch_with_budget
    return cache


def _validated_product(feature: dict[str, Any]) -> tuple[str, str, str]:
    properties = feature.get("properties", {})
    if not isinstance(properties, dict):
        raise NisarAccessError("catalog feature properties must be an object")
    scene_id = properties.get("fileID")
    url = properties.get("url")
    collection = properties.get("collectionName")
    match = _SCENE_ID.fullmatch(scene_id or "")
    if not match:
        raise NisarAccessError("catalog feature is not a NISAR L2 GCOV production scene")
    if properties.get("processingLevel") != "GCOV":
        raise NisarAccessError("catalog feature processing level must be GCOV")
    if collection not in _ASF_COLLECTIONS:
        raise NisarAccessError("catalog feature collection must be a supported ASF GCOV collection")
    if not isinstance(url, str):
        raise NisarAccessError("catalog feature has no product URL")

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        netloc = parsed.netloc
        path_parts = tuple(part for part in parsed.path.split("/") if part)
    except ValueError as exc:
        raise NisarAccessError("catalog product URL is malformed") from exc
    if (
        parsed.scheme != "https"
        or hostname != _ASF_HOST
        or netloc not in {_ASF_HOST, f"{_ASF_HOST}:443"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or path_parts != ("NISAR", collection, scene_id, f"{scene_id}.h5")
    ):
        raise NisarAccessError("catalog product URL is not a plain ASF NISAR HTTPS product URL")

    instrument = "LSAR" if match.group(1) == "L" else "SSAR"
    return scene_id, url, instrument


def _json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "tolist"):
        return _json_value(value.tolist())
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if hasattr(value, "item"):
        return _json_value(value.item())
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise NisarAccessError(f"unsupported HDF5 metadata value type: {type(value).__name__}")


def inspect_identification(
    feature: dict[str, Any], *, inspected_at: datetime | None = None
) -> dict[str, Any]:
    """Read a small allowlist from a remote HDF5 identification group.

    Authentication is read from Earthdata Login's local netrc configuration.
    Only the named identification datasets are accessed; no radar arrays are
    read, and the complete product is not downloaded.
    """
    scene_id, url, instrument = _validated_product(feature)

    try:
        import earthaccess
        import h5py
        from aiohttp import ClientTimeout
    except ImportError as exc:
        raise NisarAccessError(
            "remote NISAR inspection requires the 'nisar' optional dependencies"
        ) from exc

    try:
        auth = earthaccess.login(strategy="netrc", persist=False)
        if not auth.authenticated:
            raise NisarAccessError(
                "Earthdata Login failed; configure credentials in the local netrc file"
            )

        filesystem = earthaccess.get_fsspec_https_session()
        client_kwargs = dict(filesystem.client_kwargs)
        client_kwargs["timeout"] = ClientTimeout(total=25, connect=10, sock_read=20)
        filesystem.client_kwargs = client_kwargs

        group_path = f"/science/{instrument}/identification"
        with filesystem.open(
            url,
            "rb",
            block_size=REMOTE_BLOCK_BYTES,
            cache_type="bytes",
        ) as remote_file:
            cache = _install_read_budget(remote_file)
            with h5py.File(remote_file, "r") as product:
                group = product[group_path]
                metadata = {
                    name: _json_value(group[name][()])
                    for name in IDENTIFICATION_FIELDS
                    if name in group
                }
                missing = [name for name in IDENTIFICATION_FIELDS if name not in group]
            requested_bytes = getattr(cache, "total_requested_bytes", None)
    except NisarAccessError:
        raise
    except Exception as exc:
        raise NisarAccessError(
            f"remote identification metadata read failed ({type(exc).__name__})"
        ) from exc

    inspected_at = inspected_at or datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "inspected_at_utc": inspected_at.astimezone(timezone.utc).isoformat(),
        "product": {
            "scene_id": scene_id,
            "identification_group": group_path,
            "metadata": metadata,
            "fields_not_present": missing,
        },
        "access": {
            "provider": "Alaska Satellite Facility DAAC",
            "authentication": "Earthdata Login via local netrc",
            "method": "HTTPS byte-range streaming",
            "fsspec_read_ahead_block_bytes": REMOTE_BLOCK_BYTES,
            "max_fsspec_range_bytes_requested": MAX_METADATA_RANGE_BYTES,
            "fsspec_range_bytes_requested": requested_bytes,
            "complete_product_download_requested": False,
            "radar_measurement_arrays_read": False,
        },
        "interpretation_limit": (
            "This command inspects product identification metadata only. It does not "
            "evaluate product QA, inspect radar measurements, or validate a scientific result."
        ),
    }
