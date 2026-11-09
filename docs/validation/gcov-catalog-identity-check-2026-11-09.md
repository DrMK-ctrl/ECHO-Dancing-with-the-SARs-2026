# NISAR GCOV product-to-catalog identity check — 2026-11-09

## Result

A bounded authenticated read of the NISAR GCOV identification group found agreement between the product and its ASF catalog entry for mission, instrument, absolute orbit, track, and frame. The check used product `NISAR_L2_PR_GCOV_035_011_A_017_4005_DHDH_A_20261105T224956_20261105T225027_P05036_N_F_J_001`. The machine-readable field comparisons and retrieval limits are retained in [`gcov-catalog-identity-live-check-2026-11-09.json`](../../data/research/gcov-catalog-identity-live-check-2026-11-09.json).

The existing ASF QA review for this scene is `FAIL`. It was not refetched during this identity check. The identity match does not override that QA disposition; this product remains ineligible for accepted temporal measurement. No radar layers were read and no change was calculated.

## Method

The read used `echo.nisar_access.inspect_identification` against the ASF HDF5 product URL, authenticated through the configured local Earthdata `.netrc`. It requested 4,334,867 HTTP range bytes for identification metadata; it did not request the full product or radar measurement arrays. `echo.analysis.crosscheck_catalog_identity` compared those values with the recorded ASF catalog fields.

To repeat the live check, use the same product feature from the [retained diagnostic review](../../data/research/validated-gcov-diagnostic-window-review-2026-11-07.json) and call `inspect_identification(feature)`, then pass the returned `product.metadata`, scene ID, and feature properties to `crosscheck_catalog_identity`. Credentials remain local.

## Software verification

The focused analysis, orchestration, investigation, and web suites passed (145 tests before the final instrument-name alias case). The complete Python suite passed (406 tests). `git diff --check` passed. A live browser interaction check was not performed: Firefox/geckodriver sessions were already active, and no JavaScript runtime was installed for a standalone syntax check.
