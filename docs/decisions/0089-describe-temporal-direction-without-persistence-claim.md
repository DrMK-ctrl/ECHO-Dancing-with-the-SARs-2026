# Decision 0089: describe temporal direction without a persistence claim

**Date:** 2026-11-09
**Status:** Implemented

## Context

The T024 case has three compatible same-burst OPERA RTC-S1 observations on an identical grid and 1,034 all-date common pixels. Its two adjacent signed backscatter steps span about 24 days and 384 days. The existing median values describe each interval, but do not show how often a pixel's signed direction agrees or reverses across both steps.

## Decision

Derive an exhaustive per-pixel sign classification directly from the validated adjacent interval arrays on their common support: consistent increase, consistent decrease, direction reversal, or at least one exact zero step. Record exact interval durations and AOI pixels outside common support. Recompute the summary from the linked source series when building and validating a schema-version-2 assessment.

Expose the counts in the T024 investigation card and retain the full derivation in the inspectable assessment record. Keep the series and assessment diagnostic, keep provider QA unresolved, and keep the temporal series linked as nondistinguishing evidence.

## Limits

The screen uses a zero dB sign boundary and no magnitude threshold. Values near zero can change category with measurement noise. The intervals have very different lengths and share the middle observation; sign agreement does not establish physical persistence, an event, event duration, cause, or independent corroboration. These counts are descriptive only and do not alter any hypothesis state.

## Validation

See [T024 temporal direction screen validation](../validation/opera-t024-temporal-direction-screen-2026-11-09.md).
