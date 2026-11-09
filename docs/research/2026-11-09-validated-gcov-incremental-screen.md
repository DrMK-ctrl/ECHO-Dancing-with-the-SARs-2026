# Incremental NISAR VALIDATED-GCOV screen — 2026-11-09

## Result

The one-day ASF catalog query for 2026-11-09 returned no VALIDATED GCOV features. The query completed one page, recorded no error, and did not reach its 2,000-result cap. It produced no scene or temporal-pair candidates, so no QA products or measurement arrays were requested.

## Reproducible record

- Query record: [`validated-gcov-global-time-series-2026-11-09-2026-11-09.json`](../../data/research/validated-gcov-global-time-series-2026-11-09-2026-11-09.json)
- Query: `VALIDATED` maturity, `GCOV`, global, inclusive 2026-11-09 through 2026-11-09; one calendar day per query window.
- Retrieved: `2026-11-09T01:16:56.892706Z`.
- Record SHA-256: `b922863e3babd50dd7368a49690bf3fd5b6694a449ec33484c2a08c7378708d2`.
- Command: `.venv/bin/python tools/research/screen_validated_gcov_time_series.py --start 2026-11-09 --end 2026-11-09 --query-window-days 1`

## Interpretation

This closes only the searched date. It does not establish that no other NISAR collection, maturity, or date has a suitable observation. The existing 2026-10-09 through 2026-11-08 screen still has 54 metadata-compatible pairs. Six pairs (12 products) have exact-scene QA records; all 12 report provider `FAIL` on the aggregate identification-group check, and 48 pairs remain unassessed. The observed metadata discrepancies do not identify ASF's exact failing QA rows or supersede its disposition. Further screening within the same P05036 release remains lower priority than a new processing release or authoritative clarification.
