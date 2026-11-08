# Open evidence records from investigation links

**Date:** 2026-11-08
**Status:** Implemented; Firefox source-link interaction verified

## Context

Hypothesis evidence relationships and the assessment's dependency list displayed source identifiers as text. A reviewer had to use the general assessment record or know a separate inspector control to examine the linked artifact, breaking the direct path from an interpretation to its supporting or limiting record.

## Decision

Render linked evidence identifiers as buttons in both hypothesis relationship lists and the evidence-dependency list. Activating a button requests that exact evidence ID through ECHO's existing read-only evidence endpoint, which serves only artifacts registered in the assessment and verifies the source checksum before returning the record.

The interaction uses evidence identifiers already present in the assessment schema and does not add case-specific lookup logic. The inspector continues to show the source artifact; this interaction does not alter its relationship, QA state, or the assessment disposition.

## Verification

- Firefox opened the T163 assessment and rendered 16 direct source links.
- Clicking a hypothesis citation opened its linked `ECHO_DSWX_HLS_AOI_CONTEXT_COMPARISON` record.
- Clicking a dependency entry opened its linked `ECHO_OPERA_RTC_S1_PAIR_ANALYSIS` record.
- The Python test suite passed (295 tests); Python compilation and `git diff --check` passed.

## Limits

The linked record can show a source, its retained provenance, and declared dependencies; it does not independently validate the scientific interpretation assigned to that evidence. The surrounding assessment remains case-specific and unresolved.
