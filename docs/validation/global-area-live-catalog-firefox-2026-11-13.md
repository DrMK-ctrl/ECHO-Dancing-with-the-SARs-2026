# Global area search through live NISAR catalog

**Verification time:** 2026-11-13 14:16 UTC
**Checkout:** `main`, local source, interactive server bound to `127.0.0.1`
**Provider:** ASF CMR, NISAR GCOV catalog metadata

## Method

Started the current checkout's interactive application locally and used Firefox to open the no-case global exploration page. For each search, entered a rectangular WGS84 area, set the same inclusive date window (`2025-07-01` through `2026-11-13`) and `PROVISIONAL` maturity, then submitted through ECHO's catalog dialog. The browser captured the same-origin response and observed the rendered timeline, map footprint polygons, and evidence panel. No credentials were entered and no product pixels were downloaded.

## Live searches

| Area | WGS84 bounds (west, south, east, north) | HTTP | GCOV catalog records |
|---|---|---:|---:|
| Kyoto, Japan | `135.65, 34.95, 135.90, 35.15` | 200 | 39 |
| Dakar, Senegal | `-17.55, 14.60, -17.30, 14.85` | 200 | 20 |
| Antananarivo, Madagascar | `47.35, -19.05, 47.60, -18.80` | 200 | 28 |

Example returned product identifiers included:

- Kyoto: `NISAR_L2_PR_GCOV_033_075_D_071_4005_DHDH_A_20261017T095323_20261017T095358_P05023_N_F_J_001`
- Dakar: `NISAR_L2_PR_GCOV_033_059_A_009_4005_DHDH_A_20261016T063954_20261016T064028_P05023_N_F_J_001`
- Antananarivo: `NISAR_L2_PR_GCOV_033_099_A_168_4005_DHDH_A_20261019T024542_20261019T024615_P05023_N_F_J_001`

For the Dakar search, Firefox displayed all 20 returned observations in the timeline and all 20 footprints on the map. Eighteen use the ordinary catalog-footprint style; one is highlighted as the metadata pair's before scene and one as its after scene. The evidence panel appears after the search.

## What this verifies—and what it does not

This verifies that the global entry can submit real user-selected geographic bounds and dates to the live ASF NISAR GCOV catalog, and that returned metadata reaches the map and timeline for three geographically separate areas not selected from the saved-case list. It is more than a saved-case switch: each query used the user's AOI and live provider response.

The catalog response is availability metadata. This check does **not** establish provider QA acceptance, pixel access, measurement validity, compatible temporal observations, or a scientifically supported change result. Catalog pair candidates remain metadata candidates until the separate QA and pixel-analysis gates pass. A live ASF outage or network failure remains an external dependency; the application reports catalog failure separately from a successful search returning zero records.

The current server still needs a registered case context to route case-scoped API requests, even though the live GCOV query is formed from the submitted AOI and dates. The provider search itself is not restricted to the default case footprint. Treat this as a current server-context coupling to revisit if ECHO later supports a case-free service configuration.
