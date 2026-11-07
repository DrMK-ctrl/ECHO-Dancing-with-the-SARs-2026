# Live NISAR GCOV interface path: end-to-end evidence

## Run

On 2026-11-07, a headless Firefox session used the ECHO interface to select a GCOV scene and submit its bounded area through the real `POST /api/gcov-preview` endpoint. The endpoint contacted ASF using the local Earthdata credentials and streamed the NISAR HDF5 window; the browser did not use a mock response.

- API result: HTTP 200
- Product: `NISAR_L2_PR_GCOV_033_137_D_068_2005_DHDH_A_20261021T170432_20261021T170507_P05023_N_F_J_001`
- Acquisition: 2026-10-21 17:04:32–17:05:07 UTC
- Dataset: `/science/LSAR/GCOV/grids/frequencyA/HHHH`
- AOI (WGS84): `[28.25, 40.35, 28.26, 40.36]`
- Grid: 56 × 43 pixels, EPSG:32635
- Display-eligible samples: 2,367 of 2,367 AOI pixel centers
- Provider QA: **FAIL**; the UI labels this as a QA-held diagnostic preview and shows no change result
- HTTP range bytes requested: 36,193,262

The live API response's grid metadata and all source-array checksums match the earlier direct-read record. The exact API response is preserved in [`real-gcov-window-preview-2026-11-07.json`](../../data/research/real-gcov-window-preview-2026-11-07.json), SHA-256 `e50ca2a84d3822976397433d777eb1f2202073a7fabdf85c7856aedd9c17e847`.

## Rendered evidence

The screenshot captures the actual returned raster at its geospatial AOI and the visible QA-held warning and evidence inspector:

![ECHO live NISAR GCOV diagnostic preview](evidence/2026-11-07-nisar-gcov-live-interface.png)

Screenshot SHA-256: `397035778d34a01bd8e6e1a07a51998207337889c319b8d74324051f97b0d6e5`.

This verifies the data-access-to-map path for a single observation. Provider QA remains failed; this preview is diagnostic only and does not validate temporal change or event interpretation.
