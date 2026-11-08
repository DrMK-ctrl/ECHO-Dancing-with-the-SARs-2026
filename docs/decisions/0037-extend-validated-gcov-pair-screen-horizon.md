# Decision 0037: screen validated GCOV across the repeat interval

Date: 2026-11-08

## Context

The retained 2026-10-21 through 2026-11-07 global catalog screen contained 993 scenes and one temporal pair. That horizon began too late to include the earlier acquisitions needed to pair with recent observations. A separate 2026-11-01 through 2026-11-08 search returned 140 scenes and no pair; the latest returned acquisition date was November 6. Neither catalog screen alone establishes data quality or measurement suitability.

## Decision

Use a bounded 31-day global VALIDATED-GCOV catalog window when discovering same-path/frame repeat observations, then inspect provider QA on exact candidate scene IDs before reading measurement arrays. Retain the full query and page accounting. The pair matcher continues to label outputs as metadata matches only.

## Screen results

The 2026-10-09 through 2026-11-08 search returned 2,018 unique catalog scenes, no capped daily windows, and 54 metadata-compatible pairs. The pairs have approximately 12-day intervals and all use CRID P05036. This expands the candidate set; it does not establish a suitable real-data comparison.

Two distinct path/frame pairs (19/80 and 149/83) were selected for provider-QA sampling. All four exact products report provider `FAIL` on the aggregate identification-group check; the other listed identification, grid, calibration, data-range, and completion groups pass. The parsed QA reports expose `instrumentName=LSAR` and `listOfObservationModes=(NOT SPECIFIED)`. Their partial cross-check against cited `nisarqa` v17.2.0 rules marks both values as mismatches (`L-SAR` or `S-SAR` and formatted observation-mode values are expected). This cross-check is explanatory evidence, not ASF per-field failure attribution, and does not override the provider's aggregate failure. The four-product sample does not prove that every P05036 product fails.

No product measurement arrays or pixel measurements were read, and no temporal measurement was created.

## Processing improvement

`screen_nisar_crid_reprocessing_qa.py` now accepts repeated exact `--scene-id` values, requires them to form complete metadata-compatible pairs, and records the source catalog path and checksum. This makes the next QA step bounded to the selected candidate products instead of retrieving QA for every pair in a release.

## Reproduction

```bash
.venv/bin/python tools/research/screen_validated_gcov_time_series.py \
  --start 2026-10-09 --end 2026-11-08 \
  --output data/research/validated-gcov-global-time-series-2026-10-09-11-08.json
```

The exact product identifiers and QA artifacts for the two-pair sample are retained in [`validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json`](../../data/research/validated-gcov-p05036-cross-track-qa-sample-2026-11-08.json). The QA screener can replay that selection by passing the four values in `selected_scene_ids` as repeated `--scene-id` arguments together with the catalog record and CRID `P05036`.

## Next gate

Do not proceed to paired GCOV measurement for these QA-held products. Verify whether a later processing release corrects the identification metadata or evaluate a scientifically appropriate alternate SAR path while preserving the NASA/NISAR priority. Every new candidate still requires its own product-specific QA and pixel-support checks.
