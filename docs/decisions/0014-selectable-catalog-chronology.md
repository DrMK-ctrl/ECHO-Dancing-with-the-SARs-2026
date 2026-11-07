# Decision 0014: make returned SAR catalog records selectable in time order

**Date:** 2026-11-07

**Status:** Implemented for records returned by the current catalog query

## Context

The map and evidence panel represented a screened before/after metadata pair. ASF catalog searches can return additional observations, but users could not select those records to inspect their metadata and footprints. The pair remains a catalog candidate until product QA, grid compatibility, and valid-pixel checks pass.

## Decision

Show every record present in the current catalog response in acquisition-time order. Display the elapsed time between adjacent timestamps, including an explicit `same time` label for records with equal acquisition times. Mark the current metadata-pair members without making other records part of that pair.

Selecting a timeline record updates its observation metadata, QA availability, sequence position, contextual basemap date, and highlighted map footprint. Clicking a plotted footprint selects the same record and brings its timeline card into view. The existing source-record inspector uses the selected catalog feature.

The map continues to limit ordinary footprint rendering to the first 60 catalog records for legibility, while always adding the selected record and screened-pair members. The returned catalog response is the scope of this chronology; it is not a claim that all acquisitions for the location have been discovered.

## Scientific boundary

This is catalog navigation and provenance inspection. It does not retrieve or compare raster pixels, establish valid AOI coverage, validate temporal recurrence, or identify a physical event. Pairing remains metadata-only and existing product QA holds remain visible. Equal-time product records are shown separately and explicitly marked as simultaneous.

## Validation

See [`observation-timeline-2026-11-07.md`](../validation/observation-timeline-2026-11-07.md) for browser interaction and responsive-layout evidence.
