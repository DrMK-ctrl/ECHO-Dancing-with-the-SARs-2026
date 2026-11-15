# Incremental NISAR GCOV catalog screen — 2026-11-13

## Early-day availability snapshot

At approximately `2026-11-13T01:01:39Z`, ECHO queried the global ASF NISAR GCOV catalog for the November 13 acquisition date in each available maturity. The date was still in progress. All three requests completed one daily page, returned zero features, reported no query errors, and did not reach the 2,000-result cap. This is an early snapshot only; it does not establish final availability for November 13 or completeness of the broader archive.

No scenes were available from these queries for temporal matching, provider-QA retrieval, or measurement reads. Existing QA holds and scientific conclusions are unchanged.

| Maturity | Record | Retrieved (UTC) | Scenes / pairs | SHA-256 |
|---|---|---|---:|---|
| VALIDATED | [`validated-gcov-global-time-series-2026-11-13-early-snapshot.json`](../../data/research/validated-gcov-global-time-series-2026-11-13-early-snapshot.json) | `2026-11-13T01:01:39.209313Z` | 0 / 0 | `7caf113aa8304f5568966f8988ab48e03500a5e5fe59b5d6cb1998f162d45137` |
| PROVISIONAL | [`provisional-gcov-global-time-series-2026-11-13-early-snapshot.json`](../../data/research/provisional-gcov-global-time-series-2026-11-13-early-snapshot.json) | `2026-11-13T01:01:39.246611Z` | 0 / 0 | `d4d6be438901256d68d7fa622a2db45640b05993b04335e97d65d81f8e933488` |
| BETA | [`beta-gcov-global-time-series-2026-11-13-early-snapshot.json`](../../data/research/beta-gcov-global-time-series-2026-11-13-early-snapshot.json) | `2026-11-13T01:01:39.235860Z` | 0 / 0 | `ab528e34989d4f975afb5a41900d5daca7455c743ea68716fb048c30a1a3a8c5` |

Each record declares complete coverage and execution for its requested one-day window, with one page, zero failures, and zero potentially truncated windows. “Complete” applies only to those requests, not to archive completeness.

## Closed-day refresh — November 12

At `2026-11-13T17:34Z`, ECHO refreshed the global catalog screen for the now-closed November 12 acquisition date across all three maturities. This is a new temporal snapshot, roughly 17.5 hours after the prior post-close refresh, rather than a repeat of November 13's in-progress query. Each maturity returned zero scenes and zero pairs in one complete page, with no query error and no truncation. This adds no candidate for temporal QA screening.

| Maturity | Record | Retrieved (UTC) | Scenes / pairs | SHA-256 |
|---|---|---|---:|---|
| VALIDATED | [`validated refresh`](../../data/research/validated-gcov-global-time-series-2026-11-12-refresh-1734z.json) | `2026-11-13T17:34:26.711408Z` | 0 / 0 | `967d4201108789d97b1d0e1f4f2107b27cf1a227ef4749ce1d06cdb866735c2e` |
| PROVISIONAL | [`provisional refresh`](../../data/research/provisional-gcov-global-time-series-2026-11-12-refresh-1734z.json) | `2026-11-13T17:34:50.038832Z` | 0 / 0 | `13d20b7ed5602f5e8a3139590490e0a515d8d571831946f4edd59f63f7497d78` |
| BETA | [`BETA refresh`](../../data/research/beta-gcov-global-time-series-2026-11-12-refresh-1734z.json) | `2026-11-13T17:34:50.049815Z` | 0 / 0 | `7685a8747ad602ff9428d25105c685a558e56301e66e204a4ed05664eb97b312` |

Reproduce from the repository root with:

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-12 --end 2026-11-12 --query-window-days 1 \
  --maturity VALIDATED \
  --output data/research/validated-gcov-global-time-series-2026-11-12-refresh-1734z.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-12 --end 2026-11-12 --query-window-days 1 \
  --maturity PROVISIONAL \
  --output data/research/provisional-gcov-global-time-series-2026-11-12-refresh-1734z.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-12 --end 2026-11-12 --query-window-days 1 \
  --maturity BETA \
  --output data/research/beta-gcov-global-time-series-2026-11-12-refresh-1734z.json
```

This is a date-bounded ASF catalog result, not evidence that the full archive has no products or that later catalog updates will not appear. No provider QA artifacts or raster pixels were requested because the query returned no scenes.

## Reproduction

From the repository root:

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-13 --end 2026-11-13 --query-window-days 1 \
  --maturity VALIDATED \
  --output data/research/validated-gcov-global-time-series-2026-11-13-early-snapshot.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-13 --end 2026-11-13 --query-window-days 1 \
  --maturity PROVISIONAL \
  --output data/research/provisional-gcov-global-time-series-2026-11-13-early-snapshot.json

.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-11-13 --end 2026-11-13 --query-window-days 1 \
  --maturity BETA \
  --output data/research/beta-gcov-global-time-series-2026-11-13-early-snapshot.json
```

Recheck November 13 only after that UTC acquisition day closes, unless ASF announces a relevant catalog correction, replacement product, or processing-release update. This avoids repeating an unchanged in-progress-day query.
