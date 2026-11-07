# Decision 0016: selectable temporal pair candidates

**Date:** 2026-11-07

**Status:** Implemented for ASF catalog responses

## Context

The observation timeline showed every acquisition returned by the active query, but the map and evidence workspace always opened the first metadata-compatible pair. That hid alternative temporal baselines when a query returned several candidate pairs.

## Decision

Add a comparison selector populated only by `metadata_candidate_pairs` produced by ECHO's existing catalog screen. Each option identifies the acquisition dates, elapsed interval, path, and frame. Changing the selection updates the highlighted pair, map, timeline roles, and source details. A retained case review continues to use its explicitly reviewed pair.

Do not create arbitrary pairs in the browser or describe a selected candidate as analyzed. The metadata screen still requires distinct known orbits, nonoverlapping acquisition intervals, compatible catalog fields, and intersecting footprints. Product QA, exact pixel-grid alignment, common valid coverage, measurement, and physical interpretation remain separate gates.

## Validation and limits

Firefox browser validation with the six-record Istanbul catalog fixture exposed three selector options. Selecting the second option changed the displayed dates to 2026-10-07 and 2026-10-19, updated the selected scene roles, and retained the explicit metadata-candidate notice. At a 500 CSS-pixel viewport, document width was 488 pixels and the timeline remained the horizontally scrollable region. See [`comparison-candidate-selector-2026-11-07.md`](../validation/comparison-candidate-selector-2026-11-07.md).

The fixture contains catalog metadata only. This change does not select an event date or rank pairs by event relevance, discover acquisitions beyond the query, fetch pixels, pass QA, compare observations, or establish temporal persistence or recurrence.
