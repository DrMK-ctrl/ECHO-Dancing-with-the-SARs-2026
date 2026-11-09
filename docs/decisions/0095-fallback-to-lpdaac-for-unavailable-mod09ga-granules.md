# Fall back to LP DAAC for unavailable LAADS MOD09GA granules

## Decision

Keep LAADS OPeNDAP server-side constraints as the first retrieval route. If the exact granule's LAADS endpoint returns HTTP 404, retrieve the protected product from the exact HDF link returned by NASA CMR through LP DAAC Earthdata Cloud, then read the required native-grid window locally with GDAL. Do not retry the unchanged missing LAADS path.

## Evidence

- Earthdata authentication succeeded. The direct LP DAAC protected product route returned HTTP 206 for a one-byte range request and HTTP 200 for each of the two T024 granules.
- The T024 May 11 MOD09GA granule returned HTTP 404 through the legacy LAADS OPeNDAP path and was retrieved through its CMR-linked LP DAAC HDF link. The June 4 granule remained available through LAADS OPeNDAP: all ten bounded subset requests returned HTTP 200.
- The previous T163 MOD09GA screens used LAADS bounded OPeNDAP reads successfully. Keeping that path first preserves its smaller server-side subsets.
- The CMR JSON feed does not include the hit count in its body; the screener now takes it from `CMR-Hits`, records and checks every page, and rejects incomplete or changing result totals. The T024 exact-date searches each returned two catalog entries on one page.
- The bounded screen retained six common 500 m red/NIR centers. All six have top-ranked red/NIR band QA, but their associated 1 km state QA has land/water codes 2 or 3 and cloud-state code 1. Zero centers pass the paired vegetation gate.
- No NDVI difference is computed. H4 remains unresolved, and the MODIS optical screen does not validate the SAR measurement or its cause.

## Tradeoff and limits

The fallback is a whole-granule download (bounded to 256 MiB per product) followed by a native-grid crop; it is not a server-side spatial subset. For T024, one fallback file of 79,352,014 bytes was deleted after processing. Its source URL, byte count, and SHA-256 checksum remain in the candidate record, alongside the single LAADS 404 and the ten successful June 4 subsets (138,965 response bytes). The fallback requires `gdalinfo`, `gdal_translate`, and Rasterio. The result is quality-limited context; the 1 km state flags are coarser than the 500 m reflectance and the AOI contains only six common measurement centers.

See the [T024 MOD09GA validation record](../validation/mod09ga-lpdaac-screen-T024-2026-11-09.md).
