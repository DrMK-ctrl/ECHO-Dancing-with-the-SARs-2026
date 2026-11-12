# Decision 0112: Test OPERA temporal measurements under a one-cell grid offset

**Date:** 2026-11-12
**Status:** Accepted for diagnostic review

## Context

The T024 RTC-S1 series has exact matching CRS, affine transform, shape, and burst identity, and its values are compared on validated all-date common support. That establishes declared grid alignment; it does not show how the measured differences respond to a deliberate relative offset. OPERA's RTC-S1 specification describes 30 m pixels and a fixed geographic grid for a burst ID. A bounded one-cell perturbation is therefore a useful, inspectable stress scenario for this retained series.

## Decision

For each adjacent T024 observation pair and the first-acquisition baseline, shift the later backscatter array by one native cell in each of eight neighboring row/column directions. Do not resample or wrap edges. For each variant, use only cells with finite before, nominal after, and offset after values; recompute the unshifted control on precisely that same support. Report per-offset displacement, support count, median, mean, pixel sign counts, and difference from the matched-support control.

The challenge interface presents this under a collapsed diagnostic disclosure. It must describe the operation as a relative-offset stress test, never as estimated geolocation error, an uncertainty interval, a correction, statistical significance, or a stability score. It cannot change QA or hypothesis state.

## Consequences

- This adds a deterministic challenge to one real, source-validated multi-acquisition series without claiming provider QA clearance.
- Pixel counts remain descriptive because spatial samples are dependent.
- Only integer one-cell offsets are tested; subpixel effects and actual registration-error distributions are not estimated.
- T163 has no linked multi-acquisition series, so this test remains explicitly unavailable there.
