"""Bounded end-to-end OPERA RTC-S1 pair processing orchestration."""

from __future__ import annotations

from typing import Any

from echo.opera_rtc_access import (
    OperaRtcS1AccessError,
    read_opera_rtc_s1_window,
)
from echo.opera_rtc_analysis import (
    OperaRtcS1AnalysisError,
    build_opera_rtc_s1_pair_analysis,
)


class OperaRtcS1PipelineError(ValueError):
    """Raised when an OPERA RTC-S1 pair cannot be read or compared."""


_FEATURE_PROPERTIES = frozenset(
    {
        "fileID",
        "url",
        "startTime",
        "stopTime",
        "collectionName",
        "bytes",
        "beamModeType",
        "flightDirection",
        "polarization",
        "sensor",
        "sceneName",
    }
)


def _validate_feature(feature: Any, role: str) -> dict[str, Any]:
    if not isinstance(feature, dict) or set(feature) != {"properties"}:
        raise OperaRtcS1PipelineError(f"{role} OPERA catalog feature is invalid")
    properties = feature["properties"]
    if (
        not isinstance(properties, dict)
        or not {"fileID", "url", "startTime", "bytes"}.issubset(properties)
        or not set(properties).issubset(_FEATURE_PROPERTIES)
    ):
        raise OperaRtcS1PipelineError(f"{role} OPERA catalog properties are invalid")
    if not isinstance(properties["bytes"], dict) or len(properties["bytes"]) > 8:
        raise OperaRtcS1PipelineError(f"{role} OPERA asset metadata is invalid")
    return feature


def build_opera_rtc_s1_pair_record(
    before_feature: dict[str, Any],
    after_feature: dict[str, Any],
    *,
    bounds_wgs84: tuple[float, float, float, float] | list[float],
    polarization: str,
    window_reader: Any = read_opera_rtc_s1_window,
) -> dict[str, Any]:
    """Read two bounded RTC-S1 windows and build their provenance manifest.

    Provider QA for OPERA RTC-S1 is explicitly recorded as not retrieved by the
    current adapter. Therefore a live computed pair remains diagnostic; this
    function never calls it a provider-validated scientific finding.
    """
    before = _validate_feature(before_feature, "before")
    after = _validate_feature(after_feature, "after")
    if before["properties"]["fileID"] == after["properties"]["fileID"]:
        raise OperaRtcS1PipelineError("before and after scenes must be different")
    if polarization not in {"VV", "VH", "HH", "HV"}:
        raise OperaRtcS1PipelineError("polarization must be VV, VH, HH, or HV")
    try:
        before_window = window_reader(
            before,
            bounds_wgs84=bounds_wgs84,
            polarization=polarization,
        )
        after_window = window_reader(
            after,
            bounds_wgs84=bounds_wgs84,
            polarization=polarization,
        )
        return build_opera_rtc_s1_pair_analysis(before_window, after_window)
    except (OperaRtcS1AccessError, OperaRtcS1AnalysisError) as exc:
        raise OperaRtcS1PipelineError(str(exc)) from exc
