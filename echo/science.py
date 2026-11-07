"""Small deterministic measurement primitives for verified SAR inputs.

This module does not read product files, register images, or decide whether an
input pair is scientifically ready. Callers must establish those conditions;
the GCOV mask helper only decodes documented layer codes and cannot clear QA or
product-maturity holds.
"""

from __future__ import annotations

import re
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


@dataclass(frozen=True)
class GcovMaskResult:
    """Strict two-date mask and exclusion counts from documented GCOV layers."""

    common_valid_mask: np.ndarray
    before_nonvalid_samples: int
    after_nonvalid_samples: int
    before_exception_samples: int
    after_exception_samples: int
    before_unfocused_samples: int
    after_unfocused_samples: int
    before_unknown_exception_samples: int
    after_unknown_exception_samples: int


@dataclass(frozen=True)
class GcovExceptionMaskResult:
    """Decoded per-polarization validity and exception flags for one GCOV layer."""

    valid_mask: np.ndarray
    exception_mask: np.ndarray
    unfocused_mask: np.ndarray
    unknown_mask: np.ndarray
    encoding: str
    polarization: str
    polarization_flag: int | None


_GCOV_LAYER_POLARIZATION = {
    "HHHH": "HH",
    "HVHV": "HV",
    "VHVH": "VH",
    "VVVV": "VV",
    "RHRH": "RH",
    "RVRV": "RV",
}
_GCOV_VALIDITY_FLAGS = {
    "HH": 256,
    "HV": 512,
    "VH": 1024,
    "VV": 2048,
    "LH": 4096,
    "LV": 8192,
    "RH": 16384,
    "RV": 32768,
}
_GCOV_EXCEPTION_CODE = 2


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


def decode_gcov_exception_mask(
    exceptions: np.ndarray,
    *,
    layer: str,
    description: str | None = None,
) -> GcovExceptionMaskResult:
    """Decode documented exception-only and UInt16 validity-bit GCOV masks.

    Newer products describe a UInt16 bit field in the dataset's own HDF5
    ``description`` attribute. The low byte contains input exception codes;
    higher bits indicate fully focused input polarizations. Older UInt8
    products carry only exception codes 0 and 2. Unsupported encodings raise
    rather than interpreting numeric values by guesswork.
    """
    values = np.asarray(exceptions)
    polarization = _GCOV_LAYER_POLARIZATION.get(layer)
    if polarization is None:
        raise ValueError("GCOV exception mask requires a supported diagonal power layer")
    if values.ndim != 2 or not np.issubdtype(values.dtype, np.integer):
        raise ValueError("GCOV exception mask must be a two-dimensional integer array")

    if description and "validity mask bits" in description.lower():
        declared = {
            name: int(bit)
            for bit, name in re.findall(
                r"\b(\d+)\s*:\s*(HH|HV|VH|VV|LH|LV|RH|RV)\b", description
            )
        }
        if declared != _GCOV_VALIDITY_FLAGS:
            raise ValueError("GCOV exception-mask validity-bit description is unsupported")
        if not re.search(r"\b0\s*:\s*no anomaly\b", description, re.IGNORECASE):
            raise ValueError("GCOV exception-mask anomaly-code description is unsupported")
        allowed_bits = sum(declared.values()) | _GCOV_EXCEPTION_CODE
        unsigned = values.astype(np.uint64, copy=False)
        unknown = (unsigned & np.uint64(~allowed_bits & 0xFFFF)) != 0
        exception = (unsigned & _GCOV_EXCEPTION_CODE) != 0
        flag = declared[polarization]
        unfocused = (unsigned & flag) == 0
        return GcovExceptionMaskResult(
            valid_mask=~unknown & ~exception & ~unfocused,
            exception_mask=exception,
            unfocused_mask=~unknown & ~exception & unfocused,
            unknown_mask=unknown,
            encoding="UINT16_POLARIZATION_VALIDITY_AND_EXCEPTION_BITS",
            polarization=polarization,
            polarization_flag=flag,
        )

    if values.dtype.itemsize == 1:
        unknown = ~np.isin(values, (0, _GCOV_EXCEPTION_CODE))
        exception = values == _GCOV_EXCEPTION_CODE
        return GcovExceptionMaskResult(
            valid_mask=~unknown & ~exception,
            exception_mask=exception,
            unfocused_mask=np.zeros(values.shape, dtype=bool),
            unknown_mask=unknown,
            encoding="UINT8_EXCEPTION_CODES",
            polarization=polarization,
            polarization_flag=None,
        )

    raise ValueError("GCOV exception mask encoding is undocumented for this product")


def strict_common_gcov_mask(
    before_mask: np.ndarray,
    after_mask: np.ndarray,
    before_exceptions: np.ndarray,
    after_exceptions: np.ndarray,
    selection_mask: np.ndarray | None = None,
    *,
    layer: str = "HHHH",
    before_exception_description: str | None = None,
    after_exception_description: str | None = None,
) -> GcovMaskResult:
    """Intersect fully focused samples and exclude all documented anomalies.

    GCOV mask values 1-5 identify a fully focused sample; 0 is invalid or
    partially focused, and 255 is outside the acquisition extent. Product
    specification Rev F documents exception code 2 as an L-SAR qFSP-H1 sample
    slip. Newer UInt16 products also pack per-polarization focused-data flags;
    those are decoded from the product's own dataset description. Unknown
    encodings fail closed.

    Callers must additionally enforce product QA and maturity rules. ASF lists
    a misaligned valid-data mask issue for pre-calibration BETA products, so
    this decoder alone does not make a BETA mask safe for analysis.
    """
    arrays = [
        np.asarray(before_mask),
        np.asarray(after_mask),
        np.asarray(before_exceptions),
        np.asarray(after_exceptions),
    ]
    if any(array.ndim != 2 for array in arrays):
        raise ValueError("GCOV mask and exception arrays must be two-dimensional")
    if any(array.shape != arrays[0].shape for array in arrays[1:]):
        raise ValueError("GCOV mask and exception arrays must have identical shapes")
    selected = (
        np.ones(arrays[0].shape, dtype=bool)
        if selection_mask is None
        else np.asarray(selection_mask, dtype=bool)
    )
    if selected.shape != arrays[0].shape:
        raise ValueError("selection mask must match GCOV mask shapes")
    if any(not np.issubdtype(array.dtype, np.integer) for array in arrays):
        raise ValueError("GCOV mask and exception arrays must contain integer codes")

    before, after, before_exc, after_exc = arrays
    known_mask_codes = {0, 1, 2, 3, 4, 5, 255}
    if not np.isin(before, tuple(known_mask_codes)).all() or not np.isin(
        after, tuple(known_mask_codes)
    ).all():
        raise ValueError("GCOV mask contains an undocumented code")

    before_valid = (before >= 1) & (before <= 5)
    after_valid = (after >= 1) & (after <= 5)
    before_flags = decode_gcov_exception_mask(
        before_exc, layer=layer, description=before_exception_description
    )
    after_flags = decode_gcov_exception_mask(
        after_exc, layer=layer, description=after_exception_description
    )
    return GcovMaskResult(
        common_valid_mask=(
            selected
            & before_valid
            & after_valid
            & before_flags.valid_mask
            & after_flags.valid_mask
        ),
        before_nonvalid_samples=int(np.count_nonzero(selected & ~before_valid)),
        after_nonvalid_samples=int(np.count_nonzero(selected & ~after_valid)),
        before_exception_samples=int(
            np.count_nonzero(selected & before_flags.exception_mask)
        ),
        after_exception_samples=int(
            np.count_nonzero(selected & after_flags.exception_mask)
        ),
        before_unfocused_samples=int(
            np.count_nonzero(selected & before_flags.unfocused_mask)
        ),
        after_unfocused_samples=int(
            np.count_nonzero(selected & after_flags.unfocused_mask)
        ),
        before_unknown_exception_samples=int(
            np.count_nonzero(selected & before_flags.unknown_mask)
        ),
        after_unknown_exception_samples=int(
            np.count_nonzero(selected & after_flags.unknown_mask)
        ),
    )
