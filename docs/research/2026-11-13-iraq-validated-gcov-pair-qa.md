# Iraq VALIDATED GCOV pair: product-level QA screen

**Catalog query:** 2026-11-13 04:24:14 UTC  
**Provider:** Alaska Satellite Facility DAAC (ASF)  
**Collection:** NISAR L2 GCOV VALIDATED V1, CRID P05036

## Catalog candidate

The bounded Iraq AOI `[43.8, 32.5, 45.0, 33.5]` was searched from October 1
through November 12, 2026, with `VALIDATED` maturity. ASF returned six product
records and one metadata-compatible 12-day candidate. The returned result set
was below the 1,000-record cap and was not marked potentially truncated.

The candidate is a full-coverage ascending repeat on path 13/frame 18 with HH
and HV polarization:

| Role | Acquisition | Orbit | Product |
| --- | --- | ---: | --- |
| Before | 2026-10-25 02:10:15 UTC | 6513 | `NISAR_L2_PR_GCOV_034_013_A_018_2005_DHDH_M_20261025T021015_20261025T021050_P05036_N_F_J_001` |
| After | 2026-11-06 02:10:16 UTC | 6686 | `NISAR_L2_PR_GCOV_035_013_A_018_2005_DHDH_M_20261106T021016_20261106T021050_P05036_N_F_J_001` |

ASF's catalog maturity is `VALIDATED`; that label describes the collection
maturity and does not supersede either product's own QA disposition.

## Product QA results

The canonical 1,441-byte ASF QA summary was retrieved for each exact scene
through ECHO's bounded QA route, using local Earthdata authentication. Both
summaries have SHA-256
`8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`. Each
reports `FAIL` for “Passes all identification group checks?” and `PASS` for the
other eight checks, including coordinate-grid metadata, calibration LUTs,
four decimated-raster validity checks, and QA completion.

The identical hashes show that the two downloaded QA summaries contain the
same bytes. A separate bounded HDF5 identification read on each exact product
found the same fields and values: `instrumentName=LSAR` and
`listOfObservationModes=["(NOT SPECIFIED)"]`, alongside matching mission,
orbit, track, and frame identifiers. ECHO's pinned `nisarqa` 17.2.0 source
cross-check flags both strings as mismatches against its instrument-name and
observation-mode rules. This is consistent with the earlier P05036 pair
reviews.

ASF's QA CSV reports only an aggregate identification-group `FAIL`; it does
not attribute that provider result to either field individually. The source
cross-check is a plausible explanation of the aggregate failure, not a
provider per-field verdict. The exact QA PDFs were not retrieved. The complete
allowlisted reads requested about 4.45 MB of HTTP range data per product, did
not download either HDF5 product, and read no measurement arrays.

## Disposition

**QA-held; no measurement analysis attempted.** Only allowlisted HDF5
identification metadata was read; no raster arrays were read. The pair does
not establish a temporal change result and cannot enter accepted analysis
while either provider QA status is `FAIL`.

This is the sixth retained P05036 metadata-repeat pair identified in ECHO's
current Iraq-area screens. The other five have separate QA-report and product
metadata evidence documented in the [earlier P05036 review](2026-11-11-p05036-gcov-qa-root-cause.md).
Do not repeat QA retrieval for these exact two scenes unless ASF changes a QA
summary, replaces a product, or posts a new processing release. A different
CRID or materially changed product is a separate candidate and must be screened
on its own evidence.

A separate single-scene HHHH preview was later retrieved from the October 25
product and remains explicitly QA-held diagnostic; it does not change this
pair disposition. See the [preview validation](../validation/iraq-nisar-qa-held-backscatter-preview-2026-11-13.md).

The exact bounded catalog response, pair metadata, QA records, bounded product
identification records, retrieval timestamps, and checksums are retained in
[`2026-11-13-iraq-validated-gcov-pair-qa.json`](../../data/research/2026-11-13-iraq-validated-gcov-pair-qa.json).
Manifest SHA-256: `0e6188df940b5140438a60a68f3e38c1f6000a4b3cf50890fa0dec7fe270521f`.
