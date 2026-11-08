# Decision 0040: Require test designs for open evidence searches

**Date:** 2026-11-08
**Status:** Implemented in the assessment contract and T163 case record

## Decision

Every not-yet-searched `DISCRIMINATING_OBSERVATION` follow-up must carry a falsifiable test design before the search is treated as an open investigation action. The design identifies one hypothesis under test, the mechanism branch, expected observation, what would weaken the hypothesis, what would make the result inconclusive, acceptance gates, and the interpretation limit.

The design also lists all hypotheses outside the follow-up's declared targets. Non-targets cannot simultaneously be declared targets. This prevents an observation request from claiming to test and not test the same explanation, and makes its scope inspectable.

Completed or quality-limited retrieval records and `QUALITY_GATE` actions are not forced into this pre-search contract. Their evidence and status are handled through their own records and checks.

## Rationale

A generic request to “find more data” does not say what result would change an assessment. Requiring outcomes and acceptance conditions before retrieval makes the next investigation step falsifiable, preserves inconclusive outcomes, and helps avoid searching for data that cannot answer the stated question. It does not rank observations, guarantee that a suitable source exists, or determine scientific validity automatically.

## Current T163 result

The open independent-surface-state follow-up selects one mechanism branch before retrieval and specifies expected, weakening, and inconclusive outcomes. It requires independent inputs, retained provider quality, suitable timing, and native spatial support relevant to the AOI. It explicitly does not test the optical class-count statement, the water-change explanation, or the SAR product-quality explanation. The search remains open; no new measurement or causal finding is introduced.

## Verification

The validator rejects open searches without a design, designs with missing outcomes or acceptance gates, unknown hypotheses, and overlap between declared targets and non-targets. The T163 assessment builder and web reader apply the same contract. See [validation](../validation/open-follow-up-test-design-contract-2026-11-08.md).
