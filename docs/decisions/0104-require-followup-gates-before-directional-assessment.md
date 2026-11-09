# Decision 0104: Require registered follow-up gates before directional assessment

**Date:** 2026-11-09
**Status:** Implemented and locally validated

## Context

An analyst could screen a staged candidate against the registered next-observation gates, record a failed or unknown gate, and still assign that same candidate directional support or contradiction for the target hypothesis. The assessment form checked only the separately declared evidence fit. That left the planned test and the resulting relationship disconnected.

## Decision

For a staged user-supplied or case-imported source linked to the registered follow-up, directional assessment of that follow-up's target hypothesis requires a matching source-specific screen with every pre-registered gate marked `MET`. A missing screen, any `NOT_MET`, or any `UNKNOWN` blocks `SUPPORTS` and `CONTRADICTS`; non-directional relationships remain available. New assessment records retain both the staged evidence ID and the exact matching screen checksum.

An all-gates-met screen is still an analyst declaration. Directional assessment separately requires `SUITABLE_FOR_STATED_SCOPE`, substantive rationale, inspection basis, and limitations. The screen and assessment do not authenticate a source, establish independence, or validate a scientific claim. The backend enforces the rule both when recording and when validating an assessed draft; the UI disables unavailable directional choices, explains the requirement, shows the linked screen checksum with the relationship, and opens that exact screen from the relationship card.

New assessment records identify this rule in their method field. Earlier saved assessment records using the previous method remain readable under their original contract.

## Consequences

- The target test follows an inspectable sequence: stage a source, screen it against the registered gates, then record a separate analyst relationship if the declared gates pass.
- A failed candidate remains visible and can be recorded as non-distinguishing or interpretation-limiting, but cannot be used directionally for the target test.
- Other hypotheses are not treated as tested by this one-hypothesis follow-up design.
- QA-held or diagnostic primary SAR restrictions remain in force.
- Existing snapshots retain their original interpretation; the new screen-gate invariant applies to assessments created under the versioned gated method.

## Validation

See [follow-up gates before directional assessment validation](../validation/followup-gates-before-directional-assessment-2026-11-09.md).
