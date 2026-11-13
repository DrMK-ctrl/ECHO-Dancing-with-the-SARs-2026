# Global map navigation: Firefox verification

**Date:** 2026-11-13  
**Application:** local ECHO workbench at `127.0.0.1:8766`  
**Browser:** Firefox headless through W3C WebDriver

## Interaction sequence

Starting from the default investigation view, Firefox exercised **World View**,
zoom-in, keyboard panning on the focused map region, and pointer drag panning.
The geographic grid labels changed after each navigation action. The world
view showed the full longitude and latitude extent; after zoom-in the grid
labels narrowed, and ArrowRight then shifted them east. A subsequent drag
shifted the displayed extent again. The page had no horizontal overflow at
1366 × 900.

The keyboard check focused the map's focusable SVG region and sent a real
WebDriver ArrowRight key. The initial attempt sent the key before explicitly
focusing the region and did not move the map; after focusing the map, the key
worked. This documents the tested focus requirement rather than claiming that
keyboard-only discovery or screen-reader behavior has been evaluated.

This pass verifies global extent, zoom, keyboard pan after map focus, and drag
pan in the browser. It does not validate map-tile availability or scientific
measurement alignment; those have separate checks.

## Arbitrary area selection

In a separate Firefox workbench session, the map was reset to World View and
the **Select Area** control was used with real WebDriver pointer drags. The
catalog dialog reported these two independently selected rectangles as WGS84
west, south, east, north bounds:

- `[-141.8040, -18.8389, -77.8692, 11.4891]`
- `[77.8693, -2.4454, 141.8040, 27.8826]`

Both bounds were finite, ordered, and within longitude/latitude limits. No
catalog request was submitted, so this verifies map-to-query-area interaction
and coordinate serialization only; it does not establish observation coverage
or successful measurement retrieval for either rectangle. The workbench was
also opened directly on the Iraq NISAR case, where the interface retained
`PROVIDER QA FAIL · DIAGNOSTIC PREVIEW ONLY` and the pair remained on QA hold.

## Arbitrary-area catalog-to-timeline path

The interactive workbench then submitted the Iraq rectangle
`[43.8, 32.5, 45.0, 33.5]` for 2026-10-01 through 2026-11-12 at
`PROVISIONAL` maturity. ASF returned 13 GCOV metadata records. Firefox rendered
13 acquisitions on the timeline and reported six metadata pair candidates;
the case status read `METADATA MATCH ONLY · PROVISIONAL`, and the map caption
identified ASF footprints. This confirms that a user-entered arbitrary AOI
reaches the provider catalog and returns to the timeline/map.

No provider QA was retrieved for those six candidates and no pair analysis was
run. Their metadata matches are not QA clearance or measured change. The
separate retained Iraq case assessment remains QA-held for its documented
products; catalog search does not alter that assessment.
