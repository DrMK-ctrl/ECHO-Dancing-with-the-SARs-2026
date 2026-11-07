# Decision 0023: Record testability and falsification conditions

**Date:** 2026-11-07
**Status:** Implemented for the retained cross-sensor case; scientific relationship labels remain analyst-authored

## Context

The first assessment linked evidence to hypotheses and described follow-up actions, but did not state what observation a hypothesis predicts, what result could weaken it, or whether the retained evidence can test it. A `NOT_EVALUATED` disposition alone could not distinguish an unsearched question from an attempted but data-limited test.

## Decision

- Each hypothesis records an expected observation, a result that could weaken it, required evidence, and the reason for its current testability state.
- Use `DESCRIPTIVE_ONLY` for a reproducible product summary that does not test physical cause, `NOT_TESTED` when the proposed test has not been performed, and `NOT_TESTABLE_WITH_RETAINED_EVIDENCE` when current data do not meet the needed quality, coverage, or compatibility conditions.
- Preserve the existing evidence relationships and conservative disposition rule. The new fields do not infer a physical mechanism or assign probability.
- Validate required fields and evidence references in the reusable investigation module. Validation checks record structure only; it does not decide whether a prediction or scientific rationale is correct.
- Expose test conditions in a collapsed details section so the assessment stays scannable while remaining inspectable.

## Current case and limits

For the water explanation, the expected discriminating observation is a quality-valid water transition spatially associated with the SAR response at suitable temporal and common spatial support. The nearer retained DSWx-HLS pair cannot provide that test: WTR has zero common-valid AOI pixels, earlier WTR-2 water-coded cells are cloud/snow flagged, and the OPERA RTC-S1 pair has no consolidated provider QA verdict. The explanation is therefore marked `NOT_TESTABLE_WITH_RETAINED_EVIDENCE`, not contradicted. The alternative-driver explanation is `NOT_TESTED` because corresponding measurements are absent. Synthetic tests validate only contract handling, not these scientific predictions.
