# Live OPERA RTC-S1 browser investigation

**Checked:** 2026-11-07 UTC
**Result:** Full live catalog-to-map browser path passed; scientific result remains diagnostic

## Browser path

Headless Firefox opened ECHO against a temporary local case fixture with the selected WGS84 AOI `(-51.24, -30.04, -51.23, -30.03)`. The browser searched ASF live for 2024-04-25 through 2024-06-30. ASF returned five records and two repeated-burst candidates in one page, without reaching the configured result cap. The user interface selected the returned Sentinel-1A `T024-050661-IW1` pair for 2024-05-11 and 2024-06-04.

The browser submitted the pair through ECHO's real `/api/opera-pair-analysis` route. Earthdata-authenticated bounded reads retrieved both VV GeoTIFFs, product masks, and HDF5 metadata sidecars. The resulting map showed the measured response-difference raster in the pair's EPSG:32722 coordinates. Clicking a valid map cell populated the inspector with its row, column, and signed measurement.

| Check | Observed result |
| --- | --- |
| AOI centers | 1,199 |
| Common mask-valid measurements | 1,043 |
| Product grid | EPSG:32722; exact pair alignment passed |
| Selected map cell | Row 19, column 15; −0.332147 dB |
| Inspector | Both product IDs and dates, source links, geometric/RFI metadata, masks, processing and limits visible |
| QA disposition | No consolidated provider PASS/FAIL; explicitly diagnostic |
| Map attribution | NASA OPERA RTC-S1 · Sentinel-1 · VV · QA metadata / no PASS-FAIL |

The image and inspector remain explicitly labeled `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`. The displayed log-ratio is descriptive Sentinel-1-derived gamma-zero evidence. It is not a NISAR result, validated flood boundary, physical cause, or accepted event finding. The NISAR QA hold is unchanged.

## Reproduction and retained evidence

The live pair and its exact catalog query context, source product identities, retrieved assets, checksums, masks, grids, measurement, software and interpretation limits are in [`opera-rtc-live-pair-T024-050661-2026-11-07.json`](../../data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json). It was generated from an authenticated fresh ASF AOI catalog query followed by `build_opera_rtc_s1_pair_record` using the exact returned product features and the bounded reader.

The captured browser state is [`opera-rtc-live-ui-e2e-2026-11-07.png`](opera-rtc-live-ui-e2e-2026-11-07.png), SHA-256 `c811fa6b2b8cf6b326fa7c675f458c878bb5fd33fc7a3471a07d5d67353be9c9`. The pair record SHA-256 is `4556bd0d781de4f8e99c240682e761caa10fb540d09edcec029848b6d9c758ea`.

A separate Firefox replay of the retained real pair record checked narrow layout: at a 500 px viewport, the document width was 488 px. That replay also confirmed the source inspector and pixel click interaction. The full live run above independently exercised catalog search, asset retrieval, map rendering, and pixel selection in one session.

No authentication secrets or cookies are retained in the repository. Product access works for the configured Earthdata account; the missing consolidated product QA disposition is the remaining scientific limitation for treating this pair as a validated result.
