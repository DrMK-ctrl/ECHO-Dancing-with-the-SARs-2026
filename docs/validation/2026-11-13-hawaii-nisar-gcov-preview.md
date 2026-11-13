# Bounded NISAR GCOV preview: Hilo, Hawaiʻi

**Date:** 2026-11-13

**Result:** Real single-acquisition measurements are retrieved, geolocated, displayed, and inspectable in the ECHO workbench. This is a QA-held diagnostic preview, not a validated scientific finding.

## Observation and source

- Mission/product: NASA NISAR L2 GCOV, ASF DAAC, `VALIDATED` maturity, release `P05036`.
- Scene: `NISAR_L2_PR_GCOV_035_072_D_078_4005_DHDH_A_20261110T045757_20261110T045815_P05036_N_P_J_001`.
- Acquisition: 2026-11-10 04:57:57–04:58:15 UTC.
- Measurement: frequency A, HHHH, `/science/LSAR/GCOV/grids/frequencyA/HHHH`, linear gamma-zero power.
- AOI: WGS84 `[-155.12, 19.70, -155.10, 19.72]`; source grid EPSG:32605. The exact AOI selection contains 46,421 pixel centers in a 224 × 212 bounded window.
- Retrieval: ECHO's local `/api/gcov-preview` read authenticated ASF HTTPS byte ranges using the locally configured Earthdata Login credentials; no full product download was requested. The window read is recorded at `2026-11-13T10:31:47.049519Z`; 8,454,934 range bytes were requested.
- Preview record: [`nisar-hawaii-hilo-gcov-diagnostic-preview-2026-11-10.json`](../../data/research/nisar-hawaii-hilo-gcov-diagnostic-preview-2026-11-10.json), SHA-256 `96a0e5b866a146ac7ca9e8b8d7706839280f7d7e099c0e2d1b1e0b91ef3b33be`.

## Provider QA and scientific boundary

The retained ASF QA CSV reports overall `FAIL`: the identification-group check failed. The file-open, coordinate-grid, calibration-LUT, backscatter data-quality, and QA-completion checks report `PASS`. The record does not establish the cause of the identification failure. ECHO keeps the provider status unchanged and labels the map `QA-HELD REAL SAR PREVIEW`; no temporal comparison, change finding, event, or physical cause is asserted.

The display transform is `10 log10(linear gamma-zero power)` with an AOI 2nd–98th percentile visualization stretch of −15.71 to +0.70 dB. The stretch changes display contrast only. A browser pointer selection returned the retained measurement at row 28957, column 19819: gamma-zero 0.0692902 (−11.59 dB), mask 1, and exception mask 768. Its HHHH focused-polarization bit is 256; 768 includes that valid bit plus another polarization's validity bit.

## Rendering defect found and corrected

The browser renderer treated every nonzero `inputDataExceptionMask` value as an exception. GCOV UInt16 products combine low-byte exception codes with per-polarization focused-data bits, so this hid the entire valid HHHH window even though the backend's documented decoder accepted 46,421 display-eligible centers. The renderer now checks the selected layer's documented polarization flag and rejects nonzero low-byte exception codes; unsupported encodings or mismatched metadata remain excluded.

The earlier 0.04° AOI was rejected by ECHO's 65,536-sample limit before any raster window read. Reducing it to 0.02° kept the bounded window within that guard.

## Verification

`python3 tools/validation/check_gcov_preview_browser.py --screenshot docs/validation/screenshots/nisar-hawaii-hilo-preview-2026-11-13.png` passed in local Firefox. It exercised AOI entry, catalog timeline selection, the raster display, visible QA hold, and pointer-based pixel inspection. The catalog fixture uses the matching footprint from the retained ASF global catalog record; it is not a fresh point/AOI catalog response. The real measurement response was replayed from the retained record, so this browser check made no second provider request. No browser errors occurred.

The screenshot is evidence of the interface rendering this retained real-data response; it is not a scientific validation of the QA-held product. The full automated regression suite also passed: **535 passed in 42.55 seconds**.
