# ASF OPERA RTC-S1 access after EULA review

**Date:** 2026-11-12  
**Result:** Authenticated bounded access succeeded for one retained product on the configured Earthdata account.  
**Scientific disposition:** Diagnostic data access only; no consolidated provider PASS/FAIL verdict is asserted.

## Verification performed

1. A one-byte HTTP Range request to the T163 RTC-S1 VV COG returned **HTTP 206** with `Content-Range: bytes 0-0/7399882`. The redirect history included Earthdata OAuth authorization and the ASF Cumulus login flow, then delivered the requested range from the asset CDN. This establishes that the tested account could pass the authorization flow for this asset at the time of the check. The response body was not stored.
2. ECHO's existing `read_opera_rtc_s1_window` reader then retrieved a bounded WGS84 AOI window for the same scene. The 38 × 33 window contained 1,199 AOI-selected centers, all 1,199 finite. Measurement, mask, and HDF5 metadata ranges were retrieved and SHA-256 checksums recorded; source assets were held in memory and not written to disk.

The machine-readable record is [`asf-opera-rtc-authenticated-read-probe-T163-349925-2026-11-12.json`](../../data/research/asf-opera-rtc-authenticated-read-probe-T163-349925-2026-11-12.json). It records the product identity, acquisition time, AOI, grid, asset URLs, byte counts, checksums, software versions, and retrieval method without credentials or bearer tokens.

## Interpretation and limits

- ASF Cumulus access is now confirmed for this Earthdata account and this OPERA RTC-S1 item; the earlier authorization failure is no longer reproduced for this request.
- This does not establish access to every ASF collection or product, validate live catalog search, or verify Bhoonidhi access.
- The product's HDF5 sidecar has no consolidated PASS/FAIL field. ECHO retains that state and the single observation remains diagnostic; the access result does not clear any scientific QA gate.
- No new pair measurement or causal interpretation was produced by this access check.

No repository visibility, deployment, account permission, or external service setting was changed during verification.
