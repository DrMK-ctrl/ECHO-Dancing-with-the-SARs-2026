# Map-drawn area catalog search validation

**Date:** 2026-11-07

**Result:** Browser-to-ASF area discovery verified; SAR processing not performed

## Browser interaction

Using the local application in headless Firefox, the validation selected **Select Area**, dragged a WGS84 rectangle on the map, inspected the displayed bounds in the search dialog, and submitted a PROVISIONAL search from 2026-08-01 through 2026-11-07. The ASF response contained 33 catalog records and the interface identified a metadata candidate pair. The search remained local to the browser session; no pixels were downloaded.

A second run at a 500 CSS-pixel browser width completed the same drawing and search workflow. The document width was 488 pixels in a 500-pixel viewport, and the search returned 21 catalog records without horizontal overflow.

In a 1280-pixel browser run, all 28 returned footprint identifiers were present on the map, the metadata-pair observations received the before/after styles, and the other-results legend appeared. The post-search view is retained as a [browser screenshot](area-catalog-search-2026-11-07.png). Browser-drawn rectangles vary with the current view and viewport, so their result counts are interaction checks rather than a fixed catalog benchmark.

The rectangle was computed from the displayed map coordinates. The browser check verified the complete interaction path, not scientific suitability of any returned products. The selected candidate's provider QA was not retrieved as part of this check.

## Reproducible catalog query

A second live query used the exact WGS84 rectangle `(85.545, 28.295, 85.555, 28.305)`, dates 2026-08-01 through 2026-11-07, and PROVISIONAL maturity. ASF returned 15 records; ECHO's catalog matcher produced 9 metadata candidates. Full returned metadata, footprints, query parameters, source revision, and candidate-pair records are retained in [`kathmandu-aoi-catalog-query-2026-11-07.json`](../../data/research/kathmandu-aoi-catalog-query-2026-11-07.json).

The existing Nepal case pair appears among the returned temporal candidates and remains on its previously recorded provider QA hold. These catalog counts are not counts of validated comparisons, usable pairs, or detected changes. No QA summaries were retrieved and no raster arrays were processed for this query.

## Scientific boundary

ASF footprint intersection establishes catalog coverage metadata only. It does not establish that a product's valid pixels cover the AOI, that paired rasters align, or that any physical surface change occurred. Those checks remain separate gates before measurement.

The interface still shows the selected metadata pair in its timeline; it does not yet provide a selectable chronology of every returned acquisition or temporal persistence/recurrence analysis.
