# Decision 0088: distinguish access-required evidence searches

**Date:** 2026-11-09
**Status:** Implemented

## Context

Follow-up states distinguished unsearched, searched, candidate, provider-response, and reviewed outcomes, but could not represent an evidence route that may contain relevant data and requires provider authorization before retrieval. Treating it as `NOT_SEARCHED` hides the dependency; treating it as no suitable source would falsely imply a completed search.

## Decision

Add `ACCESS_REQUIRED` as an open evidence-search availability state. It requires the same falsifiable, hypothesis-specific test design as other open searches and renders in the existing open-search section. Record the provider approval route in a source-linked access screen; do not store credentials, user identifiers, or requested access as though approval had occurred.

For T163, use this state for the primary ANA/SGB Guaíba gauge series. Keep the emergency gauge `87444000` distinct from the corrected series `87450020`. Describe the gauge as nearby temporal context that cannot establish AOI water extent or validate SAR change. Keep the causal interpretation unresolved.

## Consequences and limits

- The user can see the actual access dependency and the next action without ECHO implying the archive is absent.
- `ACCESS_REQUIRED` remains an evidence-search workstream; it is neither a quality pass nor a scientific suitability assessment.
- An imported access-screen record with role `PRIMARY_GAUGE_SERIES_ACCESS_METADATA_ONLY` remains non-directional and cannot be submitted as the observation screened against measurement acceptance gates. The draft shows an explicit access-only notice, and the API explains that no observation was retrieved. These safeguards remain enforced when other screenable sources are present in the same draft.
- The ANA authorization request requires personal identifiers and must be submitted by the user; ECHO records the published procedure but does not send a request or collect those identifiers.
- Retrieved gauge readings, if later authorized, will require their own source, timestamp, unit, quality, and datum review.

## Validation

See [Guaíba primary-series access-gate validation](../validation/ana-guaiba-primary-series-access-gate-2026-11-09.md).
