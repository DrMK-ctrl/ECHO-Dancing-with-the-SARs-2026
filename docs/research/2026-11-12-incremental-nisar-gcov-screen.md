# Incremental NISAR GCOV catalog screen — 2026-11-12

## Result

After the November 11 UTC acquisition day closed, ASF was queried for NISAR GCOV scenes acquired on November 11 in all three available catalog maturities. Each daily query completed one page and returned no scenes. There were no query failures and no result-cap truncations. No products were available for metadata pairing, QA retrieval, or pixel analysis.

This is a date-specific catalog availability result as of the recorded retrieval time, not a statement that the broader archive has no suitable NISAR repeats. It does not change provider QA or release status for previously screened products.

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
