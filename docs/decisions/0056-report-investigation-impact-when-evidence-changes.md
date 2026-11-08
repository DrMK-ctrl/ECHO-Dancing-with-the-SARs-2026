# Report investigation impact when linked evidence changes

**Date:** 2026-11-08
**Status:** Implemented for manifest-linked evidence records

## Decision

When a case assessment fails because a linked source record is missing, unreadable, changed, or no longer matches its manifest identity, keep the assessment unavailable and return a diagnostic impact record. Include the assessment checksum, source integrity state and expected/observed hashes where available, derived records that depend on the changed source, and linked hypotheses and follow-up plans. Render that report in the investigation dialog so the analyst can identify what requires reassessment.

## Rationale

Rejecting a stale assessment protects the evidence boundary, but a generic validation error does not show the analyst which conclusions or planned tests depended on the affected source. The impact report makes those dependencies actionable while leaving all assessments and source relationships unchanged.

## Verification and limits

- A web integration test changes one linked source record and verifies that the endpoint returns HTTP 409, not the assessment; the report identifies a derived record, its dependent hypothesis, and a dependent follow-up.
- The full Python suite passes, and headless Firefox rendered the warning dialog with escaped untrusted text, the affected hypothesis, and the linked follow-up.
- The report is diagnostic. It does not restore the expected source, rebuild the assessment, or decide whether a changed source is scientifically unreliable. It currently traces manifest-linked evidence records and their declared derivations; nested assets referenced inside some source records still rely on the existing validation error path and do not yet receive a separate dependency impact entry.
