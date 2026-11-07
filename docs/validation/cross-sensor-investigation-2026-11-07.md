# Cross-sensor investigation assessment validation

ECHO now links the retained OPERA RTC-S1 diagnostic measurement and NASA OPERA DSWx-HLS optical context into one inspectable assessment. From the optical-context inspector, a user can open the assessment, review the measurement and product-class summaries, inspect four explicit hypotheses and each source's relationship and rationale, open the full linked record, and close the assessment back to the map.

## Evidence and result

- Assessment: [`opera-rtc-cross-sensor-investigation-2026-11-07.json`](../../data/research/opera-rtc-cross-sensor-investigation-2026-11-07.json), SHA-256 `a0f8a6324c44951a453142dc6450c7f1ba8c5dcca3db2432f4a324f62996d748`.
- Diagnostic Sentinel-1-derived OPERA RTC-S1 source record: [`opera-rtc-live-pair-T024-050661-2026-11-07.json`](../../data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json), SHA-256 `4556bd0d781de4f8e99c240682e761caa10fb540d09edcec029848b6d9c758ea`.
- NASA OPERA DSWx-HLS optical-context source record: [`dswx-hls-rtc-aoi-context-2026-11-07.json`](../../data/research/dswx-hls-rtc-aoi-context-2026-11-07.json), SHA-256 `8ff957f11ae7113e25609b93eabcddb7344a2d09492bd5b6ecd19ae14ba23479`.
- Builder: [`build_cross_sensor_investigation.py`](../../tools/research/build_cross_sensor_investigation.py), SHA-256 `d6ec2679cbe7289509bbde50835910c70e32df1f3e1ac490430005219aecb589`.
- Deterministic relationship evaluator: [`investigation.py`](../../echo/investigation.py), SHA-256 `c8e3f74fb231cdd079dd33b28b6b4d22e12559cad0d157f68d318a4f10ef2b97`.
- Recreate with `.venv/bin/python tools/research/build_cross_sensor_investigation.py --sar-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json --optical-record data/research/dswx-hls-rtc-aoi-context-2026-11-07.json --output data/research/opera-rtc-cross-sensor-investigation-2026-11-07.json`.

The builder verifies source record types and dispositions, identical WGS84 AOI bounds, compatible measurement and mask shapes, and sample counts before summarizing only valid stored SAR values. It links inputs by relative path and SHA-256. The result reports 1,043 of 1,199 common-clear SAR cells, with mean −2.35 dB and median −1.42 dB. DSWx-HLS WTR water-class counts change 36→27 and WTR-2 counts 135→59. These are descriptive product outputs.

The assessment state is `CAUSAL_INTERPRETATION_UNRESOLVED`. Hypothesis relationships are explicitly recorded as `SUPPORTS`, `CONTRADICTS`, `DOES_NOT_DISTINGUISH`, or `LIMITS_INTERPRETATION`. The deterministic rule yields `SUPPORTED_WITHIN_SCOPE` or `CONTRADICTED_WITHIN_SCOPE` only when all assessed relationships agree directionally; mixed, limiting, or nondiscriminating evidence is `UNRESOLVED`, and no recorded evidence is `NOT_EVALUATED`. The water-class-count statement is supported only within those product classifications. Whether it explains the SAR response is unresolved; other land-surface/acquisition effects are not tested; quality effects remain unresolved because neither RTC-S1 sidecar has a consolidated provider verdict. The products share an AOI but have different native grids and acquisition times. No pixel-wise cross-sensor comparison, causal attribution, ground-truth boundary, damage finding, confidence score, or NISAR result is claimed.

Synthetic fixtures test these software disposition rules, including agreement, contradiction, mixed evidence, nondiscriminating evidence, missing evidence, and invalid references. They contain no satellite observations and provide no scientific validation.

## Verification

- Focused reasoning and assessment tests: 15 passed.
- Full project suite: 196 passed.
- Python bytecode compilation and `git diff --check`: passed.
- Firefox/geckodriver local walkthrough: loaded 1,199 DSWx-HLS map cells; opened the linked assessment; verified the supported-within-scope, unresolved, and not-evaluated dispositions, the case's SUPPORTS, DOES_NOT_DISTINGUISH, and LIMITS_INTERPRETATION relationships, the diagnostic/not-NISAR label, and the causal boundary; closed the assessment and optical context and confirmed the original workspace returned. CONTRADICTS is covered by synthetic evaluator tests, not asserted for these observations.
- Captured interface state: [cross-sensor assessment screenshot](cross-sensor-investigation-map-2026-11-07.png), SHA-256 `8fb720c5be00988e036ca659791dbedbe0b8ce380c9ce892f14a044c47c76764`.
- JavaScript executed in Firefox. A standalone Node syntax check was unavailable because Node.js is not installed in this environment.

This verifies ECHO's software workflow and the integrity checks against the retained records. It does not independently validate the satellite algorithms, provider QA, DSWx-HLS classification accuracy, or the physical explanation of the SAR response.
