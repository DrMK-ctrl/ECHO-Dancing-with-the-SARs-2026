# Decision 0085: Start investigation drafts from a single GCOV observation

**Date:** 2026-11-09  
**Status:** Implemented and locally validated

## Context

The map can retrieve and display a bounded, real NISAR GCOV backscatter window with its acquisition metadata, provider QA, masks, and source provenance. The reusable analyst-authored investigation workflow previously started only from a pair analysis or a temporal series, leaving a single-observation preview disconnected from question framing and follow-up planning.

## Decision

Allow the user to start an unassessed investigation draft directly from the selected single-observation GCOV preview. Preserve the submitted preview record and checksum, verify its NISAR/ASF product identity, provider-QA linkage, and measurement dimensions against the declared bounded grid, and show the retained QA disposition in the evidence artifact.

Classify the source as `DESCRIPTIVE_NISAR_SINGLE_OBSERVATION`, a non-directional role. Require competing hypotheses and a falsifiable next-observation design as in other drafts. Keep every hypothesis `NOT_EVALUATED` and the follow-up `NOT_SEARCHED`; explicitly state that a single acquisition establishes no temporal change. No source is re-fetched during draft creation.

## Consequences and limits

- The geographic observation workspace can now lead into the same question, alternatives, evidence-gap, and next-observation workflow without requiring a temporal pair.
- A single GCOV backscatter observation cannot be recorded as directional support or contradiction for a physical hypothesis.
- Provider QA remains unchanged. The current P05023 example remains a `QA_HELD_DIAGNOSTIC_PREVIEW`; the draft does not promote it to an accepted result.
- The draft is analyst-authored and unverified. Its checksum establishes submitted-record integrity, not source authenticity, suitability, independence, or a scientific conclusion.

## Validation

See [single-observation investigation validation](../validation/single-observation-investigation-draft-2026-11-09.md).
