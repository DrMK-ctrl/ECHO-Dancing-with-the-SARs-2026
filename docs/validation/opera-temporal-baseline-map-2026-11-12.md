# OPERA temporal baseline map check — 2026-11-12

## Scope

The T024 three-acquisition Sentinel-1-derived OPERA RTC-S1 record already contains adjacent comparisons and comparisons against its first acquisition. This check verifies that the first-acquisition comparison is available through the existing temporal-series map interface and remains clearly diagnostic.

## Implementation and checks

- Added the retained first-acquisition comparison to the existing map-comparison selector alongside both adjacent intervals.
- The browser validates baseline source IDs, timestamps, grid shape, the all-observation common-support mask, and each finite pixel difference against the retained observation arrays before drawing the layer.
- Map caption, attribution, watermark, and value summary identify the selected first-acquisition baseline and its dates. The provider QA warning remains visible.
- Headless Firefox against the loopback T024 app displayed the three choices, selected the 408-day 2024-05-11 to 2025-06-23 baseline, and rendered the geolocated raster. The inspector showed 1,034 cells, median −1.252 dB, and mean −2.156 dB. Attribution marked it diagnostic only; the warning stated that OPERA has no consolidated provider verdict.
- Automated focused suite: `PYTHONPATH=. .venv/bin/pytest -q tests/test_opera_rtc_series_analysis.py tests/test_adversarial.py tests/test_investigation_renderer.py tests/test_web.py` — **89 passed**. The new test also guards the selector and browser-side reproduction checks.

## Scientific boundary

This is a visualization of an existing reproducible descriptive comparison. It does not clear provider QA, add an independent observation, establish persistence, identify an event or cause, or create a validated change finding. The baseline interval differs substantially in duration from the adjacent intervals, and all comparisons share the same acquisitions and common support.
