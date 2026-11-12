# Investigation case switching: Firefox verification

**Date:** 2026-11-13  
**Application:** local ECHO workbench at `127.0.0.1:8766`  
**Browser:** Firefox headless through W3C WebDriver

## Case sequence

Changed the investigation selector in one browser session through Iraq NISAR,
Rasuwa/Nepal, Istanbul, and the Rio Grande do Sul diagnostic case. For each
selection, the page reloaded the case route and rendered its case title, status,
and map coordinate grid. The case geography and QA labels changed with each
selection, and the map view returned to the selected case's own center rather
than retaining the previous case's location. The Brazil case correctly
exposed its case investigation button; QA-held NISAR cases did not expose that
validated-assessment control.

NASA basemap requests were disabled during this check so the case-switch test
covered the local geographic rendering independently of variable tile-service
latency. This verifies case selection and geographic state reset in Firefox;
it does not establish data availability or scientific suitability for the
selected cases.
