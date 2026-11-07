# Cross-sensor investigation assessment validation

ECHO now links the retained OPERA RTC-S1 diagnostic measurement and NASA OPERA DSWx-HLS optical context into one inspectable assessment. From the optical-context inspector, a user can open the assessment, review the measurement and product-class summaries, inspect four explicit hypotheses and their evidence references, open the full linked record, and close the assessment back to the map.

## Evidence and result

- Assessment: [`opera-rtc-cross-sensor-investigation-2026-11-07.json`](../../data/research/opera-rtc-cross-sensor-investigation-2026-11-07.json), SHA-256 `c814e6fd2237ee581bdd8787b1f37b545225596c4123379580edc5dc00bec326`.
- Diagnostic Sentinel-1-derived OPERA RTC-S1 source record: [`opera-rtc-live-pair-T024-050661-2026-11-07.json`](../../data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json), SHA-256 `4556bd0d781de4f8e99c240682e761caa10fb540d09edcec029848b6d9c758ea`.
- NASA OPERA DSWx-HLS optical-context source record: [`dswx-hls-rtc-aoi-context-2026-11-07.json`](../../data/research/dswx-hls-rtc-aoi-context-2026-11-07.json), SHA-256 `8ff957f11ae7113e25609b93eabcddb7344a2d09492bd5b6ecd19ae14ba23479`.
- Builder: [`build_cross_sensor_investigation.py`](../../tools/research/build_cross_sensor_investigation.py), SHA-256 `a20f19a4855a63ed3768b71969bd843bfc17f6afc7261bacce4f01346c3b6c97`.
- Recreate with `.venv/bin/python tools/research/build_cross_sensor_investigation.py --sar-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json --optical-record data/research/dswx-hls-rtc-aoi-context-2026-11-07.json --output data/research/opera-rtc-cross-sensor-investigation-2026-11-07.json`.

The builder verifies source record types and dispositions, identical WGS84 AOI bounds, compatible measurement and mask shapes, and sample counts before summarizing only valid stored SAR values. It links inputs by relative path and SHA-256. The result reports 1,043 of 1,199 common-clear SAR cells, with mean −2.35 dB and median −1.42 dB. DSWx-HLS WTR water-class counts change 36→27 and WTR-2 counts 135→59. These are descriptive product outputs.

The assessment state is `CAUSAL_INTERPRETATION_UNRESOLVED`. The water-class-count statement is supported only within those product classifications. Whether it explains the SAR response is unresolved; other land-surface/acquisition effects are not tested; quality effects remain unresolved because neither RTC-S1 sidecar has a consolidated provider verdict. The products share an AOI but have different native grids and acquisition times. No pixel-wise cross-sensor comparison, causal attribution, ground-truth boundary, damage finding, confidence score, or NISAR result is claimed.

## Verification

- Focused assessment tests: 4 passed.
- Full project suite: 185 passed.
- Python bytecode compilation and `git diff --check`: passed.
- Firefox/geckodriver local walkthrough: loaded 1,199 DSWx-HLS map cells; opened the linked assessment; verified its unresolved status, diagnostic/not-NISAR label, untested hypothesis, and causal boundary; closed the assessment and optical context and confirmed the original workspace returned.
- JavaScript executed in Firefox. A standalone Node syntax check was unavailable because Node.js is not installed in this environment.

This verifies ECHO's software workflow and the integrity checks against the retained records. It does not independently validate the satellite algorithms, provider QA, DSWx-HLS classification accuracy, or the physical explanation of the SAR response.
