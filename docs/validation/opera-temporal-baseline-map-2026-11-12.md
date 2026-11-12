# OPERA temporal baseline map check — 2026-11-12

## Scope

The T024 three-acquisition Sentinel-1-derived OPERA RTC-S1 record already contains adjacent comparisons and comparisons against its first acquisition. This check verifies that the first-acquisition comparison is available through the existing temporal-series map interface and remains clearly diagnostic.

## Implementation and checks

- Added the retained first-acquisition comparison to the existing map-comparison selector alongside both adjacent intervals.
- The browser validates baseline source IDs, timestamps, grid shape, the all-observation common-support mask, and each finite pixel difference against the retained observation arrays before drawing the layer.
- Map caption, attribution, watermark, and value summary identify the selected first-acquisition baseline and its dates. The provider QA warning remains visible.
- Headless Firefox against the loopback T024 app displayed the three choices, selected the 408-day 2024-05-11 to 2025-06-23 baseline, and rendered the geolocated raster. The inspector showed 1,034 cells, median −1.252 dB, and mean −2.156 dB. Attribution marked it diagnostic only; the warning stated that OPERA has no consolidated provider verdict.
- Each recomputed temporal comparison in **Challenge This Finding** now has a map handoff. A browser walkthrough opened the T024 assessment, challenged its H2 water-change explanation, selected the first-acquisition comparison, and returned to the geographic workspace with the corresponding baseline layer selected. Before handoff, the client checks the comparison key, source-series SHA-256, and both acquisition timestamps against the loaded series. A deliberately altered SHA-256 left the challenge open and the map selection unchanged; restoring the checksum allowed the handoff.
- Clicking a valid baseline-map cell now exposes the complete retained per-observation γ⁰ dB trace plus the selected after-minus-before difference. At cell (15, 10), 30.034077°S, 51.236841°W, the displayed trace is −1.932 dB (2024-05-11), −2.506 dB (2024-06-04), and −1.244 dB (2025-06-23). For the first-to-last comparison, the retained unrounded samples give +0.689 dB. The trace shows a decrease followed by a rebound in radar response; it does not establish persistence or cause of a surface condition.
- Automated focused suite: `PYTHONPATH=. .venv/bin/pytest -q tests/test_opera_rtc_series_analysis.py tests/test_adversarial.py tests/test_investigation_renderer.py tests/test_web.py` — **90 passed**. Renderer tests check that T024 exposes all three map actions and T163, which lacks a linked series, exposes none; the web regression test guards client-side source and measurement checks.
- Full repository suite after the handoff integration: `PYTHONPATH=. .venv/bin/pytest -q` — **478 passed**.

## Scientific boundary

This is a visualization of an existing reproducible descriptive comparison. It does not clear provider QA, add an independent observation, establish persistence, identify an event or cause, or create a validated change finding. The baseline interval differs substantially in duration from the adjacent intervals, and all comparisons share the same acquisitions and common support.
