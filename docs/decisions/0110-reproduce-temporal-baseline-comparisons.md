# Decision 0110: Reproduce retained temporal-baseline comparisons

**Date:** 2026-11-12  
**Status:** Implemented for the retained T024 OPERA RTC-S1 series; diagnostic only

## Context

The T024 temporal-series builder retains adjacent-interval measurements and comparisons against the first acquisition on one all-date common support. Its validator recomputed adjacent intervals but did not verify the stored first-acquisition baseline arrays, masks, checksums, metadata, or summaries. The Challenge This Finding view therefore could not test how the retained response changed with a different temporal baseline.

## Decision

Extend the existing OPERA series validator to reproduce each stored first-acquisition comparison from its observation backscatter arrays and the all-date support mask. Check scene identity, acquisition times, interval length, valid mask, per-pixel values, checksum, and summary statistics. Return the reproduced baseline summary alongside adjacent intervals.

When an investigation assessment links this validated series, include its adjacent and first-acquisition comparisons in the challenge dossier and present them as diagnostic temporal sensitivity. When no validated series is linked, state that alternative temporal baselines are unavailable; do not synthesize dates or observations.

## Consequences and limits

- T024 displays the 24-day and 384-day adjacent intervals and the 408-day first-to-third baseline on the same 1,034-cell common support.
- These intervals share acquisitions and differ substantially in duration. Their measurements are not independent or event-equivalent, and do not establish persistence, timing, physical cause, or provider QA clearance.
- T163's pair-only assessment reports temporal-baseline sensitivity as unavailable.
- This validates retained record calculations; it does not rerun the upstream raster reads or processing.
- No schema version, measurement, evidence relationship, or investigation disposition changes.

## Verification

Regression tests reject tampered baseline arrays and summaries. The API, challenge builder, renderer, and local Firefox workflow show the validated values and QA limits. See [Adversarial Evidence Challenge validation](../validation/adversarial-evidence-challenge-2026-11-12.md).
