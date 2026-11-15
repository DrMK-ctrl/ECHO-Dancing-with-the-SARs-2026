# P05036 validated-GCOV candidate QA review — 2026-11-11

## Finding

The five retained metadata-compatible P05036 repeat pairs below are not waiting on pixel-overlap evaluation: every one of their ten provider QA summary CSVs records `FAIL`. In all ten summaries, the same single check fails: `Passes all identification group checks?`. The other eight listed checks pass, including coordinate-grid metadata, calibration-information LUTs, four decimated-raster validity checks, and QA completion without exceptions.

The paired QA-report records independently flag the same identification values for every product:

- `/science/LSAR/identification/instrumentName` is `LSAR`; the retained `nisarqa` cross-check rule expects `L-SAR` or `S-SAR`.
- `/science/LSAR/identification/listOfObservationModes` is `(NOT SPECIFIED)`; the retained `nisarqa` cross-check reports this as invalid for the nominal product.

The provider QA disposition is `FAIL` in each QA summary CSV. The companion QA PDF parser reports `NOT_IN_REPORT_PDF` for a single disposition because the PDF contains metadata and plots rather than the CSV checklist; these are distinct artifacts and statuses. ECHO does not relabel the provider failure as a local-only warning. The raster checks passing are useful diagnostic information, but they do not clear provider QA or establish full-resolution validity, compatible grids, valid-pixel overlap, or an accepted change result.

The public `nisarqa` v17.2.0 validation source and the upstream ISCE3 GCOV QA issue document checks for invalid string metadata, including the GCOV placeholder `(NOT SPECIFIED)`. They corroborate the retained cross-check basis; the product-specific provider CSV remains the controlling QA evidence for these candidates. [Validator source](https://github.com/isce-framework/nisarqa/blob/v17.2.0/src/nisarqa/validate/sanity_checks.py) · [ISCE3 issue #216](https://github.com/isce-framework/isce3/issues/216) · [ASF NISAR GCOV guide](https://nisar-docs.asf.alaska.edu/gcov/).

## Screened candidate pairs

| Path / frame | Acquisitions (UTC) | Provider QA | Retained source |
|---|---|---|---|
| 149 / 83 | 2026-10-22 → 2026-11-03 | Both `FAIL`, identification group | [`cross-track QA sample`](../../data/research/validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json) |
| 19 / 80 | 2026-10-25 → 2026-11-06 | Both `FAIL`, identification group | [`cross-track QA sample`](../../data/research/validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json) |
| 141 / 84 | 2026-10-21 → 2026-11-02 | Both `FAIL`, identification group | [`path 141 / frame 84 review`](../../data/research/validated-gcov-p05036-path141-frame84-qa-2026-11-08.json) |
| 149 / 72 | 2026-10-22 → 2026-11-03 | Both `FAIL`, identification group | [`path 149 / frame 72 review`](../../data/research/validated-gcov-p05036-path149-frame72-qa-2026-11-08.json) |
| 19 / 79 | 2026-10-25 → 2026-11-06 | Both `FAIL`, identification group | [`path 19 / frame 79 review`](../../data/research/validated-gcov-p05036-path19-frame79-qa-2026-11-08.json) |

The four source records have SHA-256 digests:

- `validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json`: `dd1ef44ca01dae4c620328d54464771790f08dde8d3fb711ac5d933359a8342f`
- `validated-gcov-p05036-path141-frame84-qa-2026-11-08.json`: `027c6453d6e4b9e341643a8ced6741ba40c7046fa79ade38bb60397f4c6a1e02`
- `validated-gcov-p05036-path149-frame72-qa-2026-11-08.json`: `808ef051dd7dd273a01653fbcf8ff65d9463f81f6b4c2ef9a852ef529346bf05`
- `validated-gcov-p05036-path19-frame79-qa-2026-11-08.json`: `8f3848d45f90a1ef08e0a17a426851ab55d4cf10d36a67416ea2fe2d8ea122ec`

## Decision and next action

Do not repeat QA retrieval or request measurement arrays for these same ten P05036 products unless ASF posts a changed QA summary, a replacement product, or a new processing release. A provider-side metadata correction or a new validated release is needed to reopen the temporal-analysis gate. When that happens, re-read the canonical QA summary for the exact pair before proceeding to grid, mask, and common-support validation. Until then, these products may support clearly labeled diagnostic previews only.

The latest incremental global screen through 2026-11-11 found no scenes for 2026-11-10 and 2026-11-11; the latter was an incomplete acquisition day at retrieval time. This availability result is separate from the P05036 QA failure and is recorded in the [incremental screen note](2026-11-11-incremental-nisar-gcov-screen.md).

## Public ASF documentation check — 2026-11-12

The current [ASF VALIDATED known-issues page](https://nisar-docs.asf.alaska.edu/nisar-known-issues/) says that it focuses on VALIDATED products. Its table lists the incomplete-L0B issue as resolved with CRID P05036 and the permanent instrument data gap; it does not list the identification-group values observed in the retained P05036 QA reports. ASF's [PROVISIONAL known-issues page](https://nisar-docs.asf.alaska.edu/provisional-known-issues/) describes the known P05023 limitations, including residual RFI, Frequency B calibration, and incomplete L0B data, but does not identify the two retained GCOV identification values as a documented release issue.

This is a documentation check, not evidence that the products are free of other issues or that the aggregate QA failure should be disregarded. The page describes known issues rather than every QA failure, and ASF's product-specific summary remains the controlling disposition. Consequently, the exact provider-attributed reason for the repeated aggregate identification-group failure remains unresolved. Do not infer a QA override from the fact that a matching known-issue entry was not found. Preserve the existing re-open conditions above: a changed product QA summary, replacement/reprocessed product, or a new CRID. No provider or organizer contact was made for this check.

The upstream validator/release context was refreshed on 2026-11-13 in the [dated status note](2026-11-13-nisarqa-upstream-metadata-status.md). The public release page still maps the newest numbered `nisarqa` package release shown there to v17.2.0, and the related ISCE3 GCOV metadata issue remains open. This strengthens the evidence that the observed values are known to conflict with the released validator conventions; it still does not attribute ASF's aggregate product QA result to those fields or clear any scene.
