# NASA MOD09GA daily vegetation candidate screen — T163

Date: 2026-11-08

Case: `rio-grande-do-sul-t163-349925-diagnostic-2024`

Disposition: retrieved, but unsuitable for paired vegetation interpretation

## Source and retrieval

NASA LP DAAC's CMR collection `C2202497474-LPCLOUD` identified these Terra/MODIS MOD09GA Version 6.1 granules on the two OPERA RTC-S1 acquisition dates:

| Role | Daily granule | CMR granule concept |
|---|---|---|
| Before, 2024-05-08 | `MOD09GA.A2024129.h13v12.061.2024131043655` | `G2991676203-LPCLOUD` |
| After, 2024-06-01 | `MOD09GA.A2024153.h13v12.061.2024155024914` | `G3058425113-LPCLOUD` |

The bounded pixel and QA subsets were retrieved from NASA LAADS DAAC's OPeNDAP service. The LP DAAC provider/CMR identity and LAADS retrieval service are recorded separately. CMR's spatial query also returned the neighboring sinusoidal tile, so the screener independently derived tile `h13v12` from the AOI coordinates and read only that tile. The response body of each of the 20 bounded subset requests is recorded with byte count and SHA-256 in the structured [screen record](../../data/research/mod09ga-vegetation-candidate-T163-349925-2026-11-08.json). The total retained responses are 277,871 bytes.

NASA describes MOD09GA as a daily product with 500 m surface-reflectance bands and associated 1 km state QA. The red (`sur_refl_b01_1`) and NIR (`sur_refl_b02_1`) bands, `QC_500m_1`, geolocation arrays, and `state_1km_1` were read as native-grid subsets. No full granule was downloaded, and no spatial resampling was performed. QA fields follow the [NASA MODIS Surface Reflectance Collection 6.1 User Guide](https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/archives/Document%20Archive/Science%20Data%20Product%20Documentation/MOD09_C61_UserGuide_v1.7.pdf), especially its `QC_500m` and `state_1km` bit definitions.

## Result and limits

Six 500 m pixel centers fall in the linked SAR window on each date, with all six centers shared by row and column index. The red and NIR MODLAND and per-band quality fields are the best category for all retained pixels. However, the 1 km state QA assigns every associated center to land/water classes 2 or 3 (shoreline or shallow inland water). Before-date state QA also includes cloud and shadow flags; after-date flags are clear. Because the 1 km state layer does not establish suitable land support for the 500 m vegetation measurement, zero cells pass the conservative paired vegetation gate.

ECHO therefore records the red/NIR observations and QA as retrieved source measurements but does not calculate or expose a paired NDVI difference, vegetation change, or SAR association. This is a case suitability limitation, not a MOD09GA product failure. The daily granule period also does not supply per-pixel overpass timestamps in this bounded read. The MOD09GA result does not test H4 (`VEGETATION_STATE_CHANGE`) and does not validate the QA-held SAR response.

The active T163 assessment links the screen to H4 as `LIMITS_INTERPRETATION`; follow-up F9 remains `RETRIEVED_QUALITY_LIMITED`. The overall causal assessment remains `CAUSAL_INTERPRETATION_UNRESOLVED`, and the SAR product's diagnostic/QA status is unchanged.

The rebuilt assessment passed ECHO's source-linked record validator with all 23 evidence records resolved. A local Firefox WebDriver session opened the T163 assessment, rendered the MOD09GA card and its quality limitation, then opened **INSPECT DAILY REFLECTANCE AND QA**. The source inspector displayed the LP DAAC/CMR identity, LAADS retrieval service, bounded response provenance, and record JSON. The local evidence API returned HTTP 200. The full test suite passed with 331 tests, and `compileall` completed successfully.

## Reproduction

With the local Earthdata credentials available through `~/.netrc`, run:

```bash
.venv/bin/python tools/research/screen_mod09ga_vegetation.py \
  --pair-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output /tmp/mod09ga-vegetation-candidate.json
```

The screener uses CMR for exact-date granule metadata and LAADS OPeNDAP for bounded array reads. It requires the ECHO Python environment, `earthaccess`, and network access. Credentials are never written into the record.
