# Cross-sensor investigation assessment validation

ECHO now links the retained OPERA RTC-S1 diagnostic measurement and NASA OPERA DSWx-HLS optical context into one inspectable assessment. From the optical-context inspector, a user can open the assessment, review the measurement and product-class summaries, inspect four explicit hypotheses and each source's relationship and rationale, expand expected observations and weakening conditions, open the full linked record, and close the assessment back to the map.

## Evidence and result

- Assessment: [`opera-rtc-cross-sensor-investigation-2026-11-07.json`](../../data/research/opera-rtc-cross-sensor-investigation-2026-11-07.json), SHA-256 `2ec31dae8ae99e98614bf6094e265c385f2143531c470cd90dead5615be78df0`.
- Diagnostic Sentinel-1-derived OPERA RTC-S1 source record: [`opera-rtc-live-pair-T024-050661-2026-11-07.json`](../../data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json), SHA-256 `4556bd0d781de4f8e99c240682e761caa10fb540d09edcec029848b6d9c758ea`.
- NASA OPERA DSWx-HLS optical-context source record: [`dswx-hls-rtc-aoi-context-2026-11-07.json`](../../data/research/dswx-hls-rtc-aoi-context-2026-11-07.json), SHA-256 `6b9b8d2bb26ec14c70e3738cce2d36e220918640ce4092706cf46ea8da331a37`.
- CMR temporal discovery record: [`dswx-hls-followup-screen-2026-11-07.json`](../../data/research/dswx-hls-followup-screen-2026-11-07.json), SHA-256 `6aad64aae2fd7e2084070bf716b9e99237fce76963fe9c35e75660518a11a14d`.
- Retrieved nearer optical context record: [`dswx-hls-nearer-rtc-context-2026-11-07.json`](../../data/research/dswx-hls-nearer-rtc-context-2026-11-07.json), SHA-256 `ec702b3ff352f740399dbffe3dcab892287afb92108ed5a1e359392f21f813cf`.
- Builder: [`build_cross_sensor_investigation.py`](../../tools/research/build_cross_sensor_investigation.py), SHA-256 `587ba22c2b1434bb844fc04b719304f10dc8fb088dfcdfe48774d66e41ffce33`.
- Deterministic hypothesis, relationship, and follow-up validators: [`investigation.py`](../../echo/investigation.py), SHA-256 `baa0191a91f6d38bcbafa9bf2794bd5765a5f71de91b6eeb87cc3ff03093a7a9`.
- Recreate with `.venv/bin/python tools/research/build_cross_sensor_investigation.py --sar-record data/research/opera-rtc-live-pair-T024-050661-2026-11-07.json --optical-record data/research/dswx-hls-rtc-aoi-context-2026-11-07.json --nearer-optical-record data/research/dswx-hls-nearer-rtc-context-2026-11-07.json --catalog-screen-record data/research/dswx-hls-followup-screen-2026-11-07.json --output data/research/opera-rtc-cross-sensor-investigation-2026-11-07.json`.

The builder verifies source record types and dispositions, identical WGS84 AOI bounds, compatible measurement and mask shapes, and sample counts before summarizing only valid stored SAR values. It links inputs by relative path and SHA-256. The result reports 1,043 of 1,199 common-clear SAR cells, with mean −2.35 dB and median −1.42 dB. DSWx-HLS WTR water-class counts change 36→27 and WTR-2 counts 135→59. These are descriptive product outputs.

The assessment state is `CAUSAL_INTERPRETATION_UNRESOLVED`. Hypothesis relationships are explicitly recorded as `SUPPORTS`, `CONTRADICTS`, `DOES_NOT_DISTINGUISH`, or `LIMITS_INTERPRETATION`. The deterministic rule yields `SUPPORTED_WITHIN_SCOPE` or `CONTRADICTED_WITHIN_SCOPE` only when all assessed relationships agree directionally; mixed, limiting, or nondiscriminating evidence is `UNRESOLVED`, and no recorded evidence is `NOT_EVALUATED`. The water-class-count statement is supported only within those product classifications. A bounded CMR search found 13 nearby candidates; the nearest retrieved pair is 2.20 days before and 1.80 days before the two RTC-S1 acquisitions. It does not resolve the water explanation: standard WTR has zero shared valid AOI pixels, and all 329 earlier WTR-2 water-coded cells are cloud/snow flagged. This follow-up is explicitly `RETRIEVED_QUALITY_LIMITED`, not independent confirmation (the later product is shared with the original context pair). Other land-surface/acquisition effects remain untested; quality effects remain unresolved because neither RTC-S1 sidecar has a consolidated provider verdict. The products share an AOI but have different native grids and acquisition times. No pixel-wise cross-sensor comparison, causal attribution, ground-truth boundary, damage finding, confidence score, or NISAR result is claimed.

Synthetic fixtures test these software disposition rules, including agreement, contradiction, mixed evidence, nondiscriminating evidence, missing evidence, and invalid references. They contain no satellite observations and provide no scientific validation.

The follow-up plan links three actions to their target hypotheses: provider QA resolution (`PROVIDER_RESPONSE_REQUIRED`), the closer water-context search (`RETRIEVED_QUALITY_LIMITED`), and a search for scale-appropriate evidence about alternative surface drivers (`NOT_SEARCHED`). Follow-ups remain unranked; each states what it could test and what its result would and would not establish.

Each hypothesis now also states its expected observation, a result that could weaken it, required evidence, and testability status. The water-to-SAR explanation is `NOT_TESTABLE_WITH_RETAINED_EVIDENCE`; this is distinct from `NOT_TESTED` for alternative drivers and `DESCRIPTIVE_ONLY` for the optical class-count statement. The interface keeps these conditions collapsed until opened, while showing testability status beside each hypothesis. These fields are analyst-authored and structurally validated; the software does not judge whether a hypothesis or predicted relationship is scientifically correct.

## Verification

- Focused reasoning and assessment tests: included in the full suite.
- Full project suite: 214 passed.
- Python bytecode compilation and `git diff --check`: passed.
- Firefox/geckodriver local walkthrough: loaded 1,199 DSWx-HLS map cells; opened the assessment; verified all four testability states, expanded the water hypothesis's expected observation and weakening conditions, inspected the four-artifact linked record, and returned to the original workspace. `CONTRADICTS` is covered by synthetic evaluator tests, not asserted for these observations.
- Captured interface state with the water-hypothesis test conditions expanded: [cross-sensor assessment screenshot](cross-sensor-investigation-map-2026-11-07.png), SHA-256 `19366c4f80f52ec7ad3caeff5d20f74aec3d156622a6c17d01dc2b7cf034acb9`.
- JavaScript executed in Firefox. A standalone Node syntax check was unavailable because Node.js is not installed in this environment.

This verifies ECHO's software workflow and the integrity checks against the retained records. It does not independently validate the satellite algorithms, provider QA, DSWx-HLS classification accuracy, or the physical explanation of the SAR response.
