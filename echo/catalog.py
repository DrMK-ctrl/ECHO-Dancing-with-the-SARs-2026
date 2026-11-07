"""Discover and pair compatible NISAR GCOV observations using ASF metadata."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from shapely.geometry import shape


class CatalogQueryError(ValueError):
    """Raised when a catalog query is invalid or cannot be completed."""


@dataclass(frozen=True)
class CatalogQuery:
    longitude: float
    latitude: float
    start_date: str
    end_date: str
    maturity: str = "PROVISIONAL"
    max_results: int = 250

    def validate(self) -> None:
        if not -180 <= self.longitude <= 180:
            raise CatalogQueryError("longitude must be between -180 and 180")
        if not -90 <= self.latitude <= 90:
            raise CatalogQueryError("latitude must be between -90 and 90")
        if self.maturity not in {"BETA", "PROVISIONAL"}:
            raise CatalogQueryError("maturity must be BETA or PROVISIONAL")
        if not 1 <= self.max_results <= 250:
            raise CatalogQueryError("max_results must be between 1 and 250")
        try:
            start = datetime.fromisoformat(self.start_date)
            end = datetime.fromisoformat(self.end_date)
        except ValueError as exc:
            raise CatalogQueryError("dates must use ISO format YYYY-MM-DD") from exc
        if start > end:
            raise CatalogQueryError("start_date must not be after end_date")


def search_gcov(query: CatalogQuery) -> list[dict[str, Any]]:
    """Return ASF scene features for one point and product maturity.

    This query fetches public catalog metadata only. It does not retrieve raster
    pixels or use Earthdata credentials.
    """
    query.validate()
    import asf_search as asf

    options = asf.ASFSearchOptions(
        maxResults=query.max_results,
        intersectsWith=f"POINT({query.longitude} {query.latitude})",
        start=query.start_date,
        end=query.end_date,
        processingLevel=["GCOV"],
        dataset=["NISAR"],
        dataMaturity=query.maturity,
    )
    try:
        results = asf.search(opts=options)
    except Exception as exc:  # surfaced as a safe, useful CLI error
        raise CatalogQueryError(f"ASF catalog search failed: {exc}") from exc

    return results.geojson().get("features", [])


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
    )
    values = [properties.get(field) for field in fields]
    if any(value is None for value in values):
        return None
    return (
        *values[:4],
        tuple(sorted(values[4])),
        tuple(sorted(values[5])),
        *values[6:],
    )


def _footprints_intersect(left: dict[str, Any], right: dict[str, Any]) -> bool:
    try:
        return shape(left).intersects(shape(right))
    except (TypeError, ValueError):
        return False


def _as_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


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
        if identity is None or not properties.get("startTime"):
            continue
        if properties.get("processingLevel") != "GCOV":
            continue
        groups.setdefault(identity, []).append(feature)

    pairs: list[dict[str, Any]] = []
    for group in groups.values():
        scenes = sorted(group, key=lambda item: item["properties"]["startTime"])
        for before, after in zip(scenes, scenes[1:]):
            before_props = before["properties"]
            after_props = after["properties"]
            gap = (_as_utc(after_props["startTime"]) - _as_utc(before_props["startTime"]))
            gap_days = gap.total_seconds() / 86400
            if gap_days <= 0 or gap_days > max_gap_days:
                continue
            if not _footprints_intersect(before.get("geometry", {}), after.get("geometry", {})):
                continue
            pairs.append(
                {
                    "before_scene": before_props["fileID"],
                    "after_scene": after_props["fileID"],
                    "before_time_utc": before_props["startTime"],
                    "after_time_utc": after_props["startTime"],
                    "interval_days": round(gap_days, 3),
                    "collection": before_props["collectionName"],
                    "maturity": before_props["collectionName"].split("_")[3],
                    "path": before_props["pathNumber"],
                    "frame": before_props["frameNumber"],
                    "direction": before_props["flightDirection"],
                    "polarizations": before_props["mainBandPolarization"],
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
        },
        "query": {
            "dataset": "NISAR",
            "processing_level": "GCOV",
            "data_maturity": query.maturity,
            "longitude": query.longitude,
            "latitude": query.latitude,
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
