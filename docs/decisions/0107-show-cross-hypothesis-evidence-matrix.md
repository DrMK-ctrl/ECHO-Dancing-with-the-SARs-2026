# Decision 0107: Show a cross-hypothesis evidence matrix

**Date:** 2026-11-09
**Status:** Implemented and locally validated

## Context

Investigation assessments already display each hypothesis, its linked evidence, and other sources with no relationship recorded. Reviewers still had to compare separate hypothesis cards to see where the same source had different relationships or where a source-hypothesis relationship had not been assessed.

## Decision

Add a collapsed, source-linked matrix with one row per evidence artifact and one column per hypothesis. Each cell displays the relationship already retained in the assessment. A missing relationship is shown as “not assessed”; it is not inferred as negative, irrelevant, or non-distinguishing evidence. The matrix is a view only: it does not alter assessment states, infer source fit, score confidence, or verify analyst-entered relationships.

The matrix remains collapsed by default. Its scrollable table uses semantic row/column headers, accessible cell labels, and direct source-inspection buttons.

## Consequences

- Reviewers can compare evidence relationships and unassessed combinations in one place.
- The table can widen beyond the viewport within its own scroll region; the page layout remains fixed.
- In the retained T163 assessment, the matrix shows 24 source records × 6 hypotheses: 18 relationship records (1 `SUPPORTS`, 12 `DOES_NOT_DISTINGUISH`, and 5 `LIMITS_INTERPRETATION`) and 126 combinations with no recorded relationship. No `CONTRADICTS` relationship is recorded for this case; ECHO does not manufacture one.
- These are analyst-authored relationships and missing links, not an independently validated causal evaluation.

## Validation

See [evidence matrix browser validation](../validation/investigation-evidence-matrix-2026-11-09.md) and the renderer regression test.
