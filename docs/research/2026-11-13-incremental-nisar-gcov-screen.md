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
