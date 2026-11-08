# Validated GCOV pair discovery and cross-track QA sample

## Catalog discovery

- Short recent window, 2026-11-01 to 2026-11-08: 140 unique scenes, zero metadata temporal pairs, no acquisitions on November 7 or 8, and latest returned acquisition date November 6.
- Bounded 31-day window, 2026-10-09 to 2026-11-08: 2,018 unique scenes, 54 metadata-compatible pairs, no capped daily windows. Pair intervals are approximately 12 days; all candidates use CRID P05036.
- Product and map-array values were not read during catalog discovery.

The larger window recovers repeat observations whose earlier acquisition dates lie before the previous October 21 search start. A catalog pair is only a candidate; QA, product masks, pixel overlap, and grid compatibility remain separate gates.

## Provider QA sample

Two distinct path/frame pairs (19/80 and 149/83) were screened, spanning four exact products. All four ASF summaries report `FAIL` for `Passes all identification group checks?`; the other listed groups pass. Each canonical QA report's partial check against the cited `nisarqa` 17.2.0 rules finds `instrumentName=LSAR` and `(NOT SPECIFIED)` in `listOfObservationModes` inconsistent with the source rules.

The QA report cross-check is partial and does not identify ASF's exact failing row. Provider QA remains `FAIL`. This sample is evidence of a repeated P05036 issue across two paths, not proof that every product in the release fails.

No product arrays, measurements, or paired comparison values were read or produced.

## Reproduction and verification

- Global catalog screen: [`validated-gcov-global-time-series-2026-10-09-11-08.json`](../../data/research/validated-gcov-global-time-series-2026-10-09-11-08.json).
- Short-window catalog screen: [`validated-gcov-global-time-series-2026-11-01-08.json`](../../data/research/validated-gcov-global-time-series-2026-11-01-08.json).
- QA records: [`validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json`](../../data/research/validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json).
- Short-window catalog SHA-256: `ec8c74232eaba0a12b2b275f57ac5f02bf1410c6da1d679275c8908723de0c42`.
- 31-day catalog SHA-256: `a0f554e78da0ff0d295a28f8ca71172f1f044dc96da2105d914bc33b8d0448e8`.
- QA sample SHA-256: `dd1ef44ca01dae4c620328d54464771790f08dde8d3fb711ac5d933359a8342f`.
- `.venv/bin/python -m pytest tests/test_crid_qa_screen.py tests/test_validated_temporal_screen.py -q` — passed (8 tests).
- `.venv/bin/python -m compileall -q tools/research/screen_nisar_crid_reprocessing_qa.py echo` — passed.
- `git diff --check` — passed.

See [Decision 0037](../decisions/0037-extend-validated-gcov-pair-screen-horizon.md) for the search-horizon decision and next QA gate.
