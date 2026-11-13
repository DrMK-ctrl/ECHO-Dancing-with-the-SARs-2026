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

### Follow-up QA sample: path 149/frame 72

At `2026-11-08T19:57:56Z`, one previously unassessed full-coverage pair from a different frame was screened using its exact scene IDs:

- `NISAR_L2_PR_GCOV_033_149_D_072_2005_DHDH_M_20261022T130524_20261022T130558_P05036_N_F_J_001` — 2026-10-22.
- `NISAR_L2_PR_GCOV_034_149_D_072_2005_DHDH_M_20261103T130524_20261103T130559_P05036_N_F_J_001` — 2026-11-03.

Both canonical summaries report `FAIL` on `Passes all identification group checks?`; the other eight checks pass. Both QA reports parse completely, and their orbit, frame, and track cross-checks match the catalog. The same partial identification-rule findings (`instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`) are present, but the source-rule cross-check does not identify ASF's failing row and does not replace its disposition. No measurement arrays were read and no comparison was attempted. The exact source-linked QA record is [`validated-gcov-p05036-path149-frame72-qa-2026-11-08.json`](../../data/research/validated-gcov-p05036-path149-frame72-qa-2026-11-08.json), SHA-256 `808ef051dd7dd273a01653fbcf8ff65d9463f81f6b4c2ef9a852ef529346bf05`.

### Follow-up QA sample: path 141/frame 84

At `2026-11-08T21:38:23Z`, one unassessed full-coverage pair on a fourth path was screened from the same retained 31-day catalog:

- `NISAR_L2_PR_GCOV_033_141_D_084_4005_DHDH_A_20261021T235308_20261021T235336_P05036_N_F_J_001` — 2026-10-21.
- `NISAR_L2_PR_GCOV_034_141_D_084_4005_DHDH_A_20261102T235309_20261102T235337_P05036_N_F_J_001` — 2026-11-02.

Both authenticated canonical QA summaries were retrieved successfully. Both report `FAIL` for `Passes all identification group checks?`; the other eight checks pass. The parsed reports cross-check absolute orbit, frame, and track against the retained catalog. The partial `nisarqa` 17.2.0 comparison again finds `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)` inconsistent with its source rules. ASF's report does not attribute its aggregate failure to either field, and ECHO does not replace the provider disposition. No HDF5 measurement arrays were read. The retained pair record is [`validated-gcov-p05036-path141-frame84-qa-2026-11-08.json`](../../data/research/validated-gcov-p05036-path141-frame84-qa-2026-11-08.json), SHA-256 `027c6453d6e4b9e341643a8ced6741ba40c7046fa79ade38bb60397f4c6a1e02`.

### Current sample boundary

Counting the previously recorded [path 11/frame 17 review](../../data/research/validated-gcov-temporal-pair-qa-review-2026-11-07.json), six of the 54 metadata-compatible pairs in this catalog have now been QA-screened: twelve products across paths 11, 19, 141, and 149. All twelve sampled products report the same aggregate identification-group `FAIL`; 48 catalog pairs remain unassessed by this sample. This supports a repeated issue across the sampled P05036 paths, but does not prove every product in the release fails or identify ASF's exact failing identification item. Further screening of more P05036 pairs has lower priority than checking a newly available processing release or obtaining clarification of the recurring provider QA failure.

The QA report cross-check is partial and does not identify ASF's exact failing row. Provider QA remains `FAIL`. The twelve products across six pairs are evidence of a repeated issue in the sampled P05036 products, not proof that every product in the release fails.

No product arrays, measurements, or paired comparison values were read or produced.

## Official release context checked 2026-11-09

The ASF NISAR User Guide's known-issues page lists the incomplete-L0B issue as resolved with CRID P05036. It describes that earlier issue as a timestamp problem affecting downstream products and says it was resolved before VALIDATED products were processed ([ASF NISAR known issues](https://nisar-docs.asf.alaska.edu/nisar-known-issues)). This does not clear the provider QA failures retained above: those reports still return aggregate identification-group `FAIL`, and the known-issues page does not explain those specific report rows.

An open `isce3` issue records that `nisarqa` added a check for the string `(NOT SPECIFIED)` in `listOfObservationModes`, describing it as invalid for nominal NISAR data in a QP GCOV example ([isce3 issue #216](https://github.com/isce-framework/isce3/issues/216)). This is related public technical context for the same metadata field, but the example predates the sampled P05036 VALIDATED products and does not establish that this field caused ASF's aggregate failures. ECHO retains the provider disposition and its limited source-rule cross-check separately; the exact provider failure cause remains unresolved.

## Current release-status recheck — 2026-11-13

The live [ASF NISAR availability guide](https://nisar-docs.asf.alaska.edu/availability-overview/) still describes the November 6 VALIDATED launch as the initial CRID P05036 release, covering acquisitions from October 21 onward. It describes updates before a 2027 reprocessing campaign for earlier acquisitions; that campaign will replace earlier versions as products are republished. The [linked CRID reference](https://www.earthdata.nasa.gov/data/platforms/space-based-platforms/nisar/nisar-composite-release-id-crid) returned HTTP 403 in this public-page check, so this recheck does not establish a complete current CRID inventory or prove that no later release exists.

This release-status check does not change the QA disposition of any retained scene. It gives no reason to refetch the same P05036 summaries unchanged: those sampled products remain provider-QA `FAIL`. A future catalog record with a different CRID is a new product version and should be screened by its own exact source and QA record before its measurements are considered.

## Reproduction and verification

- Global catalog screen: [`validated-gcov-global-time-series-2026-10-09-11-08.json`](../../data/research/validated-gcov-global-time-series-2026-10-09-11-08.json).
- Short-window catalog screen: [`validated-gcov-global-time-series-2026-11-01-08.json`](../../data/research/validated-gcov-global-time-series-2026-11-01-08.json).
- QA records: [`validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json`](../../data/research/validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json).
- Follow-up QA record: [`validated-gcov-p05036-path19-frame79-qa-2026-11-08.json`](../../data/research/validated-gcov-p05036-path19-frame79-qa-2026-11-08.json), SHA-256 `8f3848d45f90a1ef08e0a17a426851ab55d4cf10d36a67416ea2fe2d8ea122ec`.
- Follow-up QA record: [`validated-gcov-p05036-path149-frame72-qa-2026-11-08.json`](../../data/research/validated-gcov-p05036-path149-frame72-qa-2026-11-08.json), SHA-256 `808ef051dd7dd273a01653fbcf8ff65d9463f81f6b4c2ef9a852ef529346bf05`.
- Follow-up QA record: [`validated-gcov-p05036-path141-frame84-qa-2026-11-08.json`](../../data/research/validated-gcov-p05036-path141-frame84-qa-2026-11-08.json), SHA-256 `027c6453d6e4b9e341643a8ced6741ba40c7046fa79ade38bb60397f4c6a1e02`.
- Short-window catalog SHA-256: `ec8c74232eaba0a12b2b275f57ac5f02bf1410c6da1d679275c8908723de0c42`.
- 31-day catalog SHA-256: `a0f554e78da0ff0d295a28f8ca71172f1f044dc96da2105d914bc33b8d0448e8`.
- QA sample SHA-256: `dd1ef44ca01dae4c620328d54464771790f08dde8d3fb711ac5d933359a8342f`.
- `.venv/bin/python -m pytest tests/test_crid_qa_screen.py tests/test_validated_temporal_screen.py -q` — passed (8 tests).
- `.venv/bin/python -m pytest tests/test_crid_qa_screen.py -q` — passed (2 tests) after the follow-up screen.
- Current recheck: `PYTHONPATH=. ./.venv/bin/pytest tests/test_crid_qa_screen.py tests/test_validated_temporal_screen.py -q` — **9 passed**; canonical QA record/catalog linkage and product identities were independently checked, and no pixel arrays were read.
- After the path 141/frame 84 addition: `.venv/bin/python -m pytest tests/test_crid_qa_screen.py tests/test_validated_temporal_screen.py -q` — **13 passed**. An offline evidence check confirmed both exact scene IDs link to the retained catalog, both reports match catalog orbit/frame/track, each summary has one aggregate identification `FAIL` and eight other passing checks, and no measurement arrays were read.
- `.venv/bin/python -m compileall -q tools/research/screen_nisar_crid_reprocessing_qa.py echo` — passed.
- `git diff --check` — passed.

See [Decision 0037](../decisions/0037-extend-validated-gcov-pair-screen-horizon.md) for the search-horizon decision and next QA gate.
