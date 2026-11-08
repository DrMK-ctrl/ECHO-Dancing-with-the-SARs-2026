# Decision 0035: specify the surface-state evidence test before searching

**Status:** implemented as a case-specific evidence request
**Date:** 2026-11-08

## Context

The T163 assessment identified an open search for independent soil-moisture, vegetation, or in-situ evidence. That broad list did not specify what a candidate would need to measure, what outcomes could weaken a mechanism, when missing or unsuitable data should remain inconclusive, or which competing explanations the candidate could not test. Retrieval first and methodological choices later would risk fitting the interpretation to whichever product happened to be available.

## Decision

Attach a pre-search `test_design` to the open T163 independent-surface-state follow-up. Before retrieval, an analyst must choose one mechanism branch (soil-moisture change or vegetation-state change). The record states an expected observation, a result that would weaken only that branch, explicit conditions that leave it inconclusive, and five acceptance gates covering measurement semantics, independence from Sentinel-1, provider quality, acquisition timing, and native spatial support/valid coverage.

The design explicitly states that this selected surface-state observation does not test the water-change explanation or the SAR product-quality explanation. A candidate association can make one mechanism branch more plausible within scope, but cannot establish causation or clear the diagnostic SAR QA hold. The search remains `NOT_SEARCHED`; this test design is a protocol, not an observation or result.

## Implementation

`validate_follow_up_plan` validates the test-design object, targeted hypothesis, non-target hypotheses, required acceptance gates, falsification condition, and inconclusive condition. The case UI renders it under a collapsed **Pre-search test design** section in the relevant evidence-search card. Follow-ups without a declared design retain their existing representation. No score, probability, automatic ranking, or evidence assessment is generated.

## Verification

- Unit tests validate complete designs and reject missing predictions, unknown/non-target hypothesis references, incomplete gates, and misaligned target hypotheses.
- The T163 assessment was rebuilt from its retained source records and remains `CAUSAL_INTERPRETATION_UNRESOLVED`.
- The test-design panel was opened in Firefox on the active T163 investigation; the five acceptance gates and two explicit non-target hypotheses rendered.
- See [validation record](../validation/surface-state-test-design-2026-11-08.md).
