# GPM inter-acquisition chronology validation — 2026-11-08

## Result

The complete NASA GPM IMERG Final Daily series from 9 through 31 May 2024 is linked into the T163 investigation assessment and shown in the investigation interface. The retained regional context has 23/23 complete days at 48/48 nearest-cell samples, totals 214.929991 mm, and peaks at 77.439995 mm/day on 23 May. H3 (soil-moisture change) remains unresolved and the chronology is explicitly classified as nondiscriminating regional precipitation context. Decision 0042 records the current separation of this branch from vegetation and acquisition-condition hypotheses.

## Reproducibility and integrity

- `tests/test_gpm_interacquisition_context.py` checks the interval summary and rejects a missing day and an incomplete daily sample.
- The assessment builder rebuilds the chronology from the retained SAR pair, intervening daily record, and trailing GPM context; it compares the derived values and source lineage before linking it.
- The assessment web validator checks parent record hashes, case identity, complete consecutive dates, daily-value bounds, and recomputed cumulative and maximum values. Daily source records validate their query span, bounded subset paths, and SHA-256 hashes.
- The case manifest links both the source daily record and derived chronology. All 16 new NetCDF4 subsets are retained under `data/research/source-artifacts/gpm-imerg-T163-349925-2024-05-09-24/` (approximately 644 KB total).

## Verification performed

- `.venv/bin/python -m pytest -q` — **262 passed**.
- `.venv/bin/python -m compileall -q echo tools/research/build_cross_sensor_investigation.py tools/research/build_gpm_interacquisition_context.py` — passed.
- `git diff --check` — passed.
- Firefox headless through the local ECHO server — opened the T163 NASA optical context, opened the linked assessment, confirmed the inter-acquisition series card and source-inspection control, opened the chronology evidence record, and confirmed it parsed in the record dialog.
- Node.js is unavailable; the updated JavaScript was exercised in Firefox.

## Interpretation limits

The ~0.1° native grid is much coarser than this AOI. The chronology does not measure local soil moisture or flood extent, validate the SAR measurement, distinguish a physical explanation, or resolve the RTC-S1 provider QA hold. The pair remains diagnostic Sentinel-1/OPERA data, not NISAR. This is a useful temporal evidence lane in a case-specific investigation slice, not a completed general Investigation Engine.
