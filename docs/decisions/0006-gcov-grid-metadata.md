# Decision 0006: retain grid metadata with GCOV windows

**Date:** 2026-11-07  
**Status:** Accepted for bounded reads; cross-date registration remains unverified

## Context

ECHO's bounded reader returned pixel arrays and their index slices, but the indices had no spatial meaning without the product grid. NASA's GCOV specification describes a `projection` grid-mapping dataset and one-dimensional `xCoordinates` and `yCoordinates` dimension scales whose values identify pixel centers.

## Decision

For every requested GCOV window, require the allowlisted frequency group to contain `projection`, `xCoordinates`, and `yCoordinates`. Read the projection value and selected coordinate-vector slices alongside the requested data layers. Preserve the projection attributes relevant to CRS identification, including the EPSG code. Require coordinate vectors to match the raster dimensions, be finite, and be monotonic within the requested window. Return these values with the window and count their array bytes against the bounded memory limit.

The reader records a window's coordinates; it does not transform a user AOI into pixel indices or prove that two products are co-registered. A later pair-analysis step must compare CRS, coordinate vectors, and registration evidence before computing change.

## Evidence and limits

- 39 offline tests passed, including synthetic grid metadata and requested coordinate-slice checks.
- On the same real PROVISIONAL scene used in Decision 0005, the reader returned the selected coordinate centers and EPSG:32736 with the 100 × 100 data arrays.
- The expanded read reported 37,884,386 fsspec range bytes for an estimated 101,600 bytes of output arrays and coordinates. HDF5 metadata, chunking, and read-ahead contributions were not isolated. This is one access observation, not a performance benchmark.
- No pixel values were analyzed. Product QA, cross-date registration, and scientific suitability remain unverified; current case QA holds are unchanged.

## Consequences and open work

- Window arrays can now retain their coordinate reference and pixel-center vectors for later provenance and alignment checks.
- Array indices remain caller-supplied. Interactive AOI drawing, CRS transformation, grid intersection, and common-overlap calculation are not implemented.
- A source/analysis manifest should link the scene identifiers, CRS/grid coordinates, QA references, method, parameters, software versions, and derived-output checksum when pair processing is introduced.

## References

- NASA JPL, [NISAR L2 GCOV Product Specification, Rev F](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf), Section 3.2.5.
- ASF, [Geocoded Polarimetric Covariance (GCOV)](https://nisar-docs.asf.alaska.edu/gcov/).
- ECHO, [authenticated streaming probe](../research/2026-11-07-authenticated-streaming-probe.md).
