# Decision 0091: validate HLS association cutoff sensitivity

**Date:** 2026-11-09
**Status:** Implemented

## Context

The T024 HLS L30 association already retained descriptive results at 25%, 50%, and 75% minimum optical area coverage. The active assessment and map card exposed only the 75% row, hiding how the shared SAR-cell support and correlation changed as the cutoff moved.

## Decision

Carry the full declared cutoff series into assessment schema 3 and display each cutoff, SAR-cell count, and descriptive Pearson r in the vegetation-context card. At assessment-build time, recompute the linked HLS/SAR spatial association from the exact retained SAR and optical records and their checksummed bounded pixel assets. Compare the complete derived record, excluding its generation timestamp and the human-readable sensor label; validate that label against the HLS product variant. At application load, require schema-3 sensitivity summaries to exactly match the linked association artifact.

The sensitivity is descriptive. Neighboring cells are spatially dependent, the optical common support is limited, and the RTC-S1 provider QA disposition remains unresolved. It cannot establish causality or validate the SAR measurement.

## Validation

See [T024 HLS cutoff-sensitivity validation](../validation/t024-hls-cutoff-sensitivity-2026-11-09.md).
