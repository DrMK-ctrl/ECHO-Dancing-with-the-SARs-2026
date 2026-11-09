# Iraq NISAR case workspace — 2026-11-09

## Result

The retained Iraq NISAR records are now available as a selectable case in ECHO's geographic workspace. Selecting the October 20, 2026 observation and loading its bounded preview exercised the live authenticated NISAR preview route and rendered real HHHH backscatter pixels on the map with an evidence inspector.

The preview remains `QA_HELD_DIAGNOSTIC_PREVIEW`. The metadata-matched October 8–20 pair is held because both provider QA summaries report `FAIL`; ECHO does not compute or display a change result for this pair.

## Inputs and reproducibility

The local case snapshot is assembled by [`build_iraq_nisar_case_snapshot.py`](../../tools/research/build_iraq_nisar_case_snapshot.py) from the retained complete catalog screen, two-scene provider-QA screen, and bounded HHHH preview. The builder performs no network access. It verifies the selected scene IDs, path 122/frame 70 metadata match, 12-day interval, P05023 release, provider QA failures, and that the preview belongs to the after-scene.

The registered workspace case is `iraq-2026-nisar-gcov-diagnostic`. Its catalog, case review, and both original provider QA reports are stored under [`data/cases/iraq-2026-nisar-diagnostic`](../../data/cases/iraq-2026-nisar-diagnostic/). Source artifact hashes and interpretation limits are retained in the case review. The preview source is [`nisar-iraq-p05023-hhhh-preview-2026-11-08.json`](../../data/research/nisar-iraq-p05023-hhhh-preview-2026-11-08.json).

The bounded request selected 9,918 pixel centers inside `[41.2, 36.7, 41.22, 36.72]` WGS84 from a 92 × 113 enclosing window in EPSG:32637. The browser displayed the raster and its `-19.18` to `-8.54 dB` display stretch; that stretch is visualization only. The source measurement is linear gamma-zero power. No event, cause, damage, or surface-change interpretation follows from this single observation.

## Runtime and interface check

Headless Firefox opened the Iraq case in the local application, selected the October 20 timeline observation, and invoked **Load Backscatter**. The live bounded request returned the QA-held preview; the browser rendered the raster, provider QA warning, acquisition and product identity, pair hold, and observation inspector. The screenshot is [`iraq-nisar-case-live-preview-2026-11-09.png`](assets/iraq-nisar-case-live-preview-2026-11-09.png), SHA-256 `c61dbd752f7beb8cd3ebdfe252ac22816e16962dcf352475350a275bba7cbd6c`.

The case has no OPERA temporal-series record. Its endpoint now returns the expected not-found response instead of an unrelated missing-manifest error. This is a case-routing correction, not a change to OPERA analysis.

## Verification boundary

The case builder and API tests verify deterministic assembly, case selection, QA-report access, and the absence of a false OPERA-series result. The browser check verifies the real-data map flow. Provider QA failures remain authoritative for this pair, so no scientific temporal analysis or accepted finding is claimed.
