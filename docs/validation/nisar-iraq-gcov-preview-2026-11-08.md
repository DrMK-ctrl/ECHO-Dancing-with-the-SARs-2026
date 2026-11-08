# Bounded NISAR GCOV measurement preview — Iraq, 2026-11-08

## Result

ECHO retrieved an actual, geographically bounded HHHH measurement window from a provisional NISAR L2 GCOV product. The complete preview, including source QA, measurement values, quality layers, projected grid coordinates, geographic selection, and per-array SHA-256 checksums, is retained in [`nisar-iraq-p05023-hhhh-preview-2026-11-08.json`](../../data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json) (file SHA-256 `399e78b718b47f1f4ba73de1386376fe112be321fdfe4b054d9e75b2735c0a11`).

## Acquisition and processing

- Mission/product: NASA NISAR L2 GCOV, provisional collection `NISAR_L2_GCOV_PROVISIONAL_V1`, CRID `P05023`.
- Scene: `NISAR_L2_PR_GCOV_033_122_D_070_2005_DHDH_A_20261020T160723_20261020T160758_P05023_N_F_J_001`.
- Acquired: `2026-10-20T16:07:23Z`–`2026-10-20T16:07:58Z`.
- Provider: Alaska Satellite Facility DAAC; authenticated with the local Earthdata `.netrc` through `earthaccess`.
- Requested geographic bounds: `[41.2, 36.7, 41.22, 36.72]` WGS84; product grid EPSG:32637.
- Measurement: `/science/LSAR/GCOV/grids/frequencyA/HHHH`, linear gamma-zero power. The preview contains 9,918 pixel centers inside the requested bounds, selected from a 113 × 92 enclosing read window. Mask, number-of-looks, and input-data-exception arrays were retrieved with the measurement.
- Transfer: HTTPS byte-range streaming with 16 KiB fsspec read-ahead blocks; 2,391,496 range bytes requested, under the existing 64 MiB read ceiling. No complete product download was requested.

## Scientific disposition

The provider QA summary reports **FAIL** (aggregate identification-group check). ECHO preserves that result and labels the output `QA_HELD_DIAGNOSTIC_PREVIEW`. The selected pixel centers pass the preview's display mask checks, but that does not override product QA or authorize analytical use. This is one observation: no temporal change, event, cause, damage, or ground condition is established.

## Access-path finding and limit

An earlier read of this same scene using the normal 128 KiB block size ended in a connection reset while HDF5 requested remote ranges. A separate initial-byte range check had succeeded, so the failure did not establish an account or catalog restriction. Repeating the bounded window read with 16 KiB blocks succeeded. This demonstrates that the product and geographic window are readable through an alternate bounded transfer setting; a single success does not establish that block size alone caused the earlier reset.

The successful read used a temporary in-process block-size override for this validation. The application default and HTTP API behavior remain unchanged, so the record demonstrates the scientific reader path but does not yet establish that this exact provisional scene can be fetched through the interactive API under its default transfer setting. The existing generic GCOV preview route and map renderer remain the reusable integration path; an evidence-backed retry policy should be considered before changing its defaults.
