"""Search and pair-screen OPERA RTC-S1 without conflating it with NISAR GCOV."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import math
import re
from typing import Any

from echo.catalog import ASF_CMR_PAGE_SIZE


MAX_OPERA_CATALOG_RESULTS = 1000
_SCENE_ID = re.compile(
    r"^OPERA_L2_RTC-S1_(?P<burst>T\d{3}-\d{6}-IW[1-3])_"
    r"(?P<acquired>\d{8}T\d{6}Z)_(?P<generated>\d{8}T\d{6}Z)_"
    r"(?P<platform>S1[AB])_(?P<spacing>\d+)_v(?P<version>\d+\.\d+)$"
)


class OperaRtcCatalogError(ValueError):
    """Raised for invalid OPERA RTC-S1 catalog queries or responses."""


@dataclass(frozen=True)
class OperaRtcCatalogQuery:
    bounds_wgs84: tuple[float, float, float, float]
    start_date: str
    end_date: str
    max_results: int = 500

    def validate(self) -> None:
        bounds = self.bounds_wgs84
        if not isinstance(bounds, (tuple, list)) or len(bounds) != 4:
            raise OperaRtcCatalogError("bounds_wgs84 must be west, south, east, north")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in bounds
        ):
            raise OperaRtcCatalogError("bounds_wgs84 must contain four finite numbers")
        west, south, east, north = bounds
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise OperaRtcCatalogError("bounds_wgs84 must be ordered within WGS84")
        if not isinstance(self.start_date, str) or not isinstance(self.end_date, str):
            raise OperaRtcCatalogError("dates must use ISO format YYYY-MM-DD")
        try:
            start = date.fromisoformat(self.start_date)
            end = date.fromisoformat(self.end_date)
        except ValueError as exc:
            raise OperaRtcCatalogError("dates must use ISO format YYYY-MM-DD") from exc
        if start.isoformat() != self.start_date or end.isoformat() != self.end_date:
            raise OperaRtcCatalogError("dates must use ISO format YYYY-MM-DD")
        if start > end:
            raise OperaRtcCatalogError("start_date must not be after end_date")
        if (
            isinstance(self.max_results, bool)
            or not isinstance(self.max_results, int)
            or not 1 <= self.max_results <= MAX_OPERA_CATALOG_RESULTS
        ):
            raise OperaRtcCatalogError(
                f"max_results must be between 1 and {MAX_OPERA_CATALOG_RESULTS}"
            )


def search_opera_rtc_s1_with_pagination(
    query: OperaRtcCatalogQuery,
) -> tuple[list[dict[str, Any]], int]:
    """Return ASF catalog features and the exact number of pages consumed."""
    query.validate()
    import asf_search as asf

    west, south, east, north = (float(value) for value in query.bounds_wgs84)
    polygon = (
        f"POLYGON(({west} {south},{east} {south},{east} {north},"
        f"{west} {north},{west} {south}))"
    )
    options = asf.ASFSearchOptions(
        dataset=asf.DATASET.OPERA_S1,
        processingLevel=asf.PRODUCT_TYPE.RTC,
        intersectsWith=polygon,
        start=query.start_date,
        end=query.end_date,
    )
    try:
        features: list[dict[str, Any]] = []
        pages_retrieved = 0
        for page in asf.search_generator(opts=options, maxResults=query.max_results):
            pages_retrieved += 1
            page_features = page.geojson().get("features", [])
            features.extend(page_features[: query.max_results - len(features)])
            if len(features) >= query.max_results:
                break
    except Exception as exc:
        raise OperaRtcCatalogError(
            f"ASF OPERA RTC-S1 catalog search failed ({type(exc).__name__})"
        ) from exc
    return features, pages_retrieved


def search_opera_rtc_s1(query: OperaRtcCatalogQuery) -> list[dict[str, Any]]:
    """Return paginated ASF catalog features; this reads metadata only."""
    return search_opera_rtc_s1_with_pagination(query)[0]


def build_opera_rtc_catalog_record(
    query: OperaRtcCatalogQuery,
    features: list[dict[str, Any]],
    *,
    retrieved_at: datetime | None = None,
    pages_retrieved: int | None = None,
) -> dict[str, Any]:
    """Preserve source features and screen repeated-burst metadata candidates."""
    query.validate()
    if not isinstance(features, list) or any(not isinstance(item, dict) for item in features):
        raise OperaRtcCatalogError("ASF catalog response must be a list of features")
    if len(features) > query.max_results:
        raise OperaRtcCatalogError("ASF catalog response exceeds the requested result cap")
    if pages_retrieved is not None and (
        isinstance(pages_retrieved, bool)
        or not isinstance(pages_retrieved, int)
        or pages_retrieved < 0
    ):
        raise OperaRtcCatalogError("pages_retrieved must be a non-negative integer")
    retrieved_at = retrieved_at or datetime.now(timezone.utc)
    if retrieved_at.tzinfo is None:
        raise OperaRtcCatalogError("catalog retrieval timestamp must include a timezone")

    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    retained_features: list[dict[str, Any]] = []
    for feature in features:
        properties = feature.get("properties")
        scene_id = properties.get("fileID") if isinstance(properties, dict) else None
        match = _SCENE_ID.fullmatch(scene_id) if isinstance(scene_id, str) else None
        acquired = properties.get("startTime") if isinstance(properties, dict) else None
        if match is None or not isinstance(acquired, str):
            continue
        try:
            acquired_time = datetime.fromisoformat(acquired.replace("Z", "+00:00"))
        except ValueError:
            continue
        if acquired_time.tzinfo is None:
            continue
        identity = match.groupdict()
        key = (
            identity["burst"],
            identity["platform"],
            identity["spacing"],
            identity["version"],
        )
        groups.setdefault(key, []).append(feature)
        retained_features.append(feature)

    series: list[dict[str, Any]] = []
    candidate_count = 0
    for (burst, platform, spacing, product_version), items in sorted(groups.items()):
        ordered = sorted(items, key=lambda item: item["properties"]["startTime"])
        candidates = []
        for before, after in zip(ordered, ordered[1:]):
            before_props, after_props = before["properties"], after["properties"]
            before_id, after_id = before_props["fileID"], after_props["fileID"]
            before_time = datetime.fromisoformat(
                before_props["startTime"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            after_time = datetime.fromisoformat(
                after_props["startTime"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            if before_time >= after_time or before_time.date() == after_time.date():
                continue
            candidates.append(
                {
                    "before_scene_id": before_id,
                    "after_scene_id": after_id,
                    "before_acquisition_start_utc": before_time.isoformat(),
                    "after_acquisition_start_utc": after_time.isoformat(),
                    "interval_days": (after_time - before_time).total_seconds() / 86400,
                    "metadata_candidate_only": True,
                    "grid_and_valid_coverage_verified": False,
                }
            )
        candidate_count += len(candidates)
        series.append(
            {
                "burst_id": burst,
                "platform": platform,
                "pixel_spacing_m": int(spacing),
                "product_version": product_version,
                "scene_count": len(ordered),
                "scene_ids": [item["properties"]["fileID"] for item in ordered],
                "adjacent_date_candidates": candidates,
            }
        )

    try:
        catalog_client_version = version("asf-search")
    except PackageNotFoundError:
        catalog_client_version = "unknown"
    return {
        "record_type": "ASF_OPERA_RTC_S1_CATALOG",
        "schema_version": 1,
        "retrieved_at_utc": retrieved_at.astimezone(timezone.utc).isoformat(),
        "provider": "Alaska Satellite Facility DAAC",
        "mission_product": "NASA OPERA RTC-S1 derived from Sentinel-1; not NISAR",
        "catalog_client": {"name": "asf_search", "version": catalog_client_version},
        "catalog_query": {
            "dataset": "OPERA-S1",
            "processing_level": "RTC",
            "bounds_wgs84": [float(value) for value in query.bounds_wgs84],
            "start_date_inclusive": query.start_date,
            "end_date_inclusive": query.end_date,
            "result_limit": query.max_results,
        },
        "returned_feature_count": len(features),
        "candidate_screen_feature_count": len(retained_features),
        "potentially_truncated": len(features) >= query.max_results,
        "burst_series": series,
        "metadata_candidate_count": candidate_count,
        "features": retained_features,
        "interpretation_limit": (
            "Catalog metadata only. Repeated burst identity does not prove equal pixel "
            "grids, valid-pixel overlap, provider QA, or physical change. OPERA RTC-S1 "
            "is Sentinel-1-derived and remains distinct from NISAR GCOV."
        ),
        "pagination": {
            "page_size": ASF_CMR_PAGE_SIZE,
            "pages_retrieved": pages_retrieved,
        },
    }
