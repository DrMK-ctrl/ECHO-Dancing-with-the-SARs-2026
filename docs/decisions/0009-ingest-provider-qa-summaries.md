# Decision 0009: ingest provider QA summaries as evidence

**Date:** 2026-11-07  
**Status:** Implemented; validated against a real ASF summary artifact

## Context

The paired-measurement API accepted a caller-supplied QA receipt, but did not retrieve or parse the provider's actual check rows. A recent ASF product is in the NISAR VALIDATED collection, yet its per-product QA CSV reports a failed identification-group check. Collection maturity and individual QA disposition therefore need to remain separate evidence fields.

## Decision

Add bounded retrieval of the canonical per-product `*_QA_SUMMARY.csv` from the allowlisted ASF GCOV product path. Parse its check rows without dropping duplicate check names, preserve result, threshold, actual value, and notes, and calculate a disposition as follows:

- `FAIL` if any provider check reports FAIL;
- `PASS` only if all rows report PASS and the required input-open, grid, calibration, identification, and no-exceptions checks are present;
- `INDETERMINATE` for unknown or non-PASS results, or when required checks are missing.

Hash the exact downloaded bytes and record the provider URI, retrieval time, authentication method, and requested range bytes. Keep software version unknown when it is absent from the summary rather than inferring it from product maturity or another artifact.

## Evidence and limits

- The parser is tested on pass, fail, unknown-result, missing-check, malformed, empty, oversized, and duplicate-check inputs. Remote retrieval uses strict ASF URL checks and a 64 KiB byte/range cap.
- Against the real product `NISAR_L2_PR_GCOV_033_141_D_085_4005_DHDH_A_20261021T235335_20261021T235345_P05036_N_P_J_001`, retrieval returned 1,441 bytes with SHA-256 `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`; one 1,441-byte HTTPS range was requested. ECHO derived `FAIL` from the identification-group row.
- The CSV does not identify the QA software version. Its histogram checks are explicitly decimated; passing those checks is not a full-resolution study-area quality result.
- This code parses the provider summary; it does not rerun the NASA QA validator, fetch the PDF report, independently explain the failed identification check, or make a scientific suitability judgment.

## Consequences and open work

- A retrieved provider QA failure cannot be silently converted into `PASS` by maturity labeling.
- The existing paired-measurement entry point still requires QA evidence explicitly; callers should use this parser for provider CSVs and separately supply inspected product-identification metadata.
- Reading full QA reports, resolving provider-level contradictions, and presenting these records in the interface remain open work.

## References

- ASF, [NISAR QA artifacts and product access](https://nisar-docs.asf.alaska.edu/asf-search/).
- ECHO, [provenance-gated pair measurement](0007-provenance-gated-pair-measurement.md).
- ECHO, [VALIDATED collection and case coverage](../research/2026-11-07-validated-gcov-availability.md).
