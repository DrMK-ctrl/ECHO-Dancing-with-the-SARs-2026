"""Small deterministic measurement primitives for verified SAR inputs.

This module does not read product files, decode product masks, register images,
or decide whether an input pair is scientifically ready. Callers must establish
those conditions before passing data here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChangeField:
    """Per-pixel signed log-ratio values and their usable-sample mask."""

    values_db: np.ndarray
    valid_mask: np.ndarray

    @property
    def valid_count(self) -> int:
        return int(np.count_nonzero(self.valid_mask))

    @property
    def candidate_count(self) -> int:
        return int(self.valid_mask.size)


@dataclass(frozen=True)
class RegionSummary:
    """Robust descriptive summary; it is not a confidence or accuracy score."""

    sample_count: int
    median_db: float | None
    lower_quartile_db: float | None
    upper_quartile_db: float | None


def gamma0_log_ratio_db(
    before_power: np.ndarray,
    after_power: np.ndarray,
    common_valid_mask: np.ndarray,
) -> ChangeField:
    """Compute signed temporal change from co-registered GCOV gamma0 power.

    The per-pixel quantity is ``10 * log10(after / before)``. Positive values
    mean the later gamma0 power is larger; negative values mean it is smaller.
    This is a descriptive measurement, not a classification or causal finding.

    This primitive is intended for bounded AOI windows, not complete granules;
    it allocates a result array and masks proportional to its input size.
    ``common_valid_mask`` must already combine product-specific quality and
    geometric-overlap rules established by a caller. This function only adds
    finite, strictly positive numeric checks needed by the logarithm.
    """
    before = np.asarray(before_power)
    after = np.asarray(after_power)
    common = np.asarray(common_valid_mask, dtype=bool)
    if before.ndim != 2 or after.ndim != 2:
        raise ValueError("before and after power arrays must be two-dimensional")
    if before.shape != after.shape or common.shape != before.shape:
        raise ValueError("power arrays and common-valid mask must have identical shapes")

    numeric_valid = (
        common
        & np.isfinite(before)
        & np.isfinite(after)
        & (before > 0)
        & (after > 0)
    )
    values = np.full(before.shape, np.nan, dtype=np.float32)
    if np.any(numeric_valid):
        before_values = before[numeric_valid].astype(np.float64, copy=False)
        after_values = after[numeric_valid].astype(np.float64, copy=False)
        values[numeric_valid] = (
            10.0 * (np.log10(after_values) - np.log10(before_values))
        ).astype(np.float32)
    return ChangeField(values_db=values, valid_mask=numeric_valid)


def summarize_region(field: ChangeField, region_mask: np.ndarray) -> RegionSummary:
    """Summarize valid change values in a caller-defined geographic stratum."""
    region = np.asarray(region_mask, dtype=bool)
    if region.shape != field.values_db.shape:
        raise ValueError("region mask must match the change field shape")
    selected = field.valid_mask & region
    count = int(np.count_nonzero(selected))
    if count == 0:
        return RegionSummary(0, None, None, None)
    values = field.values_db[selected].astype(np.float64, copy=False)
    q25, median, q75 = np.quantile(values, (0.25, 0.5, 0.75))
    return RegionSummary(
        sample_count=count,
        median_db=float(median),
        lower_quartile_db=float(q25),
        upper_quartile_db=float(q75),
    )
