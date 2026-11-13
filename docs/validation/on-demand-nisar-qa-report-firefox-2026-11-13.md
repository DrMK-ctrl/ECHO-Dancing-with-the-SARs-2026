# On-demand ASF NISAR QA report verification

**Date:** 2026-11-13 (UTC)
**Scope:** Local browser-to-backend retrieval of one selected NISAR GCOV product's ASF QA summary and detailed QA report. This verifies the QA evidence workflow, not radar measurement validity or scientific change analysis.

## Procedure and result

Started an isolated ECHO workbench on loopback port 8768 with the retained Nepal catalog, then used headless Firefox to select the catalog observation and open its product QA panel. The normal QA action retrieved the canonical ASF QA summary. The new **Fetch detailed ASF report** action then retrieved and parsed the corresponding canonical QA report PDF through the bounded Earthdata-authenticated reader.

The selected product was `NISAR_L2_PR_GCOV_029_098_A_016_4005_DHDH_A_20260831T233918_20260831T233952_P05023_N_F_J_001` (GCOV, PROVISIONAL). The returned ASF CSV disposition was **FAIL** for the aggregate identification group and **PASS** for the other eight reported checks. The QA PDF reported QA software 17.0.0, product specification 1.5.0, product version 1.0.11, `instrumentName=LSAR`, and observation mode `(NOT SPECIFIED)`.

The bounded local source cross-check found corresponding `nisarqa` 17.0.0 rule mismatches for the instrument name and observation mode. ECHO presents these as a partial diagnostic cross-check, explicitly not a provider per-field QA result. The provider `FAIL` remains authoritative for this workflow; no change analysis or scientific acceptance is inferred.

## Verification evidence

- ASF QA summary SHA-256: `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`
- ASF QA report PDF SHA-256: `75594782579e9c67a54566354b2e359472e67515a00f7a7517d51bcb5e8f42e6`
- Browser result: report appeared in the selected product's QA dialog; provider status remained `FAIL`; retrieval status confirmed checksum; no Firefox page errors.
- The **Export Source Record** payload now includes the detailed QA report when it has been fetched in the current session. Firefox submitted that exact UI payload to the local export endpoint and received HTTP 200 with the matching scene ID and report checksum; the exported summary still recorded provider `FAIL`.
- Automated tests: `527 passed` across the full local pytest suite, including endpoint validation, same-origin enforcement, invalid product rejection, request-size bounds, and read-only-mode blocking.
- The export endpoint also accepts the prior summary-only record and rejects a detailed report whose canonical source URL does not match the selected product.

## Limits

This is one live product and one browser walkthrough. It does not validate every catalog product, establish that the source-rule mismatches exhaust the provider's aggregate failure, inspect HDF5 radar arrays, or establish a QA-cleared product. Detailed report fetching remains unavailable in the curated read-only walkthrough; that mode continues to serve only retained local evidence.
