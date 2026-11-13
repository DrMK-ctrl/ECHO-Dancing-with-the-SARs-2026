"""Discover and pair compatible NISAR GCOV observations using ASF metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import math
from typing import Any, Iterable

from shapely.geometry import shape

ASF_CMR_PAGE_SIZE = 250
MAX_GCOV_CATALOG_RESULTS = 1000


class CatalogQueryError(ValueError):
    """Raised when a catalog query is invalid or cannot be completed."""


@dataclass(frozen=True)
class CatalogQuery:
    longitude: float
    latitude: float
    start_date: str
    end_date: str
    maturity: str = "PROVISIONAL"
    max_results: int = MAX_GCOV_CATALOG_RESULTS
    bounds_wgs84: tuple[float, float, float, float] | None = None

    def validate(self) -> None:
        if (
            isinstance(self.longitude, bool)
            or not isinstance(self.longitude, (int, float))
            or not math.isfinite(self.longitude)
        ):
            raise CatalogQueryError("longitude must be a finite number")
        if (
            isinstance(self.latitude, bool)
            or not isinstance(self.latitude, (int, float))
            or not math.isfinite(self.latitude)
        ):
            raise CatalogQueryError("latitude must be a finite number")
        if not -180 <= self.longitude <= 180:
            raise CatalogQueryError("longitude must be between -180 and 180")
        if not -90 <= self.latitude <= 90:
            raise CatalogQueryError("latitude must be between -90 and 90")
        if self.bounds_wgs84 is not None:
            bounds = self.bounds_wgs84
            if not isinstance(bounds, (tuple, list)) or len(bounds) != 4:
                raise CatalogQueryError("bounds_wgs84 must be west, south, east, north")
            if any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in bounds
            ):
                raise CatalogQueryError("bounds_wgs84 must contain four finite numbers")
            west, south, east, north = bounds
            if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
                raise CatalogQueryError("bounds_wgs84 must be ordered within WGS84")
        if not isinstance(self.maturity, str) or self.maturity not in {
            "BETA",
            "PROVISIONAL",
            "VALIDATED",
        }:
            raise CatalogQueryError("maturity must be BETA, PROVISIONAL, or VALIDATED")
        if (
            isinstance(self.max_results, bool)
            or not isinstance(self.max_results, int)
            or not 1 <= self.max_results <= MAX_GCOV_CATALOG_RESULTS
        ):
            raise CatalogQueryError(
                f"max_results must be between 1 and {MAX_GCOV_CATALOG_RESULTS}"
            )
        if not isinstance(self.start_date, str) or not isinstance(self.end_date, str):
            raise CatalogQueryError("dates must use ISO format YYYY-MM-DD")
        try:
            start = date.fromisoformat(self.start_date)
            end = date.fromisoformat(self.end_date)
        except ValueError as exc:
            raise CatalogQueryError("dates must use ISO format YYYY-MM-DD") from exc
        if start.isoformat() != self.start_date or end.isoformat() != self.end_date:
            raise CatalogQueryError("dates must use ISO format YYYY-MM-DD")
        if start > end:
            raise CatalogQueryError("start_date must not be after end_date")


def search_gcov(query: CatalogQuery) -> list[dict[str, Any]]:
    """Return ASF scene features for one point and product maturity.

    This query fetches public catalog metadata only. It does not retrieve raster
    pixels or use Earthdata credentials.
    """
    query.validate()
    import asf_search as asf

    if query.bounds_wgs84 is None:
        intersects = f"POINT({query.longitude} {query.latitude})"
    else:
        west, south, east, north = query.bounds_wgs84
        intersects = (
            f"POLYGON(({west} {south},{east} {south},{east} {north},"
            f"{west} {north},{west} {south}))"
        )
    options = asf.ASFSearchOptions(
        intersectsWith=intersects,
        start=query.start_date,
        end=asf_inclusive_end(query.end_date),
        processingLevel=["GCOV"],
        dataset=["NISAR"],
        dataMaturity=query.maturity,
    )
    try:
        features = []
        for page in asf.search_generator(opts=options, maxResults=query.max_results):
            page_features = page.geojson().get("features", [])
            remaining = query.max_results - len(features)
            features.extend(page_features[:remaining])
            if len(features) >= query.max_results:
                break
    except Exception as exc:  # surfaced as a safe, useful CLI error
        raise CatalogQueryError(f"ASF catalog search failed: {exc}") from exc

    return features


def search_gunw(query: CatalogQuery) -> list[dict[str, Any]]:
    """Return ASF metadata for NISAR GUNW products intersecting a query.

    GUNW is kept as a separate product search from GCOV because its phase,
    coherence, and quality layers support different scientific operations.
    This function retrieves catalog metadata only.
    """
    query.validate()
    if query.maturity not in {"PROVISIONAL", "VALIDATED"}:
        raise CatalogQueryError("GUNW maturity must be PROVISIONAL or VALIDATED")
    import asf_search as asf

    if query.bounds_wgs84 is None:
        intersects = f"POINT({query.longitude} {query.latitude})"
    else:
        west, south, east, north = query.bounds_wgs84
        intersects = (
            f"POLYGON(({west} {south},{east} {south},{east} {north},"
            f"{west} {north},{west} {south}))"
        )
    options = asf.ASFSearchOptions(
        maxResults=query.max_results,
        intersectsWith=intersects,
        start=query.start_date,
        end=asf_inclusive_end(query.end_date),
        processingLevel=["GUNW"],
        dataset=["NISAR"],
        dataMaturity=query.maturity,
    )
    try:
        results = asf.search(opts=options)
    except Exception as exc:
        raise CatalogQueryError(f"ASF GUNW catalog search failed: {exc}") from exc
    return results.geojson().get("features", [])


def asf_inclusive_end(end_date: str) -> str:
    """Format ECHO's inclusive calendar end date for ASF's timestamp filter.

    ASF Search parses date-only strings as 00:00 UTC. Passing an inclusive end
    date as ``YYYY-MM-DD`` therefore omits acquisitions later that same day.
    Use the final whole second of the selected UTC day instead.
    """
    return f"{date.fromisoformat(end_date).isoformat()}T23:59:59Z"


def _normalized_identity(properties: dict[str, Any]) -> tuple[Any, ...] | None:
    fields = (
        "collectionName",
        "pathNumber",
        "frameNumber",
        "flightDirection",
        "rangeBandwidth",
        "mainBandPolarization",
        "productionConfiguration",
        "crid",
        "sideBandPolarization",
    )
    values = [properties.get(field) for field in fields]
    if any(value is None for value in values):
        return None
    return (
        *values[:4],
        tuple(sorted(values[4])),
        tuple(sorted(values[5])),
        *values[6:8],
        tuple(sorted(values[8])),
    )


def _footprints_intersect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    try:
        return shape(left).intersects(shape(right))
    except (TypeError, ValueError):
        return False


def _as_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CatalogQueryError("catalog acquisition timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


def _orbit_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _collection_maturity(collection: str) -> str:
    if collection == "NISAR_L2_GCOV_V1":
        return "VALIDATED"
    for maturity in ("BETA", "PROVISIONAL"):
        if maturity in collection.split("_"):
            return maturity
    return "UNRECOGNIZED"


def pair_gcov_scenes(
    features: Iterable[dict[str, Any]], *, max_gap_days: float = 24
) -> list[dict[str, Any]]:
    """Identify adjacent metadata-compatible scenes for later pixel validation.

    A returned pair is only a catalog-level candidate. This function does not
    establish pixel-grid co-registration, valid-data overlap, or a physical
    change on the ground.
    """
    if max_gap_days <= 0:
        raise CatalogQueryError("max_gap_days must be positive")

    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for feature in features:
        properties = feature.get("properties", {})
        identity = _normalized_identity(properties)
        if (
            identity is None
            or not properties.get("startTime")
            or not properties.get("stopTime")
        ):
            continue
        if properties.get("processingLevel") != "GCOV":
            continue
        if _collection_maturity(properties.get("collectionName", "")) == "UNRECOGNIZED":
            continue
        orbit = _orbit_number(properties.get("orbit"))
        if orbit is None:
            continue
        groups.setdefault(identity, []).append(feature)

    pairs: list[dict[str, Any]] = []
    for group in groups.values():
        scenes = sorted(
            group, key=lambda item: _as_utc(item["properties"]["startTime"])
        )
        for before, after in zip(scenes, scenes[1:]):
            before_props = before["properties"]
            after_props = after["properties"]
            before_orbit = _orbit_number(before_props.get("orbit"))
            after_orbit = _orbit_number(after_props.get("orbit"))
            if before_orbit is None or after_orbit is None or before_orbit == after_orbit:
                continue
            gap = (_as_utc(after_props["startTime"]) - _as_utc(before_props["startTime"]))
            gap_days = gap.total_seconds() / 86400
            if (
                gap_days <= 0
                or gap_days > max_gap_days
                or _as_utc(before_props["stopTime"])
                >= _as_utc(after_props["startTime"])
            ):
                continue
            if not _footprints_intersect(before.get("geometry", {}), after.get("geometry", {})):
                continue
            pairs.append(
                {
                    "before_scene": before_props["fileID"],
                    "after_scene": after_props["fileID"],
                    "before_time_utc": before_props["startTime"],
                    "before_stop_time_utc": before_props["stopTime"],
                    "after_time_utc": after_props["startTime"],
                    "interval_days": round(gap_days, 3),
                    "collection": before_props["collectionName"],
                    "maturity": _collection_maturity(before_props["collectionName"]),
                    "before_orbit": before_orbit,
                    "after_orbit": after_orbit,
                    "path": before_props["pathNumber"],
                    "frame": before_props["frameNumber"],
                    "direction": before_props["flightDirection"],
                    "polarizations": before_props["mainBandPolarization"],
                    "side_band_polarizations": before_props["sideBandPolarization"],
                    "range_bandwidth_mhz": before_props["rangeBandwidth"],
                    "production_configuration": before_props["productionConfiguration"],
                    "crid": before_props["crid"],
                    "frame_coverage": [
                        before_props.get("frameCoverage"),
                        after_props.get("frameCoverage"),
                    ],
                    "metadata_footprints_intersect": True,
                    "status": "METADATA_MATCH_ONLY",
                    "required_before_analysis": [
                        "inspect both product QA reports and masks",
                        "verify spatial grid alignment and valid-pixel overlap",
                        "confirm product maturity and processing versions",
                    ],
                }
            )
    return sorted(pairs, key=lambda pair: pair["before_time_utc"])


def build_catalog_record(
    query: CatalogQuery, features: list[dict[str, Any]], *, queried_at: datetime | None = None
) -> dict[str, Any]:
    query.validate()
    queried_at = queried_at or datetime.now(timezone.utc)
    return {
        "schema_version": 1,
        "queried_at_utc": queried_at.astimezone(timezone.utc).isoformat(),
        "source": {
            "provider": "Alaska Satellite Facility DAAC",
            "api_client": "asf_search",
            "catalog_only": True,
            "pixels_downloaded": False,
            "cmr_page_size": ASF_CMR_PAGE_SIZE,
            "result_limit": query.max_results,
            "returned_feature_count": len(features),
            "pages_retrieved": math.ceil(len(features) / ASF_CMR_PAGE_SIZE),
            "potentially_truncated": len(features) >= query.max_results,
        },
        "query": {
            "dataset": "NISAR",
            "processing_level": "GCOV",
            "data_maturity": query.maturity,
            "longitude": query.longitude,
            "latitude": query.latitude,
            "bounds_wgs84": list(query.bounds_wgs84) if query.bounds_wgs84 else None,
            "start_date": query.start_date,
            "end_date": query.end_date,
        },
        "feature_count": len(features),
        "features": features,
        "metadata_candidate_pairs": pair_gcov_scenes(features),
        "interpretation_limit": (
            "Catalog metadata identifies candidate acquisitions; it does not establish "
            "pixel alignment, valid-data overlap, or physical cause."
        ),
    }
