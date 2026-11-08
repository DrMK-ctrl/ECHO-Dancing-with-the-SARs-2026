# Start investigation drafts from retained temporal series

**Status:** Accepted  
**Date:** 2026-11-08

## Context

ECHO displayed the retained three-acquisition OPERA RTC-S1 series and linked it to the T024 assessment, but the analyst-authored draft workflow only accepted a two-date SAR pair as its primary source. That split the temporal view from the reusable investigation-planning workflow.

## Decision

Allow a structurally valid `ECHO_OPERA_RTC_S1_TEMPORAL_SERIES_ANALYSIS` record to start an unassessed investigation draft. Require its explicit diagnostic status, ASF/OPERA identity, per-observation QA links, ordered unique acquisition IDs, adjacent interval links, and array dimensions consistent with the declared bounded grid.

Keep the new source role non-directional, as with the diagnostic RTC-S1 pair. It may be retained and discussed in a draft, but it cannot be entered as `SUPPORTS` or `CONTRADICTS`. Each draft remains analyst-authored and unverified; its source JSON is checksummed as submitted.

## Consequences and limits

The T024 series can now enter the same hypothesis and next-observation planning flow as a pair. This does not promote the provider QA state, independently re-fetch the source during draft creation, validate a hypothesis, or make the series NISAR data. The series' shared observations remain dependent evidence, not independent corroboration.
