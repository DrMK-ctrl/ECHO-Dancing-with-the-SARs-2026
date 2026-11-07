# Decision 0004: GCOV log-ratio as a descriptive baseline measurement

**Date:** 2026-11-07

**Status:** Accepted as a low-level method primitive; real-case use is gated

## Context

ECHO needs a reproducible, interpretable first measurement before it adds a detector or an investigation engine. ASF documents GCOV diagonal terms such as `HHHH` and `HVHV` as real-valued gamma-nought backscatter power. A ratio-based temporal comparison is a conventional SAR baseline; Rignot and van Zyl compared ratioing and difference methods using ERS-1 observations and discussed their differing statistical behavior.

The current Mozambique BETA and Nepal PROVISIONAL candidate pairs have unresolved identification-group QA failures. ASF describes the GCOV `mask` as information about the adaptive multi-look averaging ensemble. Its exact product-version semantics and the mask's suitability as a validity filter must be reviewed before ECHO derives a common-valid mask.

## Decision

Implement one deterministic, low-level quantity for arrays already proven suitable by a caller:

`delta_db = 10 * log10(after_gamma0_power / before_gamma0_power)`

The primitive accepts same-shaped two-dimensional power arrays and an explicit common-valid Boolean mask. It excludes masked, non-finite, zero, and negative samples, returns signed dB values, and supports descriptive regional median and quartile summaries. It does not classify changed pixels, attribute causes, estimate probability, evaluate statistical significance, or select a threshold.

## Preconditions for real-product use

- The exact products pass a QA disposition appropriate to the analysis; current candidate pairs do not.
- The caller establishes identical measurement semantics and compatible product maturity, acquisition configuration, and processing release.
- Coordinate transforms, grid registration, and a defensible common-valid mask are verified from the product specification and product metadata.
- The AOI and any event/control strata are documented and reproducible.
- The complete run records product IDs, source hashes where available, software version, method, region definitions, masks, and summary outputs.

This primitive is exercised only on explicitly synthetic arrays in unit tests. No real NISAR measurements have been passed through it, and no current QA hold is changed.

## Consequences

- ECHO has a small executable measurement primitive on which later raster-window processing can build.
- A signed continuous change layer can be inspected before any classification is proposed.
- This conventional baseline is a reference point for later comparisons; its usefulness for the selected event, changing GCOV look counts, residual artifacts, and control-region design remain to be evaluated.
- Passing these unit tests proves arithmetic behavior on fixtures, not the scientific validity of a NISAR case.

## References

- ASF, [Geocoded Polarimetric Covariance (GCOV)](https://nisar-docs.asf.alaska.edu/gcov/).
- Rignot, E. J. M., and van Zyl, J. J. (1993), [Change detection techniques for ERS-1 SAR data](https://doi.org/10.1109/36.239913).
- ASF, [Provisional product known issues](https://nisar-docs.asf.alaska.edu/provisional-known-issues/).
