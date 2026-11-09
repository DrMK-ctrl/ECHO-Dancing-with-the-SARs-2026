# Decision 0103: Screen multiple candidate sources against one registered test

**Date:** 2026-11-09  
**Status:** Implemented and locally validated

## Context

An investigation draft could retain several candidate source records, but its registered follow-up allowed only one source to be screened. The first screen closed the control, so the analyst could not compare another candidate against the same pre-registered acceptance gates without starting another investigation round. This made it harder to inspect source fit and evidence gaps while keeping every candidate separate from hypothesis assessment.

## Decision

Allow an unassessed follow-up to retain an ordered screen record for each distinct staged, non-primary source, using the same registered gates for every candidate. Each screen retains its source ID and checksum, ordered gate results, reviewer declaration, review basis, limitations, timestamp, and checksum. The ordered source references must exactly match the ordered screening history. Existing single-screen drafts remain valid; `screening_review` remains an alias of the most recent screen, and old records without `screening_history` are read as a one-item history.

The follow-up summary is `ANALYST_SCREENED_CANDIDATE` if at least one screen records every gate as `MET`; it is `RETRIEVED_QUALITY_LIMITED` when all recorded screens have at least one `NOT_MET` or `UNKNOWN` gate. The interface displays each candidate's own gate outcomes and inspection limits.

## Scientific and workflow boundaries

- These are analyst-entered gate declarations, not automated QA, source authentication, source independence, or suitability findings.
- A candidate screen does not establish support or contradiction and does not change hypothesis states. A separate explicit evidence-to-hypothesis assessment remains required.
- A passing screen does not turn another failed candidate into a passing source; each candidate retains its own results and source checksum.
- Re-screening the same source is rejected. The draft's existing maximum of twelve staged sources also bounds the screen history.
- No priority, confidence, probability, or information-gain score is calculated.

## Validation

See [multi-candidate follow-up screening validation](../validation/multi-candidate-followup-screening-2026-11-09.md).
