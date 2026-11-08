# Retained SAR measurement map validation

**Date:** 2026-11-08
**Result:** Passed linked-record, browser display, and workspace-return checks

## Scope

Validated that opening the registered T163 case assessment retrieves and displays the retained OPERA RTC-S1 measurement record on the interactive map, without recalculation or a new provider request.

## Evidence and behavior

- The client fetched `SAR-RTC-S1-PAIR` through the case-scoped evidence endpoint and verified the record checksum against the assessment artifact manifest before parsing it.
- Record validation required the expected record type, diagnostic status, signed gamma-zero log-ratio quantity and dB units, paired source scene IDs matching the assessment, consistent value/mask/corner dimensions, and bounded WGS84 coordinates.
- Headless Firefox rendered the retained grid in the existing map raster layer. The retained measurement AOI and measurement-center labels replaced the catalog search labels; GCOV-only backscatter controls were hidden.
- The map warning stated that the OPERA RTC-S1 comparison was diagnostic, product QA metadata had no consolidated verdict, and the result was not validated. The attribution identified Sentinel-1-derived OPERA RTC-S1, VV log-ratio dB, and NASA GIBS as context.
- Clicking the raster retained the existing per-pixel measurement readout behavior.
- Clearing the retained view removed the raster and restored the catalog workspace controls and timeline.
- Screenshot: [retained diagnostic measurement on map](retained-sar-measurement-map-2026-11-08.png).

## Verification

- Full Python suite: **298 passed**.
- Browser runtime entry, raster display, diagnostic labels, and return-to-workspace checks: **passed**.
- The case-scoped evidence integration test verifies the returned T024 artifact checksum and its scene IDs against the corresponding assessment.

## Limits

This verifies integration and display of retained diagnostic OPERA RTC-S1 evidence. The underlying pair has no consolidated provider QA verdict and remains diagnostic; this does not validate a flood boundary, event, physical cause, NISAR result, or general compatibility with other SAR product types. Browser checks used one desktop viewport and the local registered cases.
