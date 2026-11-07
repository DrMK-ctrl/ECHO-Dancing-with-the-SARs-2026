# Decision 0008: support VALIDATED GCOV and distinguish revisits from granules

**Date:** 2026-11-07  
**Status:** Implemented; live catalog and metadata access verified

## Context

ASF Search now returns NISAR VALIDATED GCOV products in collection `NISAR_L2_GCOV_V1`, but the catalog client and remote-product allowlist only supported BETA and PROVISIONAL collections. The live 21–24 October catalog query also returned many same-orbit, same-frame granules with acquisition times seconds apart. The previous metadata matcher considered adjacent timestamps and footprint intersection without requiring distinct orbital passes, so it could nominate adjacent granules as temporal change pairs.

## Decision

Accept the exact VALIDATED GCOV collection and maturity in catalog queries, CLI options, and bounded product access. Preserve the provider's returned collection and CRID; map collection maturity explicitly rather than relying on token position.

Only nominate NISAR temporal pairs when both products have known, distinct orbit numbers, complete acquisition intervals, nonoverlapping before/after intervals, and compatible collection, path/frame, direction, polarization, bandwidth, processing, and intersecting footprints. Carry orbit and acquisition interval fields into candidates and measurement manifests. Missing orbit or interval metadata yields no candidate.

## Evidence and limits

- Offline tests cover VALIDATED query and access allowlisting, maturity naming, same-orbit rejection, overlapping-interval rejection, and analysis-manifest temporal lineage.
- A live ASF Search query returned 197 VALIDATED GCOV products from 2026-10-21 through 2026-10-23 across a broad 2026-06-17 through 2026-11-07 query. A 2026-10-21 through 2026-10-24 query returned 210 products; the updated matcher produced zero temporal pairs from those products.
- Nepal's August–September and Mozambique's January–February target-period queries returned no VALIDATED GCOV products.
- A real `P05036` VALIDATED product was accessed with bounded Earthdata-authenticated metadata reads and its 1,441-byte QA summary was retrieved. The source CSV reports an identification-group `FAIL`; ECHO preserves this per-product hold despite collection-level VALIDATED status. No pixel values were analyzed.
- No real NISAR pair has passed ECHO's analysis gates. This change improves discovery and rejects a false temporal relationship; it does not establish a scientific finding.

## Consequences and open work

- Geographic and temporal discovery now includes VALIDATED GCOV wherever ASF returns it, but the current CLI still takes a point rather than a polygon AOI.
- The current matcher is NISAR-specific because it uses NISAR absolute orbit identity. Other missions will need their own acquisition identity and cadence rules before they can use this pairing path.
- Full source-QA artifact ingestion, spatial AOI-to-pixel selection, registration, and multi-date time-series analysis remain future work.

## References

- ASF, [NISAR Data Products and maturity levels](https://nisar-docs.asf.alaska.edu/products-overview/).
- ASF, [NISAR VALIDATED known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- ECHO, [provenance-gated pair measurement](0007-provenance-gated-pair-measurement.md).
