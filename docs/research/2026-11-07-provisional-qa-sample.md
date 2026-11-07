# PROVISIONAL GCOV QA sample across four regions

**Reviewed:** 2026-11-07 UTC  
**Disposition:** Eight sampled products remain on provider QA hold  
**Raster analysis:** None performed

## Question

Could ECHO use another recent PROVISIONAL NISAR pair to reach its first real-data comparison, or do the sampled products share the same provider QA failure as the current event cases?

## Method

Using the pinned ASF Search client, ECHO queried PROVISIONAL GCOV from 2026-07-01 through 2026-11-07 at four geographically separated points: Istanbul, Kathmandu, Japan, and Mozambique. At each point, it selected the metadata-compatible pair with the latest post-event acquisition. It then retrieved the canonical QA summary CSV for both scenes using the bounded, Earthdata-authenticated reader. No HDF5 product, QA report PDF, or radar raster was read in this sample.

The full query coordinates, retrieval times, selected scene metadata and footprints, pair records, QA check rows, artifact URIs, byte counts, and hashes are preserved in [`provisional-qa-sample-2026-11-07.json`](../../data/research/provisional-qa-sample-2026-11-07.json).

## Findings

| Area | Before | After | QA result |
|---|---|---|---|
| Istanbul | 2026-10-09, orbit 6291 | 2026-10-21, orbit 6464 | both FAIL |
| Kathmandu | 2026-10-06, orbit 6252 | 2026-10-18, orbit 6425 | both FAIL |
| Japan | 2026-10-09, orbit 6293 | 2026-10-21, orbit 6466 | both FAIL |
| Mozambique | 2026-10-04, orbit 6218 | 2026-10-16, orbit 6391 | both FAIL |

All eight summaries report `FAIL` for “Passes all identification group checks?” and `PASS` for the input-open, coordinate-grid, calibration-LUT, four decimated backscatter, and no-exceptions checks. Each is 1,441 bytes and has the same SHA-256: `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`. The CSV does not identify the QA software version; ECHO records it as unknown rather than inferring it.

This is a targeted sample, not an archive-wide census. Its matching checksums and dispositions indicate that another sampled PROVISIONAL pair is unlikely to bypass the current QA gate. They do not prove that all PROVISIONAL products have the same result, identify the exact failed fields, or establish whether the products are suitable for a particular scientific measurement.

## Decision and limits

Do not switch to one of these pairs or weaken ECHO's analysis gate to obtain a real-data result. Continue to seek a product whose QA evidence is reconciled or a provider disposition that resolves the identification failure. The next pixel-level work remains conditional on that evidence.

This sample is evidence about provider QA artifacts only. It is not a measurement, validation of ECHO's change method, or evidence about any event in the four regions.
