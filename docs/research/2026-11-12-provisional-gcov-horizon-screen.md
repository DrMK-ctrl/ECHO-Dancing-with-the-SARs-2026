# PROVISIONAL GCOV horizon screen — 2026-11-12

## Why this search was run

The previous global PROVISIONAL screens began on October 7. ASF documents PROVISIONAL L-band GCOV acquisitions from June 17 through part of October 23, 2026. This screen covers the previously unsearched June 17–July 17 interval. ASF describes PROVISIONAL data as calibrated and partially validated; it remains a different maturity from VALIDATED data, and the two must not be treated as interchangeable.

## Catalog result

The existing `screen_validated_gcov_time_series.py` tool was used with maturity `PROVISIONAL`, one inclusive acquisition date per query, the global catalog, and normal ASF pagination. All 31 date windows completed. None failed or reached the 2,000-feature daily cap.

| Measure | Result |
|---|---:|
| Unique scenes | 43,564 |
| Metadata temporal candidates | 14,485 |
| Full/full footprint candidates | 11,172 |
| Full/full candidates intersecting the coarse Iraq WGS84 bounds (39–49°E, 29–38°N) | 59 |

Footprint intersection and catalog metadata are discovery filters only. They do not establish aligned grids, common valid measurement pixels, accepted provider QA, or physical change.

The complete catalog response is preserved losslessly in [`provisional-gcov-global-time-series-2026-06-17-07-17.json.gz`](../../data/research/provisional-gcov-global-time-series-2026-06-17-07-17.json.gz). SHA-256 of its uncompressed JSON is `bd352730512cebfcc4c597c5a2417bc363483412a774d0a2e27a7f98c2ddfe55`; the gzip stream was decompressed and byte-verified against that digest. The record contains per-day query status, pagination, source feature hashes, geometries, and matcher output.

## Exact-pair QA screen

The first geographically complete candidate near central Iraq was selected for canonical ASF QA retrieval:

- Track/path 64, frame 72, descending; CRID `P05023`; HH/HV.
- Before: `NISAR_L2_PR_GCOV_023_064_D_072_4005_DHDH_A_20260618T153515_20260618T153551_P05023_N_F_J_001`
- After: `NISAR_L2_PR_GCOV_024_064_D_072_4005_DHDH_A_20260630T153514_20260630T153551_P05023_N_F_J_001`
- Catalog interval: 12 days; both catalog frame-coverage labels are `Full`.
- Both canonical ASF QA CSVs returned `FAIL` on `Passes all identification group checks?`; the other eight reported checks passed.

The initial source-linked CSV record is [`provisional-gcov-iraq-p05023-path64-frame72-qa-review-2026-11-12.json`](../../data/research/provisional-gcov-iraq-p05023-path64-frame72-qa-review-2026-11-12.json). A follow-up retrieved both canonical QA report PDFs and parsed the product metadata under the pinned GCOV 1.5.0 contract: [`full QA review`](../../data/research/provisional-gcov-iraq-p05023-path64-frame72-full-qa-review-2026-11-12.json). Both reports use `nisarqa` 17.0.0, parse completely with no required contract metadata missing, and their orbit, track, and frame values match the ASF catalog. Both report `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`.

ECHO then read only the 12 allowlisted `/science/LSAR/identification` fields from each product over authenticated byte-range access; all were present and the two values above were reproduced from the products. The checksummed [two-scene identification record](../../data/research/provisional-gcov-iraq-p05023-path64-frame72-identification-review-2026-11-12.json) preserves both reads. No radar measurement arrays were accessed.

The pinned [`nisarqa` v17.0.0 identification checks](https://github.com/isce-framework/nisarqa/blob/v17.0.0/src/nisarqa/validate/sanity_checks.py) accept `L-SAR` or `S-SAR` for `instrumentName` and validate `listOfObservationModes` against a formatted mode pattern. The two values read from these products do not satisfy those source rules and are sufficient to make the identification-group logic fail. The QA CSV exposes only the aggregate identification-group `FAIL`, however, so ECHO cannot determine from ASF's retained summary whether these are the only failing fields. This is a source-code explanation of the observed failure mechanism, not a provider per-field attribution or a change to the provider disposition.

NASA's [GCOV Product Specification, Revision F, Version 1.5.0](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf) describes `instrumentName` as the instrument name and describes `listOfObservationModes` as the modes of the L0B granules used to generate the input RSLC. It describes `instrumentName` as a string but does not enumerate accepted string values in that table. The available specification text does not establish that the source-rule discrepancies should be ignored. The retrieved PDF's SHA-256 was `bfddc039eab7ad328f63e8425fa8f0e0b10f9ee339983c918b13b9f6d57d89a2`. Therefore the provider QA result remains `FAIL`, and no product arrays or paired measurements were read.

## Assessment and next action

The earlier shortage of candidates was partly a search-horizon gap: the June–July PROVISIONAL archive contains many catalog-compatible repeats. For this pair, the failure mechanism is now strongly localized to identification metadata that violate the pinned QA software's source rules, rather than an absent acquisition, catalog mismatch, missing required report field, or a demonstrated defect in ECHO's comparison implementation. This does not prove that every P05023 candidate fails, nor that the backscatter measurements are analytically invalid; it does mean these exact products remain provider-QA-held. Another same-release sample has lower value than checking for a new processing release or a changed provider QA disposition.

Keep the existing QA gate closed. Reopen this pair only if ASF changes either product, its canonical QA summary, or the processing release. A new NISAR temporal result still requires QA acceptance, product identity/metadata checks, grid and valid-pixel overlap checks, and a recorded reproducible measurement. The validated P05036 samples remain a separate release-specific QA issue.

## Sources

- ASF, [NISAR product overview](https://nisar-docs.asf.alaska.edu/products-overview/) — maturity collections, provisional date coverage, calibration/validation status, and warning against mixing processing maturities.
- ASF, [PROVISIONAL product known issues](https://nisar-docs.asf.alaska.edu/provisional-known-issues/) — P05023 known limitations and provisional scope.
