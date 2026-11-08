# Partial soil-moisture source-search linkage — T163

**Date:** 2026-11-08

## Result

The T163 H3 follow-up now distinguishes an ongoing search from both an untouched search and a completed review. Its state is `SEARCH_IN_PROGRESS_NO_SUITABLE_SOURCE`; its workstream remains `NEW_EVIDENCE_SEARCH`. It links the retained ECOSTRESS and ISMN inventory records directly, and each record is available through the investigation source inspector.

The ECOSTRESS route had no cataloged granules globally during the relevant April–June 2024 interval. The ISMN inventory has no station within 100 km of the AOI; its nearest station is 245.88 km away and its listed soil-moisture series ends in 2014. These are source availability limits only. No soil-moisture measurement was retrieved, and H3 remains unresolved and not testable from retained measurements.

## Integration checks

- Availability records are rejected by the assessment builder if their case ID or either SAR acquisition start time does not match the exact T163 pair.
- The assessment records each source path, record type, role, and SHA-256; the web validator resolves all linked records.
- Firefox WebDriver opened the live T163 investigation, rendered `SEARCH IN PROGRESS NO SUITABLE SOURCE`, and exposed both route records as direct **INSPECT** buttons. Opening the ECOSTRESS record displayed its route disposition, artifact role, source status, path, and SHA-256.
- The state remains an open search and requires the same preregistered test design.
- Full suite: **326 passed**.

See [Decision 0066](../decisions/0066-link-partial-source-searches-to-open-followups.md), [ECOSTRESS screen](ecostress-soil-moisture-catalog-screen-T163-2026-11-08.md), and [ISMN screen](ismn-station-coverage-screen-T163-2026-11-08.md).
