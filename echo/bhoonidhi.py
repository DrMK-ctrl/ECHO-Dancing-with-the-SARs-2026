"""Bounded, provenance-preserving catalog access for NISAR S-SAR via Bhoonidhi."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


API_ROOT = "https://bhoonidhi-api.nrsc.gov.in"
GCOV_COLLECTION = "NISAR_SSAR_GCOV"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


_secure_open = build_opener(_NoRedirect()).open


class BhoonidhiError(ValueError):
    """Raised when Bhoonidhi authentication or catalog retrieval fails."""


def _read_json(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None = None,
    access_token: str | None = None,
    max_bytes: int,
    open_url: Callable[..., Any] = _secure_open,
) -> tuple[dict[str, Any], bytes]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with open_url(request, timeout=30) as response:
            raw = response.read(max_bytes + 1)
    except HTTPError as exc:
        raise BhoonidhiError(f"Bhoonidhi request failed with HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise BhoonidhiError(f"Bhoonidhi request failed: {type(exc).__name__}") from None
    if len(raw) > max_bytes:
        raise BhoonidhiError("Bhoonidhi response exceeded the configured size limit")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BhoonidhiError("Bhoonidhi returned invalid JSON") from None
    if not isinstance(value, dict):
        raise BhoonidhiError("Bhoonidhi returned an unexpected JSON structure")
    return value, raw


def authenticate(
    user_id: str, password: str, *, open_url: Callable[..., Any] = _secure_open
) -> str:
    """Obtain an in-memory access token; credentials and tokens are never persisted."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise BhoonidhiError("Bhoonidhi user ID is required")
    if not isinstance(password, str) or not password:
        raise BhoonidhiError("Bhoonidhi password is required")
    response, _ = _read_json(
        f"{API_ROOT}/auth/token",
        method="POST",
        payload={"userId": user_id, "password": password, "grant_type": "password"},
        max_bytes=64 * 1024,
        open_url=open_url,
    )
    token = response.get("access_token")
    token_type = response.get("token_type")
    if not isinstance(token, str) or not token or token_type != "Bearer":
        raise BhoonidhiError("Bhoonidhi authentication response did not contain a bearer token")
    return token


def search_ssar_gcov(
    access_token: str,
    *,
    bounds_wgs84: tuple[float, float, float, float],
    start: str,
    end: str,
    limit: int = 100,
    open_url: Callable[..., Any] = _secure_open,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, Any]:
    """Search one WGS84 rectangle and time range for directly online S-SAR GCOV.

    Results preserve the provider's raw STAC features. They are not normalized
    into ASF records and do not imply product QA or scientific suitability.
    """
    if not isinstance(access_token, str) or not access_token:
        raise BhoonidhiError("Bhoonidhi access token is required")
    if not isinstance(bounds_wgs84, (tuple, list)) or len(bounds_wgs84) != 4:
        raise BhoonidhiError("bounds must be west, south, east, north")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        for value in bounds_wgs84
    ):
        raise BhoonidhiError("bounds must contain four finite numbers")
    west, south, east, north = bounds_wgs84
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise BhoonidhiError("bounds must be an ordered WGS84 rectangle")
    try:
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise BhoonidhiError("start and end must be timezone-aware ISO timestamps") from None
    if start_dt.tzinfo is None or end_dt.tzinfo is None or start_dt > end_dt:
        raise BhoonidhiError("start and end must be ordered, timezone-aware ISO timestamps")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise BhoonidhiError("limit must be between 1 and 500")

    query = {
        "collections": [GCOV_COLLECTION],
        "datetime": f"{start_dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')}/"
        f"{end_dt.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')}",
        "intersects": {
            "type": "Polygon",
            "coordinates": [[
                [west, south], [east, south], [east, north], [west, north], [west, south]
            ]],
        },
        "filter": {"args": [{"property": "Online"}, "Y"], "op": "eq"},
        "filter-lang": "cql2-json",
        "limit": limit,
    }
    collection, raw = _read_json(
        f"{API_ROOT}/data/search",
        method="POST",
        payload=query,
        access_token=access_token,
        max_bytes=MAX_RESPONSE_BYTES,
        open_url=open_url,
    )
    if collection.get("type") != "FeatureCollection" or not isinstance(
        collection.get("features"), list
    ):
        raise BhoonidhiError("Bhoonidhi search did not return a STAC FeatureCollection")
    if len(collection["features"]) > limit:
        raise BhoonidhiError("Bhoonidhi returned more features than the requested limit")
    timestamp = now()
    if timestamp.tzinfo is None:
        raise BhoonidhiError("retrieval clock must return a timezone-aware timestamp")
    return {
        "schema_version": 1,
        "provider": "ISRO NRSC Bhoonidhi",
        "mission": "NISAR",
        "instrument": "S-SAR",
        "collection": GCOV_COLLECTION,
        "query": query,
        "retrieved_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "feature_count": len(collection["features"]),
        "has_next_page": any(
            isinstance(link, dict) and link.get("rel") == "next"
            for link in collection.get("links", [])
        ),
        "feature_collection": collection,
        "interpretation_limit": (
            "Catalog metadata only; provider QA, product retrieval, and measurement suitability "
            "have not been established."
        ),
    }
