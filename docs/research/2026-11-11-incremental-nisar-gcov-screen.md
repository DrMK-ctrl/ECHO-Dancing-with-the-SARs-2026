# Incremental NISAR GCOV catalog screen — 2026-11-11

## Result

ASF returned no global NISAR GCOV catalog features for acquisition dates November 10 or November 11, 2026, in any of the three queried maturities: VALIDATED, PROVISIONAL, and BETA. Each maturity used one daily query window per date. All six windows completed one page, returned no errors, and were below the 2,000-result cap. No candidate scenes or metadata temporal pairs were available in these windows, so no provider QA reports or measurement arrays were requested.

The requests were retrieved between 22:05:20Z and 22:05:39Z on November 11. November 10 is a completed acquisition date at query time. November 11 was still in progress; its empty result is an early snapshot and does not establish final archive availability for that day.

## Reproducible records

| Maturity | Record | Retrieved (UTC) | Scenes / pairs | SHA-256 |
|---|---|---|---:|---|
| VALIDATED | [`validated-gcov-global-time-series-2026-11-10-11.json`](../../data/research/validated-gcov-global-time-series-2026-11-10-11.json) | `2026-11-11T22:05:20.700683Z` | 0 / 0 | `8ab334a08feb3a2229c6691244d92495e190e1b5829c125f1af4c98ec3687ee5` |
| PROVISIONAL | [`provisional-gcov-global-time-series-2026-11-10-11.json`](../../data/research/provisional-gcov-global-time-series-2026-11-10-11.json) | `2026-11-11T22:05:34.889532Z` | 0 / 0 | `d437af9b9458bcbe4b8d25e59956860a3f271ee52023bec8fc46759fd7e12fbe` |
| BETA | [`beta-gcov-global-time-series-2026-11-10-11.json`](../../data/research/beta-gcov-global-time-series-2026-11-10-11.json) | `2026-11-11T22:05:39.138593Z` | 0 / 0 | `3b6177dd33e4b9b4798c25ff5d86474b90b2c6d3f1140d5413bf77d5262c1a48` |

Each record reports complete execution and coverage of its requested date windows, one page per window, no failures, and no cap-sized results. “Complete” here describes the catalog requests, not the completeness of ASF's evolving archive.

## Interpretation and limits

This extends the previous daily screen through November 11 and rules out newly listed scenes in the queried windows as of retrieval time. It does not establish that the broader NISAR archive has no suitable repeat observations, that future processing will not add these dates, or that previously cataloged pairs are suitable. Existing QA holds remain unchanged. Do not treat the empty current-day result as evidence of zero coverage after the retrieval time.

Reproduce the three maturity queries from the repository root:

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-10 --end 2026-11-11 --query-window-days 1 \
  --maturity VALIDATED \
  --output data/research/validated-gcov-global-time-series-2026-11-10-11.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-10 --end 2026-11-11 --query-window-days 1 \
  --maturity PROVISIONAL \
  --output data/research/provisional-gcov-global-time-series-2026-11-10-11.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-10 --end 2026-11-11 --query-window-days 1 \
  --maturity BETA \
  --output data/research/beta-gcov-global-time-series-2026-11-10-11.json
```
