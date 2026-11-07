# Decision 0005: bounded authenticated GCOV window access

**Date:** 2026-11-07  
**Status:** Accepted for data access; geographic selection, caching, and analysis integration remain open

## Context

ASF supports Earthdata-authenticated HTTPS range access to NISAR HDF5 products. ECHO previously verified one small window through an exploratory probe, while its reusable access module inspected only identification metadata. The application needs a bounded path from an ASF catalog feature to selected arrays without downloading multi-gigabyte products.

## Decision

Extend the existing `echo.nisar_access` module with `read_gcov_window` and share one authenticated remote-product opener with the existing identification inspector. Initially restrict the reader to the known BETA and PROVISIONAL GCOV collections; decision 0008 adds the exact VALIDATED collection after its release. Require explicit frequency A or B, documented GCOV layers, and non-negative row and column slices. Apply limits of 512 × 512 samples, 16 MiB estimated returned arrays, 64 MiB cumulative HTTPS ranges, and a 1 MiB read-ahead block.

Return arrays in memory with their selected indices, a bounded subset of ASF catalog metadata, and the range-access record. Do not persist source pixels or derive pixel indices from a geographic AOI inside this reader.

## Evidence and limits

- 39 offline tests passed, including allowlist, slice, authentication, and window-read behavior against synthetic arrays.
- The initial reader was exercised against one real PROVISIONAL GCOV granule. It returned `HHHH`, `mask`, `numberOfLooks`, and `inputDataExceptionMask` as 100 × 100 arrays through Earthdata-authenticated HTTPS range requests. A later amendment added grid metadata; see [Decision 0006](0006-gcov-grid-metadata.md).
- Initial fsspec accounting reported 27,978,510 range bytes requested for 100,000 bytes of returned arrays. This one HDF5 read showed substantial metadata and range-read overhead; it did not establish typical latency or resource use across products.
- The scene's pixels were not analyzed. The Mozambique and Nepal candidate pairs remain on QA hold. This access check neither clears QA nor verifies geographic alignment or scientific suitability.

## Consequences and open work

- Reusable data access now shares the existing authentication and ASF URL validation boundary.
- The API caller must still map a geographic AOI into verified product-grid indices and determine whether a product is suitable for the intended analysis.
- No provenance-aware persistent cache exists. The observed range amplification motivates a later cache design, but cache keys, retention, licensing, integrity verification, and invalidation require a separate decision.
- The array-size limit estimates returned NumPy arrays; it is not a measurement of total process peak memory. The current access record does not claim 16 GB workstation benchmarking.
- The local interface does not yet invoke this API or display SAR rasters.

## References

- ASF, [Finding NISAR Data with Earthaccess](https://nisar-docs.asf.alaska.edu/earthaccess/).
- ASF, [Geocoded Polarimetric Covariance (GCOV)](https://nisar-docs.asf.alaska.edu/gcov/).
- ECHO, [authenticated streaming probe and reusable-reader evidence](../research/2026-11-07-authenticated-streaming-probe.md).

## Operational amendment: smaller remote read blocks

**Date:** 2026-11-07

A same-product live comparison changed only the fsspec read-ahead block size for one 56 × 43 pixel Istanbul diagnostic window. At 1 MiB, the reader requested 38,298,606 range bytes and took 162.49 seconds. At 256 KiB, it requested 11,567,896 range bytes and took 83.95 seconds. The seven returned layer/coordinate/selection arrays matched the previously retained diagnostic window byte-for-byte after hashing their raw typed array contents. Both measurements remained explicitly `QA_HELD_DIAGNOSTIC_ONLY`; no temporal analysis was performed.

ECHO now uses 256 KiB blocks. The measured byte reduction is useful for this read, but latency is a single sequential comparison over a changing network and is not a general performance guarantee. HTTP request count was not recorded. The complete record is [`gcov-range-block-benchmark-2026-11-07.json`](../research/gcov-range-block-benchmark-2026-11-07.json).
