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

## Next validation gates

The authenticated ASF HTTPS request was rechecked on 2026-11-07: Earthdata Login authenticated, but the product URL redirected through ASF Cumulus to Earthdata's application-authorization flow and ended in HTTP 401. The redirect identified ASF Cumulus client ID `BO_n7nTIlMljdvU6kRRB3g`. An anonymous read of the corresponding S3 object returned HTTP 403. No OPERA raster bytes have been read. Earthdata documents pre-authorizing command-line data-access applications through its application authorization page; the exact ASF client can be opened at [this Earthdata authorization link](https://urs.earthdata.nasa.gov/approve_app?client_id=BO_n7nTIlMljdvU6kRRB3g).

After that application is authorized, retrieve a small VV/VH window and its product mask/geometry layers for the same burst on both dates. Confirm exact product IDs, CRS, affine transforms, dimensions, pixel registration, data type/units, no-data codes, masks, byte-range behavior, and source checksums. Only then run the existing log-ratio primitive through a Sentinel-1-specific adapter and compare the resulting measurements with clearly labeled contextual evidence. Keep this result identified as OPERA RTC-S1/Sentinel-1; it cannot clear any NISAR QA hold.

## References

- NASA Earth Observatory, [Floods Engulf Porto Alegre](https://science.nasa.gov/earth/earth-observatory/floods-engulf-porto-alegre-152795/).
- ASF HyP3, [OPERA RTC-S1 product guide](https://hyp3-docs.asf.alaska.edu/guides/opera_rtc_product_guide/).
- ASF HyP3, [OPERA RTC-S1 product description and access](https://hyp3-docs.asf.alaska.edu/products/).
- NASA JPL, [OPERA RTC product specification](https://www.jpl.nasa.gov/go/opera/products/rtc-product/).
- NASA Earthdata Login, [How to pre-authorize an application](https://urs.earthdata.nasa.gov/documentation/for_users/how_to_preauth_app).
