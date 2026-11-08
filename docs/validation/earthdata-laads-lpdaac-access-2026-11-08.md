# Earthdata access verification: LAADS and LP DAAC — 2026-11-08

## Result

Authenticated bounded reads succeeded against both LAADS and the LP DAAC Earthdata Cloud. This verifies current account-backed access to these endpoints; it does not establish that a particular source is scientifically suitable.

## Method and evidence

ECHO used `earthaccess` 0.19.0 with the existing local Earthdata `.netrc` entry (`0600` permissions). `earthaccess.login(strategy="netrc", persist=False)` returned authenticated, and its in-memory session made two HTTP range requests. No credential or token value was logged or persisted by this probe.

| Service and role | Request | UTC time | Response |
|---|---|---|---|
| LAADS DAAC authentication check | [`https://ladsweb.modaps.eosdis.nasa.gov/archive/README`](https://ladsweb.modaps.eosdis.nasa.gov/archive/README), bytes `0–127` | `2026-11-08T12:02:47.798203+00:00` | HTTP `206`; `Content-Range: bytes 0-127/35552` |
| LP DAAC Earthdata Cloud product check | [`MOD13Q1.A2024129.h13v11.061.2024153222252.hdf`](https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MOD13Q1.061/MOD13Q1.A2024129.h13v11.061.2024153222252/MOD13Q1.A2024129.h13v11.061.2024153222252.hdf), bytes `0–127` | `2026-11-08T12:02:49.591457+00:00` | HTTP `206`; `Content-Range: bytes 0-127/188902308` |

The MOD13Q1 product URL is on LP DAAC's cloud host, not LAADS. The successful LAADS read and successful MOD13Q1 read therefore verify two distinct services. NASA documents Earthdata application pre-authorization separately from scripted LAADS token access ([Earthdata pre-authorization](https://urs.earthdata.nasa.gov/documentation/for_users/how_to_preauth_app), [LAADS token access](https://ladsweb.modaps.eosdis.nasa.gov/learn/download-files-using-edl-tokens/)).

## Scientific boundary

The range response proves that the account-backed session could read bytes from the identified MOD13Q1 object. It is not a full-file checksum or retrieval, a product-quality assessment, or new scientific evidence. The retained T163 MOD13Q1 screen found zero paired native-grid cells passing its declared land and QA criteria and is already classified as interpretation-limited. No MODIS measurements or relationships were promoted by this access check. See [the retained candidate screen](../../data/research/mod13q1-vegetation-candidate-T163-349925-2026-11-08.json) and [its validation](mod13q1-vegetation-screen-T163-2026-11-08.md).
