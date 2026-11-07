# Live OPERA RTC-S1 access and bounded pair

**Checked:** 2026-11-07 UTC
**Result:** Earthdata/ASF access working; real bounded pair computed; diagnostic only

## Access check

Using the existing local Earthdata netrc configuration, `earthaccess.login(strategy="netrc", persist=False)` returned authenticated. A one-byte HTTP Range request to an ASF RTC-S1 catalog asset returned **206 Partial Content** with a one-byte `Content-Range`. The redirect chain passed through `datapool.asf.alaska.edu`, ASF Cumulus, and Earthdata Login before the asset was served. The request no longer returned the prior 401/403 EULA failure. No credentials, tokens, or response cookies are retained here.

## Real pair processing

ECHO read the ASF catalog features for the Sentinel-1A `T024-050660-IW1` pair and fetched the complete per-burst GeoTIFF COG byte ranges and mask byte ranges into memory. The before acquisition is 2024-05-11; the after acquisition is 2024-06-04, an interval of approximately 24 days. The WGS84 AOI was `(-51.24, -30.04, -51.23, -30.03)`.

| Check | Observed result |
| --- | --- |
| Before VV COG / mask | 7,137,589 B / 52,762 B; HTTP 206 range reads |
| After VV COG / mask | 7,130,774 B / 52,780 B; HTTP 206 range reads |
| Projected grid | EPSG:32722; exact CRS, transform, and shape agreement |
| Selected window | 38 × 33 enclosing cells; 1,199 pixel centers in the AOI |
| Common clear measurements | 1,199 of 1,199 selected centers |
| Provider QA summary | `NOT_RETRIEVED` |
| Analysis disposition | `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON` |

The pair record preserves the ASF feature metadata, exact asset URLs, retrieval times, byte-range sizes, SHA-256 checksums, mask and measurement checksums, AOI selection, processing rule, software versions, and the result arrays. The input files were held in memory and not saved as full products.

This is a measured Sentinel-1-derived OPERA gamma-zero response difference over the selected cells. Since ECHO has not retrieved a product-level ASF QA disposition for these products, the result remains diagnostic. It does not establish a flood boundary, event, cause, or independent corroboration. It is distinct from NISAR, and does not change NISAR's QA hold.

## Interface check

Headless Firefox 158 loaded the retained live ASF catalog response, selected the repeated-burst candidate, and called the live `POST /api/opera-pair-analysis` endpoint for the bounded AOI. The endpoint returned HTTP 200 after 74.9 seconds, with the same two live products and 1,199-pixel diagnostic result. The browser rendered the geolocated raster and source inspector, showed `QA NOT RETRIEVED`, closed the modal to expose the map, and restored the NISAR timeline through the return control. No browser JavaScript errors were observed. The catalog response in this UI check was replayed from the retained live catalog record; the pair measurements were freshly retrieved from ASF by the application endpoint.

The full regression suite passed: **171 tests passed**. Python compile checks and `git diff --check` also passed.

The reproducible measurement record is [`opera-rtc-live-bounded-pair-2026-11-07.json`](../../data/research/opera-rtc-live-bounded-pair-2026-11-07.json). The browser screenshot is [`opera-rtc-live-map-2026-11-07.png`](opera-rtc-live-map-2026-11-07.png).
