# Shared evidence across investigation hypotheses

**Date:** 2026-11-08
**Result:** Shared citations and their existing relationships are inspectable in the T163 assessment

## Procedure

Opened the T163 NASA optical context and linked assessment in Firefox headless, then expanded **EVIDENCE ACROSS EXPLANATIONS**. The panel showed two evidence records cited under multiple hypotheses:

- `NASA-OPERA-DSWX-HLS`: `SUPPORTS` the optical-class-count explanation and `LIMITS_INTERPRETATION` for the claim that water change explains the SAR response.
- `SAR-RTC-S1-PAIR`: `DOES_NOT_DISTINGUISH` the water explanation and `LIMITS_INTERPRETATION` for the product-quality explanation.

Clicking a shared evidence ID opened the corresponding DSWx-HLS source record through the existing local evidence inspector. The displayed relationship text matched the retained assessment. No case record, relationship, QA disposition, or result was changed.

The full Python suite passed (295 tests), Python bytecode compilation passed, and `git diff --check` passed.

## Limits

This is a view of relationships already assigned by the analyst, not an automated contradiction detector. Repeated citations do not establish independent corroboration. The underlying Sentinel-1-derived measurement remains diagnostic; this comparison does not produce a causal finding or NISAR result.

## Within-hypothesis dependency disclosure

The reasoning renderer now also compares artifacts cited by the same hypothesis. It surfaces direct shared-observation lineage, a derivation between cited records, and common recorded derivation inputs, with links to inspect both source records. This remains display-only and does not change analyst relationship labels or deterministic dispositions. Absence of a recorded dependency is explicitly not presented as proof of source independence.

Headless Firefox on the active T024 assessment showed the warning linking `SAR-RTC-S1-PAIR` and `NASA-OPERA-RTC-S1-TEMPORAL-SERIES`, with the text that their relationships are not independent corroboration. A rendered fixture exercised both the cited-source/derived-record and common-input paths. This validates interface behavior against explicit lineage metadata; it does not detect source overlap missing from the record or scientifically determine independence.
