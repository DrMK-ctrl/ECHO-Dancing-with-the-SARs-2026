# Bounded NISAR PROVISIONAL GCOV coverage and QA — 2026-11-08

## Result

The initial global PROVISIONAL search for 2026-10-07 through 2026-10-23 reached ASF's 2,000-scene result cap. It returned only acquisitions on October 20 and 21, so that partial result cannot establish what was available earlier in the interval. A bounded WGS84 search over a northern Iraq area (`[41.15, 36.66, 41.27, 36.78]`) returned five PROVISIONAL products on October 8, 15, and 20. Two same-track/frame 12-day metadata pairs were identified: ascending path 114/frame 20 and descending path 122/frame 70. Both are metadata candidates only.

The four exact pair products share CRID `P05023`, collection `NISAR_L2_GCOV_PROVISIONAL_V1`, and are full-frame products with HH/HV polarization and 20+5 MHz bandwidth. Each canonical ASF QA summary reports `FAIL` for “Passes all identification group checks?” and `PASS` for the other eight reported checks, including coordinate grid, calibration, four decimated backscatter checks, and QA completion. Their complete QA reports identify `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`. ECHO's partial cross-check against `nisarqa` v17.0.0 identifies these two values as rule mismatches; it is explanatory and does not override the ASF aggregate failure. No product arrays were read and no temporal measurement was made.

A separate completed VALIDATED query for the same WGS84 box and 2026-10-21 through 2026-11-08 returned zero scenes across one page. This is bounded to this area and interval. It does not establish global absence of suitable VALIDATED pairs. A separate Nepal-area PROVISIONAL query for 2026-10-09 through 2026-10-21 timed out at CMR and is retained as unavailable coverage, not a zero-result search.

## Retained evidence

- [Global PROVISIONAL query, 2026-10-07–2026-10-23](../../data/research/provisional-gcov-global-time-series-2026-10-07-2026-10-23.json): 2,000 returned scenes, 8 pages, cap reached, coverage status `PARTIAL` after correction of the record's status fields. SHA-256 `97fd6ad43b2ef2dbf3f878701ac037fa7058ae8b9468ab37cfd89a303b6be61b`.
- [Iraq-area PROVISIONAL catalog screen](../../data/research/provisional-gcov-path122-frame70-iraq-aoi-2026-10-08-20.json): five unique scenes, three acquisition dates, two metadata pairs, no result cap. SHA-256 `b324bc6943e881904bbad9cdea1605e6715b6e807043504f7daa370b2f1acc99`.
- [Exact-product QA screen](../../data/research/provisional-gcov-iraq-aoi-p05023-qa-sample-2026-11-08.json): canonical summary CSV and QA report provenance for four selected products; provider disposition remains `FAIL` on the aggregate identification group for each. SHA-256 `8488b1eb24a68fa043e162fdf9e4950cec716cd41ed2eba7990187a0e474c882`.
- [Iraq-area VALIDATED catalog screen](../../data/research/validated-gcov-iraq-aoi-2026-10-21-11-08.json): one completed page, zero features. SHA-256 `b87448bbc0b4cfce849777a4ac561a879d937d2c7f5afe13699bcde4f827be07`.
- [Nepal-area failed PROVISIONAL query](../../data/research/provisional-gcov-path149-frame72-aoi-2026-10-09-21.json): CMR timeout; coverage not established. SHA-256 `8aa700bce2e1eec07da38e8a0a16c24315ac5ce8a5513864f7b9092be94f7399`.

The QA summary/report retrieval is metadata-only. The report's `provider_qa_disposition` field is `NOT_IN_REPORT_PDF`; the structured QA summary CSV is the artifact containing the explicit aggregate `FAIL` result. The report PDF supplies product metadata and context but does not replace that CSV disposition.

## Reproduction

Global cap probe:

```bash
./.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --maturity PROVISIONAL --start 2026-10-07 --end 2026-10-23 \
  --cmr-timeout-seconds 60 --query-window-days 17 \
  --output data/research/provisional-gcov-global-time-series-2026-10-07-2026-10-23.json
```

Bounded PROVISIONAL area screen:

```bash
./.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --maturity PROVISIONAL --start 2026-10-08 --end 2026-10-20 \
  --cmr-timeout-seconds 60 --query-window-days 13 \
  --bounds 41.15 36.66 41.27 36.78 \
  --output data/research/provisional-gcov-path122-frame70-iraq-aoi-2026-10-08-20.json
```

Bounded VALIDATED area screen:

```bash
./.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --maturity VALIDATED --start 2026-10-21 --end 2026-11-08 \
  --cmr-timeout-seconds 60 --query-window-days 19 \
  --bounds 41.15 36.66 41.27 36.78 \
  --output data/research/validated-gcov-iraq-aoi-2026-10-21-11-08.json
```

The QA screen used `tools/research/screen_nisar_crid_reprocessing_qa.py`, CRID `P05023`, and the four exact IDs retained in `selected_scene_ids` in the QA record. Replaying it re-requests the canonical summary and report artifacts. No GUNW, optical, or other mission data is substituted for these NISAR results.

## Processing change and verification

The temporal screener now catches ASF query timeouts per window, records failed windows, pagination counts and cap status, supports validated WGS84 bounds, and distinguishes complete execution from complete query coverage. Spatial records say explicitly that footprint intersection is discovery metadata and does not establish AOI pixel coverage or analytical suitability.

Focused verification: `tests/test_validated_temporal_screen.py` — 11 passed. Full repository suite: 364 passed. `compileall` and `git diff --check` passed. These tests validate the query-recording implementation; they do not independently verify the scientific suitability of any product.
