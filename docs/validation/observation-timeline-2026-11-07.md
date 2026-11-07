# Selectable catalog chronology validation

**Date:** 2026-11-07

**Result:** Catalog navigation and source inspection verified; no SAR pixel processing performed

## Browser checks

Used the local read-only application with the six-record Rasuwā/Bhote Koshi catalog fixture in headless Firefox. The rendered timeline contained all six fixture records in nondecreasing acquisition-time order, with five interval indicators; equal-time records were labeled `same time`. The catalog-matched before/after records remained separately identified as pair members.

Selecting an unpaired record through the timeline updated the selected-card state, the observation details and the highlighted map polygon. The selected scene ID appeared in the source-record inspector. Clicking a different map footprint selected its matching timeline record and updated the detail panel. The map caption reported all six plotted footprints for this fixture.

At a 500 CSS-pixel browser width, the document remained 488 pixels wide while the chronology itself scrolled horizontally inside its panel. At 1280 pixels, the timeline heading label and explanatory note occupied separate non-overlapping regions. The inspected desktop state is retained as a [browser screenshot](observation-timeline-2026-11-07.png).

A temporary copy of the fixture with one malformed acquisition timestamp confirmed that the affected record remains visible and selectable, displays `TIME UNKNOWN`, and does not prevent details for its source record from rendering. The temporary altered fixture was kept outside the repository and is not scientific evidence.

## Limits

The timeline enumerates records returned in the active catalog response. It does not discover missing acquisitions beyond that query or result cap. Adjacent timestamps are catalog acquisition times, not proof of repeat-pass comparability. Footprints express ASF catalog geometry only. The fixture contains metadata only; this validation did not authenticate a provider QA report, download raster data, check AOI pixel coverage, compare grids, compute a change measurement, or validate an event interpretation. Existing QA status and scientific gates were not altered by this interface change.
