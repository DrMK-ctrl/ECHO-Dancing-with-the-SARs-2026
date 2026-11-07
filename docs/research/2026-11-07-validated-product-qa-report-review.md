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
- Both artifacts are under the product's canonical ASF directory. Retrieval used Earthdata-authenticated access. The summary reader recorded a 1,441-byte HTTPS range. The report was retrieved as a bounded artifact; no GCOV measurement raster was read for this review.

## Observed report content

The PDF identifies QA software version `17.2.0`, QA processing time `2026-11-07T03:01:03 UTC`, and ISCE3 software version `0.25.21`. Its product identification table reports `instrumentName=LSAR`, `listOfObservationModes=['(NOT SPECIFIED)']`, product specification version `1.6.0`, product version `1.0.20`, absolute orbit 6468, track 141, and frame 85.

The companion CSV reports `FAIL` for “Passes all `identification` group checks?”. It reports PASS for input opening, coordinate-grid metadata, calibration LUT metadata, four backscatter checks, and completion without exceptions. The report notes that crosstalk checks were skipped and backscatter checks were decimated. These checks do not establish suitability of a particular study-area window.

## Specification boundary and interpretation

The publicly accessible NASA SDS GCOV specification PDF linked by ASF is JPL D-102274 Rev F, version 1.5.0. It describes `instrumentName` as a scalar string naming the instrument and describes `listOfObservationModes` as a per-input-observation list. The reviewed passages do not enumerate accepted string values or establish whether `(NOT SPECIFIED)` is valid for every product mode. This document therefore cannot resolve the product's reported version 1.6.0 or determine whether the QA failure is a validator mismatch, a product issue, or both.

The observed fields match values previously associated with an identification-check failure in older products, and the official ASF GCOV guide uses `LSAR` in HDF5 paths. Those facts motivate a focused provider/validator reconciliation; they do not prove the 1.6.0 product passes identification requirements. Keep this product on QA review hold until the exact 1.6.0 specification and QA validator disposition are available. Do not call the failure a false positive or claim the raster is unusable on this evidence alone.

## Reproduction and references

The product and artifact paths are derived from the exact ASF catalog record and the product granule identifier. The CSV is parsed by `echo.qa.read_qa_summary`; the PDF was downloaded from the corresponding `_QA_REPORT.pdf` object and inspected with `pdftotext -layout`.

- ASF, [GCOV product guide](https://nisar-docs.asf.alaska.edu/gcov/).
- NASA JPL SDS, [GCOV Product Specification JPL D-102274 Rev F](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf), version 1.5.0.
- ASF, [NISAR known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues/).
- ECHO, [provider QA summary ingestion decision](../decisions/0009-ingest-provider-qa-summaries.md).

## Limits and next evidence

- No provider pixel arrays were analyzed and no change quantity or event interpretation was produced.
- The exact product specification version 1.6.0 and a source-to-binary mapping for QA software 17.2.0 remain unverified.
- Obtain authoritative clarification or matching versioned specification/validator evidence before changing this product's QA disposition.
