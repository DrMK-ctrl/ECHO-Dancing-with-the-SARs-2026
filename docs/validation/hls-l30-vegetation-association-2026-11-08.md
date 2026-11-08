# HLS L30 vegetation context and RTC-S1 association validation

**Date:** 2026-11-08
**Disposition:** Bounded real observations retrieved and reproducibly linked; descriptive only.

## What was validated

- CMR returned exact HLS L30 granules for the T163 AOI and requested dates. Earthdata-authenticated reads retrieved bounded COG windows for red (B04), near-infrared (B05), and Fmask. Redirected signed URLs were kept in memory and are not written to the repository.
- The screen records provider and product identity, collection, granule and CMR identifiers, acquisition and provider timestamps, source asset references, CRS, native grid transform/window, Fmask counts, retrieval method, software versions, pixel-subset sizes, and SHA-256 hashes.
- NDVI was computed from scaled surface reflectance on common clear, non-water land support. The 1,152 AOI pixel centers contain 762 valid before pixels, 375 valid after pixels, and 265 common valid pixels (23.003% of AOI-center support). Median NDVI moved from 0.3364 to 0.4172; median paired change is +0.0746, with q10/q90 of −0.0262/+0.2115.
- The association script verifies source-record and bounded-asset hashes, then intersects native HLS pixel polygons with RTC-S1 cell polygons in the SAR projected CRS. It area-weights NDVI change onto SAR cells without resampling. At 25%, 50%, and 75% common optical area thresholds, 312, 265, and 218 valid SAR cells remain; descriptive Pearson r values are −0.213, −0.230, and −0.290.
- Acquisition timestamps show each Landsat observation occurred about 8.82 hours before its paired Sentinel-1 acquisition. The timeline and evidence card display the observed offsets.
- The assessment builder links the optical observation and derived association as distinct evidence records with explicit derivation lineage. Under the mechanism split in Decision 0042, H4 (vegetation-state change) remains `UNRESOLVED`; its testability is `DESCRIPTIVE_ASSOCIATION_ONLY`, and the association is `DOES_NOT_DISTINGUISH` for vegetation causality.
- The web evidence route verifies assessment links, source-record hashes, and both bounded pixel-subset hashes before returning either record. The interface provides separate inspection actions for the Landsat observation/quality record and the association record.

## Interpretation boundary

This is an optical vegetation-index context, not direct biomass or soil-moisture measurement. The pair transitions from Landsat 8 to Landsat 9, and only 23% of AOI pixel-center support is common clear land. The cellwise association is descriptive; spatial autocorrelation prevents treating cells as independent trials, so no significance test or confidence score is reported. It does not establish a causal driver, flood boundary, or validated SAR result. The OPERA RTC-S1 product QA state remains `PRODUCT_QA_METADATA_RETRIEVED_NO_CONSOLIDATED_DISPOSITION`.

## Verification

- `tests/test_cross_sensor_investigation.py`, `tests/test_case_records.py`, and `tests/test_web.py`: **42 passed** at the integration checkpoint.
- `tests/test_investigation.py` also passed in the preceding targeted run (**75 passed** across those three suites and investigation tests).
- Full repository suite: **259 passed** after the acquisition-offset and reproducibility checks.
- Python compilation and JSON parsing passed. Firefox loaded the live page without script errors, opened the DSWx context and investigation assessment, rendered the HLS card and timeline, and opened the linked association record in the evidence inspector.

See [Decision 0033](../decisions/0033-add-hls-landsat-vegetation-as-descriptive-investigation-evidence.md) for method and reproduction commands.
