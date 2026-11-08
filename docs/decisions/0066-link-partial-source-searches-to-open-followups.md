# Decision 0066: link partial source searches to open follow-ups

**Status:** implemented
**Date:** 2026-11-08

## Context

An evidence follow-up can be an active search even after particular catalog routes have been screened and rejected. Previously, its availability state represented only an untouched search or a reviewed result. That hid useful search history, and treating the whole search as `NOT_SEARCHED` was imprecise.

## Decision

Add `SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE` for a follow-up whose screened routes produced no suitable observation while the broader search remains open. It remains on the `NEW_EVIDENCE_SEARCH` workstream and requires the same preregistered test design as an untouched search. Catalog availability records can be linked to that follow-up as evidence artifacts and opened in the source inspector. They do not count as measurement evidence or change a hypothesis disposition.

Case-bound availability records must identify the same case and the exact acquisition start times as the SAR pair before the builder links them. Their file hashes and record types are retained in the assessment manifest.

## T163 application

The H3 soil-moisture follow-up links two screened routes:

- NASA ECOSTRESS `ECO_L3G_SM` V002: CMR returned zero granules globally from April through June 2024. The product's 70 m layer is model-derived from GEOS-5 and ECOSTRESS predictors, not a direct 70 m soil-moisture measurement.
- International Soil Moisture Network: its 3,347-station inventory has no station within 100 km of the AOI. The nearest listed station is about 245.88 km away and its soil-moisture record ends in July 2014.

Neither screen tests H3. The open follow-up remains unresolved, and the diagnostic RTC-S1 measurement retains its provider QA hold.

## Verification

- Investigation and assessment tests verify the new open-search state, evidence links, exact-case association, and unchanged unresolved H3 disposition.
- Full suite: **326 passed**.
- Assessment rebuild retained all source hashes and passed the web assessment artifact validator.
- See [partial soil-moisture search linkage validation](../validation/partial-soil-moisture-search-linkage-2026-11-08.md).
