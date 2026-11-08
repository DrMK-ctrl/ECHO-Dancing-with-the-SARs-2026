# Bounded NISAR GCOV measurement preview — Iraq, 2026-11-08

## Result

ECHO retrieved an actual, geographically bounded HHHH measurement window from a provisional NISAR L2 GCOV product. The complete latest preview, including source QA, measurement values, quality layers, projected grid coordinates, geographic selection, and per-array SHA-256 checksums, is retained in [`nisar-iraq-p05023-hhhh-preview-2026-11-08.json`](../../data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json) (file SHA-256 `3d3cf2f3c4c273331557a813d8194e3bd996adc242b4df9cbccb402affed5bba`).

## Acquisition and processing

- Mission/product: NASA NISAR L2 GCOV, provisional collection `NISAR_L2_GCOV_PROVISIONAL_V1`, CRID `P05023`.
- Scene: `NISAR_L2_PR_GCOV_033_122_D_070_2005_DHDH_A_20261020T160723_20261020T160758_P05023_N_F_J_001`.
- Acquired: `2026-10-20T16:07:23Z`–`2026-10-20T16:07:58Z`.
- Provider: Alaska Satellite Facility DAAC; authenticated with the local Earthdata `.netrc` through `earthaccess`.
- Requested geographic bounds: `[41.2, 36.7, 41.22, 36.72]` WGS84; product grid EPSG:32637.
- Measurement: `/science/LSAR/GCOV/grids/frequencyA/HHHH`, linear gamma-zero power. The preview contains 9,918 pixel centers inside the requested bounds, selected from a 113 × 92 enclosing read window. Mask, number-of-looks, and input-data-exception arrays were retrieved with the measurement.
- Transfer: the normal ECHO preview builder used its 128 KiB fsspec read-ahead setting and requested 7,351,192 HTTPS range bytes, under the existing 64 MiB read ceiling. No complete product download was requested.

## Scientific disposition

The provider QA summary reports **FAIL** (aggregate identification-group check). ECHO preserves that result and labels the output `QA_HELD_DIAGNOSTIC_PREVIEW`. The selected pixel centers pass the preview's display mask checks, but that does not override product QA or authorize analytical use. This is one observation: no temporal change, event, cause, damage, or ground condition is established.

## Access-path finding and limit

An earlier read of this same scene using the normal 128 KiB block size ended in a connection reset while HDF5 requested remote ranges. A separate initial-byte range check had succeeded, so that failure did not establish an account or catalog restriction. A 16 KiB bounded read then succeeded. A later fresh read through the unmodified 128 KiB preview path also succeeded, requesting 7,351,192 bytes. Thus the original reset appears transient; the evidence does not show that smaller blocks are generally faster or more reliable.

The local application's `POST /api/gcov-preview` handler was exercised with the retained catalog feature and this same bounded AOI. It returned HTTP 200 and the complete real-data record with the same scene, QA status, 113 × 92 window, 9,918 selected centers, and 7,351,192 requested range bytes. The request succeeded on its first 128 KiB attempt. It proves the live preview API path; browser rendering of this response was not checked.

The reader now retries once with a 16 KiB block only when a bounded range read fails with a recognized transport reset, disconnect, or timeout. Bytes consumed by the failed first attempt are deducted from the retry budget, keeping combined reads within 64 MiB. Focused tests simulate a connection reset and verify the reduced remaining budget. The fallback has not yet been observed during a live provider failure.

## Browser presentation check — 2026-11-09

Headless Firefox exercised the map workspace at a 1366 × 682 viewport using the retained ASF catalog feature and the real preview record returned by the live API above. The test selected the observation from the timeline and loaded the preview through the application's UI flow. The browser rendered the HHHH raster, map color ramp, pixel readout affordance, and source inspector; the QA warning and inspector both displayed the provider `FAIL` and the no-change limitation. The responsive toolbar and measurement controls occupied separate, non-overlapping rows, and the QA callout was increased to 9 px for legibility at this viewport. This visual render used the saved live record as a local response fixture to avoid another multi-megabyte provider read; the separate HTTP 200 validation above exercised the live API. The screenshot is [`nisar-gcov-preview-browser-2026-11-09.png`](assets/nisar-gcov-preview-browser-2026-11-09.png), SHA-256 `4a5370addbe709ce164b44671c295641bdff35a948cee715b6916fa157ce2883`.

The screenshot is an interface rendering check, not independent validation of the QA-failed NISAR measurement or evidence of a temporal finding.

## Bounded repeat-coverage screen — 2026-11-09

To check whether this scene has an available same-track temporal candidate, ECHO queried ASF GCOV metadata for the exact preview bounds `[41.20, 36.70, 41.22, 36.72]` WGS84 from `2026-10-20` through `2026-11-09`, separately for `PROVISIONAL` and `VALIDATED` maturity, with a 1,000-result ceiling. The initial query completed at `2026-11-08T23:12:59Z`: the provisional search returned two scenes, of which only the reference scene matched path 122/frame 70; the validated search returned zero scenes. The returned provisional set therefore contains no metadata-compatible repeat pair under ECHO's same-path/frame rules. The result counts are below the result ceiling.

This was a catalog-only screen: no product QA reports or measurement arrays were read. The complete response was not retained by the initial exploratory command. A subsequent attempt to repeat the query and preserve its response ended in the ASF CMR client's 30-second read timeout; that timeout does not change the earlier successful result or establish that no products exist outside this query. Treat the summary above as exploratory evidence, not a checksummed catalog record. Do not repeat this unchanged screen unless ASF coverage or the search window changes.
