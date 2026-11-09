# Cross-check GCOV product identity before reading measurement windows

**Date:** 2026-11-09
**Status:** Implemented

## Context

The paired GCOV gate compared catalog compatibility between scenes and checked selected HDF5 fields for non-placeholder values. It did not verify that each product's internal scene identity agreed with its ASF catalog record. A valid QA summary and compatible-looking pair are insufficient if the product orbit, track, frame, mission, or instrument does not match the catalog entry used to select it.

ASF's [GCOV product guide](https://nisar-docs.asf.alaska.edu/data-products/level-2/gcov/) links the current [NASA SDS L2 GCOV product specification](https://cumulus.asf.earthdatacloud.nasa.gov/PUBLIC/DATA/NISAR/NISAR_D-102274_RevF_NASA_SDS_Product_Specification_L2_GCOV_w-esigs.pdf). The format records `missionId`, `absoluteOrbitNumber`, `trackNumber`, and `frameNumber` in the product identification group. ASF's GCOV naming guide identifies the L/S instrument and relative-track/frame components of the scene identifier.

## Decision

After provider QA and collection-maturity gates pass, compare the HDF5 identification with the same ASF catalog feature before reading any raster windows:

- `missionId` must identify NISAR.
- `instrumentName` must agree with the L/S instrument encoded in the scene ID. ECHO accepts the observed `LSAR`/`L-SAR` and `SSAR`/`S-SAR` spellings, then compares their normalized value.
- `absoluteOrbitNumber`, `trackNumber`, and `frameNumber` must be typed integers equal to catalog `orbit`, `pathNumber`, and `frameNumber` respectively. Missing, invalid, or conflicting values hold the analysis.

The application reports a separate `IDENTITY_HELD` disposition. It preserves provider QA as `PASS`, records field-level comparisons with the source evidence, and does not read measurement windows or calculate change. Direct calls to the measurement API enforce the same gate. The map and source inspector display the hold and its comparisons; investigation drafts retain it as non-directional evidence.

This is an ECHO identity-consistency check, not an ASF QA result and not a replacement for the provider's validation. It does not alter existing provider QA statuses or product-maturity rules.

## Verification

- Focused GCOV analysis and investigation integration tests cover exact identity matches, each field mismatch, missing product orbit, pre-window short-circuiting, evidence retention, and non-directional draft handling.
- A live bounded inspection of a retained ASF product confirmed `missionId=NISAR`, `instrumentName=LSAR`, absolute orbit 6684, track 11, and frame 17 all match its catalog record. Its prior provider QA status is `FAIL`, retained separately; this identity check did not authorize measurement. See the [validation record](../validation/gcov-catalog-identity-check-2026-11-09.md) and [machine-readable evidence](../../data/research/gcov-catalog-identity-live-check-2026-11-09.json).
- Full Python suite: `406 passed`.
- `git diff --check`: passed.
- JavaScript runtime/browser interaction check was unavailable in this increment: no JavaScript runtime was installed, and Firefox/geckodriver sessions were already active. The frontend edits were reviewed with the existing backend response tests; direct browser behavior remains unverified here.
