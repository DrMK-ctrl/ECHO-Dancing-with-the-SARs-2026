# NISAR GCOV identification QA evidence review — 2026-11-13

## Question

Do the repeated aggregate provider QA failures in the exact NISAR GCOV
candidate products establish that their measurements are unusable, or is
there evidence of an identification-metadata defect that should guide the next
step without overriding provider QA?

## Exact-product evidence

Four products from two P05036 catalog-compatible pairs were screened on
2026-11-13: the Iraq path 13/frame 18 pair and the separate path 148/frame 5
pair. Each exact ASF QA summary reports `FAIL` for the aggregate identification
group check. The other eight summary checks pass. The bounded identification
reads for these products record `instrumentName=LSAR` and
`listOfObservationModes=["(NOT SPECIFIED)"]`. The product records also report
`productSpecificationVersion=1.6.0`. No measurement arrays or grids were read
for these pair screens, and no temporal analysis was run.

The source-code cross-check against `nisarqa` v17.2.0 finds that `LSAR` is
outside its `instrumentName` allowlist (`L-SAR`, `S-SAR`) and that
`(NOT SPECIFIED)` fails its observation-mode format check. This is a partial
local comparison against one pinned validator source version. It is not a
rerun of the complete provider QA pipeline and does not attribute ASF's
aggregate result to either individual field.

## Authoritative-document comparison

The ASF-hosted NISAR GCOV guide identifies calibrated gamma-zero covariance
measurements and the GCOV HDF5 layer families. It links JPL product
specification D-102274, Revision F, version 1.5.0. That specification describes
`/science/LSAR/identification/listOfObservationModes` as one mode per input L0B
granule. Its revision history also says the field length was updated to “0”.
The online specification therefore does not unambiguously resolve the value
expected in products that themselves declare specification version 1.6.0.
The document does not define an allowed value for the `instrumentName` dataset
in the product-identification table.

An open public ISCE3 issue, #285, reports that in a prior Release 5 processing
version GCOV and related products populated `listOfObservationModes` with
`[(NOT SPECIFIED)]`; it proposes populating the field from focus metadata and
checking downstream product generation. The exact placeholder observed in
ECHO's P05036 products is consistent with that reported defect. The issue is
evidence of a known processing concern, not a per-product QA explanation or
confirmation that the current product release has the same cause.

A separate public ISCE3 issue, [#216](https://github.com/isce-framework/isce3/issues/216),
records a `nisarqa` check flagging the same `(NOT SPECIFIED)` value as invalid
in a GCOV sample product. This independently confirms that the value is
recognized by that QA tooling as a metadata problem. It still does not expose
the row-level cause behind ASF's aggregate identification-group `FAIL` for
ECHO's exact P05036 products, nor does it establish that their measurement
arrays are scientifically usable.

## Assessment and handling

The evidence supports this bounded statement: **the identification-group QA
failure is associated with a repeated metadata-format discrepancy, and the
observation-mode placeholder has been reported as a NISAR processing issue.**
It does not establish that this is the sole reason the four ASF summaries fail,
that radar measurements are otherwise suitable, or that a newer product
specification permits the observed values. The provider gives only an
aggregate group result, and the product specification version reported by the
granules is newer than the version linked from the current GCOV guide.

Accordingly, ECHO retains each provider disposition as `FAIL` and keeps both
pairs `QA_HELD`. No pair measurement analysis is authorized by this review.
Do not repeat QA retrieval for the same exact products unless ASF changes or
replaces the records. Reassess a later CRID, corrected product, or authoritative
specification update as new evidence. Until then, use the independently
qualified non-NISAR path only with its own clearly stated diagnostic limits.

## Source records and references

- Iraq P05036 pair QA, product metadata, and identification cross-checks:
  [`2026-11-13-iraq-validated-gcov-pair-qa.json`](../../data/research/2026-11-13-iraq-validated-gcov-pair-qa.json)
- Path 148/frame 5 P05036 pair QA and identification cross-checks:
  [`validated-gcov-p05036-path148-frame5-qa-2026-11-13.json`](../../data/research/validated-gcov-p05036-path148-frame5-qa-2026-11-13.json)
- ASF, [NISAR GCOV Data User Guide](https://nisar-docs.asf.alaska.edu/gcov/)
- NASA JPL, [D-102274 Rev F, L2 GCOV Product Specification, version 1.5.0](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf). Retrieved for local inspection; SHA-256 `bfddc039eab7ad328f63e8425fa8f0e0b10f9ee339983c918b13b9f6d57d89a2`.
- ISCE Framework, [`nisarqa` v17.2.0 identification checks](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py), commit `4d40bbcf9864d006c5e2656b0b9901caa51c95bf`.
- ISCE Framework, [ISCE3 issue #285: missing/unpopulated `listOfObservationModes`](https://github.com/isce-framework/isce3/issues/285), opened 2026-06-04; page showed the issue open when reviewed.

This review was conducted from public product documentation and retained local
records. No external party was contacted, and no project files or credentials
were transmitted.
