# Decision 0090: link quality-limited HLS vegetation evidence

**Date:** 2026-11-09
**Status:** Implemented

## Context

The T024 investigation had an open vegetation-state follow-up (H4). Exact-date NASA HLS searches found no products on either OPERA RTC-S1 acquisition date. A bounded ±3-day candidate screen found an HLS L30 pair on May 8 and June 1, 2024, and HLS S30 pairs on May 8/13 and June 2/7. Product selection was based on acquisition timing before inspecting pixel values: the closest HLS S30 dates to the SAR acquisitions were May 13 and June 2; the HLS L30 dates were the only candidates for their product/date windows.

## Decision

Retrieve bounded L30 and S30 red, near-infrared, and Fmask subsets for the selected candidates. Use the existing strict clear-land mask and exact native-grid checks. Compute a spatial association only when common clear-land pixels exist. Link the L30 screen and derived native-grid association to the active case assessment. Keep both records as complementary NASA/USGS optical observations; they do not validate the Sentinel-1-derived SAR measurement.

The L30 screen has 265 common clear-land pixels (23.0% of the 1,152 AOI centers). Its descriptive area-weighted NDVI-change/SAR-response association has 312, 265, and 218 SAR cells at the 25%, 50%, and 75% optical-area cutoffs, with r = −0.2499, −0.2745, and −0.2717, respectively. No inferential statistics are computed. H4 remains `UNRESOLVED`, with the relationship `DOES_NOT_DISTINGUISH` and testability `DESCRIPTIVE_ASSOCIATION_ONLY`. Cutoff sensitivity is linked and displayed per [Decision 0091](0091-validate-hls-association-cutoff-sensitivity.md).

The S30 May 13 scene has Fmask value 66 across all 1,152 AOI centers; the cloud bit is set throughout, leaving zero paired clear-land pixels. No NDVI difference or spatial association is computed for this pair. It remains a quality-limited screen, not evidence against vegetation change.

## Limits

The L30 pair is from Landsat 8 and Landsat 9 and is separated from the corresponding SAR acquisitions by about 67.5 hours. The retained common clear-land area is sparse and spatially dependent. The association is descriptive and may not distinguish H4; it neither establishes causation nor clears OPERA provider QA. HLS L30 and S30 results are not treated as independent corroboration of one another.

## Validation

See [T024 HLS vegetation investigation validation](../validation/t024-hls-vegetation-investigation-2026-11-09.md).
