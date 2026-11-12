# VALIDATED GCOV screen for the coarse Iraq window — 2026-11-12

## Why this query was run

The retained June 17–July 17 PROVISIONAL screen found 59 full/full metadata candidates intersecting the coarse Iraq bounds. Because NISAR VALIDATED products were subsequently released, this query checked whether the same acquisition window and geography had a validated alternative before investigating more PROVISIONAL QA failures.

## Result

ASF returned no NISAR GCOV VALIDATED scenes for `[39°E, 29°N, 49°E, 38°N]` during June 17–July 17, 2026. All 31 daily catalog windows completed one page each, with no errors and no result-cap truncation. There were no products to pair, and no QA report or measurement was requested.

This is a maturity- and AOI-specific catalog result, not evidence that VALIDATED NISAR lacks coverage elsewhere or that the wider archive is complete. The provisional candidates remain separate products; none becomes VALIDATED by matching a later release's catalog records.

## Reproducibility

- Record: [`validated-gcov-iraq-bounds-2026-06-17-07-17.json`](../../data/research/validated-gcov-iraq-bounds-2026-06-17-07-17.json)
- Retrieved: `2026-11-12T02:26:07.404873Z`
- SHA-256: `8664315cb27b1b6fddd1f1df6c38e316ffde6eafc6fadaaa8a352a8ab06e0a43`
- Query maturity: `VALIDATED`; WGS84 bounds: west 39, south 29, east 49, north 38; daily windows; 2026-06-17 through 2026-07-17 inclusive.

Reproduce from the repository root:

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-06-17 --end 2026-07-17 \
  --maturity VALIDATED --query-window-days 1 \
  --bounds 39 29 49 38 \
  --output data/research/validated-gcov-iraq-bounds-2026-06-17-07-17.json
```

## Decision

Do not repeat this fixed AOI/date/maturity query without evidence of late ingestion or a changed archive. It does not resolve the P05036 VALIDATED QA failures in later acquisitions. Those products remain held; an unchanged catalog result, processing maturity label, or local metadata inspection cannot substitute for provider QA acceptance.
