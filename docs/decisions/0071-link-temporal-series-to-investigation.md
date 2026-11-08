# Link the T024 temporal series as shared, non-distinguishing evidence

**Status:** Accepted
**Date:** 2026-11-08

## Context

T024 now has a reproducible three-acquisition OPERA RTC-S1 VV diagnostic series on a fixed all-date pixel support. The first two acquisitions are exactly the observations already used by the primary SAR pair. Treating the new series as independent corroboration would double-count those inputs, while leaving it outside the investigation would separate a real temporal measurement from the hypothesis workflow.

## Decision

Link the series to the water-change hypothesis as `DOES_NOT_DISTINGUISH`. Record its relation to the pair as shared source observations, not as evidence derived from the pair. Retain the water hypothesis and overall causal assessment as unresolved. Show the series timeline, interval summaries, support count, QA state, and provenance inspector in the T024 investigation view.

The assessment builder and runtime loader verify source scene identity, chronological timestamps, compatible product metadata and exact grid, common support, adjacent per-pixel differences, and reproduced summary statistics. The case manifest points to a new versioned assessment; the previous assessment remains retained.

## Consequences and limits

The additional timeline is descriptive evidence about the measured radar response across acquisitions. It does not supply an independent water measurement, establish a pre-event baseline, resolve the provider QA state, or identify a physical cause. No QA gate or scientific disposition is promoted by this integration.
