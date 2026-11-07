# VALIDATED GCOV product QA report review — 2026-11-07

## Scope

Review the provider-generated QA report for one NISAR VALIDATED GCOV product after its canonical ASF QA summary returned an identification-group failure. This is a product-quality evidence review, not radar measurement analysis.

## Product and artifacts

- Provider: NASA NISAR product distributed by the Alaska Satellite Facility DAAC.
- Collection: `NISAR_L2_GCOV_V1` (VALIDATED).
- Product: `NISAR_L2_PR_GCOV_033_141_D_085_4005_DHDH_A_20261021T235335_20261021T235345_P05036_N_P_J_001`.
- Product URL: `https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_GCOV_V1/NISAR_L2_PR_GCOV_033_141_D_085_4005_DHDH_A_20261021T235335_20261021T235345_P05036_N_P_J_001/NISAR_L2_PR_GCOV_033_141_D_085_4005_DHDH_A_20261021T235335_20261021T235345_P05036_N_P_J_001.h5`.
- Summary artifact: the matching `_QA_SUMMARY.csv`; 1,441 bytes, SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`.
- Report artifact: the matching `_QA_REPORT.pdf`; 254,569 bytes, SHA-256 `1e1b281b0fcc42efac1bb9940e8f3b1399189824b9beb4845f88dfda5f5a6176`.
- Statistics artifact: the matching `_QA_STATS.h5`; 72,840 bytes, SHA-256 `28f7c7116e14f7cc04b0becaa20fde09ad06780373bb4e2bd323e1b21193b718`.
- All three artifacts are under the product's canonical ASF directory. Retrieval used Earthdata-authenticated access. The summary reader recorded a 1,441-byte HTTPS range. The report and statistics file were retrieved as bounded artifacts; no GCOV measurement raster was read for this review.

## Observed report content

The PDF identifies QA software version `17.2.0`, QA processing time `2026-11-07T03:01:03 UTC`, and ISCE3 software version `0.25.21`. Its product identification table reports `instrumentName=LSAR`, `listOfObservationModes=['(NOT SPECIFIED)']`, product specification version `1.6.0`, product version `1.0.20`, absolute orbit 6468, track 141, and frame 85.

The companion CSV reports `FAIL` for “Passes all `identification` group checks?”. It reports PASS for input opening, coordinate-grid metadata, calibration LUT metadata, four backscatter checks, and completion without exceptions. The report notes that crosstalk checks were skipped and backscatter checks were decimated. These checks do not establish suitability of a particular study-area window.

ECHO re-fetched the canonical CSV through its bounded reader using Earthdata Login. The response was the same 1,441-byte artifact and SHA-256 recorded above, with 1,441 requested range bytes. Supplying QA version `17.2.0` from the separately reviewed PDF to ECHO's source cross-check produced candidate mismatches for `instrumentName` and `listOfObservationModes`; the provider disposition remained `FAIL`. This confirms ECHO's diagnostic path against the real artifact, not the exact internal QA log or the validity of radar measurements.

## Validator cross-check and specification boundary

The QA report names software 17.2.0. The matching public `nisarqa` tag is commit `4d40bbcf9864d006c5e2656b0b9901caa51c95bf`; its release adds the product-specification 1.6.0 XML. At that tag, `sanity_checks.py` accepts only `L-SAR` or `S-SAR` for `instrumentName`. Its observation-mode check expects a formatted mode string, and `(NOT SPECIFIED)` does not match that format. The two exact values read from this HDF5 product therefore match two conditions that the reported QA software source marks invalid.

The QA CSV reports only the aggregate identification-group failure, so it does not prove these are the only failed fields or provide the product-specific failure log. The matching implementation and observed metadata make these concrete explanations for the group failure, but are not a replacement for the provider's per-field disposition.

## QA statistics artifact inspection

ECHO retrieved the canonical QA statistics HDF5 artifact through the authenticated ASF redirect and inspected its 72,840-byte content. The artifact records institution `NASA JPL`, QA software `17.2.0`, QA processing time `2026-11-07T03:01:03`, and QA specification reference `D-107726`. Its QA group contains per-frequency and per-polarization backscatter summary statistics and histogram data. The identification section repeats the instrument, observation-mode, product-specification, and product-version values shown in the PDF.

The statistics artifact does not include per-field identification failure results or a failure reason. The expected `_QA_LOG.txt` path and the `_QA_LOG.log` variant both returned HTTP 404; the summary, report, and statistics artifacts returned successfully. The HDF5 adds provenance and QA context but does not resolve the aggregate provider failure. Its backscatter statistics are product-wide QA summaries, not measurements for ECHO's AOI and not evidence that a scene is suitable for temporal comparison.

The public upstream source trail provides additional context for the placeholder value. ISCE3 issue [#216](https://github.com/isce-framework/isce3/issues/216) includes a GCOV QA example that labels `(NOT SPECIFIED)` at `listOfObservationModes` invalid for nominal NISAR data. Its linked nisarqa pull request [#155](https://github.com/isce-framework/nisarqa/pull/155) describes checks for empty datasets, placeholder strings, and selected attribute dtypes. Both tracker records were still open when checked on 2026-11-07. This supports that the QA rule intentionally flags placeholder metadata; it does not identify this granule's exact failing subchecks, settle the versioned product-specification discrepancy, or show that its measurement arrays are scientifically unusable.

The publicly accessible NASA SDS GCOV specification PDF linked by ASF is JPL D-102274 Rev F, version 1.5.0. It describes `instrumentName` as a scalar string naming the instrument and `listOfObservationModes` as a per-input-observation list, but does not enumerate allowed values in the reviewed passages. The QA repository's version 1.6.0 XML also defines these fields' types and shapes, while the QA code applies more specific value checks. The discrepancy between those sources and the observed product is not resolved here.

ISCE3 0.25.21 release notes say it renamed the default instrument name from `L-SAR` to `LSAR` for STATIC products. The note does not say this change applies to GCOV, so it cannot establish that `LSAR` is valid for this GCOV product. Keep the product on QA review hold until the provider reconciles the observed values with the applicable product specification and QA rules. Do not call the failure a false positive or claim the raster is unusable on this evidence alone.

## Reproduction and references

The product and artifact paths are derived from the exact ASF catalog record and the product granule identifier. The CSV is parsed by `echo.qa.read_qa_summary`; the PDF was downloaded from the corresponding `_QA_REPORT.pdf` object and inspected with `pdftotext -layout`.

- ASF, [GCOV product guide](https://nisar-docs.asf.alaska.edu/gcov/).
- NASA JPL SDS, [GCOV Product Specification JPL D-102274 Rev F](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf), version 1.5.0.
- `nisarqa` [v17.2.0 release](https://github.com/isce-framework/nisarqa/releases/tag/v17.2.0), [tagged identification checks](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py), and [GCOV product-specification 1.6.0 XML](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/product_specs/1.6.0/nisar_L2_GCOV.xml).
- ISCE3 [v0.25.21 release notes](https://github.com/isce-framework/isce3/releases/tag/v0.25.21), which scope the `LSAR` default-name change to STATIC products.
- ASF, [NISAR known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- ECHO, [provider QA summary ingestion decision](../decisions/0009-ingest-provider-qa-summaries.md).

## Limits and next evidence

- No provider pixel arrays were analyzed and no change quantity or event interpretation was produced.
- The exact product specification version 1.6.0 and a source-to-binary mapping for QA software 17.2.0 remain unverified.
- Obtain authoritative clarification or matching versioned specification/validator evidence before changing this product's QA disposition.
