# Arbitrary AOI catalog search: browser verification

**Date:** 2026-11-13
**Application:** local interactive workbench at `127.0.0.1:8766`
**Browser:** Firefox headless, W3C WebDriver
**Scope:** map-drawn WGS84 area, editable catalog bounds, validation, and search handoff.

## Changes exercised

- Drawing a rectangle on the map creates editable west, south, east, and north
  WGS84 bounds in the ASF catalog dialog.
- Applying valid coordinates updates the map's area-center readout and disables
  the point-coordinate fields while area search is active.
- Invalid ordering and latitudes outside the WGS84 range are rejected with
  accessible field error states. Longitude and latitude limits, finite values,
  and the non-wrapping 180-degree longitude span are checked before use.
- Editing bounds and submitting without pressing **Apply area bounds** uses the
  values currently visible in the form. The submitted center and rectangle stay
  consistent.
- **Use point search** clears the selected area and re-enables point fields.
- A missing/unsupported catalog maturity now defaults to `PROVISIONAL` rather
  than leaving the selector blank.

## Browser results

Firefox exercised the complete map-draw → catalog dialog → edit → validate →
submit handoff at 1366×900 and 500×800. Both viewports produced map bounds,
rejected reversed longitude bounds and out-of-range latitude, submitted the
edited WGS84 rectangle, displayed its correct center, avoided horizontal page
overflow, and returned to point search when cleared. Point fields were disabled
while the rectangle was active; catalog maturity displayed `PROVISIONAL`.

The browser harness intercepted `fetch` at the page boundary and recorded the
catalog request payload, then returned a controlled error. **No ASF or NASA
catalog request was sent.** For the edited bounds `[51.2, 35.7, 51.28, 35.76]`,
the captured request contained those same bounds and center `(51.24, 35.73)`.

![Mobile catalog dialog with editable WGS84 bounds](assets/catalog-aoi-editor-mobile-2026-11-13.png)

## Verification limits

This verifies the browser interaction and request construction, not that every
provider accepts every rectangle, that catalog results cover the whole AOI, or
that any returned product passes provider QA. No measurements or scientific
findings were produced. Direct keyboard-only rectangle drawing and screen-reader
behavior remain outside this pass.
