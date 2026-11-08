# Validated GCOV pair discovery and cross-track QA sample

## Catalog discovery

- Short recent window, 2026-11-01 to 2026-11-08: 140 unique scenes, zero metadata temporal pairs, no acquisitions on November 7 or 8, and latest returned acquisition date November 6.
- Bounded 31-day window, 2026-10-09 to 2026-11-08: 2,018 unique scenes, 54 metadata-compatible pairs, no capped daily windows. Pair intervals are approximately 12 days; all candidates use CRID P05036.
- Product and map-array values were not read during catalog discovery.

The larger window recovers repeat observations whose earlier acquisition dates lie before the previous October 21 search start. A catalog pair is only a candidate; QA, product masks, pixel overlap, and grid compatibility remain separate gates.

## Provider QA sample

Two distinct path/frame pairs (19/80 and 149/83) were initially screened, spanning four exact products. All four ASF summaries report `FAIL` for `Passes all identification group checks?`; the other listed groups pass. Each canonical QA report's partial check against the cited `nisarqa` 17.2.0 rules finds `instrumentName=LSAR` and `(NOT SPECIFIED)` in `listOfObservationModes` inconsistent with the source rules.

### Follow-up QA sample: path 19/frame 79

At `2026-11-08T19:11:36Z`, the latest not-yet-screened pair in this catalog was checked using its two exact scene IDs:

- `NISAR_L2_PR_GCOV_034_019_D_079_2005_DVDV_A_20261025T124421_20261025T124455_P05036_N_F_J_001` — 2026-10-25.
- `NISAR_L2_PR_GCOV_035_019_D_079_2005_DVDV_A_20261106T124421_20261106T124456_P05036_N_F_J_001` — 2026-11-06.

Both canonical ASF QA summaries report `FAIL` for `Passes all identification group checks?`; the grid, calibration, decimated backscatter range, and QA-completion checks report `PASS`. The parsed reports show the same partial source-rule mismatches (`instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`) against `nisarqa` 17.2.0. The reports do not attribute ASF's aggregate failure to those individual fields, and the independent rule cross-check is not a substitute for ASF's disposition. Both reports parse completely and catalog track, frame, and orbit cross-checks match.

This extends the observed repeated P05036 failure sample to three path/frame pairs and six exact products across two paths (19 and 149). It is still a sample, not evidence that every P05036 product fails. No product arrays were read and no comparison was performed. The exact QA evidence and source-catalog checksum are retained in [`validated-gcov-p05036-path19-frame79-qa-2026-11-08.json`](../../data/research/validated-gcov-p05036-path19-frame79-qa-2026-11-08.json); the record SHA-256 is `8f3848d45f90a1ef08e0a17a426851ab55d4cf10d36a67416ea2fe2d8ea122ec`.

The QA report cross-check is partial and does not identify ASF's exact failing row. Provider QA remains `FAIL`. The six products across three pairs are evidence of a repeated issue in the sampled P05036 products, not proof that every product in the release fails.

No product arrays, measurements, or paired comparison values were read or produced.

## Reproduction and verification

- Global catalog screen: [`validated-gcov-global-time-series-2026-10-09-11-08.json`](../../data/research/validated-gcov-global-time-series-2026-10-09-11-08.json).
- Short-window catalog screen: [`validated-gcov-global-time-series-2026-11-01-08.json`](../../data/research/validated-gcov-global-time-series-2026-11-01-08.json).
- QA records: [`validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json`](../../data/research/validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json).
- Follow-up QA record: [`validated-gcov-p05036-path19-frame79-qa-2026-11-08.json`](../../data/research/validated-gcov-p05036-path19-frame79-qa-2026-11-08.json), SHA-256 `8f3848d45f90a1ef08e0a17a426851ab55d4cf10d36a67416ea2fe2d8ea122ec`.
- Short-window catalog SHA-256: `ec8c74232eaba0a12b2b275f57ac5f02bf1410c6da1d679275c8908723de0c42`.
- 31-day catalog SHA-256: `a0f554e78da0ff0d295a28f8ca71172f1f044dc96da2105d914bc33b8d0448e8`.
- QA sample SHA-256: `dd1ef44ca01dae4c620328d54464771790f08dde8d3fb711ac5d933359a8342f`.
- `.venv/bin/python -m pytest tests/test_crid_qa_screen.py tests/test_validated_temporal_screen.py -q` — passed (8 tests).
- `.venv/bin/python -m pytest tests/test_crid_qa_screen.py -q` — passed (2 tests) after the follow-up screen.
- `.venv/bin/python -m compileall -q tools/research/screen_nisar_crid_reprocessing_qa.py echo` — passed.
- `git diff --check` — passed.

See [Decision 0037](../decisions/0037-extend-validated-gcov-pair-screen-horizon.md) for the search-horizon decision and next QA gate.
