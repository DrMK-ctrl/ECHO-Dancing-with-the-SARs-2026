# Open evidence-search test-design contract

**Date:** 2026-11-08
**Result:** Passed

## Scope

Open scientific evidence searches now require an explicit pre-search design in `echo/investigation.py`. The contract records the hypothesis under test, mechanism branch, expected observation, weakening condition, inconclusive condition, acceptance gates, interpretation limit, and all hypotheses outside the declared target set. It rejects an open search without this design and rejects any overlap between target and non-target hypotheses.

The T163 case's H3 follow-up was regenerated from retained input records. It remains `NOT_SEARCHED`; its role is a declared investigation request, not a result or candidate source. The SAR QA prerequisite is still a separate workstream. The H3 design does not test H1, H2, or H4. All 16 linked evidence records passed the web assessment validator. The assessment's causal disposition remains unresolved and the RTC-S1 measurement remains diagnostic. The regenerated assessment SHA-256 is `7e0d13218b71c6a456bec5fc429c979dccb5dfee8e120fb90acb3ffb1905a3f3`.

The active T024 case assessment was also regenerated from its retained SAR and optical source records. Its F3 independent-surface-driver search remains `NOT_SEARCHED` and now has the same falsifiable-outcome contract. All four linked evidence records passed the web validator; the assessment remains unresolved and diagnostic. Its SHA-256 is `40ab9ee644f2a695d523cb9f341b4e1c1c232ea86fbddcf7740e55f9c767fd27`.

## Verification

- Focused investigation, assessment-builder, and web tests: **85 passed**.
- Full suite: **276 passed**.
- `.venv/bin/python -m compileall -q echo tools/research/build_cross_sensor_investigation.py` passed.
- `git diff --check` passed.
- Rebuilt the T163 assessment from its retained SAR, optical, spatial, polarization, GPM, SMAP, HLS, and ANA records; the builder returned `CAUSAL_INTERPRETATION_UNRESOLVED` and 16 evidence artifacts.
- Rebuilt the T024 assessment from its retained SAR and DSWx-HLS records; the builder returned `CAUSAL_INTERPRETATION_UNRESOLVED` and four evidence artifacts.
- `echo.web._validate_assessment_record` accepted the generated record and resolved all 16 linked records with their existing checksums.

Rebuild the T163 record from the repository root:

```bash
.venv/bin/python tools/research/build_cross_sensor_investigation.py \
  --sar-record data/research/opera-rtc-live-pair-T163-349925-IW2-2024-11-07.json \
  --optical-record data/research/dswx-hls-context-T163-349925-2026-11-07.json \
  --catalog-screen-record data/research/dswx-hls-screen-T163-349925-2026-11-07.json \
  --spatial-support-record data/research/opera-rtc-dswx-spatial-support-T163-349925-VV-2026-11-08.json \
  --polarization-vh-pair-record data/research/opera-rtc-live-pair-T163-349925-IW2-VH-2024-11-08.json \
  --polarization-vh-spatial-support-record data/research/opera-rtc-dswx-spatial-support-T163-349925-VH-2026-11-08.json \
  --polarization-sensitivity-record data/research/opera-rtc-polarization-sensitivity-T163-349925-2026-11-08.json \
  --gpm-before-record data/research/gpm-imerg-context-T163-349925-before-2024-05-08.json \
  --gpm-after-record data/research/gpm-imerg-context-T163-349925-before-2024-06-01.json \
  --gpm-intervening-record data/research/gpm-imerg-context-T163-349925-between-2024-05-08-06-01.json \
  --gpm-interacquisition-record data/research/gpm-imerg-interacquisition-T163-349925-2024-05-08-06-01.json \
  --smap-screen-record data/research/smap-sentinel-soil-moisture-screen-T163-349925-2026-11-08.json \
  --smap-radiometer-screen-record data/research/smap-radiometer-candidate-screen-T163-349925-2026-11-08.json \
  --hls-vegetation-record data/research/hls-l30-vegetation-screen-T163-349925-2026-11-08.json \
  --hls-association-record data/research/hls-l30-rtc-ndvi-association-T163-349925-2026-11-08.json \
  --guaiba-context-record data/research/ana-guaiba-official-flood-stage-context-2026-11-08.json \
  --case-id rio-grande-do-sul-t163-349925-diagnostic-2024 \
  --output data/research/opera-rtc-cross-sensor-investigation-T163-349925-2026-11-08.json
```

This contract improves the definition of a useful next observation. It does not retrieve new data, rank possible observations, validate the diagnostic pair, or resolve the physical cause.
