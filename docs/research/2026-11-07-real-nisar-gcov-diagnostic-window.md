# Real NISAR GCOV diagnostic window

## Result

ECHO retrieved a bounded window from the NISAR L2 GCOV product below using authenticated ASF range access. The window contains 2,367 of 2,367 AOI pixel centers that pass ECHO's current display screen (valid mask code, finite positive backscatter, and zero input-data exception code). It is a single-acquisition gamma-zero backscatter preview, not a temporal change measurement.

- Product: `NISAR_L2_PR_GCOV_033_137_D_068_2005_DHDH_A_20261021T170432_20261021T170507_P05023_N_F_J_001`
- Acquisition: 2026-10-21 17:04:32–17:05:07 UTC
- Dataset: `/science/LSAR/GCOV/grids/frequencyA/HHHH`
- AOI (WGS84): west 28.25, south 40.35, east 28.26, north 40.36
- Product grid: 56 rows × 43 columns, EPSG:32635
- Provider QA: **FAIL** (ASF QA summary SHA-256: `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`)
- ECHO disposition: QA-held diagnostic preview only; no accepted analytical result or event interpretation.

The provider failure remains visible even though the selected pixels pass ECHO's local display screen. ECHO did not reinterpret or waive ASF's product-level QA result. The record retains the original source arrays and quality layers, pixel-center selection mask, geolocation, array checksums, retrieval provenance, and display transform.

## Reproduction record

[`real-gcov-window-preview-2026-11-07.json`](../../data/research/real-gcov-window-preview-2026-11-07.json) is the complete returned preview record. Its SHA-256 is `d86535ca2222356d8de69f7be49729abb51dd860f445e344779b3396b0be86c1`.

The read took approximately 112 seconds for this 56 × 43 window. That is an observed first-run latency, not a general service-level estimate. The request was authenticated through the local Earthdata credentials file; no credentials are included in the record or repository.
