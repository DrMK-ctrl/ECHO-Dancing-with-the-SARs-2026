# Incremental NISAR VALIDATED-GCOV coverage check — 2026-11-09

**Retrieved:** 2026-11-09 05:35 UTC
**Provider:** Alaska Satellite Facility DAAC CMR
**Disposition:** complete for the two requested daily query windows; no new scenes found

## Query

The existing global VALIDATED-GCOV screen ended on November 7. This incremental search queried the two newly elapsed UTC acquisition-date windows:

- `[2026-11-08, 2026-11-09)` — one page, zero features.
- `[2026-11-09, 2026-11-10)` — one page, zero features as of 05:35 UTC, while November 9 was still in progress.

Both requests completed without errors. Neither response reached the 2,000-feature daily cap. The search used ASF's `asf_search` client, collection maturity `VALIDATED`, product `GCOV`, dataset `NISAR`, one-day windows, and no spatial filter. No scene metadata, QA summary, or pixel data were returned. The exact query record is retained in [`validated-gcov-global-time-series-2026-11-08-09.json`](../../data/research/validated-gcov-global-time-series-2026-11-08-09.json).

## Interpretation

The query found zero additional scenes and therefore no new temporal pair. The earlier held pair remains the only metadata-compatible VALIDATED pair in the previously retained October 21–November 7 search. This result establishes only what CMR returned for these query windows at the recorded time; it does not establish completeness of the global archive, exclude later catalog ingestion, or say anything about unqueried products or dates.

Do not repeat these same date windows without a specific reason. A later incremental check should begin after November 9 or document why the earlier interval is being refreshed.
