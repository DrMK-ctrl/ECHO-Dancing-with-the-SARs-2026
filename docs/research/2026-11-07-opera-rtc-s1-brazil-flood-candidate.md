# OPERA RTC-S1 candidate screen: Rio Grande do Sul floods

**Screened:** 2026-11-07 UTC
**Status:** Real Sentinel-1-derived OPERA RTC-S1 pair retrieved and measured; diagnostic only. Exact-AOI NASA DSWx-HLS context is recorded separately.
**Raster analysis:** Bounded RTC-S1 gamma-zero comparison and DSWx-HLS class transitions; neither is an accepted flood finding or NISAR validation.

## Question and source

The current NISAR GCOV products remain held by scene-level identification QA. This bounded screen asks whether a NASA-supported, explicitly separate SAR product can provide real temporal observations for validating a product-specific comparison path. It does not change NISAR's role in ECHO or imply that Sentinel-1 and NISAR products are interchangeable.

The search used the pinned `asf_search==14.1.0` client against `OPERA-S1` / `RTC`, intersecting the WGS84 rectangle `(-51.35, -30.12, -51.10, -29.94)` around Porto Alegre, for acquisitions from 2024-01-01 through 2024-06-30. The query returned 13 catalog features. Five burst IDs had two dates each:

| Burst | Earlier observation | Later observation | Interval |
|---|---|---|---:|
| `T163-349924-IW2` | 2024-05-08 | 2024-06-01 | 24 days |
| `T163-349925-IW2` | 2024-05-08 | 2024-06-01 | 24 days |
| `T163-349925-IW3` | 2024-05-08 | 2024-06-01 | 24 days |
| `T024-050660-IW1` | 2024-05-11 | 2024-06-04 | 24 days |
| `T024-050661-IW1` | 2024-05-11 | 2024-06-04 | 24 days |

The candidate catalog items identify Sentinel-1A, 30 m RTC, VV/VH polarization, and exact burst IDs. This supports screening paired burst products; it does not yet prove pixel-grid equality, matching valid coverage, or suitability for a given AOI.

## Event fit and limits

NASA reports that destructive flooding began after heavy rain starting April 27, 2024, and persisted through much of May. The listed May-to-June pairs are both post-onset and therefore could investigate recession or persistence. This screen found no same-burst pre-event observation in the returned AOI results, so these candidates cannot alone establish a before-versus-flood comparison.

NASA's OPERA RTC-S1 is a Sentinel-1-derived gamma-zero product, distinct from NISAR GCOV. OPERA DSWx-S1 flood maps for May 8 and May 11 exist for this event, but because DSWx-S1 uses OPERA RTC-S1 inputs, it is a related algorithm/product comparison rather than independent validation. A separate sensor/reference source would be needed for independent evaluation.

## Access check

The first authenticated product request redirected through ASF Cumulus and returned `401`, followed by a same-account EULA error on the S3 credential endpoint. Those access failures were later resolved for the bounded ASF HTTPS path: fresh authenticated requests to both pair acquisitions' VV assets and HDF5 sidecars returned `206 Partial Content`, and the end-to-end reader retrieved each selected asset. The earlier failure records below are historical; the current access and scientific disposition are recorded in the [live pair validation](../validation/opera-rtc-live-pair-2026-11-07.md).

## Harmony extraction probe

ECHO tested NASA Harmony against the exact May 11, 2024 OPERA burst. The collection resolved in CMR as `OPERA_L2_RTC-S1_V1` (`C2777436413-ASF`). A request for `image/tiff` was rejected as an unsupported operation. A browse-PNG job reached ASF's OPERA browse service but failed because the ASF Cumulus Earthdata application has not been pre-authorized. An `application/x-netcdf4` request completed through `harmony/download`, which returned links to the original full-granule assets; no raster bytes or spatial subset were returned. This does not remove the existing authorization requirement and is not measurement evidence. The exact request, job IDs, service responses, and disposition are retained in [`harmony-opera-rtc-access-probe-2026-11-07.json`](../../data/research/harmony-opera-rtc-access-probe-2026-11-07.json).

Harmony's service documentation lists the OPERA service as browse imagery (`image/png`); it does not list it as a TIFF extraction service. Its download service returns matched granule links without processing. See [Harmony service capabilities](https://harmony.earthdata.nasa.gov/docs) and the [OPERA RTC-S1 product guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/).

## Separate NASA optical reference screen

To exercise an alternative evidence path without treating related OPERA RTC-S1 outputs as independent validation, a small OPERA DSWx-HLS window was retrieved from PO.DAAC for the same flood region. DSWx-HLS is a Level-3 water classification derived from Harmonized Landsat-Sentinel-2 optical observations. It is not SAR, a raw optical measurement, or ground truth. The products were selected from the same 30 m tile (`T22JDM`): Sentinel-2A on 2024-04-21 and Landsat 8 on 2024-05-08.

The WTR and CLOUD GeoTIFF assets (1,215,015 bytes total) were retrieved through Earthdata-authenticated HTTPS. All four retrieved asset MD5 values matched the checksums in CMR. The requested WGS84 AOI was `(-51.25, -30.08, -51.24, -30.07)`. Both WTR rasters share CRS `EPSG:32622` and an exactly matching extracted grid. Of 1,116 AOI pixels, 1,114 had water classes 0/1/2 in the April product and 922 in the May product; 920 pixels were valid in both, or 82.44% of AOI pixels. The transition matrix is limited to these common valid pixels. The May product includes 194 WTR cloud/cloud-shadow pixels in this AOI, so the comparison has a substantial observation mask.

This is a verified data-access and optical-product comparison milestone, not a flood-boundary accuracy assessment. Class transitions describe only the two DSWx-HLS outputs and cannot clear any NISAR QA failure. Full product identities, acquisition/retrieval times, CMR and asset references, checksums, grid metadata, class histograms, transition counts, and limitations are recorded in [`opera-dswx-hls-rio-grande-do-sul-window-2026-11-07.json`](../../data/research/opera-dswx-hls-rio-grande-do-sul-window-2026-11-07.json). NASA describes DSWx-HLS as an optical water product and documents the cloud limitation in the [JPL product suite](https://www.jpl.nasa.gov/go/opera/products/dswx-product-suite/) and [PO.DAAC product record](https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-HLS_V1).

## Historical access block and subsequent resolution

The access failures in this section were observed before the user's later ASF EULA review on 2026-11-07. They describe the earlier state and are superseded by the successful range and pair requests recorded below.

The initial authenticated ASF HTTPS request returned HTTP 401 after Earthdata authentication; an anonymous read of the corresponding S3 object returned HTTP 403. At that point, no OPERA raster bytes had been read. The redirect identified ASF Cumulus client ID `BO_n7nTIlMljdvU6kRRB3g`.

### Follow-up and implementation status

After the user authorized ASF Cumulus, the selected May 11 VV request still failed through ASF `datapool` → Cumulus → Earthdata OAuth → Cumulus `/login` with HTTP 401; no raster body was consumed. A separate same-account S3 credential request then reported the EULA failure. These were historical access failures, later resolved for the bounded HTTPS path, and were not evidence of product unsuitability or QA. The reader reports authorization denials without exposing redirect query values and requires HTTP 206 with an exact catalog-sized `Content-Range`, consuming the response in capped 64 KiB chunks.

ECHO has a bounded OPERA RTC-S1 reader and pair-analysis path, now exercised against real pixels. It caps each in-memory GeoTIFF asset at 16 MiB, returns only a bounded AOI array, checks measurement/mask grid identity, and records source hashes and processing provenance. The pair gate requires matching burst, Sentinel-1 platform, pixel spacing, product version, polarization, CRS, affine transform, raster window, and AOI pixel-center selection. The live path retrieved and mapped the pair in the geographic workspace. Product sidecars do not provide a consolidated provider PASS/FAIL disposition, so the measured comparison remains `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`.

The selected VV assets are 7,137,589 and 7,130,774 bytes; masks are 52,762 and 52,780 bytes. The live analysis confirmed exact grid registration and 1,199 common clear centers for this AOI. Keep this result identified as OPERA RTC-S1/Sentinel-1; it cannot clear any NISAR QA hold.

### Same-account authorization follow-up

The earlier same-account probe of ASF's temporary S3 credential endpoint, `https://sentinel1.asf.alaska.edu/s3credentials`, returned Earthdata `403 invalid_token` with `EULA Acceptance Failure`. No temporary credentials were issued and no S3 object was read in that attempt. This failure was later resolved for the bounded ASF HTTPS path; it does not establish that the separate S3 credential endpoint was rechecked.

ASF's [S3 credentials guide](https://sentinel1.asf.alaska.edu/s3credentialsREADME) says these temporary credentials only permit in-region S3 requests. This laptop workflow is outside the source bucket's AWS region, so direct S3 credentials would not provide a usable desktop retrieval route. The bounded ASF HTTPS reader is the working local path, as confirmed by the later authenticated range checks.

The prior selected VV asset sizes and mask sizes were within the reader's cap. At the time of those checks, the pair had not been read; that status is superseded by the live processing result below.

### Latest access and pair result

After the user reviewed the account's ASF authorization/EULA state, a fresh Earthdata Login check using the local netrc authenticated. Bounded RTC-S1 asset ranges returned HTTP 206 through ASF delivery without the earlier 401/403 EULA failure. The live reader then retrieved both VV COGs, masks, and HDF5 sidecars for the 2024-05-11 / 2024-06-04 `T024-050660-IW1` pair over a 0.01° AOI. Exact EPSG:32722 grid alignment and mask checks yielded 1,199 common clear centers. The HDF5 sidecars contain geometric-accuracy, RFI, and processing metadata but no consolidated PASS/FAIL disposition. The result remains `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON`; it does not establish a flood extent or cause. See the [live access and pair validation](../validation/opera-rtc-live-pair-2026-11-07.md) and [updated product QA evidence](../../data/research/opera-rtc-live-pair-product-qa-2026-11-07.json).

The earlier DSWx-HLS screen above remains regional context only: its AOI does not overlap the RTC-S1 AOI; their nearest latitude edges are about 3.3 km apart. A separate bounded DSWx-HLS extraction now uses the exact RTC-S1 WGS84 rectangle and closer optical dates: May 8 Sentinel-2A and June 2 Sentinel-2B, approximately three and two days before the respective May 11 and June 4 Sentinel-1 acquisitions. The optical products share an identical native grid and the same 1,199 selected AOI pixel centers. This is same-AOI contextual comparison, not pixel-to-pixel comparison with the differently projected RTC-S1 grid.

On the common 837 centers valid in both standard WTR layers, DSWx-HLS water classes 1/2 decreased from 36 to 27 centers; 17 centers changed from a water class to not-water while 8 changed in the opposite direction. The unmasked confidence classes give the same water counts. The less cloud-restricted WTR-2 layer counts 135 water-class centers before and 59 after, but the May 8 confidence layer marks 99 of its 135 water classifications as cloud- or snow-associated. The standard WTR layer also flags 211 May 8 centers as snow/ice and 148 as cloud/cloud-shadow. These masks substantially limit the optical comparison. NASA documents both that cloud labeling can obscure water in WTR and that unusual water coloration, including sediment, can sometimes be mislabeled as snow/ice; those documented limitations are possible explanations, not evidence that these pixels were misclassified here. The product-class trend is compatible with declining classified water but is not an independent flood-extent validation or a causal conclusion. Full source identifiers, per-layer checksums, processing fields, histograms, and transition matrices are in [`dswx-hls-rtc-aoi-context-2026-11-07.json`](../../data/research/dswx-hls-rtc-aoi-context-2026-11-07.json); the bounded retrieval and transition calculation are reproducible with [`evaluate_dswx_hls_aoi.py`](../../tools/research/evaluate_dswx_hls_aoi.py).

## References

- NASA Earth Observatory, [Floods Engulf Porto Alegre](https://science.nasa.gov/earth/earth-observatory/floods-engulf-porto-alegre-152795/).
- ASF HyP3, [OPERA RTC-S1 product guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/).
- ASF HyP3, [OPERA RTC-S1 product description and access](https://hyp3-docs.asf.alaska.edu/products/).
- NASA JPL, [OPERA RTC product specification](https://www.jpl.nasa.gov/go/opera/products/rtc-product/).
- NASA Earthdata Login, [How to pre-authorize an application](https://urs.earthdata.nasa.gov/documentation/for_users/how_to_preauth_app).
