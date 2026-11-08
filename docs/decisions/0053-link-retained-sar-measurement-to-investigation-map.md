# Link retained diagnostic SAR measurement to the investigation map

**Status:** Implemented for case-linked OPERA RTC-S1 diagnostic records

## Decision

When a registered case assessment links a retained `ECHO_OPERA_RTC_S1_PAIR_ANALYSIS` record, opening the assessment also loads that record into the existing SAR raster map. The client verifies the artifact SHA-256 against the assessment manifest, validates dimensions, quantity, units, masks, geographic corners, and expected scene identifiers, then passes the original measurements to the existing raster and pixel-inspection path.

The evidence endpoint accepts the already validated registered `case_id` query parameter alongside the evidence identifier. The server continues to resolve the evidence through that case's manifest and registered evidence records; the case identifier is not used as a filesystem path.

The map switches to the retained measurement AOI, hides GCOV-only controls and the observation timeline, and labels the displayed quantity and source as Sentinel-1-derived OPERA RTC-S1. Returning from the view restores the ordinary case workspace. Product QA remains explicitly diagnostic when the retained record has no consolidated provider verdict.

## Rationale

The case assessment already described a real bounded SAR measurement, while direct case entry previously left the map on the unrelated catalog context. Rendering the linked artifact closes that gap without downloading again, recalculating values, or treating the record as accepted science. It makes the source-to-measurement-to-map connection inspectable using existing provenance and raster components.

## Boundaries

- This route supports a case-linked OPERA RTC-S1 record with the declared `signed_gamma0_log_ratio_db` quantity and matching source scene identifiers.
- It does not promote product QA, validate a physical event, or provide causal interpretation.
- It does not establish NISAR measurement support or a QA-cleared temporal comparison.
- Other product formats require their own validated measurement contracts and renderers where their semantics differ.
