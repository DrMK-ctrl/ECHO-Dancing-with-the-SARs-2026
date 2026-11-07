# VALIDATED GCOV diagnostic window: 5 November P05036 scene

**Retrieved and reviewed:** 2026-11-07 UTC  
**Disposition:** QA-held diagnostic measurement read; product mask semantics resolved and 10,562 AOI pixels displayable
**Temporal analysis:** Not performed

## Scene and provider evidence

The fresh global VALIDATED-GCOV query for 2026-10-30 through 2026-11-07 returned one scene, acquired on 2026-11-05 over path 11/frame 17. ECHO retrieved its ASF QA summary and report through Earthdata Login. The QA summary reports `FAIL` for the aggregate identification-group check; the coordinate-grid, calibration, four decimated backscatter, and no-exceptions checks report `PASS`. The PDF reports QA software 17.2.0, product specification 1.6.0, product version 1.0.20, and processing software 0.25.21. Catalog orbit, track, and frame agree with the report.

The report's `instrumentName=LSAR` and `listOfObservationModes=["(NOT SPECIFIED)"]` match rules in the pinned `nisarqa` 17.2.0 source cross-check. This is diagnostic context only; it neither attributes the provider's aggregate failure nor changes the ASF `FAIL` disposition.

## Bounded pixel read

ECHO read the real
`/science/LSAR/GCOV/grids/frequencyA/HHHH` linear gamma-zero dataset and its mask, number-of-looks, and input-data-exception layers for the WGS84 window `[96.70, 30.50, 96.71, 30.51]` (EPSG:32647; 113 rows × 98 columns). The request used 35,860,808 HTTPS range bytes. The complete response is retained in [`validated-gcov-diagnostic-preview-2026-11-07.json`](../../data/research/validated-gcov-diagnostic-preview-2026-11-07.json); a compact review record with source and array hashes is in [`validated-gcov-diagnostic-window-review-2026-11-07.json`](../../data/research/validated-gcov-diagnostic-window-review-2026-11-07.json).

Within the 10,648 selected AOI pixel centers, the GCOV subswath mask is 1 for 10,562 centers and 0 for 86. Every selected center has input-data-exception value `768`. The original read record reflects ECHO's then-current behavior: it did not recognize `768`, so it excluded all centers and displayed no pixels. That record remains in the repository as an accurate account of the first review.

## Product attribute review and diagnostic reevaluation

An authenticated bounded HDF5 metadata read of the same product's `inputDataExceptionMask` dataset resolved the value. Its product-level `description` says the layer is a bitwise OR of exception codes and polarization-validity bits: exception code 0 means no anomaly, code 2 means an L-SAR qFSP-H1 sample slip, and focused-data bits include `256:HH` and `512:HV` (with corresponding bits for other polarizations). The product reports dtype `uint16` and fill value `65535`. The `768` values equal `256 | 512`; for the selected `HHHH` measurement, bit 256 is set and the low exception bits are zero. This is per-product metadata evidence, not an inference from the older Rev F document.

The preview reader now captures the quality-layer attributes and decodes the documented bitfield by selected polarization. Its bounded reevaluation retained the original QA summary `FAIL` and `QA_HELD_DIAGNOSTIC_PREVIEW` disposition, while displaying the real HHHH gamma-zero measurements for the 10,562 centers with GCOV mask 1. The 86 mask-0 centers remain excluded. No exception, unfocused, or unknown codes were present in the selected AOI. The updated source values, quality attributes, hashes, AOI coordinates, and QA evidence are preserved in [`validated-gcov-diagnostic-preview-reevaluation-2026-11-07.json`](../../data/research/validated-gcov-diagnostic-preview-reevaluation-2026-11-07.json).

This resolves why the first preview showed no pixels. It does not resolve the provider's aggregate identification-group failure, clear QA, or make this single observation acceptable for temporal analysis. The published ASF guide still links Rev F version 1.5.0; ISCE3 release notes independently document a recent writer update for the UInt16 `inputDataExceptionMask` layer. Neither source changes the exact product QA disposition.

## Interpretation boundary and next evidence

This run confirms authenticated access to a recent, genuine NISAR measurement array through ECHO's bounded geographic reader and map renderer. It yields a visible, quality-masked single-scene layer strictly as a QA-held diagnostic. It does **not** clear provider QA, establish product suitability, or measure temporal change. The original zero-pixel result and the revised product-attribute interpretation are both retained.

Before using these data in an accepted temporal analysis, obtain a product pair that passes provider QA, then apply the product-attribute decoder and the existing compatibility, grid, and pixel-quality gates. The `inputDataExceptionMask` decoding alone is not a QA disposition.

## Sources

- ASF, [NISAR VALIDATED known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- NASA SDS, [GCOV Product Specification JPL D-102274 Rev F, version 1.5.0](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf).
- ISCE Framework, [`nisarqa` v17.2.0 identification checks](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py).
- ISCE Framework, [`isce3` GCOV dtype/attribute issue #216](https://github.com/isce-framework/isce3/issues/216). This documents related GCOV schema/attribute discrepancies, but is not product-specific evidence about this scene's exception code.
- ISCE Framework, [`isce3` release history](https://github.com/isce-framework/isce3/releases), which records the GCOV/GSLC writer update to geocode the UInt16 `inputDataExceptionMask` layer. Product-level HDF5 attributes, not the release note, provide the flag meanings used by ECHO.
