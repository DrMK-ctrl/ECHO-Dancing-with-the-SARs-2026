# Decision 0012: select bounded GCOV windows from a geographic bbox

**Date:** 2026-11-07

**Status:** Implemented for WGS84 rectangles; real-data access validated, analysis remains QA-gated

## Context

The GCOV reader accepted caller-supplied row and column indices, but had no reproducible link from a geographic area to the product's projected pixel grid. This made map-driven investigation depend on manual index guessing and left the geographic bounds out of the analysis lineage.

## Decision

Allow `read_gcov_window` to take either explicit row/column slices or a WGS84 bbox `(west, south, east, north)`. For bbox selection, read the product EPSG code and complete 1-D x/y coordinate vectors under a 16 MiB coordinate-array limit. Use pyproj with x/y axis order fixed and a densified CRS bounds transform to find an enclosing raster window. Inverse-transform the pixel-center mesh and create a Boolean mask containing only centers inside the original closed WGS84 rectangle.

Keep the existing maximum 512 × 512 sample count, 16 MiB returned-array budget, and 64 MiB cumulative remote-range budget. Include the exact bbox, CRS, transform description/accuracy, software versions, window indices, and selected-center count in the returned selection metadata. Do not persist the pixel arrays.

Paired analysis requires both windows to use identical coordinate axes, bbox metadata, and pixel-center masks. The same AOI mask is intersected with the two dates' product masks before measurement. The manifest records each AOI and mask checksum. This selection function does not evaluate product QA, establish registration beyond the existing exact-grid check, or assign physical meaning to measured differences.

Reject antimeridian-crossing bboxes for now. Callers must split such a region into separate non-crossing areas. Polygon AOIs are not implemented.

## Consequences

- A caller can request bounded data by geographic bounds without downloading a complete multi-gigabyte NISAR product.
- The returned rectangular array may enclose pixels outside the requested rectangle; its explicit Boolean selection mask identifies the pixel centers inside the AOI. Paired measurement applies that mask.
- Full coordinate-vector access adds remote range-read overhead; the call reports its byte count and remains subject to the existing range budget.
- Synthetic tests cover coordinate order, exact center masking, size limits, paired-mask matching, and the integration with bounded remote reads.
- A live bounded read of a real PROVISIONAL product verifies geographic selection and array retrieval only. The source product still has provider QA `FAIL`; no real measurement was run and no QA hold was waived.

## References

- NASA JPL, [NISAR L2 GCOV Product Specification, Rev F](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf), coordinate axes and pixel-center convention.
- ASF, [Geocoded Polarimetric Covariance (GCOV)](https://nisar-docs.asf.alaska.edu/gcov/).
- pyproj, [Transformer API](https://pyproj4.github.io/pyproj/stable/api/transformer.html), including `always_xy` and densified bounds transformation.
- ECHO, [bounded GCOV window access](0005-bounded-gcov-window-access.md) and [grid metadata](0006-gcov-grid-metadata.md).
