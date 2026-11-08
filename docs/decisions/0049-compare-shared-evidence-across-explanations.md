# Compare shared evidence across explanations

**Date:** 2026-11-08
**Status:** Implemented; Firefox rendering and source-link interaction verified

## Context

The assessment displayed evidence relationships inside separate hypothesis cards. A source cited under several explanations therefore required reviewers to move between cards to compare how the same observation was used. That obscured cross-hypothesis tensions and could make reuse of a source look like multiple independent pieces of evidence.

## Decision

Derive a collapsible comparison from the active assessment's hypothesis evidence references. Include only source IDs cited under more than one hypothesis. For each shared source, show the source role and each hypothesis statement with its analyst-assigned relationship. Keep each source ID directly linked to the existing checksum-verified inspector.

The comparison does not infer that relationships contradict each other, calculate a score, combine evidence, or change any disposition. It states that repeated citation is not independent corroboration and that the relationships remain scoped to their hypotheses. Cases without shared citations do not show an empty comparison panel.

## Verification

- The full software suite passed: 295 tests.
- Headless Firefox rendered the two shared sources in T163: `NASA-OPERA-DSWX-HLS` and `SAR-RTC-S1-PAIR`.
- The panel showed their existing, distinct hypothesis relationships and opened the linked DSWx-HLS source record.
- Python compilation and `git diff --check` passed.

## Limits

The panel compares human-authored relationships from a case-specific assessment. It does not independently discover contradictions or validate either the source or interpretation. The T163 assessment remains diagnostic and causally unresolved.
