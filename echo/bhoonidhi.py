"""Bounded, provenance-preserving catalog access for NISAR S-SAR via Bhoonidhi."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from urllib.parse import urljoin, urlsplit
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener


API_ROOT = "https://bhoonidhi-api.nrsc.gov.in"
GCOV_COLLECTION = "NISAR_SSAR_GCOV"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_RESPONSE_BYTES = 20 * 1024 * 1024
MAX_SEARCH_PAGES = 20


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
    extra_headers: dict[str, str] | None = None,
    open_url: Callable[..., Any] = _secure_open,
) -> tuple[dict[str, Any], bytes]:
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    if extra_headers:
        headers.update(extra_headers)
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


def _next_request(
    link: dict[str, Any],
    *,
    current_query: dict[str, Any],
) -> tuple[str, str, dict[str, Any] | None, dict[str, str]]:
    """Validate a STAC next link before sending the bearer token to it."""
    href = link.get("href")
    if not isinstance(href, str) or not href:
        raise BhoonidhiError("Bhoonidhi pagination link is missing a URL")
    target = urljoin(f"{API_ROOT}/data/search", href)
    parsed = urlsplit(target)
    expected = urlsplit(API_ROOT)
    try:
        port = parsed.port
    except ValueError:
        raise BhoonidhiError("Bhoonidhi pagination link has an invalid network location") from None
    if (
        parsed.scheme != "https"
        or parsed.hostname != expected.hostname
        or port not in (None, 443)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != "/data/search"
        or parsed.fragment
    ):
        raise BhoonidhiError("Bhoonidhi pagination link points outside the approved search endpoint")
    method = link.get("method", "GET")
    if not isinstance(method, str) or method not in {"GET", "POST"}:
        raise BhoonidhiError("Bhoonidhi pagination link uses an unsupported HTTP method")
    headers = link.get("headers", {})
    if not isinstance(headers, dict):
        raise BhoonidhiError("Bhoonidhi pagination link contains unsafe headers")
    normalized_headers: dict[str, str] = {}
    for key, value in headers.items():
        values = value if isinstance(value, list) else [value]
        if (
            not isinstance(key, str)
            or not key
            or key.lower() in {"authorization", "host", "cookie", "content-length", "content-type", "connection"}
            or not values
            or any(not isinstance(item, str) or "\r" in item or "\n" in item for item in values)
        ):
            raise BhoonidhiError("Bhoonidhi pagination link contains unsafe headers")
        normalized_headers[key] = ", ".join(values)
    body = link.get("body")
    merge = link.get("merge", False)
    if not isinstance(merge, bool):
        raise BhoonidhiError("Bhoonidhi pagination link has an invalid merge flag")
    if method == "GET":
        if body is not None:
            raise BhoonidhiError("Bhoonidhi GET pagination links cannot include a request body")
        payload = None
    else:
        if not isinstance(body, dict):
            raise BhoonidhiError("Bhoonidhi POST pagination link must provide a JSON body")
        payload = {**current_query, **body} if merge else body
    return target, method, payload, normalized_headers


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
    max_pages: int = 10,
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
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= MAX_SEARCH_PAGES:
        raise BhoonidhiError(f"max_pages must be between 1 and {MAX_SEARCH_PAGES}")

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
    pages: list[dict[str, Any]] = []
    seen_requests: set[str] = set()
    page_url = f"{API_ROOT}/data/search"
    method = "POST"
    payload: dict[str, Any] | None = query
    headers: dict[str, str] = {}
    total_bytes = 0
    all_features: list[dict[str, Any]] = []
    final_collection: dict[str, Any] | None = None
    has_next_page = False
    for page_number in range(1, max_pages + 1):
        request_signature = json.dumps(
            {"url": page_url, "method": method, "payload": payload, "headers": headers},
            sort_keys=True,
            separators=(",", ":"),
        )
        if request_signature in seen_requests:
            raise BhoonidhiError("Bhoonidhi pagination repeated a previously requested request")
        seen_requests.add(request_signature)
        remaining_bytes = MAX_TOTAL_RESPONSE_BYTES - total_bytes
        if remaining_bytes <= 0:
            raise BhoonidhiError("Bhoonidhi paginated search exceeded the total response size limit")
        collection, raw = _read_json(
            page_url,
            method=method,
            payload=payload,
            access_token=access_token,
            max_bytes=min(MAX_RESPONSE_BYTES, remaining_bytes),
            extra_headers=headers,
            open_url=open_url,
        )
        total_bytes += len(raw)
        if collection.get("type") != "FeatureCollection" or not isinstance(
            collection.get("features"), list
        ):
            raise BhoonidhiError("Bhoonidhi search did not return a STAC FeatureCollection")
        if len(collection["features"]) > limit:
            raise BhoonidhiError("Bhoonidhi returned more features than the requested page limit")
        all_features.extend(collection["features"])
        pages.append({
            "page_number": page_number,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "response_bytes": len(raw),
            "feature_count": len(collection["features"]),
        })
        final_collection = collection
        links = collection.get("links", [])
        if not isinstance(links, list):
            raise BhoonidhiError("Bhoonidhi search returned malformed pagination links")
        next_links = [
            link for link in links
            if isinstance(link, dict) and link.get("rel") == "next"
        ]
        if len(next_links) > 1:
            raise BhoonidhiError("Bhoonidhi search returned multiple next-page links")
        if not next_links:
            has_next_page = False
            break
        has_next_page = True
        page_url, method, payload, headers = _next_request(
            next_links[0], current_query=query
        )
    if final_collection is None:
        raise BhoonidhiError("Bhoonidhi search returned no catalog pages")
    final_collection = dict(final_collection)
    final_collection["features"] = all_features
    if len(pages) > 1:
        context = final_collection.get("context")
        final_collection["context"] = {
            **(context if isinstance(context, dict) else {}),
            "limit": limit,
            "returned": len(all_features),
        }
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
        "response_sha256": pages[0]["response_sha256"],
        "feature_count": len(all_features),
        "pages_retrieved": len(pages),
        "page_responses": pages,
        "response_bytes_total": total_bytes,
        "has_next_page": has_next_page,
        "pagination_complete": not has_next_page,
        "feature_collection": final_collection,
        "interpretation_limit": (
            "Catalog metadata only; provider QA, product retrieval, and measurement suitability "
            "have not been established."
        ),
    }
