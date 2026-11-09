# Decision 0092: generalize HLS cutoff sensitivity across cases

**Date:** 2026-11-09
**Status:** Implemented

## Context

Decision 0091 added source-recomputed HLS L30 cutoff sensitivity to the T024 assessment. The same L30 and S30 association records are also linked in T163, but that active assessment still used the earlier schema and displayed only its 75% summary. That left the new assessment contract case-specific and hid how the very small S30 support affected its reported association.

## Decision

Use assessment schema 3 for either linked HLS L30 or S30 association. Carry all declared cutoffs for each available association into the assessment, and require the application to match each summary to its linked derived record. Recompute each association from its exact SAR/HLS records and bounded pixel assets during assessment construction. Display the sensitivity series in both optical evidence cards, while retaining each sensor's independent coverage and QA limitations.

The schema change does not combine L30 and S30 evidence or make them independent validation. H4 remains `UNRESOLVED`; the correlations are descriptive, the pixels are spatially dependent, and OPERA RTC-S1 has no consolidated QA verdict.

## Validation

See [T163 HLS cutoff-sensitivity validation](../validation/t163-hls-cutoff-sensitivity-2026-11-09.md).
