# VALIDATED GCOV QA follow-up: path 148/frame 5 — 2026-11-13

## Question and selection

Does a previously unassessed full/full pair in a different P05036 path clear
the exact-product provider QA gate? The retained global catalog contains 54
metadata-compatible pairs for 2026-10-09 through 2026-11-08. This check selected
the path 148/frame 5 pair because both acquisitions are full coverage and its
exact products were not in the earlier pair-QA sample.

- Before: `NISAR_L2_PR_GCOV_033_148_A_005_2005_DHDH_M_20261022T104722_20261022T104757_P05036_N_F_J_001`
- After: `NISAR_L2_PR_GCOV_034_148_A_005_2005_DHDH_M_20261103T104722_20261103T104757_P05036_N_F_J_001`
- Acquisition interval: 12 days; ascending, path 148, frame 5; HH/HV; both catalog coverages `Full`.
- Catalog input SHA-256: `a0f554e78da0ff0d295a28f8ca71172f1f044dc96da2105d914bc33b8d0448e8`.

## Provider QA result

Both canonical ASF QA summaries report `FAIL` on the aggregate identification
group check. The other eight reported checks pass for each product. Their exact
provider QA reports were retrieved and cross-checked against catalog orbit,
frame, and track metadata. The partial `nisarqa` 17.2.0 source comparison finds
`instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)` inconsistent
with those source rules. ASF's aggregate report does not identify which field
caused its failure; ECHO preserves the provider `FAIL` and does not substitute
its own partial comparison.

No product measurement arrays were read, no grids or masks were compared, and
no change analysis was run. This metadata-compatible pair is not eligible for
an accepted temporal result while either product remains QA-failed.

## Retained records and reproduction

- Record: [`validated-gcov-p05036-path148-frame5-qa-2026-11-13.json`](../../data/research/validated-gcov-p05036-path148-frame5-qa-2026-11-13.json)
- Record SHA-256: `7d2e5b6b89a9a79f0d4ab66f17005d960d4a96e68ab7fb9494bb182018aa5d63`
- Before QA CSV SHA-256: `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`; retrieved 2026-11-13 06:12:36 UTC.
- Before QA PDF SHA-256: `21c8f8627bcf55d022641adc26611450294b3bdfecb930611de1a00e59f54d62`.
- After QA CSV SHA-256: `8938a6d85d1bcc339e850ebb7b087dc1982fdbb159995c721944b4d81880c688`; retrieved 2026-11-13 06:12:47 UTC.
- After QA PDF SHA-256: `b77cf169d2efa6d8bf632e80320ee6167a08b524df7a4e5f50f2d10e147f5a2d`.
- Screen command: `.venv/bin/python tools/research/screen_nisar_crid_reprocessing_qa.py --catalog data/research/validated-gcov-global-time-series-2026-10-09-11-08.json --case-id validated-gcov-path148-frame5-2026-11-13 --crid P05036 --scene-id NISAR_L2_PR_GCOV_033_148_A_005_2005_DHDH_M_20261022T104722_20261022T104757_P05036_N_F_J_001 --scene-id NISAR_L2_PR_GCOV_034_148_A_005_2005_DHDH_M_20261103T104722_20261103T104757_P05036_N_F_J_001 --output data/research/validated-gcov-p05036-path148-frame5-qa-2026-11-13.json`.
- `.venv/bin/pytest -q tests/test_crid_qa_screen.py` — **3 passed**, including exact retained catalog linkage, product IDs, QA status, report cross-checks, and the no-measurement invariant.

This is one additional pair screen, not an archive-wide QA conclusion. It does
not justify repeatedly screening the same unchanged P05036 release. Resume the
search if a new CRID appears or ASF publishes a relevant correction.
