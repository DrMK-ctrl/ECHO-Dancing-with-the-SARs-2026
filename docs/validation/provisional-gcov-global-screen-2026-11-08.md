# PROVISIONAL GCOV availability screen — 2026-11-08

## Result

The ASF global PROVISIONAL-GCOV catalog query for 2026-10-25 through 2026-11-06 returned zero scenes and zero temporal-pair candidates. Each of the 13 daily windows returned one catalog page with zero features; none reached the 2,000-result cap. This rules out a recent PROVISIONAL pair in this queried interval, not archive-wide availability.

## Query and provenance

- Provider: Alaska Satellite Facility DAAC, `asf_search` catalog, dataset `NISAR`, processing level `GCOV`, data maturity `PROVISIONAL`.
- Spatial extent: global, with no spatial filter.
- Inclusive acquisition-date interval: 2026-10-25 through 2026-11-06.
- Query method: daily paginated searches, scene-ID deduplication, then ECHO's metadata-only temporal matcher.
- CMR response timeout: 60 seconds per request. The timeout and maturity are recorded in the machine-readable catalog record.
- Retrieved at: `2026-11-08T19:18:31.653985+00:00`.
- Catalog record: [`provisional-gcov-global-time-series-2026-10-25-11-06.json`](../../data/research/provisional-gcov-global-time-series-2026-10-25-11-06.json), SHA-256 `b8ba54acf398342cfd83923e55e23d30780d1d2cb83f2b879fbe93157e9ee494`.

A separate global PROVISIONAL query spanning 2026-10-09 through 2026-11-08 did not complete: CMR timed out under the library's original 30-second response limit. That failed attempt is not treated as a zero-result screen or evidence of missing archive coverage. The narrower completed screen uses a longer recorded timeout and targets the dates of the latest VALIDATED repeat pair.

## Interpretation

No product QA or measurements were retrieved because the completed catalog screen contained no scenes. This provides no evidence about PROVISIONAL product quality. ECHO's analysis gate supports PROVISIONAL and VALIDATED collections only after both exact products pass ASF provider QA; BETA remains held because ASF documents calibration and mask limitations. The existing recent VALIDATED sample remains provider-QA `FAIL` for six products across three pairs. These are separate maturity and product-QA gates.

The maturity-aware temporal screener can reproduce the bounded query:

```bash
./.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --maturity PROVISIONAL \
  --cmr-timeout-seconds 60 \
  --start 2026-10-25 \
  --end 2026-11-06 \
  --output data/research/provisional-gcov-global-time-series-2026-10-25-11-06.json
```

Focused verification: `tests/test_validated_temporal_screen.py` — 7 passed; compile check and `git diff --check` passed.
