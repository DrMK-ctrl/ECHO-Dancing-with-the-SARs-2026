# Decision 0013: connect map-drawn areas to ASF catalog discovery

**Date:** 2026-11-07

**Status:** Implemented for WGS84 rectangles; catalog metadata only

## Context

The local map supported point-based catalog searches, while geographic AOI selection existed only in the bounded GCOV reader API. Users could not discover observations for the area they had drawn on the map.

## Decision

Allow users to select a rectangular WGS84 AOI by dragging over the current map extent. Carry the bounds through the local web API and issue an ASF GCOV catalog search using the corresponding WKT polygon intersection. Preserve point search, query dates and maturity, the 250-result limit, and the existing metadata-only behavior. Store the bounds and center in the returned catalog query record.

Render the selected rectangle and its center, summarize the selected bounds before submission, and keep the result labelled as catalog coverage. A returned metadata-compatible pair remains a candidate only; this path does not retrieve radar pixels, inspect product QA, perform geographic window reads, or produce a measurement.

## Validation

- Unit and web tests validate WGS84 bounds, WKT construction, API propagation, and metadata-only response semantics.
- A headless Firefox interaction drew a map rectangle, displayed the bounds in the search dialog, submitted the ASF query, and rendered 33 returned records plus a metadata candidate pair.
- A 1280-pixel browser run confirmed all 28 returned footprint IDs were plotted, with the candidate pair highlighted; a 500-pixel run completed without horizontal overflow.
- A separately retained live Kathmandu AOI query returned 15 records and 9 metadata candidates. Its exact query and ASF responses are in [`kathmandu-aoi-catalog-query-2026-11-07.json`](../../data/research/kathmandu-aoi-catalog-query-2026-11-07.json).
- These checks demonstrate interface and catalog integration only. No product QA was retrieved for these query results and no radar measurement was made.

## Limits

Only rectangles that do not cross the antimeridian are supported. Search results are capped at 250 and are not exhaustive when the cap is reached. The selection is a catalog intersection query; it does not imply full product coverage or valid measurement pixels within the AOI. Polygon drawing, direct pixel retrieval from the interface, pixel-layer rendering, and a selectable full-observation timeline are not implemented.
