# Decision 0063: Record analyst screening of a planned follow-up source

**Date:** 2026-11-08  
**Status:** Implemented in exported investigation drafts; independent source validation remains open

## Context

Drafts could preregister a single-hypothesis observation and stage additional source records, but could not connect a staged source to the planned observation or preserve which acceptance gates it met, failed, or left unknown. That left a gap between an evidence search and an evidence relationship. Updating a hypothesis state directly from the follow-up would overstate what a manual screen establishes.

## Decision

Before the draft's initial hypothesis assessment, allow an analyst to screen one staged non-primary source against every acceptance gate in the pre-registered test. Record the source ID and checksum, ordered gate results (`MET`, `NOT_MET`, or `UNKNOWN`), review basis, limitations, reviewer state, timestamp, and a checksum of the screening record.

Derive `ANALYST_SCREENED_CANDIDATE` only when the analyst marks every gate `MET`; otherwise derive `RETRIEVED_QUALITY_LIMITED`. Preserve the source's own role, QA/status, and independence state. Keep the hypothesis `NOT_EVALUATED` until a separate explicit evidence-to-hypothesis assessment is recorded. Label the gate screen analyst-declared and unverified. Case-imported records must still revalidate against the active case at screening time.

## Consequences

- The planned observation can be traced to an exact staged source and a gate-by-gate screening record.
- Gate results are user declarations, not automated product QA or independent scientific validation.
- A candidate screen does not assign support, contradiction, confidence, or causation and does not upgrade the source record.
- The draft supports one screen record for its one preregistered next observation. Revisions or multiple source comparisons require a new draft or future versioned workflow.

## Verification

See [investigation follow-up-screen validation](../validation/investigation-followup-screen-2026-11-08.md).
