# Decision 0009: ingest provider QA summaries and reports as evidence

**Date:** 2026-11-07  
**Status:** Implemented for bounded CSV/PDF retrieval, provenance, and metadata diagnostics; provider QA reconciliation remains open

## Context

The paired-measurement API accepted a caller-supplied QA receipt, but did not retrieve or parse the provider's actual check rows. A recent ASF product is in the NISAR VALIDATED collection, yet its per-product QA CSV reports a failed identification-group check. Collection maturity and individual QA disposition therefore need to remain separate evidence fields.

## Decision

Add bounded retrieval of the canonical per-product `*_QA_SUMMARY.csv` from the allowlisted ASF GCOV product path. Parse its check rows without dropping duplicate check names, preserve result, threshold, actual value, and notes, and calculate a disposition as follows:

- `FAIL` if any provider check reports FAIL;
- `PASS` only if all rows report PASS and the required input-open, grid, calibration, identification, and no-exceptions checks are present;
- `INDETERMINATE` for unknown or non-PASS results, or when required checks are missing.

Hash the exact downloaded bytes and record the provider URI, retrieval time, authentication method, and requested range bytes. Keep software version unknown when it is absent from the summary rather than inferring it from product maturity or another artifact.

When a QA software version is explicitly supplied from its matching report, attach a narrow, versioned source-code cross-check for known identification-field rules. Label it as a partial diagnostic, separate from the provider's aggregate result and per-field failure log. It must never change the provider disposition or clear the analysis gate.

Add a companion reader for the canonical per-product `*_QA_REPORT.pdf`. Validate its exact ASF scene path, cap the PDF at 5 MiB and 20 pages, extract only the first page's report identity, QA version, processing time, and product metadata, and hash the full retrieved bytes. Verify that the report's granule ID matches the requested scene and compare its orbit, track, and frame with the catalog record. Apply the versioned source cross-check using the QA version printed in that report. Do not infer provider check results from the PDF; the QA summary CSV remains authoritative for disposition.

## Evidence and limits

- The parser is tested on pass, fail, unknown-result, missing-check, malformed, empty, oversized, and duplicate-check inputs. Remote retrieval uses strict ASF URL checks and a 64 KiB byte/range cap.
- Against the real product `NISAR_L2_PR_GCOV_033_141_D_085_4005_DHDH_A_20261021T235335_20261021T235345_P05036_N_P_J_001`, retrieval returned 1,441 bytes with SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`; one 1,441-byte HTTPS range was requested. ECHO derived `FAIL` from the identification-group row.
- The CSV does not identify the QA software version. Its histogram checks are explicitly decimated; passing those checks is not a full-resolution study-area quality result.
- The matching PDF report was separately retrieved and hash-recorded. It identifies QA software 17.2.0 and ISCE3 0.25.21, and reproduces the product's `LSAR` and `(NOT SPECIFIED)` identification values. The available Rev F product specification is version 1.5.0 while this product reports 1.6.0, and does not enumerate accepted values for those fields. The failure cause therefore remains unresolved; see [the report review](../research/2026-11-07-validated-product-qa-report-review.md).
- The bounded PDF reader was exercised with Earthdata-authenticated live ASF retrieval through `echo inspect-qa-report`. The Istanbul before/after report metadata records are retained at `data/cases/istanbul-2026/qa-report-{before,after}.json`. The after report is 908,534 bytes with SHA-256 `65c086e078b133b0d929dfdf2b68742064df7431086da544875054be3f708ef0`; the before report is 896,538 bytes with SHA-256 `b20515b9e8a9f8b18862350c5418e7798c8fd3a1b3a31528e036ca47b26c65b8`. Both report records parse QA software 17.0.0, match the report granule ID, and match orbit, track, and frame to the catalog. A second pair over Kathmandu has both exact QA reports retained with checksums and matching catalog cross-checks in [the cross-region review](../research/2026-11-07-provisional-qa-sample.md).
- `crosscheck_identification_metadata` records only the versioned source rules for the `instrumentName` allowlist and observation-mode placeholder. Rule descriptions now use the exact reported QA version. Unknown and unsupported versions produce no findings, and the diagnostic never changes the provider's `FAIL`. Tests use the retained real PDFs and cover canonical retrieval, byte limits, identity mismatch, and source-version labeling.
- The report parser records metadata and source provenance only. It does not claim that either candidate rule caused the provider's aggregate failure, reproduce the provider's complete checks, or validate radar pixels.
- This code parses the provider summary; it does not rerun the NASA QA validator or make a scientific suitability judgment.

## Consequences and open work

- A retrieved provider QA failure cannot be silently converted into `PASS` by maturity labeling.
- The existing paired-measurement entry point still requires QA evidence explicitly; callers should use this parser for provider CSVs and separately supply inspected product-identification metadata.
- The CLI can now retrieve and inspect a bounded QA PDF. The interface currently exposes report source links but does not yet render this parsed report record in its evidence dialog.
- The reviewed products remain on QA hold until version-matched requirements or provider clarification resolve the identification failure.

## References

- ASF, [NISAR QA artifacts and product access](https://nisar-docs.asf.alaska.edu/asf-search/).
- ECHO, [provenance-gated pair measurement](0007-provenance-gated-pair-measurement.md).
- ECHO, [VALIDATED collection and case coverage](../research/2026-11-07-validated-gcov-availability.md).
