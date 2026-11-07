"""Product-specific validity handling for OPERA RTC-S1 mask rasters.

The OPERA RTC-S1 product mask uses 0 for a sample without layover or shadow,
1 for shadow, 2 for layover, 3 for both, and 255 for fill/invalid. For an
initial two-date backscatter comparison, ECHO uses only common code-0 samples.
Affected samples remain classified and counted; this conservative analysis
choice does not redefine the provider's mask classes.

Mask classes and meanings are documented in the ASF HyP3 OPERA RTC-S1 guide:
https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from echo.science import ChangeField, gamma0_log_ratio_db


@dataclass(frozen=True)
class OperaRtcS1Mask:
    """Decoded per-product mask flags without changing source codes."""

    clear: np.ndarray
    shadow_affected: np.ndarray
    layover_affected: np.ndarray
    invalid: np.ndarray


@dataclass(frozen=True)
class OperaRtcS1CommonMask:
    """Common clear-sample mask and selected-AOI source-code counts."""

    common_clear: np.ndarray
    before_clear_count: int
    after_clear_count: int
    before_shadow_affected_count: int
    after_shadow_affected_count: int
    before_layover_affected_count: int
    after_layover_affected_count: int
    before_invalid_count: int
    after_invalid_count: int
    aoi_pixel_count: int


@dataclass(frozen=True)
class OperaRtcS1PairMeasurement:
    """Descriptive RTC-S1 log-ratio array with its strict common mask."""

    change: ChangeField
    mask: OperaRtcS1CommonMask


def decode_opera_rtc_s1_mask(mask: np.ndarray) -> OperaRtcS1Mask:
    """Decode only the documented OPERA RTC-S1 validity-mask values."""
    values = np.asarray(mask)
    if values.ndim != 2 or not np.issubdtype(values.dtype, np.integer):
        raise ValueError("OPERA RTC-S1 mask must be a two-dimensional integer array")
    known = np.isin(values, (0, 1, 2, 3, 255))
    if not np.all(known):
        unexpected = np.unique(values[~known]).tolist()
        raise ValueError(f"OPERA RTC-S1 mask contains undocumented codes: {unexpected}")
    return OperaRtcS1Mask(
        clear=values == 0,
        shadow_affected=np.isin(values, (1, 3)),
        layover_affected=np.isin(values, (2, 3)),
        invalid=values == 255,
    )


def common_opera_rtc_s1_clear_mask(
    before_mask: np.ndarray,
    after_mask: np.ndarray,
    selection_mask: np.ndarray | None = None,
) -> OperaRtcS1CommonMask:
    """Select pixels clear of layover/shadow in both dates within one AOI.

    This helper does not assert that grids are co-registered. The caller must
    establish identical CRS, affine transform, dimensions, and pixel meaning
    before using a returned mask for temporal measurement.
    """
    before_values = np.asarray(before_mask)
    after_values = np.asarray(after_mask)
    if before_values.ndim != 2 or after_values.ndim != 2:
        raise ValueError("OPERA RTC-S1 masks must be two-dimensional")
    if before_values.shape != after_values.shape:
        raise ValueError("OPERA RTC-S1 masks must have identical shapes")
    before = decode_opera_rtc_s1_mask(before_values)
    after = decode_opera_rtc_s1_mask(after_values)
    selected = (
        np.ones(before_values.shape, dtype=bool)
        if selection_mask is None
        else np.asarray(selection_mask, dtype=bool)
    )
    if selected.shape != before_values.shape:
        raise ValueError("AOI selection mask must match OPERA RTC-S1 mask shapes")

    return OperaRtcS1CommonMask(
        common_clear=selected & before.clear & after.clear,
        before_clear_count=int(np.count_nonzero(selected & before.clear)),
        after_clear_count=int(np.count_nonzero(selected & after.clear)),
        before_shadow_affected_count=int(
            np.count_nonzero(selected & before.shadow_affected)
        ),
        after_shadow_affected_count=int(
            np.count_nonzero(selected & after.shadow_affected)
        ),
        before_layover_affected_count=int(
            np.count_nonzero(selected & before.layover_affected)
        ),
        after_layover_affected_count=int(
            np.count_nonzero(selected & after.layover_affected)
        ),
        before_invalid_count=int(np.count_nonzero(selected & before.invalid)),
        after_invalid_count=int(np.count_nonzero(selected & after.invalid)),
        aoi_pixel_count=int(np.count_nonzero(selected)),
    )


def analyze_opera_rtc_s1_pair(
    before_power: np.ndarray,
    after_power: np.ndarray,
    before_mask: np.ndarray,
    after_mask: np.ndarray,
    *,
    before_crs: str,
    after_crs: str,
    before_transform: tuple[float, ...] | list[float],
    after_transform: tuple[float, ...] | list[float],
    selection_mask: np.ndarray | None = None,
) -> OperaRtcS1PairMeasurement:
    """Measure a registered RTC-S1 pair on common AOI pixels clear both dates.

    ``before_transform`` and ``after_transform`` are the six affine terms
    ``(a, b, c, d, e, f)`` returned by raster readers. This gate intentionally
    requires exact grid equality; it performs no implicit resampling or
    registration. The log ratio is descriptive backscatter change, not an
    event classification or causal interpretation.
    """
    before = np.asarray(before_power)
    after = np.asarray(after_power)
    if before.ndim != 2 or after.ndim != 2 or before.shape != after.shape:
        raise ValueError("RTC-S1 power windows must be two-dimensional and shape matched")
    if not isinstance(before_crs, str) or not before_crs.strip():
        raise ValueError("before RTC-S1 CRS is missing")
    if not isinstance(after_crs, str) or not after_crs.strip():
        raise ValueError("after RTC-S1 CRS is missing")
    if before_crs != after_crs:
        raise ValueError("RTC-S1 pair CRS values must match exactly")

    def normalized_transform(value: tuple[float, ...] | list[float], role: str) -> tuple[float, ...]:
        if not isinstance(value, (tuple, list)) or len(value) not in (6, 9):
            raise ValueError(f"{role} RTC-S1 affine transform must contain six or nine terms")
        try:
            terms = tuple(float(term) for term in value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{role} RTC-S1 affine transform must be numeric") from exc
        if not np.isfinite(terms).all():
            raise ValueError(f"{role} RTC-S1 affine transform must be finite")
        return terms

    before_grid = normalized_transform(before_transform, "before")
    after_grid = normalized_transform(after_transform, "after")
    if before_grid != after_grid:
        raise ValueError("RTC-S1 pair affine transforms must match exactly")

    masks = common_opera_rtc_s1_clear_mask(
        before_mask, after_mask, selection_mask
    )
    if masks.common_clear.shape != before.shape:
        raise ValueError("RTC-S1 power and mask windows must have identical shapes")
    change = gamma0_log_ratio_db(before, after, masks.common_clear)
    return OperaRtcS1PairMeasurement(change=change, mask=masks)
