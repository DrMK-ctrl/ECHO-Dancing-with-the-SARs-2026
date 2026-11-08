# Temporal-series investigation draft — 2026-11-08

## Result

The retained T024 three-acquisition OPERA RTC-S1 series can start a private, unassessed investigation draft from its existing map inspector. The record retains all three observations and the exact submitted series JSON checksum. The draft role and status remain `DIAGNOSTIC_SENTINEL_1_DERIVED_OPERA_TEMPORAL_SERIES` and `DIAGNOSTIC_PRODUCT_MASKED_TIME_SERIES`.

The series role is non-directional. The deterministic draft assessor rejects `SUPPORTS` and `CONTRADICTS` for this QA-limited source. A `DOES_NOT_DISTINGUISH` analyst entry remains possible and leaves the hypothesis unresolved; it is still unauthenticated analyst input, not a scientific finding.

## Verification

- `.venv/bin/python -m pytest tests/test_investigation_draft.py tests/test_web.py -q` — **55 passed**.
- `git diff --check` — passed.
- Firefox headless against the local T024 application — opened the existing three-acquisition series inspector, launched the draft dialog, showed the missing consolidated provider QA boundary, submitted competing hypotheses and a single-target follow-up design, and rendered the resulting unassessed series-source draft.
- A regression check rejected a series record whose per-observation QA links were incomplete.

## Limits

This is workflow integration using a retained NASA OPERA RTC-S1/Sentinel-1-derived series, not a NISAR measurement or QA-cleared result. The workflow checks record structure and lineage fields supplied in the series record; draft creation does not re-fetch ASF data. It does not establish source independence, physical cause, or scientific validation.
