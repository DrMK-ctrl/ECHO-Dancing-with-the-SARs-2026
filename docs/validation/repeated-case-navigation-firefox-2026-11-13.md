# Repeated case navigation — Firefox verification

**Date:** 2026-11-13  
**Application:** local interactive workbench at `127.0.0.1:8766`  
**Browser:** Firefox 158.0.1, headless, through W3C WebDriver

## Procedure

In one browser session, the case selector visited all six registered cases in
registry order, then in reverse order, then repeated the first two selections
(14 actual page transitions). NASA basemap image requests were disabled to keep
this navigation check independent of external tile latency. After each page
load, the check compared the route query and selected case value, and inspected
the visible case heading, map SVG, initial document scroll position, and
visible page text for common server or JavaScript error signatures.

## Result

- All six case IDs were reached through the user-facing selector.
- All 14 transitions settled on the requested route and selected case.
- Every case rendered a nonzero-width map SVG and a visible heading.
- Every page remained at `window.scrollY = 0` after startup.
- No inspected page contained an `Internal Server Error`, `Traceback`, or
  `Uncaught` error signature.
- Repeated navigation did not retain the prior case ID in the selector or
  prevent later case selection.

This verifies repeated client-side case selection and initial rendering in the
local interactive workbench. It is not a full browser-console audit, does not
verify external basemap availability, and does not alter any case's scientific
status. NISAR observations remain provider-QA held; OPERA remains diagnostic.
