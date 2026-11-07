# VALIDATED GCOV diagnostic window: 5 November P05036 scene

**Retrieved and reviewed:** 2026-11-07 UTC  
**Disposition:** QA-held diagnostic measurement read; zero pixels eligible for display  
**Temporal analysis:** Not performed

## Scene and provider evidence

The fresh global VALIDATED-GCOV query for 2026-10-30 through 2026-11-07 returned one scene, acquired on 2026-11-05 over path 11/frame 17. ECHO retrieved its ASF QA summary and report through Earthdata Login. The QA summary reports `FAIL` for the aggregate identification-group check; the coordinate-grid, calibration, four decimated backscatter, and no-exceptions checks report `PASS`. The PDF reports QA software 17.2.0, product specification 1.6.0, product version 1.0.20, and processing software 0.25.21. Catalog orbit, track, and frame agree with the report.

The report's `instrumentName=LSAR` and `listOfObservationModes=["(NOT SPECIFIED)"]` match rules in the pinned `nisarqa` 17.2.0 source cross-check. This is diagnostic context only; it neither attributes the provider's aggregate failure nor changes the ASF `FAIL` disposition.

## Bounded pixel read

ECHO read the real
`/science/LSAR/GCOV/grids/frequencyA/HHHH` linear gamma-zero dataset and its mask, number-of-looks, and input-data-exception layers for the WGS84 window `[96.70, 30.50, 96.71, 30.51]` (EPSG:32647; 113 rows × 98 columns). The request used 35,860,808 HTTPS range bytes. The complete response is retained in [`validated-gcov-diagnostic-preview-2026-11-07.json`](../../data/research/validated-gcov-diagnostic-preview-2026-11-07.json); a compact review record with source and array hashes is in [`validated-gcov-diagnostic-window-review-2026-11-07.json`](../../data/research/validated-gcov-diagnostic-window-review-2026-11-07.json).

Within the 10,648 selected AOI pixel centers, the GCOV subswath mask is 1 for 10,562 centers and 0 for 86. Every selected center has input-data-exception value `768`. The array is `uint16`; ECHO's current quality screen recognizes no meaning for `768` and therefore excludes all 10,648 centers. The response contains the measured values and their checksums, but its display-eligible count is zero. No backscatter pixels appear on the map for this window.

The publicly linked NASA SDS GCOV specification, Rev F version 1.5.0, documents this layer as UByte with values 0 (no anomaly) and 2 (qFSP-H1 sample slip). The product-specific QA report instead identifies product specification version 1.6.0. The public specification and product versions therefore do not match; ECHO does not infer what `768` means from the older document or from the passing decimated backscatter checks. This flag interpretation remains unresolved.

## Interpretation boundary and next evidence

This run confirms authenticated access to a recent, genuine NISAR measurement array through ECHO's bounded geographic reader. It does **not** yield a visible valid-pixel layer for this AOI, clear provider QA, establish product suitability, or measure temporal change. The existing Nepal sample remains the validated map demonstration for displaying eligible measurement pixels; this new sample establishes that the same generic reader reaches a current VALIDATED scene and reports an unresolved quality-code state without reclassifying it.

Before using nonzero P05036 exception values in a display or analysis, establish the 1.6.0 bit definitions from the applicable authoritative product specification or NASA/ASF processing guidance, and determine whether the reported QA failure relates to those fields. Keep current exclusion behavior until then. A temporal result still requires a compatible acquisition pair whose provider QA and pixel-level gates pass.

## Sources

- ASF, [NISAR VALIDATED known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- NASA SDS, [GCOV Product Specification JPL D-102274 Rev F, version 1.5.0](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf).
- ISCE Framework, [`nisarqa` v17.2.0 identification checks](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py).
- ISCE Framework, [`isce3` GCOV dtype/attribute issue #216](https://github.com/isce-framework/isce3/issues/216). This documents related GCOV schema/attribute discrepancies, but is not product-specific evidence about this scene's exception code.
