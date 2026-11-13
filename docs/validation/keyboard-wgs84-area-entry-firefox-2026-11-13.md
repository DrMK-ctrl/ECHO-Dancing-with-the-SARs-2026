# Keyboard-accessible WGS84 area entry — Firefox validation

**Date:** 2026-11-13  
**Application:** local interactive workbench at `127.0.0.1:8766`  
**Browser:** Firefox headless with W3C WebDriver

## Interaction

On the Istanbul case, which has no saved area rectangle, the catalog dialog now
offers **Enter WGS84 area bounds** as an alternative to drawing on the map. The
control opens four labeled west/south/east/north fields and moves focus to the
west field. WebDriver keyboard entry confirmed a latitude of `91` is rejected;
the offending field receives `aria-invalid="true"` and the live status explains
the WGS84 limits.

The valid rectangle `[35, 33, 36, 34]` was submitted from the dialog without
pressing **Apply area bounds** first. A page-local `fetch` interceptor captured
the intended request and returned a controlled 502 response, so no ASF or NASA
request was sent. The captured payload contained those exact bounds, center
`(35.5, 33.5)`, and PROVISIONAL maturity. The map readout moved to
`35.5000° E, 33.5000° N`.

An incomplete entry was closed and reopened. The unsaved values cleared and the
area-entry control returned. Clearing a selected area returned keyboard focus
to that control and re-enabled the point-coordinate fields. At a 500 × 800
Firefox window, the dialog fit a 456-pixel width within the 488-pixel document
viewport, exposed all four fields, and had no horizontal page overflow.

## Limits

This verifies keyboard-accessible numeric AOI entry, input validation, and
catalog-request construction. The controlled error response means the test did
not verify ASF's response to these bounds, acquisition coverage, provider QA,
or measurement retrieval. Those remain separate scientific and service checks.
The full automated suite passed after this interface change:
`.venv/bin/python -m pytest -q` — **498 passed in 35.91s**.
