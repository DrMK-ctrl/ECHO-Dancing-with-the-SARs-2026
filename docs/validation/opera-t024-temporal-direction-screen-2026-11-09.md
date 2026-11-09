# T024 temporal direction screen — 2026-11-09

## Result

ECHO derives an additional descriptive summary from the retained OPERA RTC-S1 three-date record after validating the source series against the primary pair. The computation classifies signs of both adjacent VV gamma-zero log-ratio steps on the exact 1,034-pixel all-date common support:

| Sign category across adjacent steps | Pixels |
|---|---:|
| Both steps positive | 90 |
| Both steps negative | 294 |
| One positive and one negative | 650 |
| At least one exact-zero step | 0 |

The durations are 23.99999 and 383.99990 days (about 24 and 384 days). The remaining 165 selected AOI centers are outside the all-date common support and are not assessed. The counts sum to all 1,034 assessed pixels.

## Scientific boundary

This is a sign-only, zero-threshold description. It does not compare magnitudes against measurement uncertainty; values near zero may change category under noise. The different interval lengths and shared middle observation prevent interpreting agreement as physical persistence or independent corroboration. The summary establishes no flood/event extent, event duration, mechanism, or cause. OPERA provider QA still has no consolidated disposition, and the hypothesis relationships and case assessment remain unresolved.

## Provenance and integrity

The summary is computed from the linked temporal-series adjacent per-pixel arrays after the existing validator verifies exact scene sequence, acquisition timestamps, grid, support, derived values, and interval summaries. Schema-version-2 T024 assessments retain this summary. The web validator recomputes it from the source series and rejects a mismatched or missing value. The source evidence remains at [`opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json`](../../data/research/opera-rtc-t024-temporal-series-2024-2025-2026-11-08.json), linked through the T024 manifest and the active assessment.

The investigation card exposes counts, interval durations, the no-threshold caveat, and QA/dependence limitations. The source-inspection action still opens the linked temporal measurements and provenance record.

## Verification

- `.venv/bin/python -m pytest -q tests/test_opera_rtc_series_analysis.py tests/test_cross_sensor_investigation.py tests/test_web.py` — **74 passed**.
- `.venv/bin/python -m pytest -q` — **387 passed**.
- `.venv/bin/python -m compileall -q echo tools/research` and `git diff --check` — passed.
- A local headless Firefox WebDriver session opened the T024 assessment. The rendered card showed `24.0 d and 384.0 d`, the counts `90 / 294 / 650`, the near-zero/no-threshold limitation, and the unresolved assessment state. This checks the current browser rendering and source-linked assessment flow; it does not establish a physical event or clear provider QA.
- The active assessment builder reported `CAUSAL_INTERPRETATION_UNRESOLVED` and 11 evidence artifacts. H2 and H3 remain `UNRESOLVED`.
