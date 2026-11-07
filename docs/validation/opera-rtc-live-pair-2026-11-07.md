# Live OPERA RTC-S1 access and bounded pair

**Checked:** 2026-11-07 UTC
**Result:** Earthdata/ASF access working; real bounded pair and product QA metadata retrieved; diagnostic only

## Access check

Using the existing local Earthdata netrc configuration, `earthaccess.login(strategy="netrc", persist=False)` returned authenticated. Bounded requests to both acquisitions' VV COGs and HDF5 sidecars returned **206 Partial Content** with matching `Content-Range` headers. The end-to-end reader also retrieved each bounded COG, mask, and metadata sidecar completely. This confirms the prior ASF 401/403 EULA restriction is no longer blocking these OPERA RTC-S1 assets for this Earthdata account. No credentials, tokens, or response cookies are retained here.

## Real pair processing

ECHO read the ASF catalog features for the Sentinel-1A `T024-050660-IW1` pair and fetched the complete per-burst GeoTIFF COG byte ranges and mask byte ranges into memory. The before acquisition is 2024-05-11; the after acquisition is 2024-06-04, an interval of approximately 24 days. The WGS84 AOI was `(-51.24, -30.04, -51.23, -30.03)`.

| Check | Observed result |
| --- | --- |
| Before VV COG / mask / HDF5 | 7,137,589 B / 52,762 B / 106,216 B; HTTP 206 range reads |
| After VV COG / mask / HDF5 | 7,130,774 B / 52,780 B / 106,216 B; HTTP 206 range reads |
| Projected grid | EPSG:32722; exact CRS, transform, and shape agreement |
| Selected window | 38 × 33 enclosing cells; 1,199 pixel centers in the AOI |
| Common clear measurements | 1,199 of 1,199 selected centers |
| Product QA metadata | Retrieved from both HDF5 sidecars; stable SHA-256 hashes recorded |
| Consolidated provider QA disposition | Not present in the sidecars; no PASS/FAIL verdict asserted |
| Analysis disposition | `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON` |

The HDF5 sidecars report geometric-accuracy bias and standard-deviation fields, RFI information availability, an RFI burst report, mitigation descriptors, and processing/software/input metadata. Both report `isRfiInfoAvailable=true`, mitigation performed as `BasedOnNoiseMeas`, and processing software version `1.0.2`. This is product metadata, not an RFI-free verdict; the burst report is not a geolocated quality mask for the selected AOI. The geometric-accuracy fields are preserved as reported without assigning units or treating them as proof of temporal co-registration.

The pair record preserves the ASF feature metadata, exact measurement/mask/HDF5 asset URLs, retrieval times, byte-range sizes, SHA-256 checksums, parsed product QA fields and source HDF5 paths, AOI selection, processing rule, software versions, and result arrays. The input files were held in memory and not saved as full products.

This is a measured Sentinel-1-derived OPERA gamma-zero response difference over the selected cells. The product sidecars do not contain an aggregate provider QA disposition, so the result remains diagnostic. It does not establish a flood boundary, event, cause, or independent corroboration. It is distinct from NISAR, and does not change NISAR's QA hold.

The mask semantics follow the [ASF OPERA RTC-S1 product guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/). The HDF5 QA group and product metadata fields were checked against the [NASA JPL OPERA RTC-S1 product specification](https://d2pn8kiwq2w21t.cloudfront.net/documents/ProductSpec_RTC-S1.pdf).

## Interface check

The previous headless Firefox check loaded the retained live catalog response, selected the repeated-burst candidate, and called the live pair endpoint. For the current QA-metadata integration, Firefox loaded the dashboard and parsed the updated inspector function, and automated tests verify the new record fields. Populating the inspector with the retained live record was not successfully validated in the browser harness, so this interface detail remains unverified. The catalog response was replayed from the retained live catalog record; the new pair and HDF5 fields were freshly retrieved from ASF.

The full regression suite passed: **171 tests passed**. Python compile checks and `git diff --check` passed. JavaScript runtime validation was unavailable because Node.js is not installed in this environment.

The original reproducible measurement record is [`opera-rtc-live-bounded-pair-2026-11-07.json`](../../data/research/opera-rtc-live-bounded-pair-2026-11-07.json). The updated record with complete product sidecar provenance is [`opera-rtc-live-pair-product-qa-2026-11-07.json`](../../data/research/opera-rtc-live-pair-product-qa-2026-11-07.json). The earlier browser screenshot is [`opera-rtc-live-map-2026-11-07.png`](opera-rtc-live-map-2026-11-07.png); it predates the inspector text update.
