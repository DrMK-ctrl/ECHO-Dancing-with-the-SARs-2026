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
catalog-request construction. A subsequent Firefox pass then used the numeric
entry on a case with no selected area and submitted the same Beirut rectangle
`[35.48, 33.80, 35.60, 33.92]` to the live ASF catalog for 2026-10-01 through
2026-11-13 at PROVISIONAL maturity. The real response populated three timeline
records, with no metadata-compatible pair; the map center showed `35.5400° E,
33.8600° N`. IDs were
`NISAR_L2_PR_GCOV_032_151_D_071_2005_DHDH_A_20261010T162436_20261010T162511_P05023_N_F_J_001`,
`NISAR_L2_PR_GCOV_032_151_D_072_2005_DHDH_A_20261010T162510_20261010T162544_P05023_N_F_J_001`,
and
`NISAR_L2_PR_GCOV_032_172_A_019_2005_DHDH_A_20261012T025225_20261012T025300_P05023_N_F_J_001`.
The first product's existing checksummed bounded preview and provider-QA `FAIL`
are documented in the [Beirut real-measurement validation](arbitrary-aoi-catalog-bounds-2026-11-13.md);
the new pass did not reread QA or measurement pixels. This demonstrates the
numeric AOI-to-live-catalog-to-timeline path, not a temporal comparison or
scientific finding. The first controlled-payload test did not send a request;
the separate live query confirms provider behavior for this rectangle and date
range only.

The automated test suite also passed after the UI changes:
`.venv/bin/python -m pytest -q` — **498 passed in 35.91s**.
The full automated suite passed after this interface change:
`.venv/bin/python -m pytest -q` — **498 passed in 35.91s**.
