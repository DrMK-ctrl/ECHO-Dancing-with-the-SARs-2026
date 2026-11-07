# OPERA RTC-S1 candidate screen: Rio Grande do Sul floods

**Screened:** 2026-11-07 UTC
**Status:** Metadata candidate only; product access requires ASF Earthdata application authorization
**Raster analysis:** None performed

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

An Earthdata Login using the locally configured netrc succeeded. ASF's catalog product URL then redirected through the ASF Cumulus host and returned `401` with an explicit Earthdata application pre-authorization requirement for the ASF client. No raster bytes were retrieved. This is an account/application authorization blocker, not evidence that the candidate products are absent or unsuitable. The service's resolution URL is supplied directly to the project lead so access can be authorized; no credentials are needed in the repository or chat.

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

After the user authorized ASF Cumulus, ECHO retried the selected May 11 VV asset through its streamed Requests range reader using the local Earthdata netrc identity. Earthdata Login authenticated, but the HTTP redirect chain was ASF `datapool` 307 → ASF `cumulus` 302 → Earthdata `/oauth/authorize` 302 → ASF Cumulus `/login` 401. No raster response body was consumed. The same-account follow-up probe below narrows the access blocker to an ASF EULA acceptance failure; it is not a product suitability or QA result. ECHO reports the authentication denial without exposing redirect query values and now directs the user to check both any pending ASF data EULA and Cumulus application access. The reader also requires HTTP 206 with an exact catalog-sized `Content-Range` and consumes the response in capped 64 KiB chunks, preventing an ignored range request from buffering an unbounded response.

ECHO now has a fixture-tested OPERA RTC-S1 reader and pair-analysis path. It caps each complete in-memory GeoTIFF asset at 16 MiB, reads the requested asset byte range without writing source assets to disk, returns only a bounded AOI array, checks measurement/mask grid identity, and records source asset hashes and processing provenance. The pair gate requires matching burst, Sentinel-1 platform, pixel spacing, product version, polarization, CRS, affine transform, raster window, and AOI pixel-center selection. It preserves the per-acquisition mask, uses only code-0 pixels in the initial common mask, and records provider QA as `NOT_RETRIEVED`. The full path is not yet validated against real RTC-S1 pixels and is not wired into the interface.

The existing catalog lists the selected VV assets at 7,137,589 bytes and 7,130,774 bytes, and their masks at 52,762 and 52,780 bytes. Once the ASF authorization is effective, retrieve both dates for the same burst, inspect actual grid registration and mask coverage, then run the new manifest-producing pair path. Keep this result identified as OPERA RTC-S1/Sentinel-1; it cannot clear any NISAR QA hold.

### Same-account authorization follow-up

The earlier same-account probe of ASF's temporary S3 credential endpoint, `https://sentinel1.asf.alaska.edu/s3credentials`, returned Earthdata `403 invalid_token` with `EULA Acceptance Failure`. No temporary credentials were issued and no S3 object was read in that attempt. This failure was later resolved for the bounded ASF HTTPS path; it does not establish that the separate S3 credential endpoint was rechecked.

ASF's [S3 credentials guide](https://sentinel1.asf.alaska.edu/s3credentialsREADME) says these temporary credentials only permit in-region S3 requests. This laptop workflow is outside the source bucket's AWS region, so direct S3 credentials would not provide a usable desktop retrieval route even if issued. The existing bounded ASF HTTPS reader remains the appropriate local path once its Earthdata application/EULA authorization succeeds.

The prior selected VV asset sizes and mask sizes were within the reader's cap. At the time of those checks, the pair had not been read; that status is superseded by the live processing result below.

### Latest access and pair result

After the user reviewed the account's ASF authorization/EULA state, a fresh Earthdata Login check using the local netrc authenticated. A one-byte RTC-S1 asset range returned HTTP 206 through the ASF Cumulus and Earthdata OAuth redirect chain without the earlier 401/403 EULA failure. The live API then read both VV COGs and both masks for the 2024-05-11 / 2024-06-04 `T024-050660-IW1` pair over a 0.01° AOI. Exact EPSG:32722 grid alignment and mask checks yielded 1,199 common clear centers. The result is `DIAGNOSTIC_PRODUCT_MASKED_COMPARISON` because provider QA remains `NOT_RETRIEVED`; it does not establish a flood extent or cause. See the [live access and pair validation](../validation/opera-rtc-live-pair-2026-11-07.md).

## References

- NASA Earth Observatory, [Floods Engulf Porto Alegre](https://science.nasa.gov/earth/earth-observatory/floods-engulf-porto-alegre-152795/).
- ASF HyP3, [OPERA RTC-S1 product guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/).
- ASF HyP3, [OPERA RTC-S1 product description and access](https://hyp3-docs.asf.alaska.edu/products/).
- NASA JPL, [OPERA RTC product specification](https://www.jpl.nasa.gov/go/opera/products/rtc-product/).
- NASA Earthdata Login, [How to pre-authorize an application](https://urs.earthdata.nasa.gov/documentation/for_users/how_to_preauth_app).
