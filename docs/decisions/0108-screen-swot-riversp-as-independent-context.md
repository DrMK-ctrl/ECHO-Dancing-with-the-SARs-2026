# Decision 0108: Screen SWOT RiverSP for independent hydrologic context

**Date:** 2026-11-09
**Status:** Screen completed; no quality-accepted corroboration

## Context

The T163 case has a real, but diagnostic, Sentinel-1-derived OPERA RTC-S1 pair. Its NASA optical, precipitation, and gauge context does not resolve the causal interpretation. NASA SWOT RiverSP Version D was a plausible independent measurement source for nearby river levels.

## Decision

Screened nine temporally nearby, spatially cataloged RiverSP reach granules against the case-window bounds and the NASA-defined `reach_q` values. Do not promote this route into directional hypothesis evidence or SAR validation: no `reach_q=0` reach was present within 50 km; nearby May 6 and May 27 observations were `reach_q=1` (suspect), and the June 5 nearby records were suspect, degraded, or bad. No acceptable shared reach pair was found.

Retain the retrieved source identities, checksums, quality counts, and limits as a research screen. Revisit only if the AOI or temporal question changes, a different scientifically justified distance scope is defined, or PO.DAAC provides corrected/new processing with improved quality.

## Consequences

- The source was retrieved and its format and reach geometries were inspected; this verifies data access, not measurement suitability for the T163 question.
- No water-level change metric was computed and no hypothesis relationship was added.
- The SAR provider-QA disposition and overall case assessment remain unchanged.
- The traceable screen is in [validation](../validation/swot-riversp-screen-T163-349925-2026-11-09.md) and its [structured record](../../data/research/swot-riversp-screen-T163-349925-2026-11-09.json).
