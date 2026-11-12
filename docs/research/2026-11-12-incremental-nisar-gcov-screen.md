# Incremental NISAR GCOV catalog screen — 2026-11-12

## Result

After the November 11 UTC acquisition day closed, ASF was queried for NISAR GCOV scenes acquired on November 11 in all three available catalog maturities. Each daily query completed one page and returned no scenes. There were no query failures and no result-cap truncations. No products were available for metadata pairing, QA retrieval, or pixel analysis.

This is a date-specific catalog availability result as of the recorded retrieval time, not a statement that the broader archive has no suitable NISAR repeats. It does not change provider QA or release status for previously screened products.

## Same-day catalog refresh — 2026-11-12 14:56 UTC

Because the November 12 acquisition day was still in progress, ECHO made one later global refresh for that date in each maturity. All three requests completed one page with zero scenes, zero failures, and no potentially truncated window. This is a preliminary snapshot: late-day acquisition indexing may change the result, and it does not establish final availability for November 12. No product QA or pixels were available to inspect.

| Maturity | Record | Retrieved (UTC) | Scenes / pairs | SHA-256 |
|---|---|---|---:|---|
| VALIDATED | [`validated-gcov-global-time-series-2026-11-12-refresh-1456z.json`](../../data/research/validated-gcov-global-time-series-2026-11-12-refresh-1456z.json) | `2026-11-12T14:56:24.131238Z` | 0 / 0 | `ef0033d439034fab75714912504d229bb13e4c31327c663029c85fe806761edc` |
| PROVISIONAL | [`provisional-gcov-global-time-series-2026-11-12-refresh-1456z.json`](../../data/research/provisional-gcov-global-time-series-2026-11-12-refresh-1456z.json) | `2026-11-12T14:56:24.111768Z` | 0 / 0 | `45f5873179f5f0c09a3cfe9a0486b05fdd15b3b8deb855cbdfa6e22d7ce441e8` |
| BETA | [`beta-gcov-global-time-series-2026-11-12-refresh-1456z.json`](../../data/research/beta-gcov-global-time-series-2026-11-12-refresh-1456z.json) | `2026-11-12T14:56:24.183111Z` | 0 / 0 | `f6426b67438e9400a10da6c1789be28380b990b838c9b62f47de496bdb8ac120` |

Each record describes the global ASF NISAR GCOV catalog, the inclusive November 12 date window, one completed page, and a complete query execution/coverage status for that requested window. Recheck this date only after it closes or if ASF signals a relevant catalog update.

## Reproducible records

| Maturity | Retrieved (UTC) | Scenes / pairs | SHA-256 |
|---|---|---:|---|
| VALIDATED | `2026-11-12T00:00:38.222576Z` | 0 / 0 | `3c68b5a2189ffedc61c6253a272a6d0fad213b40978f88f3c700d2fdb43e3209` |
| PROVISIONAL | `2026-11-12T00:00:38.271704Z` | 0 / 0 | `b74377de7f0b758a027ad633b70ccdaa77ea0d166cdaefd4339c7d13d7f1c78b` |
| BETA | `2026-11-12T00:00:38.232109Z` | 0 / 0 | `5e9855db9bf7f9c29b86bb48efc41770921340db0aac14a6dd6d9bd5c38a7346` |

Each record reports `query_execution_status=COMPLETE`, one completed daily window, one page, zero returned features, zero failures, and zero potentially truncated windows.

Reproduce from the repository root with:

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-11 --end 2026-11-11 --query-window-days 1 \
  --maturity VALIDATED \
  --output data/research/validated-gcov-global-time-series-2026-11-11.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-11 --end 2026-11-11 --query-window-days 1 \
  --maturity PROVISIONAL \
  --output data/research/provisional-gcov-global-time-series-2026-11-11.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-11 --end 2026-11-11 --query-window-days 1 \
  --maturity BETA \
  --output data/research/beta-gcov-global-time-series-2026-11-11.json
```

## Next action

Do not repeat this date/maturity screen absent evidence of late catalog ingestion or a changed query. Continue with the highest-priority compatible pair search only when new acquisition dates, replacement products, or a new processing release appear. For the five reviewed P05036 repeat pairs, reopen QA only if ASF changes the corresponding QA summary, product, or release; see the [product-specific QA review](2026-11-11-p05036-gcov-qa-root-cause.md).
